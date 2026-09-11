#!/usr/bin/env python3
"""Shared-bag mandatory hooks and completion-safe reduced horizontal bases."""
from collections import Counter, defaultdict
from functools import lru_cache
import json
from pathlib import Path
import time
from seven_tail import common as V

ROOT=Path(__file__).resolve().parents[1]


class Completion:
    def __init__(self,lex,record,check_columns=False,bag_rows=False,on_board=None):
        self.lex=lex;self.record=record
        assert record['row']==1 and record['start_col']==1 and record['word']==V.MAIN_WORD
        self.meta=dict(row=1,start=1,indices=tuple(i-1 for i in record['indices']),word=record['word'])
        rec=tuple((o['word'],o['face_score'],o['start_row'],o['index']+1) for o in record['crosses'])
        self.fixed,self.forb=V.scoring_skeleton(self.meta,rec)
        self.base=Counter(record['word'])
        for w,_,_,_ in rec:self.base.update(w[1:])
        self.base=tuple(self.base[a] for a in V.LETTERS)
        old=sorted(self.fixed[1]);self.groups=[]
        for c in old:
            if not self.groups or c!=self.groups[-1][-1]+1:self.groups.append([])
            self.groups[-1].append(c)
        self.boards={};self.hook_leaves=0
        self.column_checker=None
        self.bag_rows=bag_rows
        self.on_board=on_board
        if check_columns:
            from repair_six_upper import LineCompletion
            self.column_checker=LineCompletion(lex.legal)

    def columns_possible(self,board,forbidden):
        if self.column_checker is None:return True
        for c in range(15):
            pattern=''.join(board.get((r,c),'#' if forbidden[r+1]&(1<<c) else '.') for r in range(15))
            if not self.column_checker.possible(pattern):return False
        return True

    @staticmethod
    def feasible(counts):
        return sum(counts)<=100 and V.excess_blanks(counts)<=2

    @lru_cache(maxsize=200000)
    def row_bag_possible(self,required_items,forbidden,counts):
        required=dict(required_items)
        for first,last,_,legal in V.forced_clusters(required,self.lex):
            if legal:continue
            found=False
            for start in range(first+1):
                if start and start-1 in required:continue
                for end in range(last,15):
                    if end<14 and end+1 in required:continue
                    length=end-start+1
                    if forbidden&(((1<<length)-1)<<start):continue
                    pattern=tuple((c-start,required[c]) for c in sorted(required) if start<=c<=end)
                    mask=self.lex.matching_mask(length,pattern)
                    while mask:
                        bit=mask&-mask;mask-=bit;w=self.lex.bylen[length][bit.bit_length()-1]
                        added=Counter(ch for i,ch in enumerate(w,start) if i not in required)
                        total=tuple(counts[i]+added[a] for i,a in enumerate(V.LETTERS))
                        if self.feasible(total):found=True;break
                    if found:break
                if found:break
            if not found:return False
        return True

    def rows_possible(self,fixed,forbidden,counts):
        if not V.globally_horizontally_completable(self.lex,fixed,forbidden,counts)[0]:return False
        if not self.bag_rows:return True
        # Each forced nonword may use the entire remaining bag independently.
        return all(self.row_bag_possible(tuple(sorted(fixed[r].items())),forbidden[r],counts) for r in range(1,16))

    def row_options(self,required,forbidden,base,max_add):
        if any((forbidden>>c)&1 for c in required):return []
        clusters=V.forced_clusters(required,self.lex);bad={i for i,x in enumerate(clusters) if not x[3]}
        if not bad:return [((0,)*26,())]
        candidates=defaultdict(list)
        for bi in bad:
            bs,be,_,_=clusters[bi]
            for start in range(bs+1):
                if start>0 and start-1 in required:continue
                for end in range(be,15):
                    if end<14 and end+1 in required:continue
                    length=end-start+1
                    if forbidden&(((1<<length)-1)<<start):continue
                    pattern=tuple((c-start,required[c]) for c in sorted(required) if start<=c<=end)
                    mask=self.lex.matching_mask(length,pattern)
                    covered=frozenset(i for i,(a,b,_,_) in enumerate(clusters) if start<=a and b<=end)
                    while mask:
                        bit=mask&-mask;mask-=bit;w=self.lex.bylen[length][bit.bit_length()-1]
                        additions=tuple((start+j,ch) for j,ch in enumerate(w) if start+j not in required)
                        count=Counter(ch for _,ch in additions);vector=tuple(count[a] for a in V.LETTERS)
                        if len(additions)<=max_add and self.feasible(V.add_count_tuple(base,vector)):
                            candidates[bi].append((start,end,vector,additions,covered))
        results={}
        def dfs(remaining,intervals,counts,additions):
            if not remaining:
                results[tuple(sorted(additions))]=(counts,tuple(sorted(additions)));return
            bi=min(remaining)
            for start,end,vector,adds,covered in candidates[bi]:
                if any(not(end+1<a or b+1<start) for a,b in intervals):continue
                nc=V.add_count_tuple(counts,vector)
                if sum(nc)>max_add or not self.feasible(V.add_count_tuple(base,nc)):continue
                dfs(remaining-covered,intervals+((start,end),),nc,additions+adds)
        dfs(bad,(),(0,)*26,())
        return list(results.values())

    def horizontal_bases(self,fixed,forbidden,base,hooks):
        rows=[]
        for r in range(2,16):
            options=self.row_options(fixed[r],forbidden[r],base,100-sum(base))
            if not options:return
            if not(len(options)==1 and not options[0][1]):rows.append((r,options))
        rows.sort(key=lambda item:len(item[1]))
        forced={(r-1,c):a for r in range(1,16) for c,a in fixed[r].items()}
        def dfs(i,counts,board):
            if not self.columns_possible(board,forbidden):return
            if i==len(rows):
                lines=tuple(''.join(board.get((r,c),'.') for c in range(15)) for r in range(15))
                if lines not in self.boards:
                    item=dict(rows=lines,hooks=hooks,modeled_total_count=sum(counts),
                              excess_blanks=V.excess_blanks(counts),tiles_pre=len(board))
                    self.boards[lines]=item
                    if self.on_board:self.on_board(item)
                return
            r,options=rows[i]
            for vector,adds in options:
                nc=V.add_count_tuple(counts,vector)
                if self.feasible(nc):dfs(i+1,nc,board|{(r-1,c):a for c,a in adds})
        dfs(0,base,forced)

    def run(self):
        domains=[]
        for group in self.groups:
            domain=[]
            for c in group:
                for word in V.individual_hook_domain(self.lex,self.fixed,self.forb,c,V.MAIN_WORD[c]):
                    count=Counter(word[1:]);vector=tuple(count[a] for a in V.LETTERS)
                    if not self.feasible(V.add_count_tuple(self.base,vector)):continue
                    added=V.add_hook(self.fixed,self.forb,c,word)
                    if added and self.rows_possible(*added,V.add_count_tuple(self.base,vector)):
                        domain.append((c,word,vector))
            domains.append(domain)
        order=sorted(range(len(domains)),key=lambda i:len(domains[i]))
        def dfs(depth,fixed,forbidden,counts,hooks):
            if depth==len(order):
                self.hook_leaves+=1
                self.horizontal_bases(fixed,forbidden,counts,hooks);return
            for c,w,vector in domains[order[depth]]:
                nc=V.add_count_tuple(counts,vector)
                if not self.feasible(nc):continue
                added=V.add_hook(fixed,forbidden,c,w)
                if added and self.rows_possible(*added,nc):
                    dfs(depth+1,*added,nc,hooks+((c,w),))
        dfs(0,self.fixed,self.forb,self.base,())
        return [dict(item,id=i+1) for i,(_,item) in enumerate(sorted(self.boards.items()))]


def main():
    records=json.loads((ROOT/'output/seven_completion_stage1.json').read_text())['records']
    lex=V.Lexicon(ROOT/'output/NWL23_words.txt')
    folder=ROOT/'output/seven_hooks';folder.mkdir(exist_ok=True)
    reports=[];start=time.monotonic()
    for record in records:
        solver=Completion(lex,record);boards=solver.run()
        stem=f"rank{record['rank']}_record{record['record']}"
        (folder/f'{stem}.json').write_text(json.dumps(boards,indent=2,sort_keys=True)+'\n')
        report=dict(rank=record['rank'],record=record['record'],hook_leaves=solver.hook_leaves,bases=len(boards))
        reports.append(report)
        (folder/'summary.json').write_text(json.dumps(dict(reports=reports,complete=len(reports)==len(records)),indent=2)+'\n')
        print(report,'seconds',round(time.monotonic()-start,1),flush=True)


if __name__=='__main__':main()

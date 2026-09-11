#!/usr/bin/env python3
"""Necessary, completion-safe tests; surviving patterns need not be legal."""
import argparse
from collections import defaultdict,Counter
import json
from pathlib import Path
from check_seven_products import read_products
from repair_six_upper import LineCompletion,pattern_board,bad_rows

ROOT=Path(__file__).resolve().parents[1]


def screen(words,records,counts_only=False,progress=None):
    completion=LineCompletion(words)
    hooks=defaultdict(list)
    for w in sorted(words):
        if 2<=len(w)<=15:
            hooks[1,w[0]].append(w)
            hooks[15,w[-1]].append(w)
    rejected=Counter() if counts_only else [];remaining=[]
    for number,record in enumerate(records,1):
        board,blocked=pattern_board(record)
        reason=None;detail=None
        if (8,8) in blocked:
            reason='centre forced empty'
        elif bad:=bad_rows(board,blocked,completion):
            reason='uncompletable row';detail=bad
        elif record['row'] in (1,15):
            edge=record['row'];step=1 if edge==1 else -1
            new={(edge,record['start_col']+i-1) for i in record['indices']}
            old={p:ch for p,ch in board.items() if p not in new}
            for (r,c),ch in sorted(old.items()):
                if r!=edge or (r,c-1) in old or (r,c+1) in old:continue
                possible=False
                for word in hooks[edge,ch]:
                    hook=word if step==1 else word[::-1]
                    addition={(edge+step*i,c):a for i,a in enumerate(hook)}
                    if any(p in blocked or p in board and board[p]!=a for p,a in addition.items()):continue
                    end=(edge+step*len(hook),c)
                    if end in board:continue
                    barriers=blocked|({end} if 1<=end[0]<=15 else set())
                    if not bad_rows(board|addition,barriers,completion):possible=True;break
                if not possible:
                    reason='mandatory singleton hook impossible'
                    detail=dict(cell=[r,c],letter=ch,candidates=len(hooks[edge,ch]));break
        if reason:
            if counts_only:rejected[reason]+=1
            else:rejected.append(dict(rank=record['rank'],record=record['record'],score=record['score'],
                                     reason=reason,detail=detail))
        else:remaining.append(record)
        if progress and number%10000==0:progress(number,len(remaining))
    return rejected,remaining


def main():
    ap=argparse.ArgumentParser();ap.add_argument('lexicon');ap.add_argument('k',type=int)
    ap.add_argument('--upper',type=Path);ap.add_argument('--resource-dir',type=Path)
    ap.add_argument('--output',type=Path);a=ap.parse_args()
    words,records=read_products(a.lexicon,a.k,a.resource_dir,a.upper,stream=True)
    counts,remaining=screen(words,records,counts_only=True,
                            progress=lambda n,m:print('Verified',n,'products;',m,'survivors',flush=True))
    out=dict(products=sum(counts.values())+len(remaining),remaining=remaining,
             remaining_count=len(remaining),reasons=dict(counts),complete=True)
    target=a.output or ROOT/'output'/f'{a.lexicon}_k{a.k}_screened.json'
    target.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print('Products',out['products'],'remaining',len(remaining),'reasons',out['reasons'])
    if remaining:print('Largest unresolved score',max(r['score'] for r in remaining))


if __name__=='__main__':main()

#!/usr/bin/env python3
"""Bounded constructive reverse search; failure is never an upper proof."""
import argparse
from collections import Counter
import itertools
import json
from pathlib import Path
import time
from seven_tail.common import MAIN_WORD,REAL_BAG,LETTERS
from seven_tail.verify_record74_completion import word_legal,components

ROOT=Path(__file__).resolve().parents[1]
ROWS=['.X..HEN.UTA.ON.','PEAR.DORR..OB.J','ADRED..AE..O..A',
      'C.AQUILINE.G..C','I.KUE.INTREAT.U','F.SAL..W...M..L',
      'Y..L...A...E..A','I..I...S...TOOT','N..F...H...E..I',
      'G..I...I...S..O','...E...N......N','...D...G......S',
      '...............','...............','...............']


def find_history(rows,indices,seconds=0):
    legal=set((ROOT/'output/CSW24_words.txt').read_text().split())
    board={(r,c):ch for r,row in enumerate(rows) for c,ch in enumerate(row) if ch!='.'}
    assert len(rows)==15 and all(len(row)==15 for row in rows)
    assert word_legal(board,legal) and len(components(board))==1
    assert all((0,i) not in board for i in indices)
    final=board|{(0,i):MAIN_WORD[i] for i in indices}
    counts=Counter(final.values());excess={ch:max(0,counts[ch]-n) for ch,n in zip(LETTERS,REAL_BAG)}
    assert sum(excess.values())<=2 and len(final)<=100
    print('Connected legal target:',len(final),'tiles; excess', {c:n for c,n in excess.items() if n},flush=True)
    positions=sorted(board);index={p:i for i,p in enumerate(positions)}
    neighbors=[]
    for r,c in positions:
        neighbors.append(sum(1<<index[p] for p in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)) if p in index))
    center=1<<index[(7,7)];all_mask=(1<<len(positions))-1
    began=time.monotonic();visited=set();nodes=0;best=len(board)

    def connected(mask):
        if not mask:return True
        seen=front=mask&-mask
        while front:
            expanded=0
            while front:
                b=front&-front;front-=b;expanded|=neighbors[b.bit_length()-1]
            front=expanded&mask&~seen;seen|=front
        return seen==mask

    def line_words(mask):
        for direction,(dr,dc) in enumerate(((0,1),(1,0))):
            for i,(r,c) in enumerate(positions):
                if not(mask>>i&1):continue
                previous=index.get((r-dr,c-dc))
                if previous is not None and mask>>previous&1:continue
                cells=[];rr,cc=r,c
                while (rr,cc) in index and mask>>index[rr,cc]&1:
                    cells.append(index[rr,cc]);rr+=dr;cc+=dc
                if len(cells)>1:yield direction,cells,''.join(board[positions[j]] for j in cells)

    def fragments_ok(word,removed):
        start=0
        for j in range(len(word)+1):
            if j==len(word) or j in removed:
                if j-start>1 and word[start:j] not in legal:return False
                start=j+1
        return True

    def dfs(mask,path):
        nonlocal nodes,best
        if seconds and time.monotonic()-began>seconds:raise TimeoutError
        if mask in visited:return None
        visited.add(mask);nodes+=1
        size=mask.bit_count()
        if size<best:
            best=size;print('Remaining',size,'nodes',nodes,'seconds',round(time.monotonic()-began,2),flush=True)
        words=list(line_words(mask))
        if size<=7:
            for direction,cells,w in words:
                if len(cells)==size and w in legal:
                    return path+[dict(orientation='H' if direction==0 else 'V',word=w,
                                      start=positions[cells[0]],removed=[positions[i] for i in cells])]
        perpendicular={}
        for direction,cells,w in words:
            for j,i in enumerate(cells):
                perpendicular[1-direction,i]=fragments_ok(w,{j})
        candidates=[]
        for direction,cells,w in words:
            eligible=[j for j,i in enumerate(cells) if (1<<i)!=center and perpendicular.get((direction,i),True)]
            for n in range(min(7,len(eligible)),0,-1):
                if not path and n!=7:continue
                for removed in itertools.combinations(eligible,n):
                    if not fragments_ok(w,set(removed)):continue
                    bits=sum(1<<cells[j] for j in removed)
                    rest=mask^bits
                    if not connected(rest):continue
                    candidates.append((-n,direction,cells,w,removed,rest))
        candidates.sort(key=lambda x:x[0])
        for _,direction,cells,w,removed,rest in candidates:
            item=dict(orientation='H' if direction==0 else 'V',word=w,
                      start=positions[cells[0]],removed=[positions[cells[j]] for j in removed])
            result=dfs(rest,path+[item])
            if result:return result
        return None
    try:
        reverse=dfs(all_mask,[]);status='history found' if reverse else 'chosen target exhausted'
    except TimeoutError:reverse=None;status='timed out; no impossibility claim'
    out=dict(status=status,nodes=nodes,smallest_remaining=best,seconds=time.monotonic()-began,
             rows=rows,final_tile_count=len(final),excess=excess,
             forward_history=list(reversed(reverse)) if reverse else None)
    print(status,flush=True)
    return out


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seconds',type=int,default=30,help='Zero means unlimited')
    a=ap.parse_args()
    if a.seconds<0:ap.error('Time budget cannot be negative')
    out=find_history(ROWS,(0,2,3,7,11,14),a.seconds)
    target=ROOT/'output/CSW24_k6_history_candidate.json'
    target.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')


if __name__=='__main__':main()

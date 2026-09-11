#!/usr/bin/env python3
"""Propose rational resource bounds; only the integer certificate is trusted.

With letter prices p>=0, option counts a, scores s and main counts m,
  actual score <= main + p.(B-m) + sum_j max_o(s_jo-p.a_jo)
                         + 2 max(0,max_a(p_a-v_a)).
Each forced blank costs at least its letter value. The last term allows two
blanks at whichever letters are most advantageous. Dropping all compatibility
constraints makes this a safe relaxation. No floating-point inequality prunes.
"""
import argparse
import hashlib
from pathlib import Path
import json
import subprocess
import time

import search_five_tile as base
from export_six_survivor_products import export_instance, parse_survivors
from verify_1786 import TILE_DISTRIBUTION, LETTER_VALUES

ROOT = Path(__file__).resolve().parents[1]
LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'


def certify(main, slots, prices, scale=1024):
    assert isinstance(scale,int) and scale>0
    assert len(prices)==26 and all(isinstance(p,int) and p>=0 for p in prices)
    blank = max([0]+[prices[i]-scale*LETTER_VALUES[a] for i,a in enumerate(LETTERS)])
    upper = scale*main.face_score + 2*blank
    upper += sum(prices[i]*(TILE_DISTRIBUTION[a]-base.count_tuple(main.word)[i]) for i,a in enumerate(LETTERS))
    tops=[]
    for slot in slots:
        tops.append(max(scale*o.face_score-sum(p*n for p,n in zip(prices,o.counts_without_new)) for o in slot))
    return upper+sum(tops)


def propose(main, slots):
    import numpy as np
    from scipy.optimize import linprog
    from scipy.sparse import coo_matrix
    k=len(slots)
    objective=np.array([TILE_DISTRIBUTION[a]-base.count_tuple(main.word)[i] for i,a in enumerate(LETTERS)]+[1]*k+[2],float)
    rr,cc,vv,rhs=[],[],[],[]
    for j,slot in enumerate(slots):
        for o in slot:
            r=len(rhs)
            for a,n in enumerate(o.counts_without_new):
                if n:rr.append(r);cc.append(a);vv.append(-n)
            rr.append(r);cc.append(26+j);vv.append(-1)
            rhs.append(-o.face_score)
    for i,a in enumerate(LETTERS):
        r=len(rhs);rr.extend([r,r]);cc.extend([i,26+k]);vv.extend([1,-1]);rhs.append(LETTER_VALUES[a])
    matrix=coo_matrix((vv,(rr,cc)),shape=(len(rhs),27+k)).tocsr()
    sol=linprog(objective,A_ub=matrix,b_ub=rhs,bounds=[(0,None)]*26+[(None,None)]*k+[(0,None)],method='highs')
    assert sol.success, sol.message
    prices=[max(0,round(x*1024)) for x in sol.x[:26]]
    return prices,certify(main,slots,prices)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('lexicon',choices=['NWL23','CSW24'])
    ap.add_argument('k',type=int)
    ap.add_argument('--run',action='store_true')
    ap.add_argument('--seconds-per-rank',type=int,default=120,help='Per-rank timeout; 0 means no limit')
    ap.add_argument('--upper',type=Path,help='Alternate scan input for an isolated experiment')
    ap.add_argument('--output-dir',type=Path,help='Alternate certificate directory')
    ap.add_argument('--total-seconds',type=float,help='Pilot budget; an unfinished prefix is explicitly incomplete')
    args=ap.parse_args();base.NEW_TILE_COUNT=args.k
    upper=args.upper or ROOT/'output'/f'{args.lexicon}_k{args.k}_upper.txt'
    meta={s.split()[0]:int(s.split()[1]) for s in upper.read_text().splitlines() if not s.startswith('top ')}
    survivors=parse_survivors(upper,meta['threshold'])
    assert len(survivors)==meta['independent_upper_at_least_threshold']
    words=set((ROOT/'output'/f'{args.lexicon}_words.txt').read_text().splitlines())
    crosses=base.build_cross_occurrences(words)
    folder=args.output_dir or ROOT/'output/resource'/f'{args.lexicon}_k{args.k}'
    folder.mkdir(parents=True,exist_ok=True)
    reports=[];started=time.monotonic()
    inputs=dict(upper=hashlib.sha256(upper.read_bytes()).hexdigest(),
                words=hashlib.sha256((ROOT/'output'/f'{args.lexicon}_words.txt').read_bytes()).hexdigest())
    (folder/'summary.json').write_text(json.dumps(dict(metadata=meta,input_sha256=inputs,reports=[],complete=not survivors),indent=2)+'\n')
    for s in survivors:
        remaining=None if args.total_seconds is None else args.total_seconds-(time.monotonic()-started)
        if remaining is not None and remaining<=0:
            print('Pilot budget reached; remaining ranks not searched.',flush=True)
            break
        occ=base.Occurrence(s['word'],tuple(i-1 for i in s['indices']),base.score_of(s['word']),base.count_tuple(s['word']))
        m=base.main_placement_from_occurrence(occ,s['row'],s['start_col'])
        slots=[base.cross_options_for(crosses,a,p) for a,p in zip(m.letters,m.new_cells)]
        prices,u=propose(m,slots)
        pricefile=folder/f"rank{s['rank']}.prices"
        pricefile.write_text('1024\n'+' '.join(map(str,prices))+'\n')
        instance=export_instance(s,crosses,initial_best=meta['threshold'],output_path=folder/f"rank{s['rank']}.txt")
        report=dict(s,price_scale=1024,prices=prices,resource_upper_numerator=u,integer_upper=u//1024,
                    status='resource excluded' if u<1024*meta['threshold'] else 'search pending')
        if args.run and report['status']=='search pending':
            result=folder/f"rank{s['rank']}_result.txt"
            try:
                timeout=args.seconds_per_rank or None
                if args.total_seconds is not None:
                    remaining=max(.1,args.total_seconds-(time.monotonic()-started))
                    timeout=remaining if timeout is None else min(timeout,remaining)
                with result.open('w') as stream:
                    subprocess.run([str(ROOT/'tmp/exact_product_search'),str(instance),'0','--all',str(pricefile)],stdout=stream,
                                   timeout=timeout,check=True)
                report['status']='products enumerated'
                report['records']=sum(l.startswith('record ') for l in result.read_text().splitlines())
            except subprocess.TimeoutExpired:
                report['status']='timed out; incomplete'
        reports.append(report)
        complete=(len(reports)==len(survivors) and
                  all(r['status'] in ('resource excluded','products enumerated') for r in reports))
        (folder/'summary.json').write_text(json.dumps(dict(metadata=meta,input_sha256=inputs,reports=reports,complete=complete),indent=2)+'\n')
        print(f"{args.lexicon} k={args.k} rank={s['rank']}: U={u/1024:.3f}, {report['status']} ({time.monotonic()-started:.1f}s)",flush=True)


if __name__=='__main__':main()

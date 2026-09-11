#!/usr/bin/env python3
"""Replay the complete CSW24 seven-tile exclusion above 1787, without caps."""
import hashlib
import json
from pathlib import Path
from check_seven_products import read_products
from screen_scoring_products import screen
from complete_seven_hooks import Completion
from seven_tail.common import Lexicon

ROOT=Path(__file__).resolve().parents[1]


def main():
    summary=json.loads((ROOT/'output/resource/CSW24_k7/summary.json').read_text())
    assert summary['complete'] and summary['metadata']['threshold']==1738
    words,records=read_products('CSW24',7,stream=True)
    rejected,remaining=screen(words,records,counts_only=True,
        progress=lambda n,m:print('Verified products',n,'survivors',m,flush=True))
    lex=Lexicon(ROOT/'output/CSW24_words.txt')
    reports=[]
    for record in remaining:
        solver=Completion(lex,record,check_columns=True,bag_rows=True)
        bases=solver.run()
        assert not bases,(record['rank'],record['record'],len(bases))
        report=dict(rank=record['rank'],record=record['record'],pre_bingo_score=record['score'],
                    hook_leaves=solver.hook_leaves,bases=0)
        reports.append(report);print(report,flush=True)
    paths=['data/CSW24.kwg','output/CSW24_words.txt','output/CSW24_k7_upper.txt',
           'output/resource/CSW24_k7/summary.json']
    out=dict(upper_bound=1787,pre_bingo_exclusion_threshold=1738,
             products=sum(rejected.values())+len(remaining),initial_rejections=dict(rejected),
             completion_exclusions=reports,remaining=0,
             input_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths})
    target=ROOT/'output/CSW24_k7_verified_upper.json'
    target.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print('VERIFIED M7(CSW24) <= 1787. Attainment must be checked separately.',flush=True)


if __name__=='__main__':main()

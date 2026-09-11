#!/usr/bin/env python3
"""Recheck the finite, completion-safe CSW24 six-tile bound of 1721."""
import hashlib
import json
from pathlib import Path
from check_seven_products import read_products
from screen_scoring_products import screen
from complete_seven_hooks import Completion
from seven_tail.common import Lexicon

ROOT=Path(__file__).resolve().parents[1]


def main():
    summary=json.loads((ROOT/'output/resource/CSW24_k6/summary.json').read_text())
    assert summary['complete'] and summary['metadata']['threshold']==1722
    words,records=read_products('CSW24',6)
    rejected,remaining=screen(words,records)
    lex=Lexicon(ROOT/'output/CSW24_words.txt')
    reports=[]
    for record in remaining:
        solver=Completion(lex,record,check_columns=True,bag_rows=True)
        bases=solver.run()
        assert not bases,(record['rank'],record['record'],len(bases))
        reports.append(dict(rank=record['rank'],record=record['record'],score=record['score'],bases=0))
    out=dict(upper_bound=1721,exclusion_threshold=1722,products=len(records),
             initial_rejections=len(rejected),completion_exclusions=reports,remaining=0,
             kwg_sha256=hashlib.sha256((ROOT/'data/CSW24.kwg').read_bytes()).hexdigest())
    (ROOT/'output/CSW24_k6_verified_upper.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print('VERIFIED: M6(CSW24) <= 1721;',len(records),'products,',len(remaining),'shared-bag exclusions.')


if __name__=='__main__':main()

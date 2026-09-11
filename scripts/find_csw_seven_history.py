#!/usr/bin/env python3
"""Uncapped constructive history search for a saved connected CSW24 candidate."""
import argparse
import hashlib
import json
from pathlib import Path
from find_csw_six_history import find_history

ROOT=Path(__file__).resolve().parents[1]
ROWS=['..Y.HEN.UT..ON.','PEAR.RORT.MOO.J','ADDEEM.A.REO..A',
      'C..Q..DIVULGE.C','I..U...N.BIAS.U','F..A...W..OM..L',
      'Y..L...A..RE..A','I..I...S..AT..T','N..F...H..TETRI',
      'G..I...I..IS..O','...E...N..V...N','...D...G..E...S',
      '...............','...............','...............']


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--candidate',type=Path,help='Optional discovery output; the default is the fixed published witness')
    ap.add_argument('--seconds',type=int,default=0,help='Zero means unlimited')
    a=ap.parse_args()
    if a.seconds<0:ap.error('Time budget cannot be negative')
    candidate=json.loads(a.candidate.read_text()) if a.candidate else dict(rows=ROWS,
        record=dict(word='OXYPHENBUTAZONE',indices=[1,2,4,8,11,12,15]),pre_bingo_score=1737)
    record=candidate['record'];assert record['word']=='OXYPHENBUTAZONE' and len(record['indices'])==7
    result=find_history(candidate['rows'],tuple(i-1 for i in record['indices']),a.seconds)
    result.update(candidate=candidate,candidate_sha256=hashlib.sha256(json.dumps(candidate,sort_keys=True).encode()).hexdigest())
    (ROOT/'output/CSW24_k7_history_candidate.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')


if __name__=='__main__':main()

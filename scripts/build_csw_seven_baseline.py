#!/usr/bin/env python3
"""A regression witness: postpone the X in the six-tile construction."""
import json
from pathlib import Path
from find_csw_six_history import ROWS,find_history
from verify_csw_seven_witness import verify

ROOT=Path(__file__).resolve().parents[1]


def main():
    rows=list(ROWS);assert rows[0][1]=='X'
    rows[0]=rows[0][:1]+'.'+rows[0][2:]
    indices=(0,1,2,3,7,11,14)
    history=find_history(rows,indices)
    assert history['status']=='history found'
    history['candidate']=dict(record=dict(indices=[i+1 for i in indices]),pre_bingo_score=1732)
    folder=ROOT/'output/csw7_baseline';folder.mkdir(exist_ok=True)
    source=folder/'history.json';source.write_text(json.dumps(history,indent=2,sort_keys=True)+'\n')
    out=verify(source,folder/'witness.json')
    assert out['score']==1782


if __name__=='__main__':main()

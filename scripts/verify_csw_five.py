#!/usr/bin/env python3
"""Constructive CSW24 five-tile witness; upper proof is checked separately."""
import json
from pathlib import Path
from verify_small_records import move,verify

ROOT=Path(__file__).resolve().parents[1]
SEQUENCE=[
    move('H','TUTOR',8,8),
    move('H','TUTORIAL',8,8),
    move('V','TIRED',8,10),
    move('H','JUDO',12,8),
    move('V','JAM',12,8),
    move('V','WOOT',11,11),
    move('V','SILVER',6,15),
    move('V','SILVERING',6,15),
    move('V','QUICKSILVERING',1,15),
    move('H','AG',14,14),
    move('H','ENE',15,12),
    move('H','MA',14,8),
    move('H','EN',15,9),
    move('H','YIELDER',10,4),
    move('V','PENNY',6,4),
    move('V','PENNYWORT',6,4),
    move('H','CLAP',6,1),
    move('V','CHONDRI',6,1),
    move('V','HYPOCHONDRIA',2,1),
    move('V','HYPOCHONDRIAS',2,1),
    move('H','SO',14,1),
    move('H','ET',15,2),
    move('H','TI',14,4),
    move('H','OXY',15,5),
]
FINAL=move('H','METHOXYBENZENES',15,1)
BLANKS={(2,1),(10,4)}


def main():
    upper=json.loads((ROOT/'output/CSW24_k5_verified_upper.json').read_text())
    assert upper['upper_bound']==1478 and upper['remaining']==0
    witness=verify('CSW24',5,SEQUENCE,FINAL,BLANKS,1478)
    assert all(h['total']>0 for h in witness['history'])
    witness['upper_certificate']='CSW24_k5_verified_upper.json'
    (ROOT/'output/CSW24_k5_exact.json').write_text(json.dumps(witness,indent=2,sort_keys=True)+'\n')
    print('VERIFIED M5(CSW24) =',witness['score'],witness['final_board_tiles'],'tiles')
    print(witness['history'][-1]['word_scores'])


if __name__=='__main__':main()

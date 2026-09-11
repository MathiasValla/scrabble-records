#!/usr/bin/env python3
"""Check a proposed CSW24 four-tile attainment history, never infer an upper."""
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
    move('H','FORESTER',10,3),
    move('H','DEFORESTER',10,1),
    move('V','HOND',7,1),
    move('V','CHONDRI',6,1),
    move('V','HYPOCHONDRIA',2,1),
    move('V','HYPOCHONDRIAS',2,1),
    move('H','SH',14,1),
    move('H','ETHOXY',15,2),
]
FINAL=move('H','METHOXYBENZENES',15,1)
BLANKS={(2,1),(14,2)}


def main():
    upper=json.loads((ROOT/'output/CSW24_k4_verified_upper.json').read_text())
    assert upper['upper_bound']==1349 and upper['remaining_products']==0
    witness=verify('CSW24',4,SEQUENCE,FINAL,BLANKS,1349)
    assert all(h['total']>0 for h in witness['history'])
    witness['upper_certificate']='CSW24_k4_verified_upper.json'
    (ROOT/'output/CSW24_k4_exact.json').write_text(json.dumps(witness,indent=2,sort_keys=True)+'\n')
    print('VERIFIED M4(CSW24) =',witness['score'],witness['final_board_tiles'],'tiles')
    print(witness['history'][-1]['word_scores'])


if __name__=='__main__':main()

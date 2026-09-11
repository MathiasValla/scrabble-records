#!/usr/bin/env python3
"""Attainment of the exact CSW24 three-tile upper bound, 912."""
import json
from pathlib import Path
from verify_small_records import move,verify
from verify_1786 import Kwg

ROOT=Path(__file__).resolve().parents[1]
SEQUENCE=[
    move('V','BENZENE',8,8),
    move('V','METHOXYBENZENE',1,8),
    move('H','EE',14,7),
    move('H','HIPPER',15,2),
    move('V','SH',14,2),
    move('V','OU',13,1),
    move('V','KABELJOU',7,1),
    move('H','EUTECTIC',9,8),
    move('V','CAT',9,15),
    move('H','ORIENTAL',5,8),
    move('V','ALIF',4,15),
    move('V','QUALIFICATIVE',2,15),
    move('H','AE',14,14),
    move('H','NAPPER',15,9),
]
FINAL=move('H','WHIPPERSNAPPERS',15,1)
BLANKS={(15,4),(15,5)}


def main():
    upper=json.loads((ROOT/'output/CSW24_k3_verified_upper.json').read_text())
    assert upper['upper_bound']==912
    witness=verify('CSW24',3,SEQUENCE,FINAL,BLANKS,912)
    assert all(h['total']>0 for h in witness['history'])
    witness['upper_certificate']='CSW24_k3_verified_upper.json'
    witness['contrasts']={w:{lex:Kwg(ROOT/'data'/f'{lex}.kwg').contains(w) for lex in ['NWL23','CSW24']}
                          for w in ['WHIPPERSNAPPERS','HIPPER','NAPPER','KABELJOU','KABELJOUW','METHOXYBENZENE','METHOXYBENZENES','QUALIFICATIVE','QUALIFICATIVES','EE','OU']}
    (ROOT/'output/CSW24_k3_exact.json').write_text(json.dumps(witness,indent=2,sort_keys=True)+'\n')
    print('VERIFIED: M3(CSW24) = 912;',witness['final_board_tiles'],'tiles, 14 setup moves, full racks and draws.')
    print(witness['history'][-1]['word_scores'])


if __name__=='__main__':main()

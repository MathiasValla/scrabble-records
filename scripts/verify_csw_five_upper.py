#!/usr/bin/env python3
"""Centre-square obstruction for every CSW24 five-tile score above 1478."""
import json
from pathlib import Path
from check_seven_products import read_products
from repair_six_upper import pattern_board

ROOT=Path(__file__).resolve().parents[1]


def main():
    summary=json.loads((ROOT/'output/resource/CSW24_k5/summary.json').read_text())
    assert summary['metadata']['threshold']==1479
    _,records=read_products('CSW24',5)
    reports=[]
    for record in records:
        board,blocked=pattern_board(record)
        assert (8,8) in blocked, (record['rank'],record['record'],record['score'])
        assert (8,8) not in board
        reports.append(dict(rank=record['rank'],record=record['record'],score=record['score'],
                            reason='maximal scored cross forces H8 empty'))
    out=dict(upper_bound=1478,exclusion_threshold=1479,products=len(records),
             independent_survivors=len(summary['reports']),records=reports,remaining=0)
    (ROOT/'output/CSW24_k5_verified_upper.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print('VERIFIED: M5(CSW24) <= 1478;',len(records),'products all force the centre to be empty.')


if __name__=='__main__':main()

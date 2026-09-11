#!/usr/bin/env python3
"""Verify complete CSW24 four-tile exclusions above the 1349 witness."""
import json
from pathlib import Path
from check_seven_products import read_products

ROOT=Path(__file__).resolve().parents[1]
summary=json.loads((ROOT/'output/resource/CSW24_k4/summary.json').read_text())
assert summary['metadata']['threshold']==1350
_,records=read_products('CSW24',4)
assert not records
(ROOT/'output/CSW24_k4_verified_upper.json').write_text(json.dumps(
    dict(upper_bound=1349,exclusion_threshold=1350,remaining_products=0,
         independent_survivors=len(summary['reports']),attainment_verified=False),
    indent=2,sort_keys=True)+'\n')
print('VERIFIED: M4(CSW24) <= 1349; every product at threshold 1350 excluded.')

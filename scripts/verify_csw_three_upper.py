#!/usr/bin/env python3
"""Check the CSW24 three-tile relaxed upper bound, not its attainability."""
import json
from pathlib import Path
from check_seven_products import read_products

ROOT=Path(__file__).resolve().parents[1]
_,records=read_products('CSW24',3)
assert len(records)==11350
best=max(r['score'] for r in records)
assert best==912
(ROOT/'output/CSW24_k3_verified_upper.json').write_text(json.dumps(
    dict(upper_bound=best,products=len(records),attainment_verified=False,
         top_patterns=[r for r in records if r['score']==best]),indent=2,sort_keys=True)+'\n')
print('VERIFIED: M3(CSW24) <= 912; attainment not yet established.')

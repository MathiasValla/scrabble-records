#!/usr/bin/env python3
"""Join the independent CSW24 seven-tile upper and attainment certificates."""
import hashlib
import json
from pathlib import Path
from verify_csw_seven_witness import verify

ROOT=Path(__file__).resolve().parents[1]


def main():
    upper=json.loads((ROOT/'output/CSW24_k7_verified_upper.json').read_text())
    assert upper['upper_bound']==1787 and upper['remaining']==0
    for path,digest in upper['input_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
    witness=verify(ROOT/'output/CSW24_k7_history_candidate.json',ROOT/'output/CSW24_k7_witness.json')
    assert witness['score']==upper['upper_bound']
    witness.update(claim='Exact maximum',upper_certificate='CSW24_k7_verified_upper.json')
    (ROOT/'output/CSW24_k7_exact.json').write_text(json.dumps(witness,indent=2,sort_keys=True)+'\n')
    print('VERIFIED M7(CSW24) = 1787: complete upper exclusion and a legal two-player game.')


if __name__=='__main__':main()

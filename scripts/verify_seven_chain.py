#!/usr/bin/env python3
"""Link all exhaustive seven-tile stages by content, never by record order."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    load=lambda name:json.loads((ROOT/name).read_text())
    stage=load('output/seven_completion_stage1.json')
    assert (stage['products'],stage['after_row_completion'],stage['after_singleton_hooks'])==(3748,255,34)
    hooks=load('output/seven_hooks/summary.json')
    assert hooks['complete']
    assert {(x['rank'],x['record']) for x in hooks['reports']}=={(x['rank'],x['record']) for x in stage['records']}
    remaining=[x for x in hooks['reports'] if x['bases']]
    assert len(remaining)==1 and remaining[0]['bases']==193
    r=remaining[0]
    generated=load(f"output/seven_hooks/rank{r['rank']}_record{r['record']}.json")
    supplied=load('scripts/seven_tail/rec74_horizontal_bases.json')
    canonical=lambda boards:sorted(tuple(x['rows']) for x in boards)
    assert len(set(canonical(generated)))==193
    assert canonical(generated)==canonical(supplied)
    expected_record=stage['records'][next(i for i,x in enumerate(stage['records']) if (x['rank'],x['record'])==(r['rank'],r['record']))]
    import sys
    sys.path.insert(0,str(ROOT/'scripts/seven_tail'))
    import common
    old_record=common.parse_run(ROOT/'scripts/seven_tail/032.txt')[1][73]
    fresh=tuple((x['word'],x['face_score'],x['start_row'],x['index']+1) for x in expected_record['crosses'])
    assert fresh==old_record
    tail=load('output/seven_tail/rec74_reproduced.json')
    assert tail['status']=='OK' and tail['unresolved']==0
    assert [x['board_id'] for x in tail['results']]==list(range(1,194))
    assert tail['surviving_core_assignments']==0
    assert tail['total_core_letter_assignments_checked']==5518820
    assert tail['bases_sha256']==hashlib.sha256((ROOT/'scripts/seven_tail/rec74_horizontal_bases.json').read_bytes()).hexdigest()
    racks=load('output/seven_rack_certificate.json')
    assert racks['status']=='verified' and racks['score']==1786
    out=dict(status='reproduced',lexicon='NWL23',k=7,maximum=1786,
             counts=[1187919660,87,3748,255,34,193,24293,5518820,0],
             canonical_bases_sha256=hashlib.sha256(json.dumps(canonical(generated),separators=(',',':')).encode()).hexdigest(),
             note='Each exhaustive stage must be regenerated for a fresh proof run. This command links their artifacts.')
    (ROOT/'output/seven_chain_verified.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print('VERIFIED CHAIN: NWL23 seven-tile maximum = 1786.')


if __name__=='__main__':main()

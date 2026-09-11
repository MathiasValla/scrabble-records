#!/usr/bin/env python3
"""Reproduce the staged paper's claims from KWG inputs, not stored verdicts."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
EXPECTED={
    'NWL23':'3e74af981fdd974e107283f686da0fe4b7ec84ad0d825d444330c338c33b91ba',
    'CSW24':'62ca7a84f07429a9976f77a4f74b94911aca5d49cce050dce72dd0e032c0566f',
}


def main():
    if not __debug__:
        raise SystemExit('Proof verification requires assertions: do not use python -O or PYTHONOPTIMIZE.')
    parser=argparse.ArgumentParser()
    parser.add_argument('--check-existing',action='store_true',help='Check artifacts and witnesses without repeating exhaustive searches')
    args=parser.parse_args()
    (ROOT/'tmp').mkdir(exist_ok=True)
    logs=ROOT/'output/reproduction/logs'
    logs.mkdir(parents=True,exist_ok=True)
    for name,digest in EXPECTED.items():
        assert hashlib.sha256((ROOT/'data'/f'{name}.kwg').read_bytes()).hexdigest()==digest

    started=time.monotonic()
    state_path=logs.parent/('existing_check_state.json' if args.check_existing else 'run_state.json')
    state=dict(complete=False,started_utc=datetime.now(timezone.utc).isoformat(),
               mode='artifact check only' if args.check_existing else 'fresh exhaustive reproduction',
               python=sys.version,steps=[],
               source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sorted((ROOT/'scripts').rglob('*')) if p.suffix in ('.py','.cpp')})
    def save_state():
        temporary=state_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
        temporary.replace(state_path)
    save_state()

    def run(label,command):
        start=time.monotonic()
        print(f'RUN {label}',flush=True)
        state['current_step']=label
        save_state()
        try:
            with (logs/f'{label}.log').open('w') as stream:
                subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True)
        except BaseException:
            state['failed_step']=label
            save_state()
            raise
        elapsed=time.monotonic()-start
        state['steps'].append(dict(name=label,seconds=round(elapsed,3),
                                  log_sha256=hashlib.sha256((logs/f'{label}.log').read_bytes()).hexdigest()))
        save_state()
        print(f'OK {label} ({elapsed:.1f}s)',flush=True)

    if not args.check_existing:
        run('compile_scan',['c++','-O3','-std=c++17','scripts/scan_k_upper.cpp','-o','tmp/scan_k_upper'])
        run('compile_products',['c++','-O3','-std=c++17','scripts/exact_product_search.cpp','-o','tmp/exact_product_search'])
        for name in EXPECTED:
            run(f'export_{name}',[sys.executable,'scripts/export_words.py',name])
        run('one_tile',[sys.executable,'scripts/verify_one_tile.py'])
        for name,k,threshold in [('NWL23',2,459),('CSW24',2,459),('NWL23',3,883),('NWL23',4,1131),
                                 ('NWL23',5,1402),('NWL23',6,1724),('NWL23',7,1737),('CSW24',3,883),
                                 ('CSW24',4,1350),('CSW24',5,1479),('CSW24',6,1722),('CSW24',7,1738)]:
            run(f'scan_{name}_{k}',['tmp/scan_k_upper',f'output/{name}_words.txt',str(k),str(threshold),f'output/{name}_k{k}_upper.txt'])
        for name,k in [('NWL23',2),('CSW24',2),('NWL23',6)]:
            run(f'products_{name}_{k}',[sys.executable,'scripts/reproduce_k_products.py',name,str(k)])
        for k in (3,4,5):
            run(f'cpp_products_NWL23_{k}',[sys.executable,'scripts/run_k_cpp_products.py',str(k)])
        run('six_completion',[sys.executable,'scripts/repair_six_upper.py'])
        run('adversarial_tests',[sys.executable,'scripts/test_record_bounds.py'])
        run('seven_resource_products',[sys.executable,'scripts/resource_prices.py','NWL23','7','--run','--seconds-per-rank','0'])
        run('seven_product_checks',[sys.executable,'scripts/check_seven_products.py'])
        run('seven_shared_hooks',[sys.executable,'scripts/complete_seven_hooks.py'])
        run('seven_tail',[sys.executable,'scripts/seven_tail/verify_all.py','--skip-enumeration',
                          '--words',str(ROOT/'output/NWL23_words.txt'),'--output','output/seven_tail/rec74_reproduced.json'])
        run('seven_completeness_tests',[sys.executable,'scripts/test_seven_completeness.py'])
        run('csw_three_products',[sys.executable,'scripts/resource_prices.py','CSW24','3','--run','--seconds-per-rank','0'])
        run('csw_three_upper',[sys.executable,'scripts/verify_csw_three_upper.py'])
        run('csw_four_products',[sys.executable,'scripts/resource_prices.py','CSW24','4','--run','--seconds-per-rank','0'])
        run('csw_four_upper',[sys.executable,'scripts/verify_csw_four_upper.py'])
        run('csw_five_products',[sys.executable,'scripts/resource_prices.py','CSW24','5','--run','--seconds-per-rank','0'])
        run('csw_five_upper',[sys.executable,'scripts/verify_csw_five_upper.py'])
        run('csw_six_products',[sys.executable,'scripts/resource_prices.py','CSW24','6','--run','--seconds-per-rank','0'])
        run('csw_six_upper',[sys.executable,'scripts/verify_csw_six_upper.py'])
        run('csw_seven_products',[sys.executable,'scripts/resource_prices.py','CSW24','7','--run','--seconds-per-rank','0'])
        run('csw_seven_upper',[sys.executable,'scripts/verify_csw_seven_upper.py'])
    run('small_witnesses',[sys.executable,'scripts/verify_small_records.py'])
    run('csw_three_witness',[sys.executable,'scripts/verify_csw_three.py'])
    run('csw_four_witness',[sys.executable,'scripts/verify_csw_four.py'])
    run('csw_five_witness',[sys.executable,'scripts/verify_csw_five.py'])
    run('csw_six_history',[sys.executable,'scripts/find_csw_six_history.py','--seconds','0'])
    run('csw_six_witness',[sys.executable,'scripts/verify_csw_six.py'])
    run('csw_seven_baseline',[sys.executable,'scripts/build_csw_seven_baseline.py'])
    run('csw_seven_witness_tests',[sys.executable,'scripts/test_csw_seven_witness.py'])
    run('csw_seven_history',[sys.executable,'scripts/find_csw_seven_history.py'])
    run('csw_seven_witness',[sys.executable,'scripts/verify_csw_seven.py'])
    run('seven_racks',[sys.executable,'scripts/verify_seven_racks.py'])
    run('seven_chain',[sys.executable,'scripts/verify_seven_chain.py'])
    from search_one_tile import iter_words
    from verify_1786 import Kwg
    for name in EXPECTED:
        words=set((ROOT/'output'/f'{name}_words.txt').read_text().splitlines())
        assert words=={w for w in iter_words(Kwg(ROOT/'data'/f'{name}.kwg')) if w.isalpha()}
    import verify_three_tile,verify_four_tile,verify_five_tile,verify_six_tile
    larger={}
    for k,module,expected in [(3,verify_three_tile,882),(4,verify_four_tile,1130),
                              (5,verify_five_tile,1401),(6,verify_six_tile,1723)]:
        witness=module.verify_construction()
        assert witness['score']==expected
        assert sum(ch!='.' for row in witness['final_board'] for ch in row)<=86
        if k<6:
            result=json.loads((ROOT/'output'/f'NWL23_k{k}_cpp_exclusion.json').read_text())
            assert result['remaining']==0
            assert result['metadata']['threshold']==expected+1
            assert len(result['summaries'])==result['metadata']['independent_upper_at_least_threshold']
            for item in result['summaries']:
                assert not any(line.startswith('record ') for line in (ROOT/item['output']).read_text().splitlines())
        else:
            result=json.loads((ROOT/'output/NWL23_k6_completion_safe.json').read_text())
            assert result['remaining']==0 and len(result['records'])==20
        larger[str(k)]=witness
    csw_seven=json.loads((ROOT/'output/CSW24_k7_verified_upper.json').read_text())
    assert csw_seven['upper_bound']==1787 and csw_seven['remaining']==0
    for path,digest in csw_seven['input_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
    output=dict(exact={'NWL23':{'1':213,'2':459,'3':882,'4':1130,'5':1401,'6':1723,'7':1786},
                       'CSW24':{'1':225,'2':483,'3':912,'4':1349,'5':1478,'6':1721,'7':1787}},
                pending=[],
                larger_witnesses=larger,kwg_sha256=EXPECTED,
                mode='artifact check only' if args.check_existing else 'fresh exhaustive reproduction')
    name='reproduction_existing_checked.json' if args.check_existing else 'reproduction_verified.json'
    destination=ROOT/'output'/name
    temporary=destination.with_suffix('.tmp')
    temporary.write_text(json.dumps(output,indent=2,sort_keys=True)+'\n')
    temporary.replace(destination)
    state.update(complete=True,current_step=None,finished_utc=datetime.now(timezone.utc).isoformat(),
                 elapsed_seconds=round(time.monotonic()-started,3),
                 result_sha256=hashlib.sha256(destination.read_bytes()).hexdigest())
    save_state()
    print('VERIFIED: all fourteen exact maxima, NWL23 and CSW24 k=1..7.',flush=True)


if __name__=='__main__':
    main()

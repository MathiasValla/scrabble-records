#!/usr/bin/env python3
"""Export the proof/build dependency closure, never the whole research workspace."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
ENTRY_POINTS = '''reproduce_release export_words verify_one_tile reproduce_k_products
run_k_cpp_products repair_six_upper test_record_bounds resource_prices
check_seven_products complete_seven_hooks test_seven_completeness
verify_csw_three_upper verify_csw_four_upper verify_csw_five_upper
verify_csw_six_upper verify_csw_seven_upper verify_small_records
verify_csw_three verify_csw_four verify_csw_five find_csw_six_history
verify_csw_six build_csw_seven_baseline test_csw_seven_witness
find_csw_seven_history verify_csw_seven verify_seven_racks verify_seven_chain
build_monthly_figures build_sampling_figure build_monthly export_monthly_figures
render_monthly sample_reachable_games fetch_tex_dependencies build_public_release'''.split()


def source_closure():
    selected = {ROOT/'scripts'/f'{name}.py' for name in ENTRY_POINTS}
    selected.update((ROOT/'scripts/seven_tail').glob('*.py'))
    pending = list(selected)
    while pending:
        source = pending.pop()
        for node in ast.walk(ast.parse(source.read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module] + [node.module+'.'+a.name for a in node.names]
            for name in names:
                for parent in (source.parent, ROOT/'scripts', ROOT/'scripts/seven_tail'):
                    path = (parent/Path(*name.split('.'))).with_suffix('.py')
                    if path.is_file() and path not in selected:
                        selected.add(path)
                        pending.append(path)
    selected.update(ROOT/'scripts'/name for name in ('scan_k_upper.cpp', 'exact_product_search.cpp'))
    return selected


def selected_files():
    selected = source_closure()
    selected.update(ROOT/'scripts/seven_tail'/name for name in
                    ('032.txt', 'rec74_horizontal_bases.json', 'seven_tile_upper_1737.txt'))
    selected.update(p for p in (ROOT/'monthly').rglob('*') if p.suffix in ('.tex', '.bib', '.pdf', '.eps'))
    selected.update(ROOT/name for name in ('README.md', 'LICENSE', 'THIRD_PARTY.md',
                    'MONTHLY_SUBMISSION.md', 'REPRODUCTION_STATUS.md', 'requirements-reproduce.txt',
                    '.gitignore', 'data/README.md', '.github/workflows/ci.yml'))
    files = {p.relative_to(ROOT).as_posix(): p for p in selected}
    for name in ('NWL23', 'CSW24'):
        original = ROOT/'data/sampling'/f'{name}.json'
        if not original.exists():
            original = ROOT/'output/sampling'/name/'sample.json'
        files[f'data/sampling/{name}.json'] = original
    return files


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    destination = args.destination.resolve()
    if destination == ROOT or ROOT.is_relative_to(destination):
        raise SystemExit('Choose a separate staging directory, not this workspace or its ancestor')
    files = selected_files()
    manifest = {}
    for name, source in sorted(files.items()):
        data = source.read_bytes()
        if source.suffix in ('.py', '.cpp', '.tex', '.bib', '.eps', '.json', '.md', '.yml'):
            text = data.decode('utf-8', errors='replace')
            for prefix in ('/'.join(('', 'Users', '')), '/'.join(('', 'var', 'folders', ''))):
                if prefix in text:
                    raise ValueError(f'Private local path in {name}')
        if source.suffix == '.kwg' or name.startswith(('vendor/', 'research/', 'output/')):
            raise ValueError(f'Restricted input in export: {name}')
        target = destination/name
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != target.resolve():
            shutil.copyfile(source, target)
        manifest[name] = hashlib.sha256(data).hexdigest()
    record = dict(purpose='Public source and artifact integrity; not a proof by itself',
                  files=manifest, required_external_inputs=['data/NWL23.kwg', 'data/CSW24.kwg'])
    (destination/'RELEASE_MANIFEST.json').write_text(json.dumps(record, indent=2, sort_keys=True)+'\n')
    print(f'Exported {len(files)} allowlisted files to {destination}')


if __name__ == '__main__':
    main()

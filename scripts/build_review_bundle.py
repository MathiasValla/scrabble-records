#!/usr/bin/env python3
"""Package the same minimal sources for review, without Git identity metadata."""
import hashlib
import json
import zipfile
from build_public_release import ROOT, selected_files


def main():
    files = selected_files()
    manifest = dict(schema='release-manifest-v1',
        purpose='Metadata-clean local review snapshot; not a proof by itself',
        files={name:hashlib.sha256(source.read_bytes()).hexdigest() for name,source in sorted(files.items())},
        required_external_inputs={
            'data/NWL23.kwg':'3e74af981fdd974e107283f686da0fe4b7ec84ad0d825d444330c338c33b91ba',
            'data/CSW24.kwg':'62ca7a84f07429a9976f77a4f74b94911aca5d49cce050dce72dd0e032c0566f'})
    target = ROOT/'output/monthly_review_bundle.zip'
    target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        def add(name, data):
            info = zipfile.ZipInfo('scrabble-records/'+name, date_time=(2020,1,1,0,0,0))
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
        for name, source in sorted(files.items()):
            add(name, source.read_bytes())
        add('REVIEW_MANIFEST.json', json.dumps(manifest, indent=2, sort_keys=True).encode()+b'\n')
    print('Review archive:', len(files), 'files;', target.stat().st_size, 'bytes')


if __name__ == '__main__':
    main()

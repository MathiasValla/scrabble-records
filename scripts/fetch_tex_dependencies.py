#!/usr/bin/env python3
"""Fetch pinned, unmodified TeX archives locally; do not redistribute them."""
import argparse
import hashlib
import io
from pathlib import Path
import shutil
import stat
import subprocess
import urllib.request
import urllib.error
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CTAN = 'https://mirrors.ctan.org/'
ARCHIVES = {
    'monthly_templates': ('https://maa.org/wp-content/uploads/2025/08/American_Math_Monthly_Templates.zip',
        '59c5b2bec56ce4de0e5439251cf5986050c291aca2b56819e04c779d57c53998'),
    'scrabble': (CTAN+'graphics/pgf/contrib/scrabble.zip',
        '04811839d1de9ddc17059794edcef160460823122f95e2bf75e3c9a2047c8efa'),
    'listofitems': (CTAN+'macros/generic/listofitems.zip',
        'cd071626c1c087876cc5963e2823672ce66282b0e452743160c2bedd20cf3a8b'),
    'simplekv': (CTAN+'macros/generic/simplekv.zip',
        '5801fc91093bd6ae78723c54b002de766d6b27d2262c0d39293cab04c644ef3a'),
    'xstring': (CTAN+'macros/generic/xstring.zip',
        '0d432b250e3128b0e0f70028df7ca94966f152500f9e5e208172ae5586147b2c'),
    'randomlist': (CTAN+'macros/generic/randomlist.zip',
        'ef230398c622300a713c5a0e316624e0a7d329d7ac6e5c576fe7d26f38565028'),
    'randintlist': (CTAN+'macros/latex/contrib/randintlist.zip',
        '4b62f91e55e83e8103784c1ccaef7d24aed9a5012a9c041707bcd20711199f5c'),
    'poormanlog': (CTAN+'macros/generic/poormanlog.zip',
        'e1ef81eacad559be02965fd45c63e4c89089e8ea9f6dea75a041115eff1c718e'),
    'xint': (CTAN+'macros/generic/xint.zip',
        '6fb45e71606a3da29742beab0ef4fcb1390ed52242018da47552ee03cb0898c4'),
}


def extract(data, destination):
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for item in archive.infolist():
            path = (destination/item.filename).resolve()
            if not path.is_relative_to(destination.resolve()):
                raise ValueError('Archive path escapes its destination')
            if stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError('Archive symlinks are not accepted')
        archive.extractall(destination)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache-dir', type=Path, default=ROOT/'tmp/tex_archives')
    args = parser.parse_args()
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    for name, (url, expected) in ARCHIVES.items():
        cached = args.cache_dir/f'{name}.zip'
        if cached.exists():
            data = cached.read_bytes()
        else:
            print('Downloading', name, flush=True)
            try:
                with urllib.request.urlopen(url, timeout=120) as response:
                    data = response.read()
            except urllib.error.URLError as error:
                raise SystemExit(f'{name}: download failed ({error}). Download {url} through '
                                 f'the publisher\'s website into {cached}, then rerun. '
                                 'The same SHA-256 check will still be required.') from error
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected:
            raise SystemExit(f'{name}: archive hash changed ({actual}); review upstream before updating the pin')
        if not cached.exists():
            cached.write_bytes(data)
        target = ROOT/'vendor/monthly' if name == 'monthly_templates' else ROOT/'vendor'
        extract(data, target)
        print('Verified', name, flush=True)
    # CTAN distributes xint as documented source, not pre-extracted .sty files.
    subprocess.run(['etex', '-interaction=nonstopmode', 'xint.dtx'],
                   cwd=ROOT/'vendor/xint', check=True, stdout=subprocess.DEVNULL)
    for source, name in [('Style File/maa-monthly.sty', 'maa-monthly.sty'),
                         ('Article and Note Template/vancouver.bst', 'vancouver.bst')]:
        shutil.copyfile(ROOT/'vendor/monthly'/source, ROOT/'monthly'/name)
    print('Local TeX dependencies ready; vendor/ remains untracked.')


if __name__ == '__main__':
    main()

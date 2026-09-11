#!/usr/bin/env python3
"""Compile final-size, self-contained TikZ sources to vector PDF and EPS."""
import os
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'monthly/figures'
OUT=SOURCE/'exports'


def main():
    OUT.mkdir(exist_ok=True)
    env=dict(os.environ,TEXINPUTS='.:../../../vendor//:')
    figures=[p for p in SOURCE.glob('*.tex') if re.fullmatch(r'(nwl23|csw24)_k[1-7]|record_curve|score_distributions',p.stem)]
    for source in sorted(figures):
        text='\n'.join([r'\documentclass[border=2pt]{standalone}',r'\usepackage{times,tikz}',
                         (SOURCE/'board_style.tex').read_text(),r'\begin{document}',
                         source.read_text(),r'\end{document}'])+'\n'
        (OUT/source.name).write_text(text)
        with (OUT/f'{source.stem}_build.txt').open('w') as log:
            subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error',source.name],
                           cwd=OUT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        subprocess.run(['pdftops','-eps',str(OUT/f'{source.stem}.pdf'),str(OUT/f'{source.stem}.eps')],check=True)
        info=subprocess.check_output(['pdfinfo',str(OUT/f'{source.stem}.pdf')],text=True)
        match=re.search(r'Page size:\s+([\d.]+) x ([\d.]+) pts',info)
        assert match and float(match.group(1))<=360,(source.name,match.groups() if match else info)
        print(source.stem,match.groups(),'pt; PDF/EPS/source ready',flush=True)


if __name__=='__main__':main()

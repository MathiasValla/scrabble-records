#!/usr/bin/env python3
"""Build journal-size PDFs without shell escape or post-hoc figure scaling."""
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'monthly'
env=dict(os.environ,TEXINPUTS='.:../vendor//:')
for stem in ('manuscript','supplementary_material'):
    for i in range(3):
        log=folder/f'{stem}_build{i+1}.txt'
        with log.open('w') as f:
            subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error',f'{stem}.tex'],
                           cwd=folder,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
        if i==0 and stem=='manuscript':
            with (folder/'bibliography_build.txt').open('w') as f:
                subprocess.run(['bibtex',stem],cwd=folder,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
    print(folder/f'{stem}.pdf')

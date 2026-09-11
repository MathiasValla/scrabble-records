#!/usr/bin/env python3
"""Render every PDF page and produce a review contact sheet."""
from pathlib import Path
import subprocess
import re
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'tmp/pdfs/monthly_review';folder.mkdir(parents=True,exist_ok=True)
for name in ('manuscript','board_atlas'):
    prefix=folder/name
    subprocess.run(['pdftoppm','-scale-to','1100','-png',str(ROOT/'monthly'/f'{name}.pdf'),str(prefix)],check=True)
    info=subprocess.check_output(['pdfinfo',str(ROOT/'monthly'/f'{name}.pdf')],text=True)
    count=int(re.search(r'^Pages:\s+(\d+)',info,re.M).group(1))
    pages=[folder/f'{name}-{i:0{len(str(count))}d}.png' for i in range(1,count+1)]
    assert all(p.exists() for p in pages)
    for offset in range(0,len(pages),6):
        sheet=Image.new('RGB',(1200,1100),'#c8c8c8');draw=ImageDraw.Draw(sheet)
        for j,path in enumerate(pages[offset:offset+6]):
            im=Image.open(path);im.thumbnail((385,510))
            x=(j%3)*400+(400-im.width)//2;y=(j//3)*550+22
            sheet.paste(im,(x,y));draw.text((x,y-17),path.stem,fill='black')
        sheet.save(folder/f'{name}_sheet{offset//6+1}.png')

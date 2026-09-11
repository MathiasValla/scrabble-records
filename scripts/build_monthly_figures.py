#!/usr/bin/env python3
"""Vector boards and racks rendered at final journal size, from certificates."""
import json
from pathlib import Path
from collections import Counter
import verify_1786 as V
from search_two_tile import premium_at

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'monthly/figures'

PREAMBLE=r'''\usepackage{Scrabble}
\colorlet{triplewordscore}{black!42}
\colorlet{doublewordscore}{black!20}
\colorlet{tripleletterscore}{black!32}
\colorlet{doubleletterscore}{black!12}
\colorlet{scrabblebloard}{white}
\newcommand{\RecordTile}[5]{%
  \draw[draw=black,fill=#4,line width=.5pt] (#1-.45,#2-.45) rectangle (#1+.45,#2+.45);
  \node[text=#5,font=\fontsize{9}{10}\selectfont,inner sep=0pt] at (#1-.10,#2+.06) {#3};}
'''


def board_tex(rows,new,blank,rack,required):
    lines=[r'\begin{EnvScrabble}[Scale=0.72,Labels=false,Border=false]',r'\tikzset{every node/.style={}}',
           r'\draw[black!22,line width=.5pt,step=1] (-.5,-.5) grid (14.5,14.5);',
           r'\draw[line width=.7pt] (-.5,-.5) rectangle (14.5,14.5);']
    for r in range(1,16):
        lines.append(r'\node[font=\fontsize{8}{9}\selectfont] at (-.95,%s) {%s};'%(15-r,r))
    for c in range(1,16):
        lines.append(r'\node[font=\fontsize{8}{9}\selectfont] at (%s,15) {%s};'%(c-1,chr(64+c)))
    for r,row in enumerate(rows,1):
        for c,ch in enumerate(row,1):
            x,y=c-1,15-r
            if ch=='.':
                lm,wm=premium_at((r,c))
                text=('TW' if wm==3 else 'DW' if wm==2 else 'TL' if lm==3 else 'DL' if lm==2 else '')
                if text:lines.append(r'\node[font=\fontsize{8}{9}\selectfont,inner sep=0pt] at (%s,%s) {%s};'%(x,y,text))
                continue
            is_new=(r,c) in new;is_blank=(r,c) in blank
            value=0 if is_blank else V.LETTER_VALUES[ch.upper()]
            label=r'\textit{%s}'%ch.lower() if is_blank else ch.upper()
            fill,text=('black','white') if is_new else ('white','black')
            lines.append(r'\RecordTile{%s}{%s}{%s}{%s}{%s}'%(x,y,label,fill,text))
            lines.append(r'\node[text=%s,font=\fontsize{8}{9}\selectfont,inner sep=0pt,anchor=south east] at (%s,%s) {%s};'%(text,x+.4,y-.39,value))
    needed=Counter(required)
    for i,ch in enumerate(rack):
        marked=needed[ch]>0;needed[ch]-=int(marked)
        x=4+i
        lines.append(r'\RecordTile{%s}{-1.6}{%s}{%s}{%s}'%(x,ch if ch!='?' else r'$\ast$', 'black' if marked else 'white','white' if marked else 'black'))
        value=V.LETTER_VALUES.get(ch,0)
        lines.append(r'\node[text=%s,font=\fontsize{8}{9}\selectfont,inner sep=0pt,anchor=south east] at (%s,-1.99) {%s};'%('white' if marked else 'black',x+.4,value))
    lines.extend([r'\draw[line width=.7pt] (3.45,-2.1)--(10.55,-2.1);',
                  r'\node[font=\fontsize{9}{10}\selectfont,anchor=east] at (3.1,-1.6) {Rack};',r'\end{EnvScrabble}'])
    return '\n'.join(lines)+'\n'


def history_tex(witness):
    name,k=witness['lexicon'],witness['k']
    lines=[r'\begin{table}[!ht]\centering\small',
           rf'\caption{{A legal construction for {name}, $k={k}$. Only the last row is the record move.}}',
           rf'\label{{tab:{name}-{k}-history}}',r'\begin{tabular}{@{}rllrr@{}}\toprule',
           r'No. & Word & Cells & New tiles & Score\\\midrule']
    def coordinate(p):return chr(64+p[1])+str(p[0])
    for i,h in enumerate(witness['history'],1):
        if i==len(witness['history']):lines.append(r'\midrule')
        m=h['move'];span=coordinate(m['cells'][0])+'--'+coordinate(m['cells'][-1])
        lines.append(rf'{i} & \texttt{{{m["word"]}}} & {span} & {len(h["new_cells"])} & {h["total"]}\\')
    lines.extend([r'\bottomrule\end{tabular}',r'\end{table}'])
    return '\n'.join(lines)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'board_style.tex').write_text(PREAMBLE)
    witnesses=json.loads((ROOT/'output/small_records_verified.json').read_text())['witnesses']
    witnesses.append(json.loads((ROOT/'output/CSW24_k3_exact.json').read_text()))
    witnesses.append(json.loads((ROOT/'output/CSW24_k4_exact.json').read_text()))
    witnesses.append(json.loads((ROOT/'output/CSW24_k5_exact.json').read_text()))
    witnesses.append(json.loads((ROOT/'output/CSW24_k6_exact.json').read_text()))
    witnesses.append(json.loads((ROOT/'output/CSW24_k7_exact.json').read_text()))
    from verify_small_records import verify,move
    import verify_three_tile,verify_four_tile,verify_five_tile,verify_six_tile
    for k,module,score in [(3,verify_three_tile,882),(4,verify_four_tile,1130),
                           (5,verify_five_tile,1401)]:
        witnesses.append(verify('NWL23',k,module.SEQUENCE,module.FINAL_MOVE,getattr(module,'BLANK_CELLS',set()),score))
    witnesses.append(verify('NWL23',6,verify_six_tile.construction_moves(),
                            move('H','OXYPHENBUTAZONE',1,1),set(verify_six_tile.BLANK_ASSIGNMENTS),1723))
    witnesses.sort(key=lambda w:(w['k'],w['lexicon']))
    small=sorted((w for w in witnesses if w['k']<=2),key=lambda w:(w['k'],w['lexicon']!='NWL23'))
    tables=[history_tex(w) for w in small]
    (ROOT/'monthly/small_record_histories.tex').write_text('\n\n'.join(tables[:2])+'\n\n\\clearpage\n'+
                                                          '\n\n'.join(tables[2:])+'\n')
    names=[]
    for w in witnesses:
        stem=f"{w['lexicon'].lower()}_k{w['k']}"
        h=w['history'][-1]
        tex=board_tex(w['final_board'],set(map(tuple,h['new_cells'])),set(map(tuple,w['blank_cells'])),h['rack_before'],h['rack_required'])
        (OUT/f'{stem}.tex').write_text(tex);names.append((stem,w['lexicon'],w['k'],w['score']))
    cert=json.loads((ROOT/'output/seven_rack_certificate.json').read_text())
    rows=[''.join(V.board_from_rows().get((r,c),'.') for c in range(1,16)) for r in range(1,16)]
    (OUT/'nwl23_k7.tex').write_text(board_tex(rows,set(V.FINAL_MOVE),set(V.BLANK_ASSIGNMENTS),'BENOPXZ','BENOPXZ'))
    names.append(('nwl23_k7','NWL23',7,1786))
    atlas=[r'\documentclass{article}',r'\usepackage[margin=20mm]{geometry}',r'\usepackage{times,booktabs}',
           r'\renewcommand{\ttdefault}{cmtt}',r'\input{figures/board_style}',r'\begin{document}']
    for stem,lex,k,score in names:
        atlas.extend([r'\begin{center}',r'\large %s: %s %s, %s points\par\medskip'%(lex,k,'tile' if k==1 else 'tiles',score),r'\input{figures/%s}'%stem,
                      r'\par\medskip\normalsize Black tiles are newly played; italic letters are blanks.\par The complete rack is shown below the board.'])
        if lex=='NWL23' and k==7:atlas.append(r'\par Construction by Bob Lucassen (2024), independently replayed here.')
        atlas.extend([r'\end{center}',r'\clearpage'])
    atlas.extend([r'\section*{Small-Case Construction Histories}',
                  r'The tables list complete words after each move, their occupied intervals, the number of new tiles, and the ordinary move score. Existing letters remain in place. Every setup move places at most seven tiles and scores positively. In the NWL23 two-tile construction, I13 is a permanent blank A. The three other small-case constructions use no blanks.',
                  r'\input{small_record_histories}',r'\end{document}'])
    (ROOT/'monthly/board_atlas.tex').write_text('\n'.join(atlas)+'\n')
    # Native TikZ chart at its final printed dimensions.
    graph=[r'\begin{tikzpicture}[x=1.15cm,y=.00225cm]',r'\draw[line width=.5pt,->] (0,0)--(7.6,0);',r'\draw[line width=.5pt,->] (0,0)--(0,1950);']
    for k in range(1,8):graph.append(r'\node[below,font=\fontsize{8}{9}\selectfont] at (%s,0) {%s};'%(k,k))
    for value in range(0,2000,500):
        graph.extend([r'\draw[black!20,line width=.5pt] (0,%s)--(7.3,%s);'%(value,value),r'\node[left,font=\fontsize{8}{9}\selectfont] at (0,%s) {%s};'%(value,value)])
    nwl=[213,459,882,1130,1401,1723,1786]
    graph.append(r'\draw[line width=.8pt] '+'--'.join('(%s,%s)'%(i,s) for i,s in enumerate(nwl,1))+';')
    for i,s in enumerate(nwl,1):graph.append(r'\fill (%s,%s) circle[radius=2pt];'%(i,s))
    graph.extend([r'\draw[line width=.8pt,densely dotted] (1,225)--(2,483)--(3,912)--(4,1349)--(5,1478)--(6,1721)--(7,1787);'])
    for i,s in [(1,225),(2,483),(3,912),(4,1349),(5,1478),(6,1721),(7,1787)]:graph.append(r'\draw[fill=white,line width=.7pt] (%s-.04,%s-16) rectangle (%s+.04,%s+16);'%(i,s,i,s))
    graph.extend([r'\node[font=\fontsize{9}{10}\selectfont,anchor=west] at (3,500) {Circles: NWL23};',
                  r'\node[font=\fontsize{9}{10}\selectfont,anchor=west] at (3,330) {Squares: CSW24};',
                  r'\node[font=\fontsize{9}{10}\selectfont] at (4,-200) {Number of new tiles};',r'\node[rotate=90,font=\fontsize{9}{10}\selectfont] at (-1.5,1000) {Move score};',r'\end{tikzpicture}'])
    (OUT/'record_curve.tex').write_text('\n'.join(graph)+'\n')
    print(f'Generated {len(names)} certificate boards with complete racks and both exact record curves.')


if __name__=='__main__':main()

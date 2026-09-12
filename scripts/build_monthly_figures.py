#!/usr/bin/env python3
"""Vector boards and racks rendered at final journal size, from certificates."""
import json
import hashlib
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


def board_tex(rows,new,blank,rack,required,scale=0.72):
    lines=[rf'\begin{{EnvScrabble}}[Scale={scale:.2f},Labels=false,Border=false]',r'\tikzset{every node/.style={}}',
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


def coordinate(p):
    return chr(64+p[1])+str(p[0])


def normalized_nwl_seven():
    """Convert the alternating-turn rack certificate to the common witness shape."""
    cert=json.loads((ROOT/'output/seven_rack_certificate.json').read_text())
    history=[]
    for action in cert['actions']:
        if 'move' not in action:
            continue
        history.append(dict(move=action['move'],new_cells=action['new_cells'],
                            rack_before=action['rack_before'],
                            rack_required=action['required'],total=action['score'],
                            word_scores=action['word_scores'],player=action['player']))
    rows=[''.join(V.board_from_rows().get((r,c),'.') for c in range(1,16))
          for r in range(1,16)]
    assert len(history)==25 and history[-1]['total']==1786
    return dict(lexicon='NWL23',k=7,score=1786,history=history,
                final_board=rows,blank_cells=sorted(V.BLANK_ASSIGNMENTS))


def history_tex(witness):
    """A non-floating table, kept on the same page as its board."""
    history=witness['history']
    show_player=any('player' in h for h in history)
    if len(history)>=25:
        size=r'\fontsize{8}{8.15}\selectfont'
        stretch='0.80'
    elif len(history)>=20:
        size=r'\fontsize{8}{8.3}\selectfont'
        stretch='0.84'
    else:
        size=r'\fontsize{8.5}{8.8}\selectfont'
        stretch='0.90'
    columns='rl l l rr' if show_player else 'r l l rr'
    columns=columns.replace(' ','')
    heading=(r'No. & Player & Word & Span & New tiles & Score\\'
             if show_player else r'No. & Word & Span & New tiles & Score\\')
    lines=[r'\begin{center}',size,r'\setlength{\tabcolsep}{4pt}',
           rf'\renewcommand{{\arraystretch}}{{{stretch}}}',
           rf'\begin{{tabular}}{{@{{}}{columns}@{{}}}}\toprule',heading,r'\midrule']
    for i,h in enumerate(history,1):
        if i==len(history):
            lines.append(r'\midrule')
        m=h['move'];span=coordinate(m['cells'][0])+'--'+coordinate(m['cells'][-1])
        cells=[str(i)]
        if show_player:
            cells.append(h.get('player',r'--'))
        cells.extend([rf'\texttt{{{m["word"]}}}',span,str(len(h['new_cells'])),str(h['total'])])
        if i==len(history):
            cells=[rf'\textbf{{{cell}}}' for cell in cells]
        row=' & '.join(cells)+r'\\'
        lines.append(row)
    lines.extend([r'\bottomrule\end{tabular}',r'\end{center}'])
    return '\n'.join(lines)


def board_scale(history_length):
    if history_length>=25:
        return 0.58
    if history_length>=20:
        return 0.61
    return 0.66


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest_tex(value):
    return rf'\texttt{{{value[:32]}}}\\\texttt{{{value[32:]}}}'


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
    witnesses.append(normalized_nwl_seven())
    witnesses.sort(key=lambda w:(w['k'],w['lexicon']!='NWL23'))
    expected=[(k,name) for k in range(1,8) for name in ('NWL23','CSW24')]
    assert [(w['k'],w['lexicon']) for w in witnesses]==expected
    certificates=ROOT/'certificates';certificates.mkdir(exist_ok=True)
    witness_path=certificates/'record_witnesses.json'
    witness_path.write_text(json.dumps(dict(
        format='record-witnesses-v1',
        note=('Each history lists every positive-scoring placement. '
              'Intervening turns are passes unless a player field is present.'),
        witnesses=witnesses),indent=2,sort_keys=True)+'\n')
    reproduction_path=ROOT/'certificates/reproduction_verified.json'
    nwl_rack_path=ROOT/'certificates/nwl23_k7_rack_certificate.json'
    one_tile_path=ROOT/'certificates/one_tile_certificate.json'
    upper_audit_path=ROOT/'certificates/upper_bound_audit.json'
    fresh_state_path=ROOT/'certificates/fresh_run_state.json'
    certificate_hashes={
        'record_witnesses.json':digest(witness_path),
        'one_tile_certificate.json':digest(one_tile_path),
        'upper_bound_audit.json':digest(upper_audit_path),
        'reproduction_verified.json':digest(reproduction_path),
        'fresh_run_state.json':digest(fresh_state_path),
        'nwl23_k7_rack_certificate.json':digest(nwl_rack_path),
    }
    names=[]
    for w in witnesses:
        stem=f"{w['lexicon'].lower()}_k{w['k']}"
        h=w['history'][-1]
        tex=board_tex(w['final_board'],set(map(tuple,h['new_cells'])),
                      set(map(tuple,w['blank_cells'])),h['rack_before'],
                      h['rack_required'],board_scale(len(w['history'])))
        (OUT/f'{stem}.tex').write_text(tex)
        names.append((stem,w))
    supplement=[r'\documentclass[letterpaper]{article}',
                r'\usepackage[letterpaper,left=13mm,right=13mm,top=10mm,bottom=12mm]{geometry}',
                r'\usepackage{times,booktabs}',
                r'\renewcommand{\ttdefault}{cmtt}',r'\setlength{\parindent}{0pt}',
                r'\setlength{\parskip}{0pt}',r'\pagestyle{plain}',
                r'\input{figures/board_style}',r'\begin{document}']
    supplement.extend([
        r'\begin{center}',
        r'{\fontsize{15}{17}\selectfont\bfseries Supplementary Material: Record Boards and Construction Histories\par}',
        r'\vspace{2pt}',
        r'{\fontsize{9}{10}\selectfont for \textit{How Much Can a Scrabble Move Score? Exact Records from One Tile to Seven}\par}',
        r'\vspace{5pt}',
        r'{\fontsize{12}{14}\selectfont\bfseries Rules and Certificate Guide\par}',
        r'\vspace{4pt}',r'\end{center}',
        r'{\fontsize{9}{10}\selectfont',
        r'Columns A--O run left to right and rows 1--15 top to bottom; H8 is the centre. The first move covers H8. A later move places one to seven tiles in one row or column. Every new maximal string of length at least two must be in the stated dictionary. Premiums apply only when first covered. A seven-tile move earns 50 extra points.',
        r'\vspace{5pt}',
        r'\textbf{Tile supply and face values.}\par\vspace{2pt}',
        r'\begin{center}\begin{tabular}{@{}crr@{\qquad}crr@{}}\toprule',
        r'Tile&Copies&Value&Tile&Copies&Value\\\midrule',
        r'A&9&1&N&6&1\\ B&2&3&O&8&1\\ C&2&3&P&2&3\\ D&4&2&Q&1&10\\',
        r'E&12&1&R&6&1\\ F&2&4&S&4&1\\ G&3&2&T&6&1\\ H&2&4&U&4&1\\',
        r'I&9&1&V&2&4\\ J&1&8&W&2&4\\ K&1&5&X&1&8\\ L&4&1&Y&2&4\\',
        r'M&2&3&Z&1&10\\ Blank&2&0&&&\\\bottomrule\end{tabular}\end{center}',
        r'\vspace{4pt}\textbf{Premium squares.}\par\vspace{2pt}',
        r'TW, DW, TL, and DL mean triple word, double word, triple letter, and double letter, respectively.\par\vspace{2pt}',
        r'\begin{tabular}{@{}lp{.78\textwidth}@{}}',
        r'TW&A1, H1, O1, A8, O8, A15, H15, O15.\\',
        r'DW&B2, N2, C3, M3, D4, L4, E5, K5, H8, E11, K11, D12, L12, C13, M13, B14, N14.\\',
        r'TL&F2, J2, B6, F6, J6, N6, B10, F10, J10, N10, F14, J14.\\',
        r'DL&D1, L1, G3, I3, A4, H4, O4, C7, G7, I7, M7, D8, L8, C9, G9, I9, M9, A12, H12, O12, G13, I13, D15, L15.\\',
        r'\end{tabular}\par',
        r'\vspace{5pt}\textbf{Dictionary identity.}\par\vspace{2pt}',
        r'NWL23 binary SHA-256: '+digest_tex(digest(ROOT/'data/NWL23.kwg'))+r'.\par',
        r'NWL23 sorted word-list SHA-256: '+digest_tex(digest(ROOT/'output/NWL23_words.txt'))+r'.\par',
        r'CSW24 binary SHA-256: '+digest_tex(digest(ROOT/'data/CSW24.kwg'))+r'.\par',
        r'CSW24 sorted word-list SHA-256: '+digest_tex(digest(ROOT/'output/CSW24_words.txt'))+r'.\par',
        r'NWL23 has 212,868 exported entries, of which 196,601 have board length 2--15. CSW24 has 299,162 exported entries, of which 280,887 have board length 2--15.\par',
        r'The binary dictionaries are decoded as little-endian 32-bit directed-acyclic-word-graph nodes. A depth-first traversal emits a word precisely at an accepting node; sorting the emitted uppercase strings gives the word lists hashed above.\par',
        r'\vspace{5pt}\textbf{Machine-readable certificates.}\par\vspace{2pt}',
        r'\texttt{certificates/record\_witnesses.json}: '+digest_tex(certificate_hashes['record_witnesses.json'])+r'.\par',
        r'\texttt{certificates/one\_tile\_certificate.json}: '+digest_tex(certificate_hashes['one_tile_certificate.json'])+r'.\par',
        r'\texttt{certificates/upper\_bound\_audit.json}: '+digest_tex(certificate_hashes['upper_bound_audit.json'])+r'.\par',
        r'\texttt{certificates/reproduction\_verified.json}: '+digest_tex(certificate_hashes['reproduction_verified.json'])+r'.\par',
        r'\texttt{certificates/fresh\_run\_state.json}: '+digest_tex(certificate_hashes['fresh_run_state.json'])+r'.\par',
        r'\texttt{certificates/nwl23\_k7\_rack\_certificate.json}: '+digest_tex(certificate_hashes['nwl23_k7_rack_certificate.json'])+r'.\par',
        r'The public driver \texttt{scripts/reproduce\_release.py} regenerates every upper-bound search and invokes separate forward verifiers for every history. The following tables list every tile-placement turn; omitted intervening turns are passes, while rack refills and draws remain in the JSON certificates.',
        r'}',r'\clearpage'])
    for stem,w in names:
        lex,k,score=w['lexicon'],w['k'],w['score']
        supplement.extend([r'\begin{center}',
            r'{\fontsize{11}{12}\selectfont\bfseries %s: $k=%s$, %s points\par}'%(lex,k,score),
            r'\vspace{2pt}',r'\input{figures/%s}\par'%stem,
            r'\vspace{1pt}',
            r'{\fontsize{7.2}{8}\selectfont Black tiles are newly played; italic letters are blanks; the final rack appears below the board.\par}',
            r'\vspace{2pt}',
            r'{\fontsize{8.5}{9}\selectfont\bfseries Complete tile-placement history\par}',
            r'\end{center}',history_tex(w)])
        if lex=='NWL23' and k==7:
            supplement.append(r'\vspace{-2pt}\begin{center}{\fontsize{8}{8.4}\selectfont Construction due to Bob Lucassen (2024); the table is normalized from the independently verified rack certificate.\par}\end{center}')
        supplement.extend([r'\vfill',r'\clearpage'])
    supplement.append(r'\end{document}')
    (ROOT/'monthly/supplementary_material.tex').write_text('\n'.join(supplement)+'\n')
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
    print(f'Generated {len(names)} certificate boards, same-page histories, and both exact record curves.')


if __name__=='__main__':main()

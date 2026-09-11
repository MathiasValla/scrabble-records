#!/usr/bin/env python3
"""Replay the simulation certificates, then emit exact empirical CDFs in TikZ."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
from verify_small_records import move,verify

ROOT=Path(__file__).resolve().parents[1]


def sample_path(name):
    generated=ROOT/'output/sampling'/name/'sample.json'
    return generated if generated.exists() else ROOT/'data/sampling'/f'{name}.json'


def checked_sample(name):
    path=sample_path(name)
    data=json.loads(path.read_text())
    assert data['complete'] and data['completed_games']==data['arguments']['games']==1000
    assert data['kwg_sha256']==hashlib.sha256((ROOT/'data'/f'{name}.kwg').read_bytes()).hexdigest()
    samples={str(k):[] for k in range(1,8)}
    for index,game in enumerate(data['games']):
        assert game['index']==index
        history=game['history']
        moves=[move(h['orientation'],h['word'],h['row'],h['col']) for h in history]
        checked=verify(name,history[-1]['k'],moves[:-1],moves[-1],set(map(tuple,game['blank_cells'])),history[-1]['score'])
        assert len(history)==len(checked['history'])
        assert game['final_tiles']==checked['final_board_tiles']
        assert game['rack_stream_sha256']==hashlib.sha256(checked['active_player_draw_stream'].encode()).hexdigest()
        for h,c in zip(history,checked['history']):
            assert (h['score'],h['k'])==(c['total'],len(c['new_cells']))
        expected_keys={str(h['k']) for h in history[1:]}
        assert set(game['selected'])==expected_keys
        for k,selection in game['selected'].items():
            step=selection['step']
            assert 1<=step<len(history)
            assert history[step]['k']==int(k) and history[step]['score']==selection['score']
            samples[k].append(selection['score'])
    assert samples==data['samples']
    for k,values in samples.items():
        stats=data['statistics'][k]
        assert stats['n']==len(values)
        assert stats['mean']==sum(values)/len(values)
        assert stats['maximum']==max(values)
        assert abs(stats['dkw_95_simultaneous_14_ecdfs']-math.sqrt(math.log(560)/(2*len(values))))<1e-12
    return data


def main():
    data={name:checked_sample(name) for name in ('NWL23','CSW24')}
    lines=[r'\begin{tikzpicture}[x=1cm,y=1cm,line width=.5pt,font=\fontsize{9}{11}\selectfont]']
    for k in range(1,8):
        col=(k-1)%2;row=(k-1)//2
        lines.append(rf'\begin{{scope}}[shift={{({col*5.8},{-row*2.7})}}]')
        lo,hi=(50,250) if k==7 else (0,80)
        n=[data[name]['statistics'][str(k)]['n'] for name in data]
        lines.append(rf'\node[anchor=west] at (0,1.93) {{$k={k}$\quad $N={n[0]}/{n[1]}$}};')
        for y in (0,.5,1):
            lines.append(rf'\draw[black!20] (0,{1.6*y}) -- (4.6,{1.6*y});')
            lines.append(rf'\node[anchor=east,font=\fontsize{{8}}{{9}}\selectfont] at (-.08,{1.6*y}) {{{y:g}}};')
        lines.append(r'\draw (0,1.6) -- (0,0) -- (4.6,0);')
        for x in ([50,100,150,200,250] if k==7 else [0,20,40,60,80]):
            p=4.6*(x-lo)/(hi-lo)
            lines.append(rf'\draw ({p},0) -- ({p},-.06);\node[anchor=north,font=\fontsize{{8}}{{9}}\selectfont] at ({p},-.06) {{{x}}};')
        for name,style in [('NWL23','black,line width=.65pt'),('CSW24','black!65,densely dashed,line width=.65pt')]:
            values=data[name]['samples'][str(k)];counts=Counter(values);cumulative=0
            points=[(0,0)]
            for score,count in sorted(counts.items()):
                assert lo<=score<=hi
                x=4.6*(score-lo)/(hi-lo)
                points.append((x,1.6*cumulative/len(values)))
                cumulative+=count
                points.append((x,1.6*cumulative/len(values)))
            points.append((4.6,1.6))
            lines.append(r'\draw['+style+'] '+' -- '.join(f'({x:.5f},{y:.5f})' for x,y in points)+';')
        lines.append(r'\end{scope}')
    lines.extend([r'\draw[line width=.65pt] (5.8,-6.85) -- (6.5,-6.85);',
        r'\node[anchor=west] at (6.6,-6.85) {NWL23};',
        r'\draw[black!65,densely dashed,line width=.65pt] (5.8,-7.35) -- (6.5,-7.35);',
        r'\node[anchor=west] at (6.6,-7.35) {CSW24};',
        r'\node[anchor=west,align=left] at (5.8,-8.05) {Horizontal: move score\\Vertical: cumulative fraction};',
        r'\end{tikzpicture}'])
    (ROOT/'monthly/figures/score_distributions.tex').write_text('\n'.join(lines)+'\n')
    table=[r'\begin{tabular}{@{}rrrrrrr@{}}\toprule',
           r'&\multicolumn{3}{c}{NWL23}&\multicolumn{3}{c}{CSW24}\\',
           r'$k$&$N_k$&Mean&$\epsilon_k$&$N_k$&Mean&$\epsilon_k$\\\midrule']
    for k in range(1,8):
        row=[str(k)]
        for name in data:
            s=data[name]['statistics'][str(k)]
            row.extend([str(s['n']),f"{s['mean']:.2f}",f"{s['dkw_95_simultaneous_14_ecdfs']:.3f}"])
        table.append(' & '.join(row)+r'\\')
    table.append(r'\bottomrule\end{tabular}')
    (ROOT/'monthly/sampling_statistics.tex').write_text('\n'.join(table)+'\n')
    out={name:dict(games=d['completed_games'],statistics=d['statistics'],
                  sample_sha256=hashlib.sha256(sample_path(name).read_bytes()).hexdigest()) for name,d in data.items()}
    (ROOT/'output/sampling').mkdir(parents=True,exist_ok=True)
    (ROOT/'output/sampling/verified.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print('Verified 2,000 complete histories and all sampled scores; seven ECDF panels written.')


if __name__=='__main__':main()

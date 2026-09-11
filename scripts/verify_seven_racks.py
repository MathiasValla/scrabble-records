#!/usr/bin/env python3
"""An explicit two-player deal and draw order for the 97-tile 1786 board."""
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
import verify_1786 as V
from search_two_tile import premium_at

ROOT=Path(__file__).resolve().parents[1]


def main():
    lex=V.Kwg(V.DATA/'NWL23.kwg')
    moves=V.construction_moves()+[V.Move('H','OXYPHENBUTAZONE',tuple((1,c) for c in range(1,16)))]
    board={};history=[]
    for i,move in enumerate(moves):
        new={p:ch for p,ch in zip(move.cells,move.word) if p not in board}
        required=''.join(sorted('?' if p in V.BLANK_ASSIGNMENTS else ch for p,ch in new.items()))
        after=V.validate_forward_move(board,move,lex,first_move=i==0)
        scores=[]
        for w in V.words_on(after):
            if not set(w.cells).intersection(new):continue
            value=0;mult=1
            for p in w.cells:
                v=0 if p in V.BLANK_ASSIGNMENTS else V.LETTER_VALUES[after[p]]
                lm,wm=premium_at(p) if p in new else (1,1)
                value+=lm*v;mult*=wm
            scores.append([w.word,value*mult])
        score=sum(s for _,s in scores)+(50 if len(new)==7 else 0)
        assert score>0
        history.append(dict(move=asdict(move),new_cells=sorted(new),required=required,score=score,word_scores=scores))
        board=after
    assert board==V.board_from_rows() and history[-1]['score']==1786
    assert history[-2]['move']['word']=='LADDERLIKE' and len(history[-2]['required'])==7
    bag=V.TILE_DISTRIBUTION+Counter({'?':2})
    used=Counter(''.join(h['required'] for h in history))
    assert not (used-bag)
    remainder=bag-used
    assert sum(remainder.values())==3
    # Player B reserves exactly the penultimate setup move, and passes until then.
    stream=''.join(h['required'] for h in history[:-2])+history[-1]['required']+''.join(sorted(remainder.elements()))
    racks=[Counter(stream[:7]),Counter(history[-2]['required'])]
    initial=[''.join(sorted(r.elements())) for r in racks]
    bag_order=stream[7:]
    assert sum((Counter(initial[0]),Counter(initial[1]),Counter(bag_order)),Counter())==bag
    actions=[]
    for i,h in enumerate(history):
        player=1 if i==len(history)-2 else 0
        needed=Counter(h['required']);assert not (needed-racks[player])
        before=''.join(sorted(racks[player].elements()))
        racks[player]-=needed
        draw=bag_order[:min(7-sum(racks[player].values()),len(bag_order))]
        bag_order=bag_order[len(draw):];racks[player].update(draw)
        assert i==len(history)-1 or sum(racks[player].values())>0 or bag_order
        actions.append(dict(h,player='AB'[player],rack_before=before,draw_after=draw,
                            rack_after=''.join(sorted(racks[player].elements())),bag_left=len(bag_order)))
        if i<len(history)-3:actions.append(dict(player='B',pass_turn=True))
    assert not racks[0] and sum(racks[1].values())==3 and not bag_order
    out=dict(status='verified',score=1786,final_board_tiles=len(board),initial_racks=initial,
             initial_bag_order=stream[7:],actions=actions,final_racks=[''.join(sorted(r.elements())) for r in racks],
             note='Endgame rack transfers are not part of the ordinary 1786-point move score.')
    (ROOT/'output/seven_rack_certificate.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print('VERIFIED: 1786, full legal board history, deals, alternating turns, draws, and endgame racks.')


if __name__=='__main__':main()

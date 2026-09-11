#!/usr/bin/env python3
"""Independent forward replay, tile accounting, and two-player rack certificate."""
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
import verify_1786 as V
from verify_small_records import move
from verify_one_tile import score_word,check_tile_bag,board_rows

ROOT=Path(__file__).resolve().parents[1]
BLANKS={(6,4),(4,9)}


def main():
    candidate=json.loads((ROOT/'output/CSW24_k6_history_candidate.json').read_text())
    assert candidate['status']=='history found'
    upper=json.loads((ROOT/'output/CSW24_k6_verified_upper.json').read_text())
    assert upper['upper_bound']==1721 and upper['remaining']==0
    moves=[move(h['orientation'],h['word'],h['start'][0]+1,h['start'][1]+1) for h in candidate['forward_history']]
    moves.append(move('H','OXYPHENBUTAZONE',1,1))
    lex=V.Kwg(ROOT/'data/CSW24.kwg');board={};history=[]
    for i,m in enumerate(moves):
        before=board;board=V.validate_forward_move(before,m,lex,first_move=i==0)
        new=set(board)-set(before)
        check_tile_bag(board,BLANKS&set(board))
        words=V.all_formed_words_after_move(before,{p:board[p] for p in new})
        scores=[(w.word,score_word(w,new,BLANKS)) for w in words]
        total=sum(s for _,s in scores)+(50 if len(new)==7 else 0)
        assert total>0
        required=''.join(sorted('?' if p in BLANKS else board[p] for p in new))
        history.append(dict(move=asdict(m),new_cells=sorted(new),rack_required=required,total=total,word_scores=scores))
    assert len(board)==93 and len(history[-1]['new_cells'])==6 and history[-1]['total']==1721
    assert history[-2]['move']['word']=='PACIFYING' and len(history[-2]['new_cells'])==7
    bag=V.TILE_DISTRIBUTION+Counter({'?':2})
    used=Counter(''.join(h['rack_required'] for h in history));assert not(used-bag)
    leftovers=bag-used;assert sum(leftovers.values())==7
    stream=''.join(h['rack_required'] for h in history[:-2])+history[-1]['rack_required']+''.join(sorted(leftovers.elements()))
    racks=[Counter(stream[:7]),Counter(history[-2]['rack_required'])]
    initial=[''.join(sorted(r.elements())) for r in racks];draws=stream[7:];initial_draws=draws
    assert Counter(initial[0]+initial[1]+draws)==bag
    actions=[]
    for i,h in enumerate(history):
        player=1 if i==len(history)-2 else 0
        needed=Counter(h['rack_required']);assert not(needed-racks[player])
        h['rack_before']=''.join(sorted(racks[player].elements()))
        racks[player]-=needed
        draw=draws[:min(7-sum(racks[player].values()),len(draws))];draws=draws[len(draw):]
        racks[player].update(draw)
        h.update(player='AB'[player],draw_after=draw,rack_after=''.join(sorted(racks[player].elements())))
        actions.append(dict(h,bag_left=len(draws)))
        if i<len(history)-3:actions.append(dict(player='B',pass_turn=True))
        assert racks[player] or draws, 'No early go-out is allowed in this construction'
    assert not draws and list(map(lambda r:sum(r.values()),racks))==[1,6]
    assert all(actions[i]['player']!=actions[i+1]['player'] for i in range(len(actions)-1))
    out=dict(lexicon='CSW24',k=6,score=1721,history=history,actions=actions,
             blank_cells=sorted(BLANKS),final_board=board_rows(board),final_board_tiles=len(board),
             initial_racks=initial,initial_bag_order=initial_draws,
             final_racks=[''.join(sorted(r.elements())) for r in racks],
             upper_certificate='CSW24_k6_verified_upper.json')
    (ROOT/'output/CSW24_k6_exact.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print('VERIFIED M6(CSW24) = 1721; 93 tiles; 25 setup moves; complete alternating rack/draw history.')
    print(history[-1]['word_scores']);print('Final rack',history[-1]['rack_before'])


if __name__=='__main__':main()

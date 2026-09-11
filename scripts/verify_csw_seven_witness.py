#!/usr/bin/env python3
"""Independent board, score, blank, and two-player checks for a CSW24 witness."""
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
import verify_1786 as V
from verify_small_records import move
from verify_one_tile import score_word,check_tile_bag,board_rows

ROOT=Path(__file__).resolve().parents[1]


def choose_blanks(before,final):
    new=set(final)-set(before)
    formed=V.all_formed_words_after_move(before,{p:final[p] for p in new})
    real=sum(score_word(w,new,set()) for w in formed)
    counts=Counter(final.values());blanks=set()
    for ch,count in counts.items():
        excess=max(0,count-V.TILE_DISTRIBUTION[ch])
        costs=[]
        for p,a in final.items():
            if a==ch:
                loss=real-sum(score_word(w,new,{p}) for w in formed)
                costs.append((loss,p))
        blanks.update(p for _,p in sorted(costs)[:excess])
    check_tile_bag(final,blanks)
    return blanks


def verify(source,output):
    candidate=json.loads(source.read_text())
    assert candidate['status']=='history found'
    moves=[move(h['orientation'],h['word'],h['start'][0]+1,h['start'][1]+1) for h in candidate['forward_history']]
    moves.append(move('H','OXYPHENBUTAZONE',1,1))
    lex=V.Kwg(ROOT/'data/CSW24.kwg');board={};boards=[]
    for i,m in enumerate(moves):
        board=V.validate_forward_move(board,m,lex,first_move=i==0);boards.append(board)
    assert board_rows(boards[-2])==candidate['rows']
    new=set(boards[-1])-set(boards[-2])
    assert new=={(1,i) for i in candidate['candidate']['record']['indices']} and len(new)==7
    blanks=choose_blanks(boards[-2],boards[-1]);history=[];before={}
    for m,board in zip(moves,boards):
        new=set(board)-set(before)
        check_tile_bag(board,blanks&set(board))
        formed=V.all_formed_words_after_move(before,{p:board[p] for p in new})
        scores=[(w.word,score_word(w,new,blanks)) for w in formed]
        total=sum(s for _,s in scores)+(50 if len(new)==7 else 0)
        assert total>0
        required=''.join(sorted('?' if p in blanks else board[p] for p in new))
        history.append(dict(move=asdict(m),new_cells=sorted(new),rack_required=required,total=total,word_scores=scores))
        before=board
    expected=candidate['candidate']['pre_bingo_score']+50
    assert history[-1]['total']==expected
    assert len(history[-2]['new_cells'])==7 and len(board)<100
    bag=V.TILE_DISTRIBUTION+Counter({'?':2})
    used=Counter(''.join(h['rack_required'] for h in history));assert not(used-bag)
    leftovers=bag-used
    stream=''.join(h['rack_required'] for h in history[:-2])+history[-1]['rack_required']+''.join(sorted(leftovers.elements()))
    racks=[Counter(stream[:7]),Counter(history[-2]['rack_required'])]
    initial=[''.join(sorted(r.elements())) for r in racks];draws=stream[7:];initial_draws=draws
    assert Counter(initial[0]+initial[1]+draws)==bag
    actions=[]
    for i,h in enumerate(history):
        player=1 if i==len(history)-2 else 0
        needed=Counter(h['rack_required']);assert not(needed-racks[player])
        h['rack_before']=''.join(sorted(racks[player].elements()));racks[player]-=needed
        draw=draws[:min(7-sum(racks[player].values()),len(draws))];draws=draws[len(draw):]
        racks[player].update(draw)
        h.update(player='AB'[player],draw_after=draw,rack_after=''.join(sorted(racks[player].elements())))
        actions.append(dict(h,bag_left=len(draws)))
        if i<len(history)-3:actions.append(dict(player='B',pass_turn=True))
        if i<len(history)-1:assert racks[player] or draws,'Premature go-out'
    assert all(actions[i]['player']!=actions[i+1]['player'] for i in range(len(actions)-1))
    out=dict(lexicon='CSW24',k=7,score=expected,history=history,actions=actions,
             blank_cells=sorted(blanks),final_board=board_rows(board),final_board_tiles=len(board),
             initial_racks=initial,initial_bag_order=initial_draws,
             final_racks=[''.join(sorted(r.elements())) for r in racks],
             claim='Certified lower bound; optimality requires the separate upper certificate')
    output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print('VERIFIED attainable CSW24 seven-tile score',expected,'with',len(board),'tiles.',flush=True)
    return out


if __name__=='__main__':
    verify(ROOT/'output/CSW24_k7_history_candidate.json',ROOT/'output/CSW24_k7_witness.json')

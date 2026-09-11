#!/usr/bin/env python3
"""Check the four k=1,2 attainment witnesses and fresh exhaustive outputs."""
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from verify_1786 import (Kwg, Move, LETTER_VALUES, TILE_DISTRIBUTION,
                         validate_forward_move, all_formed_words_after_move)
from verify_one_tile import (NWL23_SEQUENCE, NWL23_FINAL, CSW24_SEQUENCE,
                             CSW24_FINAL, score_word, check_tile_bag, board_rows)
from verify_two_tile import SEQUENCE, FINAL_MOVE, BLANK_CELLS

ROOT = Path(__file__).resolve().parents[1]


def move(orientation, word, row, col):
    return Move(orientation, word, tuple((row+(i if orientation=='V' else 0),
                                          col+(i if orientation=='H' else 0))
                                         for i in range(len(word))))


CSW_TWO = [
    move('V','ALIF',5,8),
    move('H','FIREBOMB',8,8),
    move('V','EAT',8,11),
    move('H','CART',10,8),
    move('V','CAT',10,8),
    move('V','QUALIFICATOR',3,8),
    move('V','BENZENE',8,15),
    move('V','METHOXYBENZENE',1,15),
    move('H','ERA',14,7),
    move('H','HAWKER',15,9),
    move('H','JA',15,6),
]
CSW_TWO_FINAL = move('H','JAYHAWKERS',15,6)


def verify(lexicon, k, sequence, final, blanks, expected):
    lex = Kwg(ROOT/'data'/f'{lexicon}.kwg')
    board, history = {}, []
    for i, m in enumerate(sequence+[final]):
        assert all(1 <= r <= 15 and 1 <= c <= 15 for r,c in m.cells)
        before = board
        board = validate_forward_move(board, m, lex, first_move=(i==0))
        new = set(board)-set(before)
        active_blanks = blanks & set(board)
        check_tile_bag(board, active_blanks)
        formed = all_formed_words_after_move(before, {p:board[p] for p in new})
        scores = [(entry.word, score_word(entry,new,active_blanks)) for entry in formed]
        total = sum(s for _,s in scores)+(50 if len(new)==7 else 0)
        assert total > 0, 'Sparse-history rack lemma requires positive scoring moves'
        history.append(dict(move=asdict(m), new_cells=sorted(new),
                            rack_required=''.join(sorted('?' if p in blanks else board[p] for p in new)),
                            word_scores=scores, bingo=50 if len(new)==7 else 0, total=total))
    assert len(history[-1]['new_cells']) == k
    assert history[-1]['total'] == expected
    assert len(board) <= 86
    counts = Counter('?' if p in blanks else ch for p,ch in board.items())
    full_bag = TILE_DISTRIBUTION + Counter({'?':2})
    leftovers = full_bag-counts
    assert sum(leftovers.values()) >= 7
    opponent_rack = ''.join(sorted(leftovers.elements()))[:7]
    leftovers.subtract(opponent_rack)
    fillers = ''.join(sorted(leftovers.elements()))[:7]
    assert len(fillers)==7
    stream = ''.join(h['rack_required'] for h in history)+fillers
    assert not (Counter(stream)+Counter(opponent_rack)-full_bag)
    rack=Counter(stream[:7])
    offset=7
    for h in history:
        required=Counter(h['rack_required'])
        assert not required-rack
        h['rack_before']=''.join(sorted(rack.elements()))
        rack.subtract(required)
        draw=stream[offset:offset+len(h['rack_required'])]
        offset+=len(draw)
        rack.update(draw)
        assert sum(rack.values())==7
        h['draw_after']=draw
    return dict(lexicon=lexicon, k=k, score=expected, history=history,
                blank_cells=sorted(blanks), final_board=board_rows(board),
                final_board_tiles=len(board), unused_opponent_rack=opponent_rack,
                active_player_draw_stream=stream,
                physical_tile_counts=dict(sorted(counts.items())))


def main():
    witnesses = [
        verify('NWL23',1,NWL23_SEQUENCE,NWL23_FINAL,set(),213),
        verify('CSW24',1,CSW24_SEQUENCE,CSW24_FINAL,set(),225),
        verify('NWL23',2,SEQUENCE,FINAL_MOVE,BLANK_CELLS,459),
        verify('CSW24',2,CSW_TWO,CSW_TWO_FINAL,set(),483),
    ]
    one = json.loads((ROOT/'output/one_tile_certificate.json').read_text())
    for w in witnesses:
        name,k = w['lexicon'],w['k']
        if k==1:
            assert one['upper_bounds'][name]['best_score'] == w['score']
        else:
            result = json.loads((ROOT/'output'/f'{name}_k2_products.json').read_text())
            assert result['best_prebonus'] == w['score']
            assert result['metadata']['threshold'] <= w['score']
            assert len(result['reports']) == result['metadata']['independent_upper_at_least_threshold']
        print(f"{name} k={k}: score={w['score']}, board={w['final_board_tiles']} tiles, {len(w['history'])-1} setup moves, witness OK")
        print(w['history'][-1]['word_scores'])
    contrasts = {}
    for word in ['METHOXYBENZENE','METHOXYBENZENES','QUICKSILVERING','QUICKSILVERINGS',
                 'JAYHAWKERS','QUALIFICATOR','QUALIFICATORY','JA','HAWKER','OPACIFICATIONS']:
        contrasts[word] = {name:Kwg(ROOT/'data'/f'{name}.kwg').contains(word) for name in ['NWL23','CSW24']}
    hashes = {name:hashlib.sha256((ROOT/'data'/f'{name}.kwg').read_bytes()).hexdigest() for name in ['NWL23','CSW24']}
    output = ROOT/'output/small_records_verified.json'
    output.write_text(json.dumps(dict(witnesses=witnesses, contrasts=contrasts, kwg_sha256=hashes),indent=2,sort_keys=True)+'\n')
    print(contrasts)


if __name__=='__main__':
    main()

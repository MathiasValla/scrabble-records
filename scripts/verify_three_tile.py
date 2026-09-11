#!/usr/bin/env python3
"""Verify the NWL23 three-tile Scrabble record certificate found here.

Claim checked:
    In NWL23, no legal three-tile Scrabble move scores more than 882, and 882
    is attained by playing W, S, and S to make WHIPPERSNAPPERS, RICKSHAW,
    OBJECTIVIZES, and DEMISEMIQUAVERS.

The upper-bound portion is delegated to search_three_tile.search, whose search
space is a necessary superset of all legal three-tile moves.  The construction
portion is a literal legal move sequence checked against the NWL23 KWG lexicon.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import json

from search_one_tile import premium_at
from search_three_tile import search
from verify_1786 import (
    Kwg,
    LETTER_VALUES,
    Move,
    TILE_DISTRIBUTION,
    all_formed_words_after_move,
    legal_board,
    validate_forward_move,
    words_on,
)


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "output"


SEQUENCE = [
    Move("V", "OBJECT", tuple((row, 8) for row in range(4, 10))),
    Move("V", "OBJECTIVIZE", tuple((row, 8) for row in range(4, 15))),
    Move("H", "VENDETTA", tuple((11, col) for col in range(8, 16))),
    Move("V", "QUAVER", tuple((row, 15) for row in range(9, 15))),
    Move("V", "SEMIQUAVER", tuple((row, 15) for row in range(5, 15))),
    Move("V", "DEMISEMIQUAVER", tuple((row, 15) for row in range(1, 15))),
    Move("H", "RABIETIC", tuple((8, col) for col in range(1, 9))),
    Move("V", "RICKSHA", tuple((row, 1) for row in range(8, 15))),
    Move("H", "AE", ((14, 7), (14, 8))),
    Move("H", "HIPPER", tuple((15, col) for col in range(2, 8))),
    Move("H", "AR", ((14, 14), (14, 15))),
    Move("H", "NAPPER", tuple((15, col) for col in range(9, 15))),
]

FINAL_MOVE = Move("H", "WHIPPERSNAPPERS", tuple((15, col) for col in range(1, 16)))
FINAL_NEW_CELLS = {(15, 1), (15, 8), (15, 15)}
BLANK_CELLS = {(15, 5), (15, 11)}  # two P's in WHIPPERSNAPPERS


def score_word(entry, new_cells: set[tuple[int, int]], blank_cells: set[tuple[int, int]]) -> int:
    word_multiplier = 1
    letter_sum = 0
    for cell, ch in zip(entry.cells, entry.word):
        value = 0 if cell in blank_cells else LETTER_VALUES[ch]
        if cell in new_cells:
            letter_multiplier, cell_word_multiplier = premium_at(cell)
            value *= letter_multiplier
            word_multiplier *= cell_word_multiplier
        letter_sum += value
    return letter_sum * word_multiplier


def check_tile_bag(board: dict[tuple[int, int], str], blank_cells: set[tuple[int, int]]) -> dict[str, int]:
    counts = Counter(board.values())
    for cell in blank_cells:
        counts[board[cell]] -= 1
    excess = {
        ch: counts[ch] - TILE_DISTRIBUTION[ch]
        for ch in sorted(counts)
        if counts[ch] > TILE_DISTRIBUTION[ch]
    }
    if excess or len(blank_cells) > 2:
        raise AssertionError(f"tile distribution exceeded: excess={excess}, blanks={blank_cells}")
    return dict(sorted(counts.items()))


def board_rows(board: dict[tuple[int, int], str]) -> list[str]:
    return ["".join(board.get((row, col), ".") for col in range(1, 16)) for row in range(1, 16)]


def verify_construction() -> dict[str, object]:
    lexicon = Kwg(DATA / "NWL23.kwg")
    board: dict[tuple[int, int], str] = {}
    move_table = []
    for move_no, move in enumerate(SEQUENCE, start=1):
        before = dict(board)
        board = validate_forward_move(board, move, lexicon, first_move=(move_no == 1))
        move_table.append(
            {
                "move": move_no,
                "word": move.word,
                "tiles_placed": len(set(board) - set(before)),
            }
        )

    ok, bad = legal_board(board, lexicon)
    if not ok:
        raise AssertionError(f"pre-final board is illegal: {bad}")

    before_final = dict(board)
    after_final = validate_forward_move(board, FINAL_MOVE, lexicon)
    new_cells = set(after_final) - set(before_final)
    if new_cells != FINAL_NEW_CELLS:
        raise AssertionError(f"wrong final cells: {new_cells}")

    formed = all_formed_words_after_move(before_final, {cell: after_final[cell] for cell in new_cells})
    formed_words = {entry.word for entry in formed}
    expected_words = {"WHIPPERSNAPPERS", "RICKSHAW", "OBJECTIVIZES", "DEMISEMIQUAVERS"}
    if formed_words != expected_words:
        raise AssertionError(f"formed {formed_words}, expected {expected_words}")

    score_table = [(entry.word, score_word(entry, new_cells, BLANK_CELLS)) for entry in formed]
    total = sum(score for _, score in score_table)
    if total != 882:
        raise AssertionError(f"score {total}, expected 882")

    final_ok, final_bad = legal_board(after_final, lexicon)
    if not final_ok:
        raise AssertionError(f"final board is illegal: {final_bad}")

    counts = check_tile_bag(after_final, BLANK_CELLS)
    return {
        "lexicon": "NWL23",
        "score": total,
        "final_tiles": sorted(new_cells),
        "blank_cells": sorted(BLANK_CELLS),
        "sequence": move_table,
        "pre_final_words": [entry.word for entry in words_on(before_final)],
        "score_table": score_table,
        "tile_counts_with_blanks_removed": counts,
        "final_board": board_rows(after_final),
    }


def main() -> None:
    OUT.mkdir(exist_ok=True)
    upper_bound = search("NWL23", DATA / "NWL23.kwg", initial_best=882, certify_from_initial=True)
    if upper_bound["best_score"] != 882:
        raise AssertionError(f"upper-bound search found {upper_bound['best_score']}, expected 882")
    construction = verify_construction()
    out_path = OUT / "three_tile_certificate.json"
    out_path.write_text(json.dumps({"upper_bound": upper_bound, "construction": construction}, indent=2, sort_keys=True))

    print("\nNWL23 three-tile certificate: OK")
    print("  attained score: 882; run reproduce_release.py for the complete optimality proof")
    print("  final tiles: W at A15, S at H15, S at O15")
    print("  score table:")
    for word, score in construction["score_table"]:
        print(f"    {word:18s} {score:3d}")
    print("  blanks: P at E15 and P at K15")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()

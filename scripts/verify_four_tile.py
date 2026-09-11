#!/usr/bin/env python3
"""Verify the NWL23 four-tile Scrabble record certificate found here.

Claim checked by this script:
    In NWL23, the four-tile score 1130 is attained by playing O, Y, O, and S
    to make OXYHAEMOGLOBINS, BALDACHINO, PLETHYSMOGRAPHY, JOCKO, and
    VENTRILOQUIZES.

The upper-bound enumeration is stored in output/four_tile_certify_search.json
and can be regenerated with:
    python3 -u scripts/search_four_tile.py NWL23 --certify-from-initial --initial-best 1130
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import argparse
import json

from search_four_tile import search
from search_one_tile import premium_at
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
    Move("H", "FIRER", tuple((8, col) for col in range(8, 13))),
    Move("H", "FIREREEL", tuple((8, col) for col in range(8, 16))),
    Move("V", "OSE", tuple((row, 14) for row in range(6, 9))),
    Move("H", "OR", ((6, 14), (6, 15))),
    Move("V", "REFIT", tuple((row, 10) for row in range(8, 13))),
    Move("H", "OSTINATI", tuple((12, col) for col in range(8, 16))),
    Move("V", "QUIZ", tuple((row, 15) for row in range(10, 14))),
    Move("V", "VENTRILOQUIZE", tuple((row, 15) for row in range(2, 15))),
    Move("V", "JOCK", tuple((row, 8) for row in range(11, 15))),
    Move("H", "POETIC", tuple((13, col) for col in range(3, 9))),
    Move("V", "GRAPH", tuple((row, 3) for row in range(10, 15))),
    Move("H", "NAH", tuple((14, col) for col in range(1, 4))),
    Move("V", "AX", ((14, 2), (15, 2))),
    Move("H", "KA", ((14, 8), (14, 9))),
    Move("H", "GLOBIN", tuple((15, col) for col in range(9, 15))),
    Move("V", "ETA", tuple((row, 5) for row in range(13, 16))),
    Move("H", "HAEM", tuple((15, col) for col in range(4, 8))),
    Move("V", "CHI", tuple((row, 1) for row in range(11, 14))),
    Move("V", "BALDACHIN", tuple((row, 1) for row in range(6, 15))),
    Move("H", "BAY", tuple((6, col) for col in range(1, 4))),
    Move("V", "THY", tuple((row, 3) for row in range(4, 7))),
    Move("V", "PLETHYSMOGRAPH", tuple((row, 3) for row in range(1, 15))),
    Move("H", "ADS", tuple((7, col) for col in range(1, 4))),
    Move("H", "AR", ((11, 2), (11, 3))),
    Move("H", "DUO", tuple((9, col) for col in range(1, 4))),
]

FINAL_MOVE = Move("H", "OXYHAEMOGLOBINS", tuple((15, col) for col in range(1, 16)))
FINAL_NEW_CELLS = {(15, 1), (15, 3), (15, 8), (15, 15)}
BLANK_CELLS = {(5, 3), (14, 3)}
EXPECTED_FINAL_WORDS = {
    "OXYHAEMOGLOBINS",
    "BALDACHINO",
    "PLETHYSMOGRAPHY",
    "JOCKO",
    "VENTRILOQUIZES",
}


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
    return dict(sorted((ch, count) for ch, count in counts.items() if count))


def board_rows(board: dict[tuple[int, int], str]) -> list[str]:
    return ["".join(board.get((row, col), ".") for col in range(1, 16)) for row in range(1, 16)]


def verify_upper_bound(*, rerun: bool) -> dict[str, object]:
    if rerun:
        result = search("NWL23", DATA / "NWL23.kwg", initial_best=1130, certify_from_initial=True)
    else:
        path = OUT / "four_tile_certify_search.json"
        result = json.loads(path.read_text())["NWL23"]
    if result["best_score"] != 1130:
        raise AssertionError(f"upper-bound search reports {result['best_score']}, expected 1130")
    return result


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
    if formed_words != EXPECTED_FINAL_WORDS:
        raise AssertionError(f"formed {formed_words}, expected {EXPECTED_FINAL_WORDS}")

    score_table = [(entry.word, score_word(entry, new_cells, BLANK_CELLS)) for entry in formed]
    total = sum(score for _, score in score_table)
    if total != 1130:
        raise AssertionError(f"score {total}, expected 1130")

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
    parser = argparse.ArgumentParser()
    parser.add_argument("--rerun-upper-bound", action="store_true")
    args = parser.parse_args()

    OUT.mkdir(exist_ok=True)
    upper_bound = verify_upper_bound(rerun=args.rerun_upper_bound)
    construction = verify_construction()
    out_path = OUT / "four_tile_certificate.json"
    out_path.write_text(json.dumps({"upper_bound": upper_bound, "construction": construction}, indent=2, sort_keys=True))

    print("\nNWL23 four-tile certificate: OK")
    print("  attained score: 1130; run reproduce_release.py for the complete optimality proof")
    print("  final tiles: O at A15, Y at C15, O at H15, S at O15")
    print("  score table:")
    for word, score in construction["score_table"]:
        print(f"    {word:18s} {score:4d}")
    print("  blanks: H at C5 and H at C14")
    print(f"  upper-bound placements: {upper_bound['main_placements']:,}")
    print(f"  exact main placements checked: {upper_bound['checked_main_placements_exactly']:,}")
    print(f"  exact cross products checked: {upper_bound['checked_cross_quadruples']:,}")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Verify the best one-tile Scrabble moves in NWL23 and CSW24.

This script is a certificate checker for two claims:

* In NWL23, the maximum score of a legal one-tile move is 213.
* In CSW24, the maximum score of a legal one-tile move is 225.

For each lexicon it checks both sides of the proof:

1. an exhaustive blank-aware upper-bound search over all locally legal
   one-tile scoring patterns; and
2. a concrete legal sequence reaching a board on which the claimed one-tile
   move attains the bound.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import json

from search_one_tile import premium_at, search
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


NWL23_SEQUENCE = [
    Move("H", "AMNESIA", tuple((8, col) for col in range(8, 15))),
    Move("V", "TECH", tuple((row, 15) for row in range(6, 10))),
    Move("V", "TECHNIQUE", tuple((row, 15) for row in range(6, 15))),
    Move("V", "MICROTECHNIQUE", tuple((row, 15) for row in range(1, 15))),
    Move("H", "RE", ((14, 14), (14, 15))),
    Move("H", "ZINE", tuple((15, col) for col in range(11, 15))),
    Move("H", "HYDROXYZINE", tuple((15, col) for col in range(4, 15))),
]

NWL23_FINAL = Move("H", "HYDROXYZINES", tuple((15, col) for col in range(4, 16)))


CSW24_SEQUENCE = [
    Move("H", "ANTENNA", tuple((8, col) for col in range(8, 15))),
    Move("V", "SILVER", tuple((row, 15) for row in range(6, 12))),
    Move("V", "SILVERING", tuple((row, 15) for row in range(6, 15))),
    Move("V", "QUICKSILVERING", tuple((row, 15) for row in range(1, 15))),
    Move("H", "AG", ((14, 14), (14, 15))),
    Move("H", "BENZENE", tuple((15, col) for col in range(8, 15))),
    Move("H", "METHOXYBENZENE", tuple((15, col) for col in range(1, 15))),
]

CSW24_FINAL = Move("H", "METHOXYBENZENES", tuple((15, col) for col in range(1, 16)))


def score_word(entry, new_cells: set[tuple[int, int]], blank_cells: set[tuple[int, int]]) -> int:
    word_multiplier = 1
    letter_sum = 0
    for cell, ch in zip(entry.cells, entry.word):
        letter_score = 0 if cell in blank_cells else LETTER_VALUES[ch]
        if cell in new_cells:
            letter_multiplier, cell_word_multiplier = premium_at(cell)
            letter_score *= letter_multiplier
            word_multiplier *= cell_word_multiplier
        letter_sum += letter_score
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


def verify_construction(
    lexicon_name: str,
    kwg_path: Path,
    sequence: list[Move],
    final_move: Move,
    expected_score: int,
    expected_words: set[str],
) -> dict[str, object]:
    lexicon = Kwg(kwg_path)
    board: dict[tuple[int, int], str] = {}
    move_rows = []
    for move_no, move in enumerate(sequence, start=1):
        before = dict(board)
        board = validate_forward_move(board, move, lexicon, first_move=(move_no == 1))
        move_rows.append(
            {
                "move": move_no,
                "word": move.word,
                "tiles_placed": len(set(board) - set(before)),
            }
        )

    ok, bad = legal_board(board, lexicon)
    if not ok:
        raise AssertionError(f"{lexicon_name} pre-final board is illegal: {bad}")

    before_final = dict(board)
    after_final = validate_forward_move(board, final_move, lexicon)
    new_cells = set(after_final) - set(before_final)
    if len(new_cells) != 1:
        raise AssertionError(f"{lexicon_name} final move placed {len(new_cells)} tiles, not one")

    formed = all_formed_words_after_move(before_final, {cell: after_final[cell] for cell in new_cells})
    formed_words = {entry.word for entry in formed}
    if formed_words != expected_words:
        raise AssertionError(f"{lexicon_name} formed {formed_words}, expected {expected_words}")

    score_rows = [(entry.word, score_word(entry, new_cells, set())) for entry in formed]
    total = sum(score for _, score in score_rows)
    if total != expected_score:
        raise AssertionError(f"{lexicon_name} score {total}, expected {expected_score}")

    final_ok, final_bad = legal_board(after_final, lexicon)
    if not final_ok:
        raise AssertionError(f"{lexicon_name} final board is illegal: {final_bad}")

    counts = check_tile_bag(after_final, set())
    return {
        "lexicon": lexicon_name,
        "expected_score": expected_score,
        "new_cell": sorted(new_cells)[0],
        "sequence": move_rows,
        "pre_final_words": [entry.word for entry in words_on(before_final)],
        "score_table": score_rows,
        "tile_counts_without_blanks": counts,
        "final_board": board_rows(after_final),
    }


def main() -> None:
    OUT.mkdir(exist_ok=True)
    upper_bounds = {
        "NWL23": search("NWL23", DATA / "NWL23.kwg"),
        "CSW24": search("CSW24", DATA / "CSW24.kwg"),
    }
    if upper_bounds["NWL23"]["best_score"] != 213:
        raise AssertionError("NWL23 upper-bound search did not return 213")
    if upper_bounds["CSW24"]["best_score"] != 225:
        raise AssertionError("CSW24 upper-bound search did not return 225")

    constructions = {
        "NWL23": verify_construction(
            "NWL23",
            DATA / "NWL23.kwg",
            NWL23_SEQUENCE,
            NWL23_FINAL,
            213,
            {"HYDROXYZINES", "MICROTECHNIQUES"},
        ),
        "CSW24": verify_construction(
            "CSW24",
            DATA / "CSW24.kwg",
            CSW24_SEQUENCE,
            CSW24_FINAL,
            225,
            {"METHOXYBENZENES", "QUICKSILVERINGS"},
        ),
    }

    certificate = {"upper_bounds": upper_bounds, "constructions": constructions}
    out_path = OUT / "one_tile_certificate.json"
    out_path.write_text(json.dumps(certificate, indent=2, sort_keys=True))

    for name, construction in constructions.items():
        print(f"\n{name} certificate: OK")
        print(f"  one-tile score: {construction['expected_score']}")
        print(f"  final tile: {construction['new_cell']}")
        print("  score table:")
        for word, score in construction["score_table"]:
            print(f"    {word:18s} {score:3d}")
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()

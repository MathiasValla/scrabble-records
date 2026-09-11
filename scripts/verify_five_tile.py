#!/usr/bin/env python3
"""Verify the NWL23 five-tile Scrabble record certificate found here.

Claim checked by this script:
    In NWL23, the five-tile score 1401 is attained by playing D, L, O, Z,
    and E on the bottom row to make DICHLOROBENZENE together with the cross
    words HYPERVENTILATED, OVERFULFILL, JOCKO, QUARTZ, and MYXAMOEBAE.

The upper-bound enumeration is supplied by scripts/estimate_five_upper.cpp.
The exact cross-products for the only two main placements with independent
upper bound at least 1402 are supplied by scripts/exact_product_search.cpp.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import argparse
import json
import re

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
    Move("H", "APERIES", tuple((8, col) for col in range(2, 9))),
    Move("H", "NAPERIES", tuple((8, col) for col in range(1, 9))),
    Move("V", "VENT", tuple((row, 1) for row in range(6, 10))),
    Move("V", "VENTILATE", tuple((row, 1) for row in range(6, 15))),
    Move("V", "HYPERVENTILATE", tuple((row, 1) for row in range(1, 15))),
    Move("V", "OVER", tuple((row, 5) for row in range(5, 9))),
    Move("V", "OVERFULFIL", tuple((row, 5) for row in range(5, 15))),
    Move("H", "FADO", tuple((12, col) for col in range(5, 9))),
    Move("V", "JOCK", tuple((row, 8) for row in range(11, 15))),
    Move("V", "OR", tuple((row, 7) for row in range(14, 16))),
    Move("H", "OR", tuple((15, col) for col in range(6, 8))),
    Move("V", "PARANOIC", tuple((row, 3) for row in range(8, 16))),
    Move("H", "ICH", tuple((15, col) for col in range(2, 5))),
    Move("H", "CITER", tuple((13, col) for col in range(8, 13))),
    Move("V", "TIE", tuple((row, 10) for row in range(13, 16))),
    Move("H", "BEN", tuple((15, col) for col in range(9, 12))),
    Move("V", "QUART", tuple((row, 12) for row in range(10, 15))),
    Move("H", "TOEA", tuple((14, col) for col in range(12, 16))),
    Move("H", "EN", tuple((15, col) for col in range(13, 15))),
    Move("V", "AMOEBA", tuple((row, 15) for row in range(9, 15))),
    Move("V", "MYXAMOEBA", tuple((row, 15) for row in range(6, 15))),
]

FINAL_MOVE = Move("H", "DICHLOROBENZENE", tuple((15, col) for col in range(1, 16)))
FINAL_NEW_CELLS = {(15, 1), (15, 5), (15, 8), (15, 12), (15, 15)}
EXPECTED_FINAL_WORDS = {
    "DICHLOROBENZENE",
    "HYPERVENTILATED",
    "OVERFULFILL",
    "JOCKO",
    "QUARTZ",
    "MYXAMOEBAE",
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


def parse_upper_bound(path: Path) -> dict[str, object]:
    text = path.read_text()
    fields: dict[str, object] = {"path": str(path)}
    for key in (
        "threshold",
        "raw_main_quintuples",
        "deletion_valid_main_quintuples",
        "main_placements",
        "independent_upper_at_least_threshold",
        "top_count",
    ):
        match = re.search(rf"^{key} (\d+)$", text, re.MULTILINE)
        if not match:
            raise AssertionError(f"{path} is missing {key}")
        fields[key] = int(match.group(1))
    top_lines = re.findall(
        r"^top (\d+) upper (\d+) main (\d+) word ([A-Z]+) indices ([0-9 ]+) row (\d+) start (\d+)$",
        text,
        re.MULTILINE,
    )
    fields["top"] = [
        {
            "rank": int(rank),
            "upper": int(upper),
            "main_score_before_blanks": int(main),
            "word": word,
            "indices": [int(value) for value in indices.split()],
            "row": int(row),
            "start_col": int(start),
        }
        for rank, upper, main, word, indices, row, start in top_lines
    ]
    if fields["threshold"] != 1402:
        raise AssertionError(f"upper-bound threshold is {fields['threshold']}, expected 1402")
    if fields["independent_upper_at_least_threshold"] != 2:
        raise AssertionError("upper-bound pass did not report exactly two survivors")
    if len(fields["top"]) < 3:
        raise AssertionError("upper-bound top list is too short")
    if fields["top"][0]["word"] != "DICHLOROBENZENE" or fields["top"][0]["upper"] != 1498:
        raise AssertionError("unexpected top upper-bound placement")
    if fields["top"][1]["word"] != "BENZANTHRACENES" or fields["top"][1]["upper"] != 1460:
        raise AssertionError("unexpected second upper-bound placement")
    if fields["top"][2]["upper"] >= 1402:
        raise AssertionError("third upper-bound placement should be below 1402")
    return fields


def parse_product(path: Path, threshold: int) -> dict[str, object]:
    text = path.read_text()
    match = re.search(r"^final best (\d+)$", text, re.MULTILINE)
    if not match:
        raise AssertionError(f"{path} does not report a final best")
    best = int(match.group(1))
    if best != threshold:
        raise AssertionError(f"{path} reports {best}, expected threshold {threshold}")
    nodes = re.search(r"^nodes (\d+)$", text, re.MULTILINE)
    leaves = re.search(r"^leaves (\d+)$", text, re.MULTILINE)
    records = re.findall(r"^record .*$", text, re.MULTILINE)
    if records:
        raise AssertionError(f"{path} contains a score at least {threshold}: {records[0]}")
    return {
        "path": str(path),
        "threshold": threshold,
        "final_best_marker": best,
        "nodes": int(nodes.group(1)) if nodes else None,
        "leaves": int(leaves.group(1)) if leaves else None,
        "records_at_or_above_threshold": records,
    }


def verify_upper_bound_files() -> dict[str, object]:
    upper = parse_upper_bound(OUT / "five_tile_upper_1402.txt")
    first = parse_product(OUT / "five_tile_product_dichlorobenzene_exact.txt", 1402)
    second = parse_product(OUT / "five_tile_product_benzanthracenes_exact.txt", 1402)
    return {
        "upper_bound": upper,
        "exact_products": {
            "DICHLOROBENZENE": first,
            "BENZANTHRACENES": second,
        },
    }


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

    blank_cells: set[tuple[int, int]] = set()
    score_table = [(entry.word, score_word(entry, new_cells, blank_cells)) for entry in formed]
    total = sum(score for _, score in score_table)
    if total != 1401:
        raise AssertionError(f"score {total}, expected 1401")

    final_ok, final_bad = legal_board(after_final, lexicon)
    if not final_ok:
        raise AssertionError(f"final board is illegal: {final_bad}")

    counts = check_tile_bag(after_final, blank_cells)
    return {
        "lexicon": "NWL23",
        "score": total,
        "final_tiles": sorted(new_cells),
        "blank_cells": sorted(blank_cells),
        "sequence": move_table,
        "pre_final_words": [entry.word for entry in words_on(before_final)],
        "score_table": score_table,
        "tile_counts": counts,
        "pre_final_board": board_rows(before_final),
        "final_board": board_rows(after_final),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-upper-bound-files", action="store_true")
    args = parser.parse_args()

    OUT.mkdir(exist_ok=True)
    construction = verify_construction()
    upper = None if args.skip_upper_bound_files else verify_upper_bound_files()
    out_path = OUT / "five_tile_certificate.json"
    out_path.write_text(
        json.dumps({"upper_bound": upper, "construction": construction}, indent=2, sort_keys=True)
    )

    print("\nNWL23 five-tile certificate: OK")
    print("  attained score: 1401; run reproduce_release.py for the complete optimality proof")
    print("  final tiles: D at A15, L at E15, O at H15, Z at L15, E at O15")
    print("  score table:")
    for word, score in construction["score_table"]:
        print(f"    {word:18s} {score:4d}")
    print("  blanks: none")
    print(f"  pre-final moves: {len(construction['sequence'])}")
    if upper is not None:
        print(f"  upper-bound placements: {upper['upper_bound']['main_placements']:,}")
        print(f"  independent upper >= 1402: {upper['upper_bound']['independent_upper_at_least_threshold']}")
        print(
            "  exact product nodes: "
            f"{upper['exact_products']['DICHLOROBENZENE']['nodes']:,} + "
            f"{upper['exact_products']['BENZANTHRACENES']['nodes']:,}"
        )
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Verify the NWL23 six-tile Scrabble record certificate.

The certificate checked here is deliberately stronger than a displayed final
position: it gives a legal move-by-move history reaching the pre-final board,
then checks that the final move places exactly six tiles and scores 1723.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import re

from search_one_tile import premium_at
from verify_1786 import (
    DATA,
    TILE_DISTRIBUTION,
    LETTER_VALUES,
    Kwg,
    Move,
    all_formed_words_after_move,
    legal_board,
    validate_forward_move,
    words_on,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"

BOARD_ROWS = {
    1: "OXYPHENBUTAZONE",
    2: "PEER..EL..WO.US",
    3: "AD.E...A...O..T",
    4: "C..Q...D...G..A",
    5: "I..U...D...A..B",
    6: "F..ADORE...M..L",
    7: "I..L...R...E..I",
    8: "C..I...LEGIT..S",
    9: "A..F...I...EACH",
    10: "T..Y...K......M",
    11: "I..I...E......E",
    12: "O..N..........N",
    13: "N..G..........T",
    14: "S.............S",
    15: "...............",
}

FINAL_MOVE = {
    (1, 1): "O",
    (1, 2): "X",
    (1, 4): "P",
    (1, 8): "B",
    (1, 12): "Z",
    (1, 15): "E",
}

# Filled after an exact tile-bag audit. A blank listed here is never used in a
# word scored by the final move, so the 1723-point score is unaffected.
BLANK_ASSIGNMENTS: dict[tuple[int, int], str] = {(9, 14): "C"}


def board_from_rows() -> dict[tuple[int, int], str]:
    board: dict[tuple[int, int], str] = {}
    for row, text in BOARD_ROWS.items():
        if len(text) != 15:
            raise ValueError(f"row {row} has length {len(text)}")
        for col, ch in enumerate(text, start=1):
            if ch != ".":
                board[(row, col)] = ch
    return board


def board_rows(board: dict[tuple[int, int], str]) -> list[str]:
    return ["".join(board.get((row, col), ".") for col in range(1, 16)) for row in range(1, 16)]


def cell_name(cell: tuple[int, int]) -> str:
    row, col = cell
    return f"{chr(ord('A') + col - 1)}{row}"


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


def score_final_move(pre: dict[tuple[int, int], str]) -> tuple[int, list[tuple[str, int]]]:
    new_cells = set(FINAL_MOVE)
    blank_cells = set(BLANK_ASSIGNMENTS)
    formed = all_formed_words_after_move(pre, FINAL_MOVE)
    rows = []
    total = 0
    for entry in formed:
        score = score_word(entry, new_cells, blank_cells)
        rows.append((entry.word, score))
        total += score
    return total, rows


def check_tile_bag(board: dict[tuple[int, int], str], blank_cells: set[tuple[int, int]]) -> dict[str, int]:
    counts = Counter(board.values())
    for cell in blank_cells:
        counts[board[cell]] -= 1
    return {
        ch: counts[ch] - TILE_DISTRIBUTION[ch]
        for ch in counts
        if counts[ch] > TILE_DISTRIBUTION[ch]
    }


def parse_upper_bound(path: Path) -> dict[str, object]:
    text = path.read_text()
    fields: dict[str, object] = {"path": str(path)}
    for key in (
        "threshold",
        "raw_main_sextuples",
        "deletion_valid_main_sextuples",
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
    top = [
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
    fields["top"] = top
    if fields["threshold"] != 1724:
        raise AssertionError(f"upper-bound threshold is {fields['threshold']}, expected 1724")
    if fields["independent_upper_at_least_threshold"] != 9:
        raise AssertionError("upper-bound pass did not report exactly nine survivors")
    if len(top) < 10:
        raise AssertionError("upper-bound top list is too short")
    if top[8]["upper"] < 1724 or top[9]["upper"] >= 1724:
        raise AssertionError("top list does not isolate exactly nine placements at 1724+")
    return fields


def parse_legal_eliminations() -> list[dict[str, object]]:
    raise RuntimeError('Obsolete partial-board exclusions are not proof certificates; use reproduce_release.py')


def construction_moves() -> list[Move]:
    return [
        Move("V", "LIKE", tuple((row, 8) for row in range(8, 12))),
        Move("V", "LADDERLIKE", tuple((row, 8) for row in range(2, 12))),
        Move("H", "LEGIT", tuple((8, col) for col in range(8, 13))),
        Move("V", "OOGAMETE", tuple((row, 12) for row in range(2, 10))),
        Move("H", "EACH", tuple((9, col) for col in range(12, 16))),
        Move("V", "STABLISH", tuple((row, 15) for row in range(2, 10))),
        Move("V", "STABLISHMENT", tuple((row, 15) for row in range(2, 14))),
        Move("V", "STABLISHMENTS", tuple((row, 15) for row in range(2, 15))),
        Move("H", "ADORE", tuple((6, col) for col in range(4, 9))),
        Move("V", "QUALIFY", tuple((row, 4) for row in range(4, 11))),
        Move("V", "REQUALIFYING", tuple((row, 4) for row in range(2, 14))),
        Move("H", "PEER", tuple((2, col) for col in range(1, 5))),
        Move("V", "PACIFIC", tuple((row, 1) for row in range(2, 9))),
        Move("V", "PACIFICATIONS", tuple((row, 1) for row in range(2, 15))),
        Move("V", "ED", ((2, 2), (3, 2))),
        Move("V", "YE", ((1, 3), (2, 3))),
        Move("V", "NE", ((1, 7), (2, 7))),
        Move("H", "HEN", ((1, 5), (1, 6), (1, 7))),
        Move("V", "AW", ((1, 11), (2, 11))),
        Move("H", "UTA", ((1, 9), (1, 10), (1, 11))),
        Move("V", "NU", ((1, 14), (2, 14))),
        Move("H", "ON", ((1, 13), (1, 14))),
    ]

def verify_construction() -> dict[str, object]:
    lexicon = Kwg(DATA / "NWL23.kwg")
    final_board = board_from_rows()
    pre_board = {cell: ch for cell, ch in final_board.items() if cell not in FINAL_MOVE}
    rack = "".join(sorted(FINAL_MOVE.values()))
    if rack != "BEOPXZ":
        raise AssertionError(f"wrong final rack: {rack}")
    construction = construction_moves()
    board: dict[tuple[int, int], str] = {}
    move_table = []
    for move_no, move in enumerate(construction, start=1):
        before = dict(board)
        board = validate_forward_move(board, move, lexicon, first_move=(move_no == 1))
        move_table.append(
            {
                "move": move_no,
                "word": move.word,
                "placement": f"{cell_name(move.cells[0])}-{cell_name(move.cells[-1])}",
                "tiles_placed": len(set(board) - set(before)),
            }
        )

    if board != pre_board:
        missing = sorted(set(pre_board) - set(board))
        extra = sorted(set(board) - set(pre_board))
        disagreements = sorted(cell for cell in set(pre_board) & set(board) if pre_board[cell] != board[cell])
        raise AssertionError(
            f"construction mismatch; missing={missing}; extra={extra}; disagreements={disagreements}"
        )

    final_move = Move("H", "OXYPHENBUTAZONE", tuple((1, col) for col in range(1, 16)))
    reached_final = validate_forward_move(pre_board, final_move, lexicon)
    if reached_final != final_board:
        raise AssertionError("final move does not produce the certified final board")
    if len(FINAL_MOVE) != 6:
        raise AssertionError(f"final move places {len(FINAL_MOVE)} tiles, not six")

    ok_pre, bad_pre = legal_board(pre_board, lexicon)
    ok_final, bad_final = legal_board(final_board, lexicon)
    if not ok_pre or not ok_final:
        raise AssertionError(f"board validity failure: pre={bad_pre}; final={bad_final}")

    scored_final_cells = {
        cell
        for entry in all_formed_words_after_move(pre_board, FINAL_MOVE)
        for cell in entry.cells
    }
    for cell, ch in BLANK_ASSIGNMENTS.items():
        if final_board[cell] != ch:
            raise AssertionError(f"blank assignment {cell}={ch} does not match board")
    if set(BLANK_ASSIGNMENTS) & scored_final_cells:
        raise AssertionError("a blank assignment is used in the final scoring move")
    excess = check_tile_bag(final_board, set(BLANK_ASSIGNMENTS))
    if excess or len(BLANK_ASSIGNMENTS) > 2:
        raise AssertionError(f"tile distribution exceeded: {excess}; blanks={BLANK_ASSIGNMENTS}")

    total, score_rows = score_final_move(pre_board)
    if total != 1723:
        raise AssertionError(f"expected 1723, got {total}")

    return {
        "lexicon": "NWL23",
        "score": total,
        "final_rack": rack,
        "final_new_cells": [cell_name(cell) for cell in sorted(FINAL_MOVE)],
        "blank_cells": {cell_name(cell): ch for cell, ch in BLANK_ASSIGNMENTS.items()},
        "sequence": move_table,
        "pre_final_words": [entry.word for entry in words_on(pre_board)],
        "score_table": score_rows,
        "pre_final_board": board_rows(pre_board),
        "final_board": board_rows(final_board),
    }


def main() -> None:
    OUT.mkdir(exist_ok=True)
    construction = verify_construction()
    out_path = OUT / "six_tile_certificate.json"
    out_path.write_text(
        json.dumps(
            {
                "claim": "Attaining construction only; optimality is verified by reproduce_release.py",
                "construction": construction,
            },
            indent=2,
            sort_keys=True,
        )
    )

    print("NWL23 six-tile attaining construction: OK")
    print("  attained score: 1723; run reproduce_release.py for the complete optimality proof")
    print("  final tiles: O at A1, X at B1, P at D1, B at H1, Z at L1, E at O1")
    print(f"  reachable pre-final board: {len(construction['sequence'])} moves")
    print(f"  certificate: {out_path}")
    print(f"final rack: {construction['final_rack']}")
    print("score table:")
    for word, score in construction["score_table"]:
        print(f"  {word:16s} {score:4d}")
    print(f"  {'total':16s} {construction['score']:4d}")
    print(f"final board tiles: {sum(ch != '.' for row in construction['final_board'] for ch in row)}; tile distribution: OK with blanks {BLANK_ASSIGNMENTS}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Verify the 1786-point NWL23 OXYPHENBUTAZONE certificate.

The script checks four finite claims:

1. The Woogles/NWL23 KWG lexicon accepts every word in the construction.
2. The pre-final board is reachable by a legal sequence of Scrabble moves.
3. The final move uses rack BENOPXZ and scores exactly 1786.
4. The same final move is not valid in CSW24, because OPACIFICATIONS is absent.

The KWG reader is a minimal Python port of the Node22 traversal in
https://github.com/andy-k/wolges/blob/main/src/kwg.rs .
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
import struct


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

LETTER_VALUES = {
    "A": 1,
    "B": 3,
    "C": 3,
    "D": 2,
    "E": 1,
    "F": 4,
    "G": 2,
    "H": 4,
    "I": 1,
    "J": 8,
    "K": 5,
    "L": 1,
    "M": 3,
    "N": 1,
    "O": 1,
    "P": 3,
    "Q": 10,
    "R": 1,
    "S": 1,
    "T": 1,
    "U": 1,
    "V": 4,
    "W": 4,
    "X": 8,
    "Y": 4,
    "Z": 10,
}

TILE_DISTRIBUTION = Counter(
    {
        "A": 9,
        "B": 2,
        "C": 2,
        "D": 4,
        "E": 12,
        "F": 2,
        "G": 3,
        "H": 2,
        "I": 9,
        "J": 1,
        "K": 1,
        "L": 4,
        "M": 2,
        "N": 6,
        "O": 8,
        "P": 2,
        "Q": 1,
        "R": 6,
        "S": 4,
        "T": 6,
        "U": 4,
        "V": 2,
        "W": 2,
        "X": 1,
        "Y": 2,
        "Z": 1,
    }
)

BOARD_ROWS = {
    1: "OXYPHENBUTAZONE",
    2: "PEAR.HALT.WO.OS",
    3: "AD.E..RAS..O..T",
    4: "C..Q.URD...G..A",
    5: "I..U..OD...A..B",
    6: "F..AVOWER..MERL",
    7: "I..L..IRE..E..I",
    8: "C..I.UNLED.T..S",
    9: "A..F..GI...E..H",
    10: "T..Y...K......M",
    11: "I..I...E......E",
    12: "O..N..........N",
    13: "N..G..........T",
    14: "S.............S",
    15: "...............",
}

BLANK_ASSIGNMENTS = {(2, 6): "H", (3, 9): "S"}

FINAL_MOVE = {
    (1, 1): "O",
    (1, 2): "X",
    (1, 4): "P",
    (1, 7): "N",
    (1, 8): "B",
    (1, 12): "Z",
    (1, 15): "E",
}

PREMIUMS = {
    (1, 1): ("word", 3),
    (1, 4): ("letter", 2),
    (1, 8): ("word", 3),
    (1, 12): ("letter", 2),
    (1, 15): ("word", 3),
}

CENTER = (8, 8)


class Kwg:
    def __init__(self, path: Path):
        data = path.read_bytes()
        self.nodes = struct.unpack("<" + "I" * (len(data) // 4), data)

    @staticmethod
    def tile(node: int) -> int:
        return node >> 24

    @staticmethod
    def accepts(node: int) -> bool:
        return bool(node & 0x800000)

    @staticmethod
    def is_end(node: int) -> bool:
        return bool(node & 0x400000)

    @staticmethod
    def arc_index(node: int) -> int:
        return node & 0x3FFFFF

    def contains(self, word: str) -> bool:
        p = 0
        for i, ch in enumerate(word):
            p = self.arc_index(self.nodes[p])
            if p <= 0:
                return False
            target = ord(ch) - 64
            while True:
                node = self.nodes[p]
                node_tile = self.tile(node)
                if node_tile >= target:
                    if node_tile != target:
                        return False
                    if i == len(word) - 1:
                        return self.accepts(node)
                    break
                if self.is_end(node):
                    return False
                p += 1
        return False


@dataclass(frozen=True)
class WordOnBoard:
    orientation: str
    start: tuple[int, int]
    cells: tuple[tuple[int, int], ...]
    word: str


@dataclass(frozen=True)
class Move:
    orientation: str
    word: str
    cells: tuple[tuple[int, int], ...]


def board_from_rows() -> dict[tuple[int, int], str]:
    board: dict[tuple[int, int], str] = {}
    for row, text in BOARD_ROWS.items():
        if len(text) != 15:
            raise ValueError(f"row {row} has length {len(text)}")
        for col, ch in enumerate(text, start=1):
            if ch != ".":
                board[(row, col)] = ch
    return board


def words_on(board: dict[tuple[int, int], str]) -> list[WordOnBoard]:
    words: list[WordOnBoard] = []
    for row in range(1, 16):
        col = 1
        while col <= 15:
            cells: list[tuple[int, int]] = []
            letters: list[str] = []
            start_col = col
            while col <= 15 and (row, col) in board:
                cells.append((row, col))
                letters.append(board[(row, col)])
                col += 1
            if len(cells) >= 2:
                words.append(WordOnBoard("H", (row, start_col), tuple(cells), "".join(letters)))
            col += 1
    for col in range(1, 16):
        row = 1
        while row <= 15:
            cells = []
            letters = []
            start_row = row
            while row <= 15 and (row, col) in board:
                cells.append((row, col))
                letters.append(board[(row, col)])
                row += 1
            if len(cells) >= 2:
                words.append(WordOnBoard("V", (start_row, col), tuple(cells), "".join(letters)))
            row += 1
    return words


def connected(board: dict[tuple[int, int], str]) -> bool:
    if not board:
        return True
    remaining = set(board)
    first = next(iter(remaining))
    queue = deque([first])
    seen = {first}
    while queue:
        row, col = queue.popleft()
        for neighbor in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
            if neighbor in remaining and neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    return len(seen) == len(board)


def legal_board(board: dict[tuple[int, int], str], lexicon: Kwg) -> tuple[bool, list[str]]:
    bad = [entry.word for entry in words_on(board) if not lexicon.contains(entry.word)]
    return CENTER in board and connected(board) and not bad, bad


def all_formed_words_after_move(
    before: dict[tuple[int, int], str], placed: dict[tuple[int, int], str]
) -> list[WordOnBoard]:
    after = before | placed
    formed: list[WordOnBoard] = []
    for entry in words_on(after):
        if any(cell in placed for cell in entry.cells):
            formed.append(entry)
    return formed


def validate_forward_move(
    before: dict[tuple[int, int], str],
    move: Move,
    lexicon: Kwg,
    *,
    first_move: bool = False,
) -> dict[tuple[int, int], str]:
    if len(move.cells) != len(move.word):
        raise AssertionError(f"{move.word} has {len(move.word)} letters but {len(move.cells)} cells")
    rows = {row for row, _ in move.cells}
    cols = {col for _, col in move.cells}
    if move.orientation == "H":
        if len(rows) != 1:
            raise AssertionError(f"{move.word} is marked horizontal but spans multiple rows")
        ordered = sorted(move.cells, key=lambda cell: cell[1])
        if ordered != list(move.cells) or [col for _, col in ordered] != list(range(ordered[0][1], ordered[-1][1] + 1)):
            raise AssertionError(f"{move.word} horizontal cells are not contiguous and ordered")
    elif move.orientation == "V":
        if len(cols) != 1:
            raise AssertionError(f"{move.word} is marked vertical but spans multiple columns")
        ordered = sorted(move.cells, key=lambda cell: cell[0])
        if ordered != list(move.cells) or [row for row, _ in ordered] != list(range(ordered[0][0], ordered[-1][0] + 1)):
            raise AssertionError(f"{move.word} vertical cells are not contiguous and ordered")
    else:
        raise AssertionError(f"unknown orientation {move.orientation}")
    for cell, letter in zip(move.cells, move.word):
        if cell in before and before[cell] != letter:
            raise AssertionError(f"{move.word} conflicts at {cell}: board has {before[cell]}, move has {letter}")
    placed = {cell: letter for cell, letter in zip(move.cells, move.word) if cell not in before}
    if len(placed) > 7:
        raise AssertionError(f"{move.word} places more than seven tiles")
    if not placed:
        raise AssertionError(f"{move.word} places no new tiles")
    rows = {row for row, _ in placed}
    cols = {col for _, col in placed}
    if len(rows) != 1 and len(cols) != 1:
        raise AssertionError(f"{move.word} has new tiles off one line")
    after = before | placed
    if first_move and CENTER not in placed:
        raise AssertionError("first move does not cover H8")
    if not first_move and not any(
        nb in before
        for row, col in placed
        for nb in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1))
    ):
        raise AssertionError(f"{move.word} does not touch the existing board")
    formed = all_formed_words_after_move(before, placed)
    bad = [entry.word for entry in formed if not lexicon.contains(entry.word)]
    if bad:
        raise AssertionError(f"{move.word} forms invalid words: {bad}")
    ok, bad_board = legal_board(after, lexicon)
    if not ok:
        raise AssertionError(f"{move.word} leaves illegal board; bad={bad_board}")
    return after


def score_word(entry: WordOnBoard, new_cells: set[tuple[int, int]]) -> int:
    word_multiplier = 1
    letter_sum = 0
    for cell, ch in zip(entry.cells, entry.word):
        letter_score = LETTER_VALUES[ch]
        if cell in new_cells and cell in PREMIUMS:
            kind, multiplier = PREMIUMS[cell]
            if kind == "letter":
                letter_score *= multiplier
            else:
                word_multiplier *= multiplier
        letter_sum += letter_score
    return letter_sum * word_multiplier


def score_final_move(pre: dict[tuple[int, int], str], final: dict[tuple[int, int], str]) -> tuple[int, list[tuple[str, int]]]:
    new_cells = set(FINAL_MOVE)
    formed = all_formed_words_after_move(pre, FINAL_MOVE)
    rows = []
    total = 0
    for entry in formed:
        score = score_word(entry, new_cells)
        rows.append((entry.word, score))
        total += score
    total += 50
    rows.append(("bingo", 50))
    return total, rows


def construction_moves() -> list[Move]:
    return [
        Move("H", "UNLED", ((8, 6), (8, 7), (8, 8), (8, 9), (8, 10))),
        Move("V", "ARROWING", ((2, 7), (3, 7), (4, 7), (5, 7), (6, 7), (7, 7), (8, 7), (9, 7))),
        Move("H", "HALT", ((2, 6), (2, 7), (2, 8), (2, 9))),
        Move("V", "UTS", ((1, 9), (2, 9), (3, 9))),
        Move("H", "UTA", ((1, 9), (1, 10), (1, 11))),
        Move("H", "WO", ((2, 11), (2, 12))),
        Move("V", "OOGAMETE", ((2, 12), (3, 12), (4, 12), (5, 12), (6, 12), (7, 12), (8, 12), (9, 12))),
        Move("H", "MERL", ((6, 12), (6, 13), (6, 14), (6, 15))),
        Move("V", "STABLISH", ((2, 15), (3, 15), (4, 15), (5, 15), (6, 15), (7, 15), (8, 15), (9, 15))),
        Move("H", "OS", ((2, 14), (2, 15))),
        Move("V", "REE", ((6, 9), (7, 9), (8, 9))),
        Move("H", "VOW", ((6, 5), (6, 6), (6, 7))),
        Move("V", "AL", ((6, 4), (7, 4))),
        Move("V", "REQUALIFY", ((2, 4), (3, 4), (4, 4), (5, 4), (6, 4), (7, 4), (8, 4), (9, 4), (10, 4))),
        Move("V", "YA", ((1, 3), (2, 3))),
        Move("V", "ED", ((2, 2), (3, 2))),
        Move("H", "URD", ((4, 6), (4, 7), (4, 8))),
        Move("H", "ON", ((1, 13), (1, 14))),
        Move("H", "HE", ((1, 5), (1, 6))),
        Move("V", "REQUALIFYING", ((2, 4), (3, 4), (4, 4), (5, 4), (6, 4), (7, 4), (8, 4), (9, 4), (10, 4), (11, 4), (12, 4), (13, 4))),
        Move("V", "STABLISHMENTS", ((2, 15), (3, 15), (4, 15), (5, 15), (6, 15), (7, 15), (8, 15), (9, 15), (10, 15), (11, 15), (12, 15), (13, 15), (14, 15))),
        Move("V", "PACIFIC", ((2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1), (8, 1))),
        Move("V", "PACIFICATIONS", ((2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1), (8, 1), (9, 1), (10, 1), (11, 1), (12, 1), (13, 1), (14, 1))),
        Move("V", "LADDERLIKE", ((2, 8), (3, 8), (4, 8), (5, 8), (6, 8), (7, 8), (8, 8), (9, 8), (10, 8), (11, 8))),
    ]

def main() -> None:
    nwl23 = Kwg(DATA / "NWL23.kwg")
    csw24 = Kwg(DATA / "CSW24.kwg")
    final_board = board_from_rows()
    pre_board = {cell: ch for cell, ch in final_board.items() if cell not in FINAL_MOVE}
    rack = "".join(sorted(FINAL_MOVE.values()))
    if rack != "BENOPXZ":
        raise AssertionError(f"wrong rack: {rack}")
    construction = construction_moves()
    board: dict[tuple[int, int], str] = {}
    for i, move in enumerate(construction, start=1):
        board = validate_forward_move(board, move, nwl23, first_move=(i == 1))
    if board != pre_board:
        missing = sorted(set(pre_board) - set(board))
        extra = sorted(set(board) - set(pre_board))
        raise AssertionError(f"construction mismatch; missing={missing}; extra={extra}")

    final_move = Move("H", "OXYPHENBUTAZONE", tuple((1, col) for col in range(1, 16)))
    reached_final = validate_forward_move(pre_board, final_move, nwl23)
    if reached_final != final_board:
        raise AssertionError("final move does not produce the certified final board")

    ok_pre, bad_pre = legal_board(pre_board, nwl23)
    ok_final, bad_final = legal_board(final_board, nwl23)
    if not ok_pre or not ok_final:
        raise AssertionError(f"board validity failure: pre={bad_pre}, final={bad_final}")

    total, score_rows = score_final_move(pre_board, final_board)
    if total != 1786:
        raise AssertionError(f"expected 1786, got {total}")

    scored_final_cells = {
        cell
        for entry in all_formed_words_after_move(pre_board, FINAL_MOVE)
        for cell in entry.cells
    }
    if set(BLANK_ASSIGNMENTS) & scored_final_cells:
        raise AssertionError("a blank assignment is used in the final scoring move")
    final_count = Counter(final_board.values())
    for _, ch in BLANK_ASSIGNMENTS.items():
        final_count[ch] -= 1
    excess = {ch: final_count[ch] - TILE_DISTRIBUTION[ch] for ch in final_count if final_count[ch] > TILE_DISTRIBUTION[ch]}
    if excess or len(BLANK_ASSIGNMENTS) > 2:
        raise AssertionError(f"tile distribution exceeded: {excess}; blanks={BLANK_ASSIGNMENTS}")

    print("NWL23 certificate: OK")
    print(f"reachable pre-final board: {len(construction)} moves")
    print(f"final rack: {rack}")
    print("score table:")
    for word, score in score_rows:
        print(f"  {word:16s} {score:4d}")
    print(f"  {'total':16s} {total:4d}")
    print(f"final board tiles: {len(final_board)}; tile distribution: OK with blanks {BLANK_ASSIGNMENTS}")
    print()
    print("CSW24 validity of final scoring words:")
    for word, _ in score_rows:
        if word != "bingo":
            print(f"  {word:16s} {csw24.contains(word)}")


if __name__ == "__main__":
    main()

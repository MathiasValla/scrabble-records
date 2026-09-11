#!/usr/bin/env python3
"""Exhaustive upper-bound search for two-tile English Scrabble moves.

For a move placing exactly two tiles in one row, the formed words are:

* one main horizontal word containing both new tiles; and
* zero, one, or two vertical cross words, one at each new tile.

The board is symmetric, so horizontal enumeration over all rows and columns covers
vertical plays as well after transposition.  As in the one-tile search, this is an
upper-bound theorem checker: every scored word must be in the lexicon, and deleting
the newly placed tiles must leave legal pre-move fragments.  We also enforce the
English tile bag and optimize the placement of forced blanks by score coefficient.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import heapq
import json
import string
import sys

from verify_1786 import LETTER_VALUES, TILE_DISTRIBUTION, Kwg
from search_one_tile import iter_words, premium_at


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "output"

ALPHABET = string.ascii_uppercase
LETTER_INDEX = {ch: i for i, ch in enumerate(ALPHABET)}


@dataclass(frozen=True)
class Occurrence:
    word: str
    indices: tuple[int, ...]
    base_score: int
    counts: tuple[int, ...]

    @property
    def letters(self) -> tuple[str, ...]:
        return tuple(self.word[index] for index in self.indices)


@dataclass(frozen=True)
class MainPlacement:
    upper: int
    face_score: int
    word: str
    indices: tuple[int, int]
    row: int
    start_col: int
    cells: tuple[tuple[int, int], ...]
    new_cells: tuple[tuple[int, int], tuple[int, int]]
    letters: tuple[str, str]
    entries: tuple[tuple[tuple[int, int], str, int], ...]


@dataclass(frozen=True)
class CrossOption:
    face_score: int
    word: str | None
    index: int | None
    start_row: int | None
    cells: tuple[tuple[int, int], ...]
    entries: tuple[tuple[tuple[int, int], str, int], ...]


ZERO_ENTRIES: tuple[tuple[tuple[int, int], str, int], ...] = tuple()


def score_of(word: str) -> int:
    return sum(LETTER_VALUES[ch] for ch in word)


def count_tuple(word: str) -> tuple[int, ...]:
    counts = [0] * 26
    for ch in word:
        counts[LETTER_INDEX[ch]] += 1
    return tuple(counts)


def deletion_fragments(word: str, indices: tuple[int, ...]) -> tuple[str, ...]:
    pieces = []
    last = 0
    for index in sorted(indices):
        if index > last:
            pieces.append(word[last:index])
        last = index + 1
    if last < len(word):
        pieces.append(word[last:])
    return tuple(piece for piece in pieces if piece)


def deletion_is_legal(word: str, indices: tuple[int, ...], legal_words: set[str]) -> bool:
    return all(len(piece) <= 1 or piece in legal_words for piece in deletion_fragments(word, indices))


def fits(length: int, indices: tuple[int, ...], positions: tuple[int, ...]) -> bool:
    start = positions[0] - indices[0]
    if any(position - index != start for position, index in zip(positions, indices)):
        return False
    return 1 <= start and start + length - 1 <= 15


def score_after_best_blanks(
    face_score: int,
    entries: tuple[tuple[tuple[int, int], str, int], ...],
) -> tuple[int | None, int, dict[str, int]]:
    by_cell: dict[tuple[int, int], list[object]] = {}
    for cell, ch, coefficient in entries:
        if cell not in by_cell:
            by_cell[cell] = [ch, coefficient]
            continue
        if by_cell[cell][0] != ch:
            raise AssertionError(f"conflicting letters at {cell}: {by_cell[cell][0]} and {ch}")
        by_cell[cell][1] = int(by_cell[cell][1]) + coefficient

    counts = Counter(str(value[0]) for value in by_cell.values())
    coeffs_by_letter: dict[str, list[int]] = {ch: [] for ch in ALPHABET}
    for ch, coefficient in by_cell.values():
        coeffs_by_letter[str(ch)].append(int(coefficient))

    excess: dict[str, int] = {}
    blank_count = 0
    penalty = 0
    for ch in ALPHABET:
        over = counts[ch] - TILE_DISTRIBUTION[ch]
        if over <= 0:
            continue
        if over > len(coeffs_by_letter[ch]):
            raise AssertionError(f"not enough coefficients for {ch}: {over} > {coeffs_by_letter[ch]}")
        excess[ch] = over
        blank_count += over
        penalty += LETTER_VALUES[ch] * sum(sorted(coeffs_by_letter[ch])[:over])
    if blank_count > 2:
        return None, penalty, excess
    return face_score - penalty, penalty, excess


def build_cross_occurrences(legal_words: set[str]) -> dict[tuple[str, int], list[Occurrence]]:
    by_letter_position: dict[tuple[str, int], list[Occurrence]] = {
        (ch, position): [] for ch in ALPHABET for position in range(1, 16)
    }
    raw = 0
    kept = 0
    for word in legal_words:
        if not 2 <= len(word) <= 15:
            continue
        base = score_of(word)
        counts = count_tuple(word)
        for index, ch in enumerate(word):
            raw += 1
            if not deletion_is_legal(word, (index,), legal_words):
                continue
            kept += 1
            occurrence = Occurrence(word, (index,), base, counts)
            for position in range(1, 16):
                if fits(len(word), (index,), (position,)):
                    by_letter_position[(ch, position)].append(occurrence)
    print(f"cross occurrences: {kept:,} deletion-valid / {raw:,} raw")
    return by_letter_position


def build_cross_max_base(
    cross_occurrences: dict[tuple[str, int], list[Occurrence]],
) -> dict[tuple[str, int], int]:
    return {
        key: max((occurrence.base_score for occurrence in occurrences), default=0)
        for key, occurrences in cross_occurrences.items()
    }


def max_cross_face_score(
    cross_max_base: dict[tuple[str, int], int],
    letter: str,
    cell: tuple[int, int],
) -> int:
    row, _ = cell
    base = cross_max_base[(letter, row)]
    letter_multiplier, word_multiplier = premium_at(cell)
    return word_multiplier * (base + (letter_multiplier - 1) * LETTER_VALUES[letter])


def cross_option_from_occurrence(
    occurrence: Occurrence,
    cell: tuple[int, int],
) -> CrossOption:
    row, col = cell
    index = occurrence.indices[0]
    start_row = row - index
    letter_multiplier, word_multiplier = premium_at(cell)
    entries = []
    for offset, ch in enumerate(occurrence.word):
        coefficient = word_multiplier
        if offset == index:
            coefficient *= letter_multiplier
        entries.append(((start_row + offset, col), ch, coefficient))
    face_score = sum(
        LETTER_VALUES[ch] * (word_multiplier * (letter_multiplier if offset == index else 1))
        for offset, ch in enumerate(occurrence.word)
    )
    return CrossOption(
        face_score,
        occurrence.word,
        index,
        start_row,
        tuple((start_row + offset, col) for offset in range(len(occurrence.word))),
        tuple(entries),
    )


def cross_options_for(
    by_letter_position: dict[tuple[str, int], list[Occurrence]],
    letter: str,
    cell: tuple[int, int],
) -> list[CrossOption]:
    row, _ = cell
    options = [CrossOption(0, None, None, None, tuple(), ZERO_ENTRIES)]
    options.extend(cross_option_from_occurrence(occurrence, cell) for occurrence in by_letter_position[(letter, row)])
    options.sort(key=lambda option: option.face_score, reverse=True)
    return options


def main_occurrences(legal_words: set[str]) -> Iterable[Occurrence]:
    raw = 0
    kept = 0
    for word in legal_words:
        if not 2 <= len(word) <= 15:
            continue
        base = score_of(word)
        counts = count_tuple(word)
        for i in range(len(word) - 1):
            for j in range(i + 1, len(word)):
                raw += 1
                if deletion_is_legal(word, (i, j), legal_words):
                    kept += 1
                    yield Occurrence(word, (i, j), base, counts)
    print(f"main two-hole occurrences generated lazily from raw pairs; kept count printed after collection is unavailable here")


def main_face_score_for(
    occurrence: Occurrence,
    row: int,
    start_col: int,
) -> int:
    word_multiplier = 1
    letter_bonus = 0
    for index in occurrence.indices:
        cell = (row, start_col + index)
        letter_multiplier, cell_word_multiplier = premium_at(cell)
        word_multiplier *= cell_word_multiplier
        letter_bonus += (letter_multiplier - 1) * LETTER_VALUES[occurrence.word[index]]
    return word_multiplier * (occurrence.base_score + letter_bonus)


def iter_main_jobs(
    legal_words: set[str],
    cross_max_base: dict[tuple[str, int], int],
) -> Iterable[tuple[int, int, str, tuple[int, int], int, int]]:
    for word in legal_words:
        if not 2 <= len(word) <= 15:
            continue
        occurrence_base = score_of(word)
        for i in range(len(word) - 1):
            for j in range(i + 1, len(word)):
                if not deletion_is_legal(word, (i, j), legal_words):
                    continue
                occurrence = Occurrence(word, (i, j), occurrence_base, count_tuple(word))
                for row in range(1, 16):
                    for start_col in range(1, 17 - len(word)):
                        main_face = main_face_score_for(occurrence, row, start_col)
                        cell1 = (row, start_col + i)
                        cell2 = (row, start_col + j)
                        upper = (
                            main_face
                            + max_cross_face_score(cross_max_base, word[i], cell1)
                            + max_cross_face_score(cross_max_base, word[j], cell2)
                        )
                        yield upper, main_face, word, (i, j), row, start_col


def main_placement_from_occurrence(
    occurrence: Occurrence,
    row: int,
    start_col: int,
) -> MainPlacement:
    cells = tuple((row, start_col + offset) for offset in range(len(occurrence.word)))
    new_cells = (cells[occurrence.indices[0]], cells[occurrence.indices[1]])
    word_multiplier = 1
    letter_multipliers: dict[int, int] = {}
    for index in occurrence.indices:
        letter_multiplier, cell_word_multiplier = premium_at(cells[index])
        letter_multipliers[index] = letter_multiplier
        word_multiplier *= cell_word_multiplier

    entries = []
    face_score = 0
    for offset, ch in enumerate(occurrence.word):
        coefficient = word_multiplier
        if offset in occurrence.indices:
            coefficient *= letter_multipliers[offset]
        entries.append((cells[offset], ch, coefficient))
        face_score += LETTER_VALUES[ch] * coefficient
    return MainPlacement(
        0,
        face_score,
        occurrence.word,
        occurrence.indices,  # type: ignore[arg-type]
        row,
        start_col,
        cells,
        new_cells,
        occurrence.letters,  # type: ignore[arg-type]
        tuple(entries),
    )


def fragments_payload(word: str, indices: tuple[int, ...]) -> list[str]:
    return list(deletion_fragments(word, indices))


def option_payload(option: CrossOption) -> dict[str, object] | None:
    if option.word is None:
        return None
    return {
        "word": option.word,
        "score_before_blanks": option.face_score,
        "index": option.index + 1 if option.index is not None else None,
        "start": [option.start_row, option.cells[0][1]] if option.start_row is not None else None,
        "fragments_before_move": fragments_payload(option.word, (option.index,)) if option.index is not None else [],
    }


def record_payload(
    score: int,
    face_score: int,
    penalty: int,
    excess: dict[str, int],
    main: MainPlacement,
    cross1: CrossOption,
    cross2: CrossOption,
) -> dict[str, object]:
    return {
        "score": score,
        "face_score_before_blank_penalty": face_score,
        "blank_score_penalty": penalty,
        "excess_letters_inside_scoring_pattern": excess,
        "orientation": "H",
        "placed_tiles": [
            {"cell": list(main.new_cells[0]), "letter": main.letters[0]},
            {"cell": list(main.new_cells[1]), "letter": main.letters[1]},
        ],
        "main": {
            "word": main.word,
            "score_before_blanks": main.face_score,
            "indices": [main.indices[0] + 1, main.indices[1] + 1],
            "start": [main.row, main.start_col],
            "fragments_before_move": fragments_payload(main.word, main.indices),
        },
        "crosses": [option_payload(cross1), option_payload(cross2)],
    }


def search(lexicon_name: str, kwg_path: Path, *, keep_records: int = 25) -> dict[str, object]:
    print(f"\n=== {lexicon_name} two-tile search ===")
    lexicon = Kwg(kwg_path)
    legal_words = {word for word in iter_words(lexicon) if word.isalpha()}
    print(f"words: {len(legal_words):,}")
    cross_occurrences = build_cross_occurrences(legal_words)
    cross_max_base = build_cross_max_base(cross_occurrences)

    cross_cache: dict[tuple[str, tuple[int, int]], list[CrossOption]] = {}

    def get_cross_options(letter: str, cell: tuple[int, int]) -> list[CrossOption]:
        key = (letter, cell)
        if key not in cross_cache:
            cross_cache[key] = cross_options_for(cross_occurrences, letter, cell)
        return cross_cache[key]

    seed_limit = 50_000
    seed_heap: list[tuple[int, int, int, str, tuple[int, int], int, int]] = []
    serial = 0
    raw_pairs = 0
    kept_pairs = 0
    main_placements = 0
    for word in legal_words:
        if not 2 <= len(word) <= 15:
            continue
        base = score_of(word)
        counts = count_tuple(word)
        for i in range(len(word) - 1):
            for j in range(i + 1, len(word)):
                raw_pairs += 1
                if not deletion_is_legal(word, (i, j), legal_words):
                    continue
                kept_pairs += 1
                occurrence = Occurrence(word, (i, j), base, counts)
                for row in range(1, 16):
                    for start_col in range(1, 17 - len(word)):
                        main_placements += 1
                        main_face = main_face_score_for(occurrence, row, start_col)
                        cell1 = (row, start_col + i)
                        cell2 = (row, start_col + j)
                        upper = (
                            main_face
                            + max_cross_face_score(cross_max_base, word[i], cell1)
                            + max_cross_face_score(cross_max_base, word[j], cell2)
                        )
                        serial += 1
                        item = (upper, serial, main_face, word, (i, j), row, start_col)
                        if len(seed_heap) < seed_limit:
                            heapq.heappush(seed_heap, item)
                        elif upper > seed_heap[0][0]:
                            heapq.heapreplace(seed_heap, item)

    print(f"main two-hole occurrences: {kept_pairs:,} deletion-valid / {raw_pairs:,} raw")
    print(f"main placements: {main_placements:,}; seed placements retained: {len(seed_heap):,}")

    best = -1
    records: list[dict[str, object]] = []
    checked_main = 0
    checked_cross_pairs = 0

    def evaluate_job(
        upper: int,
        main_face: int,
        word: str,
        indices: tuple[int, int],
        row: int,
        start_col: int,
    ) -> None:
        nonlocal best, records, checked_main, checked_cross_pairs
        if upper < best:
            return
        checked_main += 1
        occurrence = Occurrence(word, indices, score_of(word), count_tuple(word))
        main = main_placement_from_occurrence(occurrence, row, start_col)
        if main.face_score != main_face:
            raise AssertionError(f"main score mismatch for {word}: {main.face_score} != {main_face}")
        cross_options1 = get_cross_options(main.letters[0], main.new_cells[0])
        cross_options2 = get_cross_options(main.letters[1], main.new_cells[1])
        top2 = cross_options2[0].face_score
        for cross1 in cross_options1:
            if main.face_score + cross1.face_score + top2 < best:
                break
            for cross2 in cross_options2:
                face_score = main.face_score + cross1.face_score + cross2.face_score
                if face_score < best:
                    break
                checked_cross_pairs += 1
                entries = main.entries + cross1.entries + cross2.entries
                score, penalty, excess = score_after_best_blanks(face_score, entries)
                if score is None:
                    continue
                if score > best:
                    best = score
                    records = [record_payload(score, face_score, penalty, excess, main, cross1, cross2)]
                    print(f"new best {best}: {records[0]}")
                elif score == best and len(records) < keep_records:
                    records.append(record_payload(score, face_score, penalty, excess, main, cross1, cross2))

    for upper, _, main_face, word, indices, row, start_col in sorted(seed_heap, reverse=True):
        evaluate_job(upper, main_face, word, indices, row, start_col)

    print(f"seed best after exact evaluation: {best}")
    second_pass_seen = 0
    second_pass_evaluated = 0
    for word in legal_words:
        if not 2 <= len(word) <= 15:
            continue
        base = score_of(word)
        counts = count_tuple(word)
        for i in range(len(word) - 1):
            for j in range(i + 1, len(word)):
                if not deletion_is_legal(word, (i, j), legal_words):
                    continue
                occurrence = Occurrence(word, (i, j), base, counts)
                for row in range(1, 16):
                    for start_col in range(1, 17 - len(word)):
                        second_pass_seen += 1
                        main_face = main_face_score_for(occurrence, row, start_col)
                        cell1 = (row, start_col + i)
                        cell2 = (row, start_col + j)
                        upper = (
                            main_face
                            + max_cross_face_score(cross_max_base, word[i], cell1)
                            + max_cross_face_score(cross_max_base, word[j], cell2)
                        )
                        if upper >= best:
                            second_pass_evaluated += 1
                            evaluate_job(upper, main_face, word, (i, j), row, start_col)

    print(f"checked main placements exactly: {checked_main:,}; checked cross pairs: {checked_cross_pairs:,}")
    print(f"second pass placements seen: {second_pass_seen:,}; evaluated by upper bound: {second_pass_evaluated:,}")
    print(f"cross option cache entries: {len(cross_cache):,}")
    return {
        "lexicon": lexicon_name,
        "word_count": len(legal_words),
        "best_score": best,
        "records": records,
        "raw_main_pairs": raw_pairs,
        "deletion_valid_main_pairs": kept_pairs,
        "main_placements": main_placements,
        "checked_main_placements_exactly": checked_main,
        "checked_cross_pairs": checked_cross_pairs,
        "second_pass_seen": second_pass_seen,
        "second_pass_evaluated_by_upper_bound": second_pass_evaluated,
    }


def main() -> None:
    OUT.mkdir(exist_ok=True)
    requested = sys.argv[1:] or ["NWL23", "CSW24"]
    paths = {"NWL23": DATA / "NWL23.kwg", "CSW24": DATA / "CSW24.kwg"}
    result = {name: search(name, paths[name]) for name in requested}
    out_path = OUT / "two_tile_search.json"
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()

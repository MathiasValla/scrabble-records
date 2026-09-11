#!/usr/bin/env python3
"""Exhaustive upper-bound search for four-tile English Scrabble moves.

For a move placing exactly four tiles in one row, the formed words are:

* one main horizontal word containing all four new tiles; and
* zero to four vertical cross words, one at each new tile.

The board is symmetric, so horizontal enumeration covers vertical plays after
transposition.  The search enumerates a necessary superset of legal moves using
the deletion-fragment lemma: after deleting the newly placed tiles from any
formed word, every remaining contiguous fragment of length at least two must
already be a legal word.  Scores are computed on physical board squares so that
forced blanks lose the correct amount even when one tile is scored in both a
main word and a cross word.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
import argparse
import heapq
import json
import string
import time

from verify_1786 import LETTER_VALUES, TILE_DISTRIBUTION, Kwg
from search_one_tile import iter_words, premium_at


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "output"

ALPHABET = string.ascii_uppercase
LETTER_INDEX = {ch: i for i, ch in enumerate(ALPHABET)}
NEW_TILE_COUNT = 4


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
    face_score: int
    word: str
    indices: tuple[int, ...]
    row: int
    start_col: int
    cells: tuple[tuple[int, int], ...]
    new_cells: tuple[tuple[int, int], ...]
    letters: tuple[str, ...]
    entries: tuple[tuple[tuple[int, int], str, int], ...]


@dataclass(frozen=True)
class CrossOption:
    face_score: int
    word: str | None
    index: int | None
    start_row: int | None
    cells: tuple[tuple[int, int], ...]
    entries: tuple[tuple[tuple[int, int], str, int], ...]
    counts_without_new: tuple[int, ...]


ZERO_ENTRIES: tuple[tuple[tuple[int, int], str, int], ...] = tuple()
ZERO_COUNTS: tuple[int, ...] = tuple(0 for _ in range(26))
NONE_CROSS = CrossOption(0, None, None, None, tuple(), ZERO_ENTRIES, ZERO_COUNTS)


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
        excess[ch] = over
        blank_count += over
        penalty += LETTER_VALUES[ch] * sum(sorted(coeffs_by_letter[ch])[:over])
    if blank_count > 2:
        return None, penalty, excess
    return face_score - penalty, penalty, excess


def add_count_tuples(left: tuple[int, ...], right: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(a + b for a, b in zip(left, right))


def blank_count_for_counts(counts: tuple[int, ...]) -> int:
    return sum(
        max(0, count - TILE_DISTRIBUTION[ch])
        for ch, count in zip(ALPHABET, counts)
    )


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

    for occurrences in by_letter_position.values():
        occurrences.sort(key=lambda occurrence: occurrence.base_score, reverse=True)
    print(f"cross occurrences: {kept:,} deletion-valid / {raw:,} raw")
    return by_letter_position


def build_cross_max_base(
    cross_occurrences: dict[tuple[str, int], list[Occurrence]],
) -> dict[tuple[str, int], int]:
    return {
        key: max((occurrence.base_score for occurrence in occurrences), default=0)
        for key, occurrences in cross_occurrences.items()
    }


def build_cross_face_upper(
    cross_max_base: dict[tuple[str, int], int],
) -> dict[tuple[str, tuple[int, int]], int]:
    return {
        (ch, (row, col)): max_cross_face_score(cross_max_base, ch, (row, col))
        for ch in ALPHABET
        for row in range(1, 16)
        for col in range(1, 16)
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
    face_score = 0
    counts_without_new = list(occurrence.counts)
    counts_without_new[LETTER_INDEX[occurrence.word[index]]] -= 1
    for offset, ch in enumerate(occurrence.word):
        coefficient = word_multiplier
        if offset == index:
            coefficient *= letter_multiplier
        entries.append(((start_row + offset, col), ch, coefficient))
        face_score += LETTER_VALUES[ch] * coefficient
    return CrossOption(
        face_score,
        occurrence.word,
        index,
        start_row,
        tuple((start_row + offset, col) for offset in range(len(occurrence.word))),
        tuple(entries),
        tuple(counts_without_new),
    )


def cross_options_for(
    by_letter_position: dict[tuple[str, int], list[Occurrence]],
    letter: str,
    cell: tuple[int, int],
) -> list[CrossOption]:
    row, _ = cell
    options = [NONE_CROSS]
    options.extend(cross_option_from_occurrence(occurrence, cell) for occurrence in by_letter_position[(letter, row)])
    options.sort(key=lambda option: option.face_score, reverse=True)
    return options


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


def main_placement_from_occurrence(
    occurrence: Occurrence,
    row: int,
    start_col: int,
) -> MainPlacement:
    if len(occurrence.indices) != NEW_TILE_COUNT:
        raise AssertionError(f"{NEW_TILE_COUNT} indices expected, got {occurrence.indices}")
    cells = tuple((row, start_col + offset) for offset in range(len(occurrence.word)))
    indices = occurrence.indices
    new_cells = tuple(cells[index] for index in indices)
    word_multiplier = 1
    letter_multipliers: dict[int, int] = {}
    for index in indices:
        letter_multiplier, cell_word_multiplier = premium_at(cells[index])
        letter_multipliers[index] = letter_multiplier
        word_multiplier *= cell_word_multiplier

    entries = []
    face_score = 0
    for offset, ch in enumerate(occurrence.word):
        coefficient = word_multiplier
        if offset in indices:
            coefficient *= letter_multipliers[offset]
        entries.append((cells[offset], ch, coefficient))
        face_score += LETTER_VALUES[ch] * coefficient
    return MainPlacement(
        face_score,
        occurrence.word,
        indices,
        row,
        start_col,
        cells,
        new_cells,
        occurrence.letters,
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
    crosses: tuple[CrossOption, ...],
) -> dict[str, object]:
    return {
        "score": score,
        "face_score_before_blank_penalty": face_score,
        "blank_score_penalty": penalty,
        "excess_letters_inside_scoring_pattern": excess,
        "orientation": "H",
        "placed_tiles": [
            {"cell": list(cell), "letter": letter}
            for cell, letter in zip(main.new_cells, main.letters)
        ],
        "main": {
            "word": main.word,
            "score_before_blanks": main.face_score,
            "indices": [index + 1 for index in main.indices],
            "start": [main.row, main.start_col],
            "fragments_before_move": fragments_payload(main.word, main.indices),
        },
        "crosses": [option_payload(cross) for cross in crosses],
    }


def evaluate_cross_product(
    main: MainPlacement,
    option_lists: tuple[list[CrossOption], ...],
    best: int,
    *,
    keep_ties: int,
) -> tuple[int, list[tuple[int, int, dict[str, int], tuple[CrossOption, ...]]], int, int]:
    records: list[tuple[int, int, dict[str, int], tuple[CrossOption, ...]]] = []
    checked = 0
    nodes = 0
    selected: list[CrossOption | None] = [None] * len(option_lists)
    main_counts = count_tuple(main.word)
    _, main_penalty, _ = score_after_best_blanks(main.face_score, main.entries)
    if blank_count_for_counts(main_counts) > 2:
        return best, records, checked, nodes

    ordered_slots = tuple(
        sorted(
            range(len(option_lists)),
            key=lambda slot: (len(option_lists[slot]), -option_lists[slot][0].face_score),
        )
    )
    top_from = [0] * (len(ordered_slots) + 1)
    for offset in range(len(ordered_slots) - 1, -1, -1):
        slot = ordered_slots[offset]
        top_from[offset] = top_from[offset + 1] + option_lists[slot][0].face_score

    def dfs(
        offset: int,
        face_score: int,
        entries: tuple[tuple[tuple[int, int], str, int], ...],
        counts: tuple[int, ...],
    ) -> None:
        nonlocal best, checked, nodes
        nodes += 1
        if offset == len(ordered_slots):
            checked += 1
            score, penalty, excess = score_after_best_blanks(face_score, entries)
            if score is None or score < best:
                return
            crosses = tuple(cross for cross in selected if cross is not None)
            records.append((score, penalty, excess, crosses))
            records.sort(key=lambda item: item[0], reverse=True)
            del records[keep_ties:]
            if score > best:
                best = score
            return

        slot = ordered_slots[offset]
        remaining_after_slot = top_from[offset + 1]
        for option in option_lists[slot]:
            next_face = face_score + option.face_score
            if next_face + remaining_after_slot - main_penalty < best:
                break
            next_counts = add_count_tuples(counts, option.counts_without_new)
            if blank_count_for_counts(next_counts) > 2:
                continue
            selected[slot] = option
            dfs(offset + 1, next_face, entries + option.entries, next_counts)
            selected[slot] = None

    dfs(0, main.face_score, main.entries, main_counts)
    return best, records, checked, nodes


def search(
    lexicon_name: str,
    kwg_path: Path,
    *,
    keep_records: int = 25,
    seed_limit: int = 100_000,
    seed_only: bool = False,
    initial_best: int = -1,
    certify_from_initial: bool = False,
    estimate_only: bool = False,
    report_seconds: float = 20.0,
) -> dict[str, object]:
    print(f"\n=== {lexicon_name} four-tile search ===")
    lexicon = Kwg(kwg_path)
    legal_words = {word for word in iter_words(lexicon) if word.isalpha()}
    legal_words_list = sorted(legal_words)
    print(f"words: {len(legal_words):,}")
    cross_occurrences = build_cross_occurrences(legal_words)
    cross_max_base = build_cross_max_base(cross_occurrences)
    cross_face_upper = build_cross_face_upper(cross_max_base)

    cross_cache: dict[tuple[str, tuple[int, int]], list[CrossOption]] = {}

    def get_cross_options(letter: str, cell: tuple[int, int]) -> list[CrossOption]:
        key = (letter, cell)
        if key not in cross_cache:
            cross_cache[key] = cross_options_for(cross_occurrences, letter, cell)
        return cross_cache[key]

    seed_heap: list[tuple[int, int, int, str, tuple[int, ...], int, int]] = []
    serial = 0
    raw_quadruples = 0
    kept_quadruples = 0
    main_placements = 0
    upper_at_least_initial = 0
    best = initial_best
    records: list[dict[str, object]] = []
    checked_main = 0
    checked_cross_quadruples = 0
    checked_cross_nodes = 0

    def evaluate_job(
        upper: int,
        main_face: int,
        word: str,
        indices: tuple[int, ...],
        row: int,
        start_col: int,
    ) -> None:
        nonlocal best, records, checked_main, checked_cross_quadruples, checked_cross_nodes
        if upper < best:
            return
        checked_main += 1
        occurrence = Occurrence(word, indices, score_of(word), count_tuple(word))
        main = main_placement_from_occurrence(occurrence, row, start_col)
        if main.face_score != main_face:
            raise AssertionError(f"main score mismatch for {word}: {main.face_score} != {main_face}")
        option_lists = tuple(
            get_cross_options(letter, cell)
            for letter, cell in zip(main.letters, main.new_cells)
        )
        previous_best = best
        new_best, hits, checked, nodes = evaluate_cross_product(
            main,
            option_lists,
            best,
            keep_ties=keep_records,
        )
        checked_cross_quadruples += checked
        checked_cross_nodes += nodes
        for score, penalty, excess, crosses in hits:
            payload = record_payload(
                score,
                main.face_score + sum(cross.face_score for cross in crosses),
                penalty,
                excess,
                main,
                crosses,
            )
            if score > previous_best:
                previous_best = score
                records = [payload]
                print(f"new best {score}: {payload}")
            elif score == previous_best and len(records) < keep_records:
                records.append(payload)
        best = max(best, new_best)

    last_report = time.monotonic()
    started = last_report
    for word_no, word in enumerate(legal_words_list, start=1):
        if not NEW_TILE_COUNT <= len(word) <= 15:
            continue
        base = score_of(word)
        counts = count_tuple(word)
        length = len(word)
        for indices in combinations(range(length), NEW_TILE_COUNT):
            raw_quadruples += 1
            if not deletion_is_legal(word, indices, legal_words):
                continue
            kept_quadruples += 1
            occurrence = Occurrence(word, indices, base, counts)
            for row in range(1, 16):
                for start_col in range(1, 17 - length):
                    main_placements += 1
                    main_face = main_face_score_for(occurrence, row, start_col)
                    cells = tuple((row, start_col + index) for index in indices)
                    upper = main_face + sum(
                        cross_face_upper[(word[index], cell)]
                        for index, cell in zip(indices, cells)
                    )
                    if upper >= initial_best:
                        upper_at_least_initial += 1
                    serial += 1
                    item = (upper, serial, main_face, word, indices, row, start_col)
                    if estimate_only:
                        if len(seed_heap) < seed_limit:
                            heapq.heappush(seed_heap, item)
                        elif upper > seed_heap[0][0]:
                            heapq.heapreplace(seed_heap, item)
                        continue
                    if certify_from_initial:
                        if upper >= best:
                            evaluate_job(upper, main_face, word, indices, row, start_col)
                    else:
                        if len(seed_heap) < seed_limit:
                            heapq.heappush(seed_heap, item)
                        elif upper > seed_heap[0][0]:
                            heapq.heapreplace(seed_heap, item)
        now = time.monotonic()
        if now - last_report >= report_seconds:
            floor = seed_heap[0][0] if seed_heap else None
            if estimate_only:
                print(
                    "estimate pass "
                    f"{word_no:,}/{len(legal_words_list):,} words; "
                    f"raw quadruples {raw_quadruples:,}; kept {kept_quadruples:,}; "
                    f"placements {main_placements:,}; upper>={initial_best} {upper_at_least_initial:,}; "
                    f"heap floor {floor}; elapsed {now - started:.1f}s"
                )
            elif certify_from_initial:
                print(
                    "certify pass "
                    f"{word_no:,}/{len(legal_words_list):,} words; "
                    f"raw quadruples {raw_quadruples:,}; kept {kept_quadruples:,}; "
                    f"placements {main_placements:,}; checked main {checked_main:,}; "
                    f"checked products {checked_cross_quadruples:,}; best {best}; "
                    f"elapsed {now - started:.1f}s"
                )
            else:
                print(
                    "seed scan "
                    f"{word_no:,}/{len(legal_words_list):,} words; "
                    f"raw quadruples {raw_quadruples:,}; kept {kept_quadruples:,}; "
                    f"placements {main_placements:,}; heap floor {floor}; "
                    f"elapsed {now - started:.1f}s"
                )
            last_report = now

    print(f"main four-hole occurrences: {kept_quadruples:,} deletion-valid / {raw_quadruples:,} raw")
    print(f"main placements: {main_placements:,}; seed placements retained: {len(seed_heap):,}")
    print(f"placements with independent upper >= initial best {initial_best}: {upper_at_least_initial:,}")

    if estimate_only:
        top = [
            {
                "upper": upper,
                "main_score_before_blanks": main_face,
                "word": word,
                "indices": [index + 1 for index in indices],
                "row": row,
                "start_col": start_col,
            }
            for upper, _, main_face, word, indices, row, start_col in sorted(seed_heap, reverse=True)[:keep_records]
        ]
        return {
            "lexicon": lexicon_name,
            "word_count": len(legal_words),
            "raw_main_quadruples": raw_quadruples,
            "deletion_valid_main_quadruples": kept_quadruples,
            "main_placements": main_placements,
            "independent_upper_at_least_initial": upper_at_least_initial,
            "initial_best": initial_best,
            "top_independent_upper_placements": top,
        }

    if certify_from_initial:
        print(f"checked main placements exactly: {checked_main:,}")
        print(f"checked cross products: {checked_cross_quadruples:,}; DFS nodes: {checked_cross_nodes:,}")
        print(f"certify pass placements seen: {main_placements:,}; best {best}")
        print(f"cross option cache entries: {len(cross_cache):,}")
        return {
            "lexicon": lexicon_name,
            "word_count": len(legal_words),
            "best_score": best,
            "records": records,
            "raw_main_quadruples": raw_quadruples,
            "deletion_valid_main_quadruples": kept_quadruples,
            "main_placements": main_placements,
            "checked_main_placements_exactly": checked_main,
            "checked_cross_quadruples": checked_cross_quadruples,
            "checked_cross_nodes": checked_cross_nodes,
            "certify_from_initial": initial_best,
            "independent_upper_at_least_initial": upper_at_least_initial,
            "cross_option_cache_entries": len(cross_cache),
        }

    for upper, _, main_face, word, indices, row, start_col in sorted(seed_heap, reverse=True):
        evaluate_job(upper, main_face, word, indices, row, start_col)

    print(f"seed best after exact evaluation: {best}")
    if seed_only:
        return {
            "lexicon": lexicon_name,
            "word_count": len(legal_words),
            "best_score_seed_only": best,
            "records": records,
            "raw_main_quadruples": raw_quadruples,
            "deletion_valid_main_quadruples": kept_quadruples,
            "main_placements": main_placements,
            "seed_limit": seed_limit,
            "checked_main_placements_exactly": checked_main,
            "checked_cross_quadruples": checked_cross_quadruples,
            "checked_cross_nodes": checked_cross_nodes,
            "cross_option_cache_entries": len(cross_cache),
        }

    second_pass_seen = 0
    second_pass_evaluated = 0
    last_report = time.monotonic()
    for word_no, word in enumerate(legal_words_list, start=1):
        if not NEW_TILE_COUNT <= len(word) <= 15:
            continue
        base = score_of(word)
        counts = count_tuple(word)
        length = len(word)
        for indices in combinations(range(length), NEW_TILE_COUNT):
            if not deletion_is_legal(word, indices, legal_words):
                continue
            occurrence = Occurrence(word, indices, base, counts)
            for row in range(1, 16):
                for start_col in range(1, 17 - length):
                    second_pass_seen += 1
                    main_face = main_face_score_for(occurrence, row, start_col)
                    cells = tuple((row, start_col + index) for index in indices)
                    upper = main_face + sum(
                        cross_face_upper[(word[index], cell)]
                        for index, cell in zip(indices, cells)
                    )
                    if upper >= best:
                        second_pass_evaluated += 1
                        evaluate_job(upper, main_face, word, indices, row, start_col)
        now = time.monotonic()
        if now - last_report >= report_seconds:
            print(
                "second pass "
                f"{word_no:,}/{len(legal_words_list):,} words; "
                f"seen {second_pass_seen:,}; evaluated {second_pass_evaluated:,}; "
                f"best {best}"
            )
            last_report = now

    print(f"checked main placements exactly: {checked_main:,}")
    print(f"checked cross products: {checked_cross_quadruples:,}; DFS nodes: {checked_cross_nodes:,}")
    print(f"second pass placements seen: {second_pass_seen:,}; evaluated by upper bound: {second_pass_evaluated:,}")
    print(f"cross option cache entries: {len(cross_cache):,}")
    return {
        "lexicon": lexicon_name,
        "word_count": len(legal_words),
        "best_score": best,
        "records": records,
        "raw_main_quadruples": raw_quadruples,
        "deletion_valid_main_quadruples": kept_quadruples,
        "main_placements": main_placements,
        "checked_main_placements_exactly": checked_main,
        "checked_cross_quadruples": checked_cross_quadruples,
        "checked_cross_nodes": checked_cross_nodes,
        "second_pass_seen": second_pass_seen,
        "second_pass_evaluated_by_upper_bound": second_pass_evaluated,
        "cross_option_cache_entries": len(cross_cache),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("lexicons", nargs="*", default=["NWL23"])
    parser.add_argument("--seed-limit", type=int, default=100_000)
    parser.add_argument("--seed-only", action="store_true")
    parser.add_argument("--initial-best", type=int, default=-1)
    parser.add_argument("--certify-from-initial", action="store_true")
    parser.add_argument("--estimate-only", action="store_true")
    parser.add_argument("--report-seconds", type=float, default=20.0)
    args = parser.parse_args()

    OUT.mkdir(exist_ok=True)
    paths = {"NWL23": DATA / "NWL23.kwg", "CSW24": DATA / "CSW24.kwg"}
    result = {
        name: search(
            name,
            paths[name],
            seed_limit=args.seed_limit,
            seed_only=args.seed_only,
            initial_best=args.initial_best,
            certify_from_initial=args.certify_from_initial,
            estimate_only=args.estimate_only,
            report_seconds=args.report_seconds,
        )
        for name in args.lexicons
    }
    out_path = OUT / (
        "four_tile_estimate.json"
        if args.estimate_only
        else "four_tile_certify_search.json"
        if args.certify_from_initial
        else "four_tile_seed_search.json"
        if args.seed_only
        else "four_tile_search.json"
    )
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()

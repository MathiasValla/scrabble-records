#!/usr/bin/env python3
"""Exhaustive upper-bound search for one-tile English Scrabble moves.

The search is deliberately phrased as a theorem checker rather than as a
game-playing engine.  For a one-tile move, at most two new words can be formed:
one horizontal and one vertical, crossing at the newly played tile.  Every
candidate word is required to survive deletion of the played tile: the pre-move
left/right (or up/down) fragments of length at least two must already be legal
words.  This is a necessary condition for the pre-move board to be legal.

What the script proves:
    no legal one-tile move can score more than the reported bound.

What still needs a human/verifier certificate:
    a reachable pre-move board attaining the bound.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
import json
import string
import sys
from typing import Iterable

from verify_1786 import Kwg, LETTER_VALUES, TILE_DISTRIBUTION


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "output"


TWS = {(1, 1), (1, 8), (1, 15), (8, 1), (8, 15), (15, 1), (15, 8), (15, 15)}
DWS = {
    (2, 2),
    (2, 14),
    (3, 3),
    (3, 13),
    (4, 4),
    (4, 12),
    (5, 5),
    (5, 11),
    (8, 8),
    (11, 5),
    (11, 11),
    (12, 4),
    (12, 12),
    (13, 3),
    (13, 13),
    (14, 2),
    (14, 14),
}
TLS = {
    (2, 6),
    (2, 10),
    (6, 2),
    (6, 6),
    (6, 10),
    (6, 14),
    (10, 2),
    (10, 6),
    (10, 10),
    (10, 14),
    (14, 6),
    (14, 10),
}
DLS = {
    (1, 4),
    (1, 12),
    (3, 7),
    (3, 9),
    (4, 1),
    (4, 8),
    (4, 15),
    (7, 3),
    (7, 7),
    (7, 9),
    (7, 13),
    (8, 4),
    (8, 12),
    (9, 3),
    (9, 7),
    (9, 9),
    (9, 13),
    (12, 1),
    (12, 8),
    (12, 15),
    (13, 7),
    (13, 9),
    (15, 4),
    (15, 12),
}

ALPHABET = string.ascii_uppercase
LETTER_INDEX = {ch: i for i, ch in enumerate(ALPHABET)}


@dataclass(frozen=True)
class Candidate:
    word: str
    index: int
    base_score: int
    counts: tuple[int, ...]

    @property
    def letter(self) -> str:
        return self.word[self.index]

    @property
    def before_fragments(self) -> tuple[str, ...]:
        fragments = []
        left = self.word[: self.index]
        right = self.word[self.index + 1 :]
        if left:
            fragments.append(left)
        if right:
            fragments.append(right)
        return tuple(fragments)


def iter_words(lexicon: Kwg) -> Iterable[str]:
    def visit_list(pointer: int, prefix: str) -> Iterable[str]:
        while pointer > 0:
            node = lexicon.nodes[pointer]
            tile = lexicon.tile(node)
            word = prefix + chr(tile + 64)
            if lexicon.accepts(node):
                yield word
            child = lexicon.arc_index(node)
            if child > 0:
                yield from visit_list(child, word)
            if lexicon.is_end(node):
                break
            pointer += 1

    yield from visit_list(lexicon.arc_index(lexicon.nodes[0]), "")


def score_of(word: str) -> int:
    return sum(LETTER_VALUES[ch] for ch in word)


def count_tuple(word: str) -> tuple[int, ...]:
    counts = [0] * 26
    for ch in word:
        counts[LETTER_INDEX[ch]] += 1
    return tuple(counts)


def premium_at(cell: tuple[int, int]) -> tuple[int, int]:
    if cell in TWS:
        return 1, 3
    if cell in DWS:
        return 1, 2
    if cell in TLS:
        return 3, 1
    if cell in DLS:
        return 2, 1
    return 1, 1


def candidate_score(candidate: Candidate, cell: tuple[int, int]) -> int:
    letter_multiplier, word_multiplier = premium_at(cell)
    extra = (letter_multiplier - 1) * LETTER_VALUES[candidate.letter]
    return (candidate.base_score + extra) * word_multiplier


def deletion_is_board_legal(word: str, index: int, legal_words: set[str]) -> bool:
    left = word[:index]
    right = word[index + 1 :]
    return (len(left) <= 1 or left in legal_words) and (len(right) <= 1 or right in legal_words)


def feasible_counts(
    first: Candidate,
    second: Candidate | None,
    placed_letter: str,
) -> tuple[bool, int, dict[str, int]]:
    counts = list(first.counts)
    if second is not None:
        counts = [a + b for a, b in zip(counts, second.counts)]
        counts[LETTER_INDEX[placed_letter]] -= 1

    excess: dict[str, int] = {}
    blank_count = 0
    for ch, count in zip(ALPHABET, counts):
        over = count - TILE_DISTRIBUTION[ch]
        if over > 0:
            excess[ch] = over
            blank_count += over

    return blank_count <= 2, blank_count, excess


def blank_penalty(excess: dict[str, int], cell: tuple[int, int]) -> int:
    """Return the score lost because forced blanks have zero face value.

    In a one-tile move every scoring word receives the same word multiplier,
    namely the multiplier under the newly played square.  A forced blank used
    for an already-present letter therefore loses value(letter) times that
    multiplier.  The newly played tile is taken to be a real tile; each English
    letter has at least one real tile, so this is always compatible with a
    feasible multiset.
    """

    _, word_multiplier = premium_at(cell)
    return word_multiplier * sum(LETTER_VALUES[ch] * count for ch, count in excess.items())


def fits_line_position(word_length: int, index: int, line_position: int) -> bool:
    start = line_position - index
    end = start + word_length - 1
    return 1 <= start and end <= 15


def start_for(word_length: int, index: int, cell: tuple[int, int], orientation: str) -> tuple[int, int]:
    row, col = cell
    if orientation == "H":
        return row, col - index
    return row - index, col


def build_candidates(legal_words: set[str]) -> dict[str, dict[int, list[Candidate]]]:
    by_letter_pos: dict[str, dict[int, list[Candidate]]] = {
        ch: {pos: [] for pos in range(1, 16)} for ch in ALPHABET
    }
    raw = 0
    deletion_ok = 0
    for word in legal_words:
        if not 2 <= len(word) <= 15:
            continue
        base = score_of(word)
        counts = count_tuple(word)
        for index, ch in enumerate(word):
            raw += 1
            if not deletion_is_board_legal(word, index, legal_words):
                continue
            deletion_ok += 1
            candidate = Candidate(word, index, base, counts)
            for pos in range(1, 16):
                if fits_line_position(len(word), index, pos):
                    by_letter_pos[ch][pos].append(candidate)

    for ch in ALPHABET:
        for pos in range(1, 16):
            by_letter_pos[ch][pos].sort(key=lambda item: item.base_score, reverse=True)

    print(f"candidate letter occurrences: {deletion_ok:,} deletion-valid / {raw:,} raw")
    return by_letter_pos


def record_for(
    score: int,
    face_score: int,
    cell: tuple[int, int],
    letter: str,
    horizontal: Candidate,
    vertical: Candidate | None,
    blanks: int,
    excess: dict[str, int],
) -> dict[str, object]:
    h_score = candidate_score(horizontal, cell)
    if vertical is None:
        v_score = 0
    else:
        v_score = candidate_score(vertical, cell)
    row, col = cell
    h_start = start_for(len(horizontal.word), horizontal.index, cell, "H")
    payload: dict[str, object] = {
        "score": score,
        "face_score_before_blank_penalty": face_score,
        "blank_score_penalty": face_score - score,
        "cell": [row, col],
        "placed_letter": letter,
        "premium": premium_at(cell),
        "horizontal": {
            "word": horizontal.word,
            "score": h_score,
            "index": horizontal.index + 1,
            "start": list(h_start),
            "fragments_before_move": list(horizontal.before_fragments),
        },
        "blanks_needed_inside_scoring_words": blanks,
        "excess_letters_inside_scoring_words": excess,
    }
    if vertical is not None:
        v_start = start_for(len(vertical.word), vertical.index, cell, "V")
        payload["vertical"] = {
            "word": vertical.word,
            "score": v_score,
            "index": vertical.index + 1,
            "start": list(v_start),
            "fragments_before_move": list(vertical.before_fragments),
        }
    return payload


def vertical_single_record_for(
    score: int,
    face_score: int,
    cell: tuple[int, int],
    letter: str,
    vertical: Candidate,
    blanks: int,
    excess: dict[str, int],
) -> dict[str, object]:
    row, col = cell
    return {
        "score": score,
        "face_score_before_blank_penalty": face_score,
        "blank_score_penalty": face_score - score,
        "cell": [row, col],
        "placed_letter": letter,
        "premium": premium_at(cell),
        "vertical": {
            "word": vertical.word,
            "score": score,
            "index": vertical.index + 1,
            "start": list(start_for(len(vertical.word), vertical.index, cell, "V")),
            "fragments_before_move": list(vertical.before_fragments),
        },
        "blanks_needed_inside_scoring_words": blanks,
        "excess_letters_inside_scoring_words": excess,
    }


def search(lexicon_name: str, kwg_path: Path) -> dict[str, object]:
    print(f"\n=== {lexicon_name} ===")
    lexicon = Kwg(kwg_path)
    legal_words = {word for word in iter_words(lexicon) if word.isalpha()}
    print(f"words: {len(legal_words):,}")
    by_letter_pos = build_candidates(legal_words)

    best = -1
    records: list[dict[str, object]] = []

    jobs = []
    for row in range(1, 16):
        for col in range(1, 16):
            cell = (row, col)
            for letter in ALPHABET:
                hlist = by_letter_pos[letter][col]
                vlist = by_letter_pos[letter][row]
                if hlist:
                    jobs.append((candidate_score(hlist[0], cell), cell, letter, "single_h"))
                if vlist:
                    jobs.append((candidate_score(vlist[0], cell), cell, letter, "single_v"))
                if hlist and vlist:
                    upper = candidate_score(hlist[0], cell) + candidate_score(vlist[0], cell)
                    jobs.append((upper, cell, letter, "cross"))

    jobs.sort(reverse=True, key=lambda item: item[0])
    checked_jobs = 0
    checked_pairs = 0
    pruned_jobs = 0

    def consider(record: dict[str, object]) -> None:
        nonlocal best, records
        score = int(record["score"])
        if score > best:
            best = score
            records = [record]
            print(f"new best {best}: {record}")
        elif score == best and len(records) < 50:
            records.append(record)

    for upper, cell, letter, mode in jobs:
        if upper < best:
            pruned_jobs += 1
            continue
        checked_jobs += 1
        row, col = cell
        hlist = by_letter_pos[letter][col]
        vlist = by_letter_pos[letter][row]

        if mode == "single_h":
            for h in hlist:
                face_score = candidate_score(h, cell)
                if face_score < best:
                    break
                ok, blanks, excess = feasible_counts(h, None, letter)
                if ok:
                    score = face_score - blank_penalty(excess, cell)
                    consider(record_for(score, face_score, cell, letter, h, None, blanks, excess))
        elif mode == "single_v":
            for v in vlist:
                face_score = candidate_score(v, cell)
                if face_score < best:
                    break
                ok, blanks, excess = feasible_counts(v, None, letter)
                if ok:
                    score = face_score - blank_penalty(excess, cell)
                    consider(vertical_single_record_for(score, face_score, cell, letter, v, blanks, excess))
        else:
            if not hlist or not vlist:
                continue
            top_v = candidate_score(vlist[0], cell)
            for h in hlist:
                h_score = candidate_score(h, cell)
                if h_score + top_v < best:
                    break
                for v in vlist:
                    face_score = h_score + candidate_score(v, cell)
                    if face_score < best:
                        break
                    checked_pairs += 1
                    ok, blanks, excess = feasible_counts(h, v, letter)
                    if ok:
                        score = face_score - blank_penalty(excess, cell)
                        consider(record_for(score, face_score, cell, letter, h, v, blanks, excess))

    print(f"checked jobs: {checked_jobs:,}; checked pairs above live bound: {checked_pairs:,}; pruned jobs: {pruned_jobs:,}")
    return {
        "lexicon": lexicon_name,
        "word_count": len(legal_words),
        "best_score": best,
        "records": records,
        "checked_jobs": checked_jobs,
        "checked_pairs_above_live_bound": checked_pairs,
        "pruned_jobs": pruned_jobs,
    }


def main() -> None:
    OUT.mkdir(exist_ok=True)
    requested = sys.argv[1:] or ["NWL23", "CSW24"]
    paths = {"NWL23": DATA / "NWL23.kwg", "CSW24": DATA / "CSW24.kwg"}
    result = {name: search(name, paths[name]) for name in requested}
    out_path = OUT / "one_tile_search.json"
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()

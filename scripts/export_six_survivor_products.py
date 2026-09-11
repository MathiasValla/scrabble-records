#!/usr/bin/env python3
"""Export all six-tile upper-bound survivors as exact product instances."""

from __future__ import annotations

from pathlib import Path
import argparse
import re

import search_five_tile as base
from search_five_tile import (
    DATA,
    OUT,
    Occurrence,
    build_cross_occurrences,
    count_tuple,
    cross_options_for,
    main_placement_from_occurrence,
    score_of,
)
from search_one_tile import iter_words
from verify_1786 import Kwg


base.NEW_TILE_COUNT = 6


def cell_id(cell: tuple[int, int]) -> int:
    row, col = cell
    return (row - 1) * 15 + (col - 1)


def write_entries(handle, entries) -> None:
    for cell, ch, coefficient in entries:
        handle.write(f"{cell_id(cell)} {ord(ch) - ord('A')} {coefficient}\n")


def safe_name(word: str, indices: list[int], row: int, start_col: int, initial_best: int) -> str:
    joined = "_".join(str(index) for index in indices)
    return f"six_tile_product_{word.lower()}_{joined}_r{row}_c{start_col}_t{initial_best}.txt"


def parse_survivors(path: Path, threshold: int) -> list[dict[str, object]]:
    text = path.read_text()
    survivors = []
    pattern = re.compile(
        r"^top (\d+) upper (\d+) main (\d+) word ([A-Z]+) "
        r"indices ([0-9 ]+) row (\d+) start (\d+)$",
        re.MULTILINE,
    )
    for match in pattern.finditer(text):
        rank = int(match.group(1))
        upper = int(match.group(2))
        if upper < threshold:
            continue
        survivors.append(
            {
                "rank": rank,
                "upper": upper,
                "main_score": int(match.group(3)),
                "word": match.group(4),
                "indices": [int(value) for value in match.group(5).split()],
                "row": int(match.group(6)),
                "start_col": int(match.group(7)),
            }
        )
    return survivors


def export_instance(
    survivor: dict[str, object],
    cross_occurrences,
    *,
    initial_best: int,
    output_path: Path | None = None,
) -> Path:
    word = str(survivor["word"])
    indices = [int(value) for value in survivor["indices"]]
    row = int(survivor["row"])
    start_col = int(survivor["start_col"])
    occurrence = Occurrence(word, tuple(index - 1 for index in indices), score_of(word), count_tuple(word))
    main = main_placement_from_occurrence(occurrence, row, start_col)
    if main.face_score != int(survivor["main_score"]):
        raise AssertionError(f"main score mismatch for {survivor}")

    option_lists = tuple(
        cross_options_for(cross_occurrences, letter, cell)
        for letter, cell in zip(main.letters, main.new_cells)
    )
    out_path = output_path or OUT / safe_name(word, indices, row, start_col, initial_best)
    with out_path.open("w") as handle:
        handle.write(f"BEST {initial_best}\n")
        handle.write(f"SLOTS {len(option_lists)}\n")
        handle.write(f"MAIN_FACE {main.face_score}\n")
        handle.write("MAIN_WORD " + main.word + "\n")
        handle.write("MAIN_INDICES " + " ".join(str(index + 1) for index in main.indices) + "\n")
        handle.write("MAIN_CELLS " + " ".join(str(cell_id(cell)) for cell in main.new_cells) + "\n")
        handle.write("MAIN_COUNTS " + " ".join(str(value) for value in count_tuple(main.word)) + "\n")
        handle.write(f"MAIN_ENTRIES {len(main.entries)}\n")
        write_entries(handle, main.entries)
        for slot, options in enumerate(option_lists):
            handle.write(f"SLOT {slot} {len(options)}\n")
            for option in options:
                option_word = option.word if option.word is not None else "."
                index = option.index + 1 if option.index is not None else 0
                start_row = option.start_row if option.start_row is not None else 0
                handle.write(
                    "OPTION "
                    f"{option.face_score} {option_word} {index} {start_row} {len(option.entries)} "
                    + " ".join(str(value) for value in option.counts_without_new)
                    + "\n"
                )
                write_entries(handle, option.entries)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lexicon", default="NWL23", choices=["NWL23", "CSW24"])
    parser.add_argument("--upper-file", default="six_tile_upper_1726.txt")
    parser.add_argument("--threshold", type=int, default=1726)
    parser.add_argument("--initial-best", type=int, default=1726)
    args = parser.parse_args()

    OUT.mkdir(exist_ok=True)
    survivors = parse_survivors(OUT / args.upper_file, args.threshold)
    print(f"survivors: {len(survivors)}")
    lexicon = Kwg(DATA / f"{args.lexicon}.kwg")
    legal_words = {word for word in iter_words(lexicon) if word.isalpha()}
    cross_occurrences = build_cross_occurrences(legal_words)
    for survivor in survivors:
        out_path = export_instance(survivor, cross_occurrences, initial_best=args.initial_best)
        print(
            f"rank {survivor['rank']}: upper={survivor['upper']} "
            f"word={survivor['word']} indices={survivor['indices']} -> {out_path}"
        )


if __name__ == "__main__":
    main()

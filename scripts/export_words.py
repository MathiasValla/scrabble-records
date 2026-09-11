#!/usr/bin/env python3
"""Export a KWG lexicon to a plain uppercase word list."""

from __future__ import annotations

from pathlib import Path
import argparse

from search_five_tile import DATA, OUT
from search_one_tile import iter_words
from verify_1786 import Kwg


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("lexicon", choices=["NWL23", "CSW24"])
    parser.add_argument("--output")
    args = parser.parse_args()

    words = sorted(word for word in iter_words(Kwg(DATA / f"{args.lexicon}.kwg")) if word.isalpha())
    OUT.mkdir(exist_ok=True)
    out_path = OUT / (args.output or f"{args.lexicon}_words.txt")
    out_path.write_text("\n".join(words) + "\n")
    print(f"wrote {len(words):,} words to {out_path}")


if __name__ == "__main__":
    main()

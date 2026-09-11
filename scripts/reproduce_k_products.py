#!/usr/bin/env python3
"""Enumerate all threshold-surviving scoring products, without legality rejection.

The input is the complete output of scan_k_upper. Every record at or above the
fixed threshold is retained, including records below a subsequently found best.
"""
import argparse
from dataclasses import asdict
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import time

import search_five_tile as base
from search_two_tile import score_after_best_blanks
from export_six_survivor_products import parse_survivors

ROOT = Path(__file__).resolve().parents[1]


def run(lexicon, k, upper_path, output_path):
    base.NEW_TILE_COUNT = k
    lines = upper_path.read_text().splitlines()
    metadata = {line.split()[0]: int(line.split()[1]) for line in lines if not line.startswith('top ')}
    threshold = metadata['threshold']
    survivors = parse_survivors(upper_path, threshold)
    assert len(survivors) == metadata['independent_upper_at_least_threshold']
    words = set((ROOT / 'output' / f'{lexicon}_words.txt').read_text().splitlines())
    cross_occurrences = base.build_cross_occurrences(words)

    @lru_cache(None)
    def options(letter, cell):
        # Tie order is part of the reproducible certificate.
        return sorted(base.cross_options_for(cross_occurrences, letter, cell),
                      key=lambda o: (-o.face_score, o.word or '', o.index or 0))

    all_records, reports = [], []
    started = time.monotonic()
    for survivor in survivors:
        word = survivor['word']
        occurrence = base.Occurrence(word, tuple(i-1 for i in survivor['indices']),
                                     base.score_of(word), base.count_tuple(word))
        main = base.main_placement_from_occurrence(occurrence, survivor['row'], survivor['start_col'])
        assert main.face_score == survivor['main_score']
        slots = [options(ch, cell) for ch, cell in zip(main.letters, main.new_cells)]
        assert main.face_score + sum(s[0].face_score for s in slots) <= survivor['upper']
        order = sorted(range(k), key=lambda j: len(slots[j]))
        suffix = [0]*(k+1)
        for depth in range(k-1, -1, -1):
            suffix[depth] = suffix[depth+1] + slots[order[depth]][0].face_score
        selected = [None]*k
        nodes = leaves = 0
        records = []

        def dfs(depth, face, counts, entries):
            nonlocal nodes, leaves
            nodes += 1
            # Every excess in a subset already forces blanks inside that subset.
            # Future support cannot relocate those forced blanks out of it;
            # future scored words can only increase its cell coefficients.
            partial_score, partial_penalty, _ = score_after_best_blanks(face, entries)
            if partial_score is None or face + suffix[depth] - partial_penalty < threshold:
                return
            if depth == k:
                leaves += 1
                score, penalty, excess = score_after_best_blanks(face, entries)
                if score is None or score < threshold:
                    return
                record = dict(survivor, score=score, face=face, penalty=penalty, excess=excess,
                              cross_words=[o.word for o in selected],
                              cross_scores=[o.face_score for o in selected],
                              crosses=[asdict(o) for o in selected],
                              main_entries=main.entries)
                records.append(record)
                return
            j = order[depth]
            for option in slots[j]:
                next_face = face + option.face_score
                if next_face + suffix[depth+1] < threshold:
                    break
                next_counts = base.add_count_tuples(counts, option.counts_without_new)
                if base.blank_count_for_counts(next_counts) > 2:
                    continue
                if next_face + suffix[depth+1] - base.optimistic_blank_penalty_for_counts(next_counts) < threshold:
                    continue
                selected[j] = option
                dfs(depth+1, next_face, next_counts, entries+option.entries)
            selected[j] = None

        dfs(0, main.face_score, base.count_tuple(word), main.entries)
        all_records.extend(records)
        reports.append(dict(rank=survivor['rank'], nodes=nodes, leaves=leaves, records=len(records)))
        if records or survivor['rank'] % 25 == 0:
            print(f"{lexicon} k={k} rank={survivor['rank']}/{len(survivors)} nodes={nodes} records={len(records)} elapsed={time.monotonic()-started:.1f}s", flush=True)
    all_records.sort(key=lambda r: (-r['score'], r['rank'], tuple(w or '' for w in r['cross_words'])))
    result = dict(lexicon=lexicon, k=k, threshold_prebonus=threshold, metadata=metadata,
                  upper_sha256=hashlib.sha256(upper_path.read_bytes()).hexdigest(),
                  words_sha256=hashlib.sha256((ROOT/'output'/f'{lexicon}_words.txt').read_bytes()).hexdigest(),
                  kwg_sha256=hashlib.sha256((ROOT/'data'/f'{lexicon}.kwg').read_bytes()).hexdigest(),
                  reports=reports, records=all_records,
                  best_prebonus=max((r['score'] for r in all_records), default=None))
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(f"DONE {lexicon} k={k}: {len(all_records)} records, best={result['best_prebonus']}", flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('lexicon', choices=['NWL23','CSW24'])
    parser.add_argument('k', type=int)
    args = parser.parse_args()
    run(args.lexicon, args.k, ROOT/'output'/f'{args.lexicon}_k{args.k}_upper.txt',
        ROOT/'output'/f'{args.lexicon}_k{args.k}_products.json')

#!/usr/bin/env python3
"""Fresh exact C++ exclusions for NWL23 k=3..5; never use for board legality."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import search_five_tile as base
from export_six_survivor_products import export_instance, parse_survivors

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('k',type=int,choices=[3,4,5])
    k=parser.parse_args().k
    base.NEW_TILE_COUNT=k
    upper=ROOT/'output'/f'NWL23_k{k}_upper.txt'
    metadata={line.split()[0]:int(line.split()[1]) for line in upper.read_text().splitlines() if not line.startswith('top ')}
    threshold=metadata['threshold']
    survivors=parse_survivors(upper,threshold)
    assert len(survivors)==metadata['independent_upper_at_least_threshold']
    words=set((ROOT/'output/NWL23_words.txt').read_text().splitlines())
    crosses=base.build_cross_occurrences(words)
    folder=ROOT/'output'/'reproduction'/f'NWL23_k{k}'
    folder.mkdir(parents=True,exist_ok=True)
    summaries=[]
    for s in survivors:
        instance=export_instance(s,crosses,initial_best=threshold,output_path=folder/f"rank{s['rank']}.txt")
        result=folder/f"rank{s['rank']}_result.txt"
        with result.open('w') as stream:
            subprocess.run([str(ROOT/'tmp/exact_product_search'),str(instance)],stdout=stream,check=True)
        lines=result.read_text().splitlines()
        assert not any(line.startswith('record ') for line in lines), f'unexcluded pattern {instance}'
        summaries.append(dict(rank=s['rank'],output=str(result.relative_to(ROOT)),
                              nodes=int(next(l.split()[1] for l in lines if l.startswith('nodes ')))))
        print(f"k={k} rank={s['rank']}: excluded",flush=True)
    out=ROOT/'output'/f'NWL23_k{k}_cpp_exclusion.json'
    out.write_text(json.dumps(dict(metadata=metadata,summaries=summaries,remaining=0,
                                   upper_sha256=hashlib.sha256(upper.read_bytes()).hexdigest()),indent=2,sort_keys=True)+'\n')


if __name__=='__main__':
    main()

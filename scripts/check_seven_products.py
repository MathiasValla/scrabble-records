#!/usr/bin/env python3
"""Independently check complete product records and completion-safe row cuts."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import search_five_tile as B
from export_six_survivor_products import parse_survivors
from search_two_tile import score_after_best_blanks
from repair_six_upper import LineCompletion, pattern_board, bad_rows

ROOT=Path(__file__).resolve().parents[1]


def read_products(lexicon,k,folder=None,upper=None,stream=False):
    B.NEW_TILE_COUNT=k
    folder=Path(folder) if folder else ROOT/'output/resource'/f'{lexicon}_k{k}'
    summary=json.loads((folder/'summary.json').read_text())
    assert summary['complete']
    words=set((ROOT/'output'/f'{lexicon}_words.txt').read_text().splitlines())
    occurrences=B.build_cross_occurrences(words)
    upper=Path(upper) if upper else ROOT/'output'/f'{lexicon}_k{k}_upper.txt'
    if 'input_sha256' in summary:
        assert summary['input_sha256']==dict(upper=hashlib.sha256(upper.read_bytes()).hexdigest(),
            words=hashlib.sha256((ROOT/'output'/f'{lexicon}_words.txt').read_bytes()).hexdigest())
    meta={x['rank']:x for x in parse_survivors(upper,summary['metadata']['threshold'])}
    assert set(meta)=={x['rank'] for x in summary['reports']}
    records=iter_records(summary,meta,occurrences,folder,k)
    return words,records if stream else list(records)


def iter_records(summary,meta,occurrences,folder,k):
    """Yield checked records; callers must not mutate shared cross dictionaries."""
    from resource_prices import certify
    for report in summary['reports']:
        s=meta[report['rank']]
        occ=B.Occurrence(s['word'],tuple(i-1 for i in s['indices']),B.score_of(s['word']),B.count_tuple(s['word']))
        main=B.main_placement_from_occurrence(occ,s['row'],s['start_col'])
        slots=[B.cross_options_for(occurrences,a,p) for a,p in zip(main.letters,main.new_cells)]
        u=certify(main,slots,report['prices'],report['price_scale'])
        assert u==report['resource_upper_numerator']
        if report['status']=='resource excluded':
            assert u<summary['metadata']['threshold']*report['price_scale'];continue
        assert report['status']=='products enumerated'
        lookups=[{(o.word or '.',o.start_row or 0,(o.index+1) if o.index is not None else 0):o for o in slot} for slot in slots]
        encoded={}
        def encode(option):
            key=id(option)
            if key not in encoded:encoded[key]=asdict(option)
            return encoded[key]
        number=0;footer=False
        with (folder/f"rank{s['rank']}_result.txt").open() as lines:
            for line in lines:
                if line.strip()==f'records_retained {report["records"]}':footer=True
                if not line.startswith('record '):continue
                number+=1
                fields=line.split();score,face,penalty=map(int,(fields[3],fields[5],fields[7]))
                parts=line.strip().split(' | ')[1:];assert len(parts)==k
                crosses=[]
                for j,part in enumerate(parts):
                    w,sc,sr,wi=part.split(':')
                    o=lookups[j][w,int(sr),int(wi)];assert int(sc)==o.face_score
                    crosses.append(o)
                entries=main.entries+tuple(e for o in crosses for e in o.entries)
                expected_face=main.face_score+sum(o.face_score for o in crosses)
                expected_score,expected_penalty,_=score_after_best_blanks(expected_face,entries)
                assert (score,face,penalty)==(expected_score,expected_face,expected_penalty)
                assert score>=summary['metadata']['threshold']
                yield dict(s,record=number,score=score,face=face,penalty=penalty,
                           crosses=[encode(o) for o in crosses],main_entries=main.entries)
        assert footer and number==report['records']


def main():
    words,records=read_products('NWL23',7)
    assert len(records)==3748
    completion=LineCompletion(words);row_ok=[];singleton_ok=[]
    for record in records:
        board,blocked=pattern_board(record)
        if bad_rows(board,blocked,completion):continue
        row_ok.append(record)
        new={(record['row'],record['start_col']+i-1) for i in record['indices']}
        old={p:ch for p,ch in board.items() if p not in new}
        assert record['row'] in (1,15)
        edge=record['row'];step=1 if edge==1 else -1
        isolated=[(p,ch) for p,ch in old.items() if p[0]==edge and (edge,p[1]-1) not in old and (edge,p[1]+1) not in old]
        impossible=False
        for (_,col),ch in isolated:
            possible=[]
            for w in sorted(words):
                if not 2<=len(w)<=15 or (w[0] if step==1 else w[-1])!=ch:continue
                hook=w if step==1 else w[::-1]
                addition={(edge+step*i,col):a for i,a in enumerate(hook)}
                if any(p in blocked or (p in board and board[p]!=a) for p,a in addition.items()):continue
                end=(edge+step*len(hook),col)
                if end in board:continue
                ext=board|addition;barriers=blocked|({end} if 1<=end[0]<=15 else set())
                if not bad_rows(ext,barriers,completion):possible.append(w)
            if not possible:impossible=True;break
        if not impossible:singleton_ok.append(record)
    output=dict(products=len(records),after_row_completion=len(row_ok),after_singleton_hooks=len(singleton_ok),records=singleton_ok)
    (ROOT/'output/seven_completion_stage1.json').write_text(json.dumps(output,indent=2,sort_keys=True)+'\n')
    print({k:v for k,v in output.items() if k!='records'})


if __name__=='__main__':main()

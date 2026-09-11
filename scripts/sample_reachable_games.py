#!/usr/bin/env python3
"""Empirical post-opening scores under a specified cooperative-game model.

An opening word is uniform among playable 2..7-letter entries; its position
through H8 is uniform. Later proposals pick an occupied anchor uniformly, an
orientation uniformly, then a matching (word, letter-index) occurrence uniformly
among 2..15-letter entries. Accept the first legal proposal with 1..7 new tiles,
a feasible physical bag, positive score, and at most 86 total tiles. Stop after
the step/attempt cap. Draws are existential, not random competition draws.

For each k, choose one post-opening k-tile move uniformly from each game that
contains one. Games, rather than all their correlated moves, are the sampling
units. Every complete history is independently replayed with legal rack streams.
"""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import sys
import time

from verify_1786 import Kwg,TILE_DISTRIBUTION,validate_forward_move,all_formed_words_after_move
from verify_small_records import move,verify
from verify_one_tile import score_word

ROOT=Path(__file__).resolve().parents[1]


def allocate(board,blanks,candidate):
    remaining=TILE_DISTRIBUTION-Counter(ch for p,ch in board.items() if p not in blanks)
    added_blanks=set()
    for p,ch in zip(candidate.cells,candidate.word):
        if p in board:continue
        if remaining[ch]:remaining[ch]-=1
        else:added_blanks.add(p)
    if len(blanks)+len(added_blanks)>2:return None
    return blanks|added_blanks


def attempt(board,blanks,candidate,lex,first=False):
    if any(not(1<=r<=15 and 1<=c<=15) for r,c in candidate.cells):return None
    if any(p in board and board[p]!=ch for p,ch in zip(candidate.cells,candidate.word)):return None
    new=set(candidate.cells)-set(board)
    if not 1<=len(new)<=7 or len(board)+len(new)>86:return None
    assigned=allocate(board,blanks,candidate)
    if assigned is None:return None
    try:after=validate_forward_move(board,candidate,lex,first_move=first)
    except AssertionError:return None
    formed=all_formed_words_after_move(board,{p:after[p] for p in new})
    score=sum(score_word(w,new,assigned) for w in formed)+(50 if len(new)==7 else 0)
    if score<=0:return None
    return after,assigned,score,len(new)


def quantile(values,p):
    return sorted(values)[max(0,math.ceil(len(values)*p)-1)]


def main():
    ap=argparse.ArgumentParser();ap.add_argument('lexicon',choices=['NWL23','CSW24'])
    ap.add_argument('--games',type=int,default=20);ap.add_argument('--seed',type=int,default=20260910)
    ap.add_argument('--steps',type=int,default=24);ap.add_argument('--attempts',type=int,default=3000)
    ap.add_argument('--total-seconds',type=int,default=60)
    a=ap.parse_args();start=time.monotonic()
    lex=Kwg(ROOT/'data'/f'{a.lexicon}.kwg')
    words=sorted(w for w in (ROOT/'output'/f'{a.lexicon}_words.txt').read_text().splitlines() if 2<=len(w)<=15)
    openings=[w for w in words if len(w)<=7]
    occurrences=defaultdict(list)
    for w in words:
        for i,ch in enumerate(w):occurrences[ch].append((w,i))
    folder=ROOT/'output/sampling'/a.lexicon;folder.mkdir(parents=True,exist_ok=True)
    samples={k:[] for k in range(1,8)};games=[];proposals=0
    for game in range(a.games):
        if time.monotonic()-start>=a.total_seconds:break
        seed=int.from_bytes(hashlib.sha256(f'{a.seed}:{a.lexicon}:{game}'.encode()).digest(),'big')
        rng=random.Random(seed);board={};blanks=set();history=[];moves=[];per_k=defaultdict(list)
        for step in range(a.steps):
            result=None
            for trial in range(a.attempts):
                proposals+=1
                if not board:
                    w=rng.choice(openings);candidate=move('H',w,8,8-rng.randrange(len(w)))
                else:
                    r,c=rng.choice(sorted(board))
                    w,i=rng.choice(occurrences[board[r,c]])
                    orientation=rng.choice(['H','V'])
                    candidate=move(orientation,w,r-(i if orientation=='V' else 0),c-(i if orientation=='H' else 0))
                result=attempt(board,blanks,candidate,lex,first=not board)
                if result:break
            if not result:break
            board,blanks,score,k=result;moves.append(candidate)
            history.append(dict(orientation=candidate.orientation,word=candidate.word,
                                row=candidate.cells[0][0],col=candidate.cells[0][1],score=score,k=k))
            if step:per_k[k].append((step,score))
        assert history
        certificate=verify(a.lexicon,history[-1]['k'],moves[:-1],moves[-1],blanks,history[-1]['score'])
        assert all(h['total']>0 for h in certificate['history'])
        selections={}
        for k,options in sorted(per_k.items()):
            step,score=rng.choice(options);samples[k].append(score);selections[k]=dict(step=step,score=score)
        games.append(dict(index=game,history=history,blank_cells=sorted(blanks),
                          final_tiles=len(board),selected=selections,
                          rack_stream_sha256=hashlib.sha256(certificate['active_player_draw_stream'].encode()).hexdigest()))
        if (game+1)%10==0:print(a.lexicon,'games',game+1,'seconds',round(time.monotonic()-start,2),flush=True)
    stats={}
    for k,values in samples.items():
        stats[k]=dict(n=len(values),mean=sum(values)/len(values) if values else None,
            median=quantile(values,.5) if values else None,q10=quantile(values,.1) if values else None,
            q90=quantile(values,.9) if values else None,maximum=max(values) if values else None,
            dkw_95_simultaneous_14_ecdfs=min(1,math.sqrt(math.log(2*14/.05)/(2*len(values)))) if values else None)
    result=dict(model=__doc__,arguments=vars(a),completed_games=len(games),complete=len(games)==a.games,
                proposals=proposals,seconds=time.monotonic()-start,python=sys.version,
                kwg_sha256=hashlib.sha256((ROOT/'data'/f'{a.lexicon}.kwg').read_bytes()).hexdigest(),
                statistics=stats,samples=samples,games=games)
    (folder/'sample.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print('Completed',len(games),'of',a.games,'games in',round(result['seconds'],2),'seconds;',stats,flush=True)


if __name__=='__main__':main()

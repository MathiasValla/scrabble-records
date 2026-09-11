#!/usr/bin/env python3
"""Completion-safe elimination of the twenty NWL23 six-tile scoring patterns."""
from collections import defaultdict
from functools import lru_cache
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class LineCompletion:
    def __init__(self, words):
        self.words = set(words)
        self.bits = defaultdict(int)
        self.full = {}
        by_length = defaultdict(list)
        for w in sorted(words):
            if 2 <= len(w) <= 15:
                by_length[len(w)].append(w)
        for length, group in by_length.items():
            self.full[length] = (1 << len(group))-1
            for index, word in enumerate(group):
                bit = 1 << index
                for position, ch in enumerate(word):
                    self.bits[length,position,ch] |= bit

    @lru_cache(None)
    def word_exists(self, pattern):
        if len(pattern)==1:
            return pattern!='.'
        mask = self.full.get(len(pattern),0)
        for i,ch in enumerate(pattern):
            if ch!='.':
                mask &= self.bits.get((len(pattern),i,ch),0)
                if not mask:
                    return False
        return bool(mask)

    @lru_cache(None)
    def possible(self, pattern):
        """'.' is optional, '#' forced empty, letters are mandatory occupied."""
        n=len(pattern)

        @lru_cache(None)
        def suffix(start):
            if start>=n:
                return True
            if pattern[start] in '.#' and suffix(start+1):
                return True
            if pattern[start]=='#':
                return False
            for end in range(start+1,n+1):
                part=pattern[start:end]
                if '#' in part:
                    break
                if all(ch=='.' for ch in part):
                    continue
                if end<n and pattern[end] not in '.#':
                    continue
                if self.word_exists(part) and suffix(end+1):
                    return True
            return False
        return suffix(0)


def pattern_board(record):
    board, blocked = {},set()
    for cell,ch,_ in record['main_entries']:
        board[tuple(cell)] = ch
    row,start=record['row'],record['start_col']
    for col in (start-1,start+len(record['word'])):
        if 1<=col<=15:
            blocked.add((row,col))
    for i,cross in zip(record['indices'],record['crosses']):
        col=start+i-1
        if cross['word'] is None:
            ends=(row-1,row+1)
        else:
            for cell,ch,_ in cross['entries']:
                cell=tuple(cell)
                assert cell not in board or board[cell]==ch
                board[cell]=ch
            ends=(cross['start_row']-1,cross['start_row']+len(cross['word']))
        for r in ends:
            if 1<=r<=15:
                blocked.add((r,col))
    assert not set(board)&blocked
    return board,blocked


def bad_rows(board,blocked,completion):
    return [(row,p) for row in range(1,16)
            if not completion.possible(p:=''.join(board.get((row,col),'#' if (row,col) in blocked else '.')
                                                  for col in range(1,16)))]


def main():
    words=set((ROOT/'output/NWL23_words.txt').read_text().splitlines())
    completion=LineCompletion(words)
    # A nonword can be repaired. The old blanket rejection is invalid.
    assert 'CINQ' in words and 'CHEQUE' in words
    assert completion.possible('C.NQ...........')
    assert completion.possible('C.EQ...........')
    assert not completion.possible('CO.Q...D...G..A')
    data=json.loads((ROOT/'output/NWL23_k6_products.json').read_text())
    assert len(data['records'])==20
    results=[]
    for number,record in enumerate(data['records']):
        board,blocked=pattern_board(record)
        bad=bad_rows(board,blocked,completion)
        if bad:
            results.append(dict(record=number,score=record['score'],reason='uncompletable row',bad_rows=bad))
            continue
        assert record['row']==1
        new={(1,record['start_col']+i-1) for i in record['indices']}
        old={p:ch for p,ch in board.items() if p not in new}
        singletons=[(p,ch) for p,ch in old.items() if p[0]==1 and (1,p[1]-1) not in old and (1,p[1]+1) not in old]
        eliminated=False
        for (row,col),ch in singletons:
            candidates=[w for w in sorted(words) if 2<=len(w)<=15 and w[0]==ch]
            hook_survivors=[]
            for hook in candidates:
                additions={(i+1,col):c for i,c in enumerate(hook)}
                if any(p in blocked or (p in board and board[p]!=c) for p,c in additions.items()):
                    continue
                end=(len(hook)+1,col)
                if end in board:
                    continue
                extension=board|additions
                barriers=blocked|({end} if end[0]<=15 else set())
                if not bad_rows(extension,barriers,completion):
                    hook_survivors.append(hook)
            if not hook_survivors:
                results.append(dict(record=number,score=record['score'],reason='mandatory singleton hook impossible',
                                    cell=[row,col],letter=ch,words_examined=len(candidates)))
                eliminated=True
                break
        if not eliminated:
            raise AssertionError(f'unresolved scoring product {number}')
    output=ROOT/'output/NWL23_k6_completion_safe.json'
    output.write_text(json.dumps(dict(records=results,remaining=0),indent=2,sort_keys=True)+'\n')
    print('NWL23 k=6: 20 products eliminated with completion-safe relaxations')
    print(dict((reason,sum(r['reason']==reason for r in results)) for reason in sorted({r['reason'] for r in results})))


if __name__=='__main__':
    main()

#!/usr/bin/env python3
"""Adversarial checks of the common bound, including last-letter deletions."""
import itertools
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from search_one_tile import premium_at
from search_two_tile import deletion_is_legal, score_after_best_blanks
from verify_1786 import LETTER_VALUES

ROOT = Path(__file__).resolve().parents[1]


class BoundsTests(unittest.TestCase):
    def test_obsolete_partial_board_exclusion_is_disabled(self):
        from verify_six_tile import parse_legal_eliminations
        with self.assertRaises(RuntimeError):
            parse_legal_eliminations()

    def test_blank_counted_by_physical_square(self):
        entries = (((1,1),'Z',9), ((1,1),'Z',3), ((2,1),'Z',1))
        score, penalty, excess = score_after_best_blanks(130, entries)
        self.assertEqual((score,penalty,excess),(120,10,{'Z':1}))

    def test_three_excess_letters_are_impossible(self):
        entries = tuple(((1,c),'Z',1) for c in range(1,5))
        self.assertIsNone(score_after_best_blanks(40,entries)[0])

    def test_transposition_preserves_every_premium(self):
        for r in range(1,16):
            for c in range(1,16):
                self.assertEqual(premium_at((r,c)),premium_at((c,r)))

    def test_cpp_matches_direct_enumeration_on_small_lexicon(self):
        words = {'AA','AAA','AAAA','AAAAA','AAAAAA','AAAAAAA','AZ','ZA','AZAAAAZ'}
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            directory = Path(directory)
            lex = directory/'words.txt'
            lex.write_text('\n'.join(sorted(words))+'\n')
            for k in range(2,8):
                output = directory/f'k{k}.txt'
                subprocess.run([str(ROOT/'tmp/scan_k_upper'),str(lex),str(k),'70',str(output)],check=True,capture_output=True)
                expected, raw, kept, placements = set(),0,0,0
                for word in words:
                    for holes in itertools.combinations(range(len(word)),k):
                        raw += 1
                        if not deletion_is_legal(word,holes,words):
                            continue
                        kept += 1
                        for row in range(1,16):
                            for start in range(1,17-len(word)):
                                placements += 1
                                mult,letter_sum = 1,sum(LETTER_VALUES[ch] for ch in word)
                                crosses = 0
                                for index in holes:
                                    cell = (row,start+index)
                                    lm,wm = premium_at(cell)
                                    mult *= wm
                                    letter_sum += (lm-1)*LETTER_VALUES[word[index]]
                                    cross_scores = [0]
                                    for cross in words:
                                        for ci,ch in enumerate(cross):
                                            if ch!=word[index] or not 1<=row-ci<=16-len(cross):
                                                continue
                                            if deletion_is_legal(cross,(ci,),words):
                                                cross_scores.append(wm*(sum(LETTER_VALUES[x] for x in cross)+(lm-1)*LETTER_VALUES[ch]))
                                    crosses += max(cross_scores)
                                main = mult*letter_sum
                                if main+crosses>=70:
                                    expected.add((main+crosses,main,word,tuple(i+1 for i in holes),row,start))
                actual = set()
                metadata = {}
                for line in output.read_text().splitlines():
                    if not line.startswith('top '):
                        key,value=line.split(); metadata[key]=int(value); continue
                    match=re.fullmatch(r'top \d+ upper (\d+) main (\d+) word (\w+) indices ([\d ]+) row (\d+) start (\d+)',line)
                    a,b,w,indices,r,c=match.groups()
                    actual.add((int(a),int(b),w,tuple(map(int,indices.split())),int(r),int(c)))
                self.assertEqual(actual,expected,f'k={k}')
                self.assertEqual((metadata['raw_main_choices'],metadata['deletion_valid_main_choices'],metadata['main_placements']),
                                 (raw,kept,placements))


if __name__=='__main__':
    unittest.main()

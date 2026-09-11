#!/usr/bin/env python3
"""Adversarial finite tests for the upper-proof relaxations."""
import itertools
import random
import unittest
from unittest.mock import patch
import tempfile
from collections import Counter
from pathlib import Path
from complete_seven_hooks import Completion
from seven_tail.common import Lexicon, LETTERS
from seven_tail.verify_record74_completion import components,connectivity_cores


class CompletenessTests(unittest.TestCase):
    def test_streamed_products_require_footer_count_and_correct_score(self):
        import search_five_tile as B
        from check_seven_products import iter_records
        s=dict(rank=1,word='AA',indices=[1,2],row=5,start_col=5)
        with patch.object(B,'NEW_TILE_COUNT',2),patch.object(B,'cross_options_for',return_value=[B.NONE_CROSS]):
            occ=B.Occurrence('AA',(0,1),2,B.count_tuple('AA'))
            face=B.main_placement_from_occurrence(occ,5,5).face_score
            report=dict(rank=1,prices=[0]*26,price_scale=1024,resource_upper_numerator=1024*face,
                        status='products enumerated',records=1)
            summary=dict(reports=[report],metadata=dict(threshold=face))
            line=f'record 1 score {face} face {face} penalty 0 | .:0:0:0 | .:0:0:0\n'
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'rank1_result.txt'
                path.write_text(line+'records_retained 1\n')
                self.assertEqual(len(list(iter_records(summary,{1:s},{},Path(folder),2))),1)
                for corrupt in (line,line+'records_retained 2\n',line+line+'records_retained 1\n',
                                line.replace(f'score {face}',f'score {face+1}')+'records_retained 1\n'):
                    path.write_text(corrupt)
                    with self.assertRaises(AssertionError):
                        list(iter_records(summary,{1:s},{},Path(folder),2))

    def test_bag_row_pruning_preserves_every_toy_completion(self):
        rng=random.Random(1721)
        words={'AB','BA','AAB','BBA','ABBA','BAAB','AABBA','BBAAB'}
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'toy.txt'
            path.write_text('\n'.join(sorted(words)))
            solver=object.__new__(Completion)
            solver.lex=Lexicon(path)
            tested=0
            for w in sorted(words):
                for start in (0,4,15-len(w)):
                    for mask in range(1,1<<len(w)):
                        required={start+i:ch for i,ch in enumerate(w) if mask>>i&1}
                        for _ in range(3):
                            extras=Counter({'A':rng.randrange(5),'B':rng.randrange(2)})
                            final=Counter(w)+extras
                            if not solver.feasible(tuple(final[a] for a in LETTERS)):continue
                            counts=Counter(required.values())+extras
                            vector=tuple(counts[a] for a in LETTERS)
                            forbidden=sum(1<<c for c in range(15) if not start<=c<start+len(w))
                            self.assertTrue(solver.row_bag_possible(tuple(sorted(required.items())),forbidden,vector))
                            tested+=1
            self.assertGreater(tested,500)
            # A forced AB fragment can only be repaired to ABB in this lexicon;
            # no spare B and two already consumed blanks makes that impossible.
            path.write_text('ABB\n')
            solver.lex=Lexicon(path)
            solver.row_bag_possible.cache_clear()
            counts=tuple(4 if a=='B' else 1 if a=='A' else 0 for a in LETTERS)
            self.assertFalse(solver.row_bag_possible(((0,'A'),(1,'B')),0,counts))

    def test_every_tiny_connector_contains_an_enumerated_core(self):
        rng=random.Random(74293)
        cells=[(r,c) for r in range(4) for c in range(4)]
        outside={(r,c) for r in range(15) for c in range(15)}-set(cells)
        boards=0;connecting_sets=0
        while boards<45:
            occupied=set(rng.sample(cells,6))
            board={p:'A' for p in occupied};comps=components(board)
            if len(comps)!=3:continue
            boards+=1
            cores,_=connectivity_cores(board,comps,3,outside)
            empty=sorted(set(cells)-occupied)
            for n in range(4):
                for extra in itertools.combinations(empty,n):
                    if len(components(board|dict.fromkeys(extra,'A')))==1:
                        connecting_sets+=1
                        self.assertTrue(any(core<=set(extra) for core in cores),(occupied,extra))
        self.assertGreater(connecting_sets,100)

    def test_resource_bound_and_reduced_cost_on_all_toy_products(self):
        # Two scarce high-value letters, one abundant letter, two real blanks.
        bag=[1,1,4];values=[10,8,1];main=[1,0,1];main_score=11
        slots=[[(5,[0,0,1]),(25,[1,0,2]),(20,[0,1,1])],[(4,[0,0,2]),(28,[0,2,1]),(31,[2,0,1])]]
        for prices in itertools.product(range(0,18,3),repeat=3):
            z=[max(s-sum(p*n for p,n in zip(prices,a)) for s,a in slot) for slot in slots]
            upper=main_score+sum(p*(b-m) for p,b,m in zip(prices,bag,main))+sum(z)+2*max([0]+[p-v for p,v in zip(prices,values)])
            for choices in itertools.product(*slots):
                counts=[main[a]+sum(o[1][a] for o in choices) for a in range(3)]
                excess=[max(0,n-b) for n,b in zip(counts,bag)]
                if sum(excess)>2:continue
                score=main_score+sum(s for s,_ in choices)-sum(e*v for e,v in zip(excess,values))
                loss=sum(z[j]-s+sum(p*n for p,n in zip(prices,a)) for j,(s,a) in enumerate(choices))
                self.assertLessEqual(score,upper-loss)


if __name__=='__main__':unittest.main()

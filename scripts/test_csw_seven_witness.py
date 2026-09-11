#!/usr/bin/env python3
"""Integration corruption tests; first build the authorized baseline witness."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from verify_csw_seven_witness import verify

ROOT=Path(__file__).resolve().parents[1]


class WitnessTests(unittest.TestCase):
    def test_score_cells_board_and_history_are_independently_checked(self):
        original=json.loads((ROOT/'output/csw7_baseline/history.json').read_text())
        variants=[]
        bad=copy.deepcopy(original);bad['candidate']['pre_bingo_score']+=1;variants.append(bad)
        bad=copy.deepcopy(original);bad['candidate']['record']['indices'][0]=5;variants.append(bad)
        bad=copy.deepcopy(original);bad['rows'][0]='A'+bad['rows'][0][1:];variants.append(bad)
        bad=copy.deepcopy(original);bad['forward_history'][0]['word']='ZZ';variants.append(bad)
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'history.json';output=Path(folder)/'witness.json'
            source.write_text(json.dumps(original))
            self.assertEqual(verify(source,output)['score'],1782)
            for bad in variants:
                source.write_text(json.dumps(bad))
                with self.assertRaises((AssertionError,ValueError)):
                    verify(source,output)


if __name__=='__main__':unittest.main()

#!/usr/bin/env python3
"""One-command driver for the corrected record-74 tail certificate.

By default this recomputes the 193 reduced horizontal bases from the supplied
NWL23 word export, checks their canonical board set, then verifies all 193 bases in fresh
subprocess chunks and combines the results.  Use --skip-enumeration to trust the
hashed supplied base file and rerun only the completion certificate.
"""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED_BASES_SHA='6db81327274d4991efcefb22e336cdcf2b60971bf1d7a429682f00ccf702484b'
EXPECTED_WORDS_SHA='5254d44586c3af6a8530427b14ef0251af5aa47906ce32a45e4c229261b1456b'
RANGES=[(1,40),(41,100),(101,120),(121,134),(135,145),(146,170),(171,193)]

def sha256(p:Path):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--words',required=True,type=Path)
 ap.add_argument('--skip-enumeration',action='store_true')
 ap.add_argument('--output',type=Path,default=ROOT/'rec74_193_certificate.recomputed.json')
 a=ap.parse_args()
 if sha256(a.words)!=EXPECTED_WORDS_SHA:raise SystemExit('NWL23_words.txt hash mismatch')
 bases=ROOT/'rec74_horizontal_bases.json'
 if sha256(bases)!=EXPECTED_BASES_SHA:raise SystemExit('supplied base fixture hash mismatch')
 if not a.skip_enumeration:
  with tempfile.TemporaryDirectory() as td:
   out=Path(td)/'bases.json'
   subprocess.run([sys.executable,str(ROOT/'enumerate_record74_bases.py'),'--words',str(a.words),'--output',str(out)],check=True)
   canonical=lambda p:sorted(tuple(x['rows']) for x in json.loads(p.read_text()))
   rebuilt=canonical(out)
   if len(rebuilt)!=193 or len(set(rebuilt))!=193 or rebuilt!=canonical(bases):
    raise SystemExit('recomputed canonical board set differs from certificate input')
 print('hashed supplied bases (not re-enumerated)' if a.skip_enumeration else 'base enumeration: OK',EXPECTED_BASES_SHA)
 parts=[]
 with tempfile.TemporaryDirectory() as td:
  for lo,hi in RANGES:
   out=Path(td)/f'{lo:03d}_{hi:03d}.json'
   print(f'verifying bases {lo}-{hi} ...',flush=True)
   subprocess.run([sys.executable,str(ROOT/'verify_record74_completion.py'),'--words',str(a.words),'--start',str(lo),'--end',str(hi),'--output',str(out)],check=True)
   d=json.loads(out.read_text())
   if d['status']!='OK' or d['unresolved']!=0:raise SystemExit(f'failed range {lo}-{hi}')
   parts.append(d)
 results=[x for d in parts for x in d['results']]
 ids=[x['board_id'] for x in results]
 if ids!=list(range(1,194)):raise SystemExit('base-id coverage mismatch')
 cores=sum(x['connectivity_core_count'] for x in results)
 assignments=sum(x['core_letter_assignments_checked'] for x in results)
 rowrej=sum(x['rejected_on_row_relaxation'] for x in results)
 colrej=sum(x['rejected_on_column_relaxation'] for x in results)
 survivors=sum(x['surviving_core_assignments'] for x in results)
 expected=(24293,5518820,5518814,6,0)
 got=(cores,assignments,rowrej,colrej,survivors)
 if got!=expected:raise SystemExit(f'aggregate mismatch: {got} != {expected}')
 combined={
  'status':'OK',
  'claim':'All 193 reduced horizontal bases for rank-32 record 74 are impossible to extend to a connected all-word-legal pre-final board; record 74 cannot realize 1787.',
  'record74_exact_prebonus':1737,
  'with_bingo':1787,
  'reduced_horizontal_bases':193,
  'unresolved':0,
  'total_connectivity_cores_enumerated':cores,
  'total_core_letter_assignments_checked':assignments,
  'row_relaxation_rejections':rowrej,
  'column_relaxation_rejections':colrej,
  'surviving_core_assignments':survivors,
  'bases_sha256':EXPECTED_BASES_SHA,
  'words_sha256':EXPECTED_WORDS_SHA,
  'results':results,
 }
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps(combined,indent=2,sort_keys=True)+'\n')
 print('FINAL TAIL CERTIFICATE: OK')
 print(json.dumps({k:combined[k] for k in ['reduced_horizontal_bases','total_connectivity_cores_enumerated','total_core_letter_assignments_checked','row_relaxation_rejections','column_relaxation_rejections','surviving_core_assignments']},indent=2))

if __name__=='__main__':main()

#!/usr/bin/env python3
"""Machine-checkable elimination of the last record-74 completion problem.

Input ``rec74_horizontal_bases.json`` contains the 193 reduced, horizontally legal
preboards obtained after choosing mandatory downward hooks from each top-row
component and retaining only horizontal additions needed to repair forced illegal
runs.  Any genuine completion has one of these 193 boards as a subboard; omitted
tiles are deliberately restored to the available bag.

For each reduced base this verifier enumerates every possible connectivity core of
at most R added cells, where R is the number of real tiles still available.  With
three existing components, every inclusion-minimal connecting set is the union of
two simple paths from a suitable component chosen as root to the other two.  The
script tries all three roots and every simple path of length at most R, so every
minimal core is represented.

Every multiset-respecting assignment of the remaining real tiles to every core is
then tested against an exact one-dimensional relaxation on all 15 rows and all 15
columns.  For a line containing an illegal maximal run, the line solver enumerates
every NWL23 final maximal word that could contain that run, fills its empty cells
using a submultiset of the leftover tiles, and recurses.  Crucially, each line is
allowed to use the *entire* leftover multiset independently of every other line, and
perpendicular compatibility is ignored.  This enlarges the feasible set.  Hence if
even one row or column cannot be completed in this relaxation, the corresponding
core assignment is impossible in Scrabble.

The supplied certificate has zero surviving core assignments over all 193 bases.
"""
from __future__ import annotations
from collections import Counter
from functools import lru_cache
from pathlib import Path
import argparse, hashlib, itertools, json, sys, time

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import common as V

LET=V.LETTERS
BAG={LET[i]:V.REAL_BAG[i] for i in range(26)}
MAIN=V.MAIN_WORD

def sha256(p:Path):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def components(board:dict[tuple[int,int],str]):
 occ=set(board); seen=set(); out=[]
 for x in sorted(occ):
  if x in seen: continue
  stack=[x];seen.add(x);cc=set()
  while stack:
   u=stack.pop();cc.add(u);r,c=u
   for v in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
    if v in occ and v not in seen:seen.add(v);stack.append(v)
  out.append(frozenset(cc))
 return tuple(out)

def word_legal(board,legal):
 for r in range(15):
  c=0
  while c<15:
   if (r,c) not in board:c+=1;continue
   j=c;s=[]
   while j<15 and (r,j) in board:s.append(board[r,j]);j+=1
   if len(s)>=2 and ''.join(s) not in legal:return False
   c=j
 for c in range(15):
  r=0
  while r<15:
   if (r,c) not in board:r+=1;continue
   j=r;s=[]
   while j<15 and (j,c) in board:s.append(board[j,c]);j+=1
   if len(s)>=2 and ''.join(s) not in legal:return False
   r=j
 return True

def remaining_tiles(rows, new_indices):
 counts=Counter(''.join(rows).replace('.',''))
 for i in new_indices: counts[MAIN[i]]+=1
 excess={ch:max(0,counts[ch]-BAG[ch]) for ch in LET}
 if sum(excess.values())!=2:
  raise AssertionError(f'expected exactly two forced blanks, got {excess}')
 real={ch:counts[ch]-excess[ch] for ch in LET}
 rem=Counter({ch:BAG[ch]-real[ch] for ch in LET if BAG[ch]-real[ch]>0})
 if any(v<0 for v in rem.values()):raise AssertionError('negative remainder')
 return rem, excess

def simple_paths(board, A, T, R, forbidden):
 """All sets of empty vertices of simple A-to-T paths using at most R new cells.
 The path leaves A once, stops on first adjacency to T, and cannot traverse any
 pre-existing component or forbidden square."""
 occ=set(board);out=set();starts=set()
 for r,c in A:
  for v in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
   if 0<=v[0]<15 and 0<=v[1]<15 and v not in occ and v not in forbidden:starts.add(v)
 def dfs(cur,path):
  r,c=cur
  if any(v in T for v in ((r-1,c),(r+1,c),(r,c-1),(r,c+1))):
   out.add(frozenset(path));return
  if len(path)>=R:return
  for v in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
   if not(0<=v[0]<15 and 0<=v[1]<15):continue
   if v in occ or v in forbidden or v in path:continue
   dfs(v,path+(v,))
 for s in sorted(starts):dfs(s,(s,))
 return out

def connectivity_cores(board, comps, R, forbidden):
 pair={}
 for i in range(3):
  for j in range(i+1,3):pair[i,j]=simple_paths(board,comps[i],comps[j],R,forbidden)
 cores=set()
 for root in range(3):
  others=[i for i in range(3) if i!=root]
  p1=pair[tuple(sorted((root,others[0])))]
  p2=pair[tuple(sorted((root,others[1])))]
  for a in p1:
   for b in p2:
    u=a|b
    if len(u)<=R:cores.add(frozenset(u))
 return cores, {f'{i}-{j}':len(v) for (i,j),v in pair.items()}

def multiset_assignments(cells, rem:Counter):
 cells=tuple(sorted(cells));rr=rem.copy()
 def go(i,cur):
  if i==len(cells):yield dict(cur);return
  for ch in sorted(rr):
   if rr[ch]<=0:continue
   rr[ch]-=1;cur[cells[i]]=ch
   yield from go(i+1,cur)
   del cur[cells[i]];rr[ch]+=1
 yield from go(0,{})

def bad_runs(s, legal):
 out=[];i=0
 while i<15:
  if s[i]=='.':i+=1;continue
  j=i
  while j<15 and s[j]!='.':j+=1
  if j-i>=2 and s[i:j] not in legal:out.append((i,j-1,s[i:j]))
  i=j
 return tuple(out)

def run(words_path:Path, boards_path:Path, upper_path:Path, run32_path:Path, start:int=19,end:int=54):
 lex=V.Lexicon(words_path); legal=lex.legal
 upper=V.parse_upper(upper_path); meta=upper[32]
 hdr,recs=V.parse_run(run32_path); rec=recs[73] # record 74, 0-based
 if meta['word']!=MAIN or meta['row']!=1 or meta['start']!=1:raise AssertionError('unexpected rank32 main')
 if V.exact_scoring_score(meta,rec)[1] != 1737:raise AssertionError('record74 is not exact 1737 prebonus')
 _,score_forb=V.scoring_skeleton(meta,rec)
 forbidden={(r-1,c) for r in range(1,16) for c in range(15) if (score_forb[r]>>c)&1}
 row_forb=tuple(sum(1<<c for r,c in forbidden if r==rr) for rr in range(15))
 col_forb=tuple(sum(1<<r for r,c in forbidden if c==cc) for cc in range(15))
 new_indices=set(meta['indices'])
 data=json.loads(boards_path.read_text())
 if len(data)!=193: raise AssertionError(f'expected 193 reduced bases, got {len(data)}')
 expected={'words':'5254d44586c3af6a8530427b14ef0251af5aa47906ce32a45e4c229261b1456b','boards':'6db81327274d4991efcefb22e336cdcf2b60971bf1d7a429682f00ccf702484b','upper':'be3a28379bbe8c568ee988899f1e375310749c69a7ec4c998b6fefc5c96a02f7','run32':'b996a868ebba9b92414d857b0a51f15fe3e7c5e6e8180e2c3354bfee7b2716bb'}
 actual={'words':sha256(words_path),'boards':sha256(boards_path),'upper':sha256(upper_path),'run32':sha256(run32_path)}
 if actual!=expected: raise AssertionError(f'input hash mismatch: {actual}')

 @lru_cache(None)
 def line_can_complete(s:str, remkey:str, forbmask:int)->bool:
  """Exact legal completion of one 15-cell line using a submultiset of remkey."""
  br=bad_runs(s,legal)
  if not br:return True
  if not remkey:return False
  rr=Counter(remkey); best=None
  for a,b,_ in br:
   cand=set()
   for st in range(a+1):
    if st>0 and s[st-1]!='.':continue
    for en in range(b,15):
     if en<14 and s[en+1]!='.':continue
     empt=tuple(p for p in range(st,en+1) if s[p]=='.')
     if not empt or len(empt)>len(remkey):continue
     if any((forbmask>>p)&1 for p in empt):continue
     pat=tuple((p-st,s[p]) for p in range(st,en+1) if s[p]!='.')
     mask=lex.matching_mask(en-st+1,pat)
     while mask:
      lb=mask&-mask;wi=lb.bit_length()-1;mask-=lb
      w=lex.bylen[en-st+1][wi]
      need=Counter(w[p-st] for p in empt)
      if not all(need[ch]<=rr[ch] for ch in need):continue
      ns=list(s)
      for p in empt:ns[p]=w[p-st]
      nr=rr.copy();nr.subtract(need);nr=+nr
      cand.add((''.join(ns),''.join(sorted(nr.elements()))))
   if not cand:return False
   if best is None or len(cand)<len(best):best=cand
  for ns,nr in best:
   if line_can_complete(ns,nr,forbmask):return True
  return False

 results=[];t0=time.time()
 for idx in range(start,end+1):
  line_can_complete.cache_clear()
  item=data[idx-1]; rows=tuple(item['rows'])
  board={(r,c):ch for r,s in enumerate(rows) for c,ch in enumerate(s) if ch!='.'}
  # These reduced bases are guaranteed horizontally legal; vertical legality may require leftover tiles.
  for r in range(15):
   c=0
   while c<15:
    if (r,c) not in board: c+=1; continue
    j=c; ss=[]
    while j<15 and (r,j) in board: ss.append(board[r,j]); j+=1
    if len(ss)>=2 and ''.join(ss) not in legal: raise AssertionError(f'board {idx} not horizontally legal')
    c=j
  cs=components(board)
  if len(cs)!=3:raise AssertionError(f'board {idx}: expected 3 components, got {len(cs)}')
  rem,excess=remaining_tiles(rows,new_indices);R=sum(rem.values())
  cores,paircounts=connectivity_cores(board,cs,R,forbidden)
  if not cores:raise AssertionError(f'board {idx}: no connectivity core generated')
  # Every generated core really connects the three base components.
  for core in cores:
   dummy=dict(board);dummy.update({x:'?' for x in core})
   if len(components(dummy))!=1:raise AssertionError(f'board {idx}: nonconnecting core')
  core_sizes=Counter(map(len,cores)); assignments=0; row_rejects=0; col_rejects=0; survivors=0; row_pass_details=[]
  base_rows=rows; base_cols=tuple(''.join(rows[r][c] for r in range(15)) for c in range(15))
  for core in sorted(cores,key=lambda x:(len(x),sorted(x)),reverse=True):
   for ass in multiset_assignments(core,rem):
    assignments+=1
    left=rem.copy();left.subtract(Counter(ass.values()));left=+left
    rk=''.join(sorted(left.elements()))
    ok=True
    for r in range(15):
     arr=list(base_rows[r])
     for (rr,c),ch in ass.items():
      if rr==r:arr[c]=ch
     if not line_can_complete(''.join(arr),rk,row_forb[r]):
      row_rejects+=1;ok=False;break
    if not ok:continue
    row_pass_record={'core_cells_1_based':sorted([[r+1,c+1] for r,c in core]),'assignment':sorted([[r+1,c+1,ch] for (r,c),ch in ass.items()]),'leftover':rk}
    for c in range(15):
     arr=list(base_cols[c])
     for (r,cc),ch in ass.items():
      if cc==c:arr[r]=ch
     colline=''.join(arr)
     if not line_can_complete(colline,rk,col_forb[c]):
      col_rejects+=1;ok=False
      row_pass_record.update({'rejecting_column_1_based':c+1,'column_state':colline,'current_bad_runs':bad_runs(colline,legal)})
      row_pass_details.append(row_pass_record)
      break
    if ok:
     survivors+=1
     raise AssertionError(f'board {idx}: a connectivity-core assignment survives line relaxation: core={sorted(core)}, ass={ass}, leftover={rk}')
  res={
   'board_id':idx,'preboard_tiles':len(board),'component_sizes':sorted(map(len,cs)),
   'remaining_real_tiles':''.join(sorted(rem.elements())),'remaining_count':R,
   'forced_blank_letters':''.join(ch*excess[ch] for ch in LET if excess[ch]),
   'pair_path_counts':paircounts,'connectivity_core_count':len(cores),
   'connectivity_core_size_histogram':{str(k):core_sizes[k] for k in sorted(core_sizes)},
   'core_letter_assignments_checked':assignments,'rejected_on_row_relaxation':row_rejects,
   'rejected_on_column_relaxation':col_rejects,'row_pass_details':row_pass_details,'surviving_core_assignments':survivors,
  }
  results.append(res)
  print(f"{idx}/{len(data)} CLOSED R={R} rem={res['remaining_real_tiles']} cores={len(cores)} assignments={assignments} rowrej={row_rejects} colrej={col_rejects}",flush=True)
 return {
  'status':'OK','claim':'All requested reduced horizontal bases are impossible to extend to a connected all-word-legal pre-final board, even under independent line-completion relaxations.',
  'board_range':[start,end],'boards_closed':len(results),'unresolved':0,
  'record74_exact_prebonus':V.exact_scoring_score(meta,rec)[1],
  'first_forbidden_total_with_bingo':1787,
  'forbidden_cells_1_based':sorted([[r+1,c+1] for r,c in forbidden]),
  'hashes':{'words_sha256':sha256(words_path),'boards_sha256':sha256(boards_path),'upper_sha256':sha256(upper_path),'run32_sha256':sha256(run32_path)},
  'results':results,'elapsed_seconds':time.time()-t0,
  'line_cache':{'hits':line_can_complete.cache_info().hits,'misses':line_can_complete.cache_info().misses,'states':line_can_complete.cache_info().currsize}
 }

def main():
 ap=argparse.ArgumentParser();
 ap.add_argument('--words',type=Path,required=True)
 ap.add_argument('--boards',type=Path,default=ROOT/'rec74_horizontal_bases.json')
 ap.add_argument('--upper',type=Path,default=ROOT/'seven_tile_upper_1737.txt')
 ap.add_argument('--run32',type=Path,default=ROOT/'032.txt')
 ap.add_argument('--start',type=int,default=1);ap.add_argument('--end',type=int,default=193)
 ap.add_argument('--output',type=Path,default=ROOT/'rec74_193_certificate.recomputed.json')
 a=ap.parse_args();res=run(a.words,a.boards,a.upper,a.run32,a.start,a.end)
 a.output.write_text(json.dumps(res,indent=2,sort_keys=True)+'\n');print(json.dumps({k:res[k] for k in ('status','boards_closed','unresolved','elapsed_seconds','line_cache')},indent=2))
if __name__=='__main__':main()

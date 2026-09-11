from pathlib import Path
from collections import Counter,defaultdict
import sys,time,json,hashlib,argparse
sys.path.insert(0,str(Path(__file__).resolve().parent)); import common as V
ap=argparse.ArgumentParser(); ap.add_argument('--words',required=True,type=Path); ap.add_argument('--upper',type=Path,default=Path(__file__).resolve().parent/'seven_tile_upper_1737.txt'); ap.add_argument('--run32',type=Path,default=Path(__file__).resolve().parent/'032.txt'); ap.add_argument('--output',type=Path,default=Path(__file__).resolve().parent/'rec74_horizontal_bases.recomputed.json'); args=ap.parse_args()
lex=V.Lexicon(args.words)
upper=V.parse_upper(args.upper); rec=V.parse_run(args.run32)[1][73]; meta=upper[32]
CLUSTERS=[(4,5,6),(8,9),(12,13)]

def ctuple(w):
 c=Counter(w[1:]);return tuple(c[V.LETTERS[i]] for i in range(26))
def base0(words):
 c=Counter(V.MAIN_WORD)
 for w,_,_,_ in rec:c.update(w[1:])
 for w in words:c.update(w[1:])
 return tuple(c[V.LETTERS[i]] for i in range(26))
def candidates(fx,fb,cl,base):
 out=[]
 for c in cl:
  for w in V.individual_hook_domain(lex,fx,fb,c,V.MAIN_WORD[c]):
   v=ctuple(w);nb=V.add_count_tuple(base,v)
   if sum(nb)<=100 and V.excess_blanks(nb)<=2:out.append((c,w,v))
 return out

def concrete_row(required, forbidden, base, max_add):
 if any((forbidden>>c)&1 for c in required):return []
 clusters=V.forced_clusters(required,lex);bad={i for i,x in enumerate(clusters) if not x[3]}
 if not bad:return [((0,)*26,())]
 cands=defaultdict(list)
 for bi in bad:
  bs,be,_,_=clusters[bi]
  for s in range(bs+1):
   if s>0 and s-1 in required:continue
   for e in range(be,15):
    if e<14 and e+1 in required:continue
    L=e-s+1;interval=((1<<L)-1)<<s
    if forbidden&interval:continue
    pat=tuple((c-s,required[c]) for c in sorted(required) if s<=c<=e)
    mask=lex.matching_mask(L,pat)
    if not mask:continue
    cov=tuple(i for i,(cs,ce,_,_) in enumerate(clusters) if s<=cs and ce<=e)
    if bi not in cov:continue
    while mask:
     lb=mask&-mask;wi=lb.bit_length()-1;mask-=lb;w=lex.bylen[L][wi];av=[0]*26;adds=[]
     for j,ch in enumerate(w):
      c=s+j
      if c not in required:av[ord(ch)-65]+=1;adds.append((c,ch))
     av=tuple(av)
     if sum(av)<=max_add and V.excess_blanks(V.add_count_tuple(base,av))<=2:cands[bi].append((s,e,w,av,tuple(adds),cov))
 out=[]
 def go(rem,ints,av,adds):
  if not rem:out.append((av,adds));return
  bi=min(rem)
  for s,e,w,v,a,cov in cands.get(bi,[]):
   if any(not(e+1<s2 or e2+1<s) for s2,e2 in ints):continue
   nv=V.add_count_tuple(av,v)
   if sum(nv)>max_add or V.excess_blanks(V.add_count_tuple(base,nv))>2:continue
   go(rem-set(cov),tuple(sorted(ints+((s,e),))),nv,adds+a)
 go(set(bad),(),(0,)*26,())
 d={}
 for av,a in out:d.setdefault(a,(av,a))
 return list(d.values())

def horizontal_bases(fx,fb,base):
 rows=[]
 for r in range(2,16):
  ops=concrete_row(fx[r],fb[r],base,100-sum(base))
  if not ops:return []
  if not(len(ops)==1 and not ops[0][1]):rows.append((r,ops))
 rows.sort(key=lambda x:len(x[1]));out=[]
 forced={(r-1,c):ch for r in range(1,16) for c,ch in fx[r].items()}
 def dfs(k,cnts,adds):
  if k==len(rows):
   board=dict(forced)
   for r,a in adds:
    for c,ch in a:board[(r-1,c)]=ch
   out.append((board,cnts));return
  r,ops=rows[k]
  for av,a in ops:
   nc=V.add_count_tuple(cnts,av)
   if sum(nc)>100 or V.excess_blanks(nc)>2:continue
   dfs(k+1,nc,adds+((r,a),))
 dfs(0,base,())
 d={}
 for bo,ct in out:d.setdefault(tuple(sorted(bo.items())),(bo,ct))
 return list(d.values())

fixed0,forb0=V.scoring_skeleton(meta,rec);ycol=V.isolated_old_columns(meta['indices'])[0];ydom=V.individual_hook_domain(lex,fixed0,forb0,ycol,V.MAIN_WORD[ycol])
stats=Counter();boards={};t=time.time()
for yw in ydom:
 by0=base0([yw])
 if sum(by0)>100 or V.excess_blanks(by0)>2:continue
 z=V.add_hook(fixed0,forb0,ycol,yw)
 if not z:continue
 fy,fb=z;doms=[candidates(fy,fb,cl,by0) for cl in CLUSTERS];order=sorted(range(3),key=lambda i:len(doms[i]))
 print('Y',yw,'doms',list(map(len,doms)),flush=True)
 def pick(k,fx,fb,cnts,picks):
  if k==3:
   stats['bag_hook']+=1
   poss,_=V.globally_horizontally_completable(lex,fx,fb,cnts)
   if not poss:return
   stats['horiz_possible']+=1
   bs=horizontal_bases(fx,fb,cnts);stats['horizontal_instances']+=len(bs)
   for bo,ct in bs:
    key=tuple(sorted(bo.items()))
    if key not in boards:boards[key]={'board':bo,'counts':ct,'hooks':(yw,tuple(picks))}
   return
  ii=order[k]
  for c,w,v in doms[ii]:
   stats['hook_nodes']+=1;nc=V.add_count_tuple(cnts,v)
   if sum(nc)>100 or V.excess_blanks(nc)>2:continue
   z2=V.add_hook(fx,fb,c,w)
   # Failure of the same permissive completion test is also safe on a prefix.
   if z2 and V.globally_horizontally_completable(lex,*z2,nc)[0]:
    pick(k+1,*z2,nc,picks+[(ii,c,w)])
 pick(0,fy,fb,by0,[])
print('stats',stats,'unique horizontal bases',len(boards),'time',time.time()-t)
out=[]
for i,x in enumerate(boards.values(),1):
 bo=x['board'];ct=x['counts'];rows=[''.join(bo.get((r,c),'.') for c in range(15)) for r in range(15)]
 out.append({'id':i,'hooks':x['hooks'],'tiles_pre':len(bo),'modeled_total_count':sum(ct),'excess_blanks':V.excess_blanks(ct),'rows':rows})
args.output.write_text(json.dumps(out,indent=2))
assert len(out)==193, f'expected 193 reduced bases, got {len(out)}'
raw=args.output.read_bytes(); print('wrote',len(out),args.output,'sha256',hashlib.sha256(raw).hexdigest())

from __future__ import annotations
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
import re
LETTERS='ABCDEFGHIJKLMNOPQRSTUVWXYZ'
REAL_BAG=(9,2,2,4,12,2,3,2,9,1,1,4,2,6,8,2,1,6,4,6,4,2,2,1,2,1)
VALUES=(1,3,3,2,1,4,2,4,1,8,5,1,3,1,1,3,10,1,1,1,1,4,4,8,4,10)
MAIN_WORD='OXYPHENBUTAZONE'
TW={0,7,14,105,119,210,217,224}; DW={16,28,32,42,48,56,64,70,112,154,160,168,176,182,192,196,208}
TL={20,24,76,80,84,88,136,140,144,148,200,204}; DL={3,11,36,38,45,52,59,92,96,98,102,108,116,122,126,128,132,165,172,179,186,188,213,221}
def premium(r,c):
    i=(r-1)*15+(c-1)
    if i in TW:return 1,3
    if i in DW:return 1,2
    if i in TL:return 3,1
    if i in DL:return 2,1
    return 1,1
class Lexicon:
    def __init__(self,path):
        self.words=tuple(x.strip().upper() for x in Path(path).read_text().splitlines() if x.strip().isalpha())
        self.legal=set(self.words); self.bylen={L:[] for L in range(1,16)}
        for w in self.words:
            if len(w)<=15:self.bylen.setdefault(len(w),[]).append(w)
        for L in self.bylen:self.bylen[L].sort()
        self.bits=defaultdict(int)
        for L,words in self.bylen.items():
            for i,w in enumerate(words):
                bit=1<<i
                for p,ch in enumerate(w):self.bits[L,p,ch]|=bit
    @lru_cache(None)
    def matching_mask(self,L,pat):
        m=(1<<len(self.bylen.get(L,())))-1
        for p,ch in pat:
            m &= self.bits.get((L,p,ch),0)
            if not m:break
        return m
    @lru_cache(None)
    def row_completable(self,required_items,forbidden):
        required=dict(required_items)
        for s,e,w,ok in forced_clusters(required,self):
            if ok:continue
            possible=False
            for L in range(e-s+1,16):
                for st in range(max(0,e-L+1),min(s,15-L)+1):
                    if any((forbidden>>c)&1 for c in range(st,st+L) if c not in required):continue
                    pat=tuple((c-st,required[c]) for c in sorted(required) if st<=c<st+L)
                    if self.matching_mask(L,pat):possible=True;break
                if possible:break
            if not possible:return False
        return True

def add_count_tuple(a,b):return tuple(x+y for x,y in zip(a,b))
def excess_blanks(c):return sum(max(0,c[i]-REAL_BAG[i]) for i in range(26))
def parse_upper(path):
    out={}
    rx=re.compile(r'^survivor (\d+) upper_prebonus (\d+) total_with_bingo \d+ main (\d+) word (\S+) indices ([0-9 ]+) row (\d+) start (\d+)$')
    for ln in Path(path).read_text().splitlines():
        m=rx.match(ln)
        if m:
            rank=int(m.group(1));out[rank]={'rank':rank,'upper':int(m.group(2)),'main_face':int(m.group(3)),'word':m.group(4),'indices':tuple(int(x)-1 for x in m.group(5).split()),'row':int(m.group(6)),'start':int(m.group(7))}
    return out

def parse_run(path):
    lines=Path(path).read_text().splitlines(); hdr={}; rec=[]
    for ln in lines:
        if ln.startswith('record '):
            parts=ln.split('|')[1:]; rr=[]
            for p in parts:
                s=p.strip(); w,score,start,index=s.split(':');rr.append((w,int(score),int(start),int(index)))
            rec.append(tuple(rr))
        elif ' ' in ln and not ln.startswith('slot '):
            k,v=ln.split(' ',1);hdr[k]=v
    return hdr,rec

def scoring_skeleton(meta,rec):
    fixed={r:{} for r in range(1,16)}; forb={r:0 for r in range(1,16)}
    row=meta['row'];start=meta['start'];new=set(meta['indices'])
    for i,ch in enumerate(meta['word']):
        c=start+i
        if i in new:forb[row]|=1<<(c-1)
        else:fixed[row][c-1]=ch
    # cross tuples are in new-index order
    for idx,(w,score,sr,wi) in zip(meta['indices'],rec):
        c=start+idx
        for j,ch in enumerate(w,1):
            r=sr+j-1
            if j==wi: continue
            if 1<=r<=15:
                if (forb[r]>>(c-1))&1:return None
                old=fixed[r].get(c-1)
                if old is not None and old!=ch:return None
                fixed[r][c-1]=ch
        if sr>1:forb[sr-1]|=1<<(c-1)
        er=sr+len(w)-1
        if er<15:forb[er+1]|=1<<(c-1)
    return fixed,forb

def exact_scoring_score(meta,rec):
    # Build physical cells with score coefficients and face total.
    coeff={}; letters={}; row=meta['row'];start=meta['start']; new=set(meta['indices'])
    wm=1
    for idx in new: wm*=premium(row,start+idx)[1]
    face=0
    for i,ch in enumerate(meta['word']):
        c=start+i; lm=premium(row,c)[0] if i in new else 1
        v=VALUES[ord(ch)-65]; face += v*lm*wm
        cell=(row,c);letters[cell]=ch;coeff[cell]=coeff.get(cell,0)+lm*wm
    for idx,(w,sc,sr,wi) in zip(meta['indices'],rec):
        c=start+idx; lm_new,wmc=premium(row,c)
        assert w in meta.get('legal_words', {w})
        assert sr+wi-1==row and w[wi-1]==meta['word'][idx]
        expected_sc=wmc*(sum(VALUES[ord(a)-65] for a in w)+(lm_new-1)*VALUES[ord(w[wi-1])-65])
        assert sc==expected_sc, (w,sc,expected_sc)
        face += sc
        for j,ch in enumerate(w,1):
            r=sr+j-1;cell=(r,c)
            if j==wi:
                coeff[cell]=coeff.get(cell,0)+lm_new*wmc
            else:
                letters[cell]=ch;coeff[cell]=coeff.get(cell,0)+wmc
    by=Counter(letters.values()); penalty=0;blanks=0
    for ch,n in by.items():
        over=max(0,n-REAL_BAG[ord(ch)-65]);blanks+=over
        if over:
            cs=sorted(coeff[cell] for cell,x in letters.items() if x==ch)
            penalty += VALUES[ord(ch)-65]*sum(cs[:over])
    if blanks>2:return face,None
    return face,face-penalty

def isolated_old_columns(indices):
    new=set(indices); old=[i for i in range(15) if i not in new]
    return [c for c in old if (c-1 not in old) and (c+1 not in old)]
def individual_hook_domain(lex,fixed,forb,col,letter):
    out=[]
    for L in range(2,16):
        for w in lex.bylen.get(L,()):
            if w[0]!=letter:continue
            ok=True
            for r,ch in enumerate(w,1):
                if (forb[r]>>col)&1:ok=False;break
                x=fixed[r].get(col)
                if x is not None and x!=ch:ok=False;break
            if ok and L<15 and ((L+1 in fixed and col in fixed[L+1]) or ((forb[L+1]>>col)&1)==0):
                # cell after a maximal hook may be forced empty; add_hook handles it
                pass
            if ok:out.append(w)
    return out
def add_hook(fixed,forb,col,w):
    nf={r:dict(x) for r,x in fixed.items()};nb=dict(forb)
    for r,ch in enumerate(w,1):
        if (nb[r]>>col)&1:return None
        old=nf[r].get(col)
        if old is not None and old!=ch:return None
        nf[r][col]=ch
    if len(w)<15:
        r=len(w)+1
        if col in nf[r]:return None
        nb[r]|=1<<col
    return nf,nb
def forced_clusters(required,lex):
    if not required:return []
    ks=sorted(required);out=[];s=p=ks[0]
    for c in ks[1:]:
        if c==p+1:p=c;continue
        w=''.join(required[i] for i in range(s,p+1));out.append((s,p,w,(len(w)==1 or w in lex.legal)));s=p=c
    w=''.join(required[i] for i in range(s,p+1));out.append((s,p,w,(len(w)==1 or w in lex.legal)))
    return out
def globally_horizontally_completable(lex,fixed,forb,counts):
    # Safe feasibility relaxation used by the base enumerator. The detailed concrete_row
    # stage that follows performs the exact reduced-row enumeration.
    for r in range(1,16):
        if not lex.row_completable(tuple(sorted(fixed[r].items())),forb[r]):return False,None
    return True,None

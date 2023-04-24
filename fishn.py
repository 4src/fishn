#!/usr/bin/env python3 -B
# vim: set ts=2 sw=2 et:
"""
fishn.py: look a little, catch some good stuff    
(c) 2023, Tim Menzies, <timm@ieee.org>  BSD-2    

              O  o    
         _\_   o    
      \\\\/  o\ .    
      //\___=    
         ''    

USAGE: ./fishn.py [OPTIONS] [-g ACTIONs]    

OPTIONS:    

      -b  --bins    number of bins                         = 16    
      -c  --cohen   'not different' if under the.cohen*sd  = .2    
      -f  --file    data csv file                          = ../data/auto93.csv    
      -g  --go      start up action                        = nothing    
      -h  --help    show help                              = False    
      -m  --min     on N items, recurse down to N**min     = .5    
      -r  --rest    expand to len(list)*rest               = 4    
      -s  --seed    random number seed                     = 1234567891    
      -w --want     goal: plan,watch,xplore,doubt          = plan   

NOTES:    
- ass    
"""
from lib import *
the= obj(**{m[1]:coerce(m[2]) for m in
            re.finditer(r"\n\s*-\w+\s*--(\w+)[^=]*=\s*(\S+)",__doc__)})
#-----------------------------------------------------------------------------
class BIN(obj):
  def slots(i, at=0, txt="", lo=1E60, hi=None):
    return dict(at=at,txt=txt,lo=lo,hi= hi or lo,n=0,_rows=[],ys={},score=0)

  def add(i,x,y,row):
    if x=="?": return x
    i.n += 1
    i.lo = min(i.lo,x)
    i.hi = max(i.hi,x)
    i._rows += [row]
    i.ys[y] = 1 + i.ys.get(y,0)

  def merge(i,j):
    out = BIN(at=i.at, txt=i.txt, lo=i.lo, hi=j.hi)
    out._rows = i._rows + j._rows
    out.n = i.n + j.n
    for d in [i.ys, j.ys]:
      for key in d:
        out.ys[key] = d[key] + out.ys.get(key,0)
    return out

#-----------------------------------------------------------------------------
def COLS(names):
  cols,x,y = [COL(at=i,txt=s) for i,s in enumerate(names)], [], []
  for col in cols:
    if col.txt[-1] != "X":
      (y if col.txt[-1] in "+-" else x).append(col)
  return names,cols,x,y

def COL(at=0,txt=" "):
  w = -1 if txt[-1] == "-" else 1
  return NUM(at=at,txt=txt,w=w) if txt[0].isupper() else SYM(at=at,txt=txt)

class col(obj):
  def slots(i,at=0,txt=" "): return dict(at=at, txt=txt, bins={}, n=0)
  def adds(i,lst): [i.add(x) for x in lst]; return i

  def add(i,x,inc=1):
    if x=="?": return x
    i.n += inc
    i.add1(x,inc)

  def bin(i,x,y,row):
    k = i.bin1(x)
    if not k in i.bins: i.bins[k] = BIN(at=i.at, txt=i.txt, lo=x)
    i.bins[k].add(x,y,row)

#-------------------------------------------------------------------------------
class SYM(col):
  def slots(i,**d): return super().slots(**d) | dict(has={},mode=None,most=0)

  def mid(i): return i.mode
  def div(i): return entropy(i.has)
  def stats(i, div=False, **_) : return i.div() if div else i.mid()

  def add1(i,x,inc=1):
    i.has = i.has or {}
    tmp = i.has[x] = inc + i.has.get(x,0)
    if tmp > i.most: i.most,i.mode = tmp,x

  def bin1(i,x): return x
  def merges(i,bins): return bins

#-------------------------------------------------------------------------------
class NUM(col):
  def slots(i,at=0,txt=" ",w=1) :
    return super().slots(at=at,txt=txt) | dict(w=1,mu=0,m2=0,sd=0,lo=1E60,hi=-1E60)

  def mid(i): return i.mu
  def div(i): return i.sd
  def norm(i,x): return x if x=="?" else (x - i.lo) / (i.hi - i.lo + 1E-60)
  def stats(i,div=False,rnd=2): return round(i.div() if div else i.mid(), rnd)

  def bin1(i,x):
    z = int((x - i.mu) / (i.sd + 1E-60) /(4/the.bins))
    z = max(the.bins/ -2, min( the.bins/2, z))
    return  z

  def add1(i,x,n):
    i.lo  = min(i.lo, x)
    i.hi  = max(i.hi, x)
    d     = x - i.mu
    i.mu += d/i.n
    i.m2 += d*(x - i.mu)
    i.sd  = 0 if i.n<2 else (i.m2/(i.n - 1))**.5

  def merged(i,bin1,bin2):
    out   = bin1.merge(bin2)
    small = i.n / the.bins
    if bin1.n <= small or bin2.n <= small : return out
    if bin1.hi - bin1.lo < i.sd*the.cohen : return out
    if bin2.hi - bin2.lo < i.sd*the.cohen : return out
    e1,e2,e3 = entropy(bin1.ys), entropy(bin2.ys), entropy(out.ys)
    if e3 <= (bin1.n*e1 + bin2.n*e2)/out.n : return out

  def merges(i,bins):
    now,j = [],0
    while j < len(bins):
      bin = bins[j]
      if j < len(bins) - 1:
        if new := i.merged(bin, bins[j+1]):
          bin = new
          j += 1
      now += [bin]
      j += 1
    if len(now) < len(bins):
      bins = i.merges(now)
    else:
      for j in range(len(bins)-1): bins[j].hi = bins[j+1].lo
      bins[ 0].lo = -1E60
      bins[-1].hi =  1E60
    return bins

#-------------------------------------------------------------------------------
class ROW(obj):
  def slots(i,cells=[]): return dict(cells=cells)
  def better(i,j,data):
    s1, s2, cols, n = 0, 0, data.y, len(data.y)
    for col in cols:
      a,b  = col.norm(i.cells[col.at]), col.norm(j.cells[col.at])
      s1  -= math.exp(col.w * (a - b) / n)
      s2  -= math.exp(col.w * (b - a) / n)
    return s1 / n < s2 / n

#-------------------------------------------------------------------------------
class DATA(obj):
  def slots(i):  return dict(x=[], y=[], cols=[], names=[], rows=[])
  def clone(i,rows=[]):
    d = DATA()
    d.names, d.cols, d.x, d.y = COLS(i.names)
    [d.add(row) for row in rows]
    return d

  def read(i,file):
    with open(file) as fp:
      for line in fp:
        line = re.sub(r'([\n\t\r"\' ]|#.*)', '', line)
        if line:
          i.add(ROW(cells = [coerce(s.strip()) for s in line.split(",")]))
    return i

  def add(i,row):
    if i.x:
      [col.add(row.cells[col.at]) for cols in [i.x, i.y] for col in cols]
      i.rows += [row]
    else:
      i.names, i.cols, i.x, i.y = COLS(row.cells)
    return i

  def stats(i, cols=None, div=False, rnd=2):
    return obj(N=len(i.rows), **{col.txt: col.stats(div=div, rnd=rnd)
                                 for col in (cols or i.y)})

  def betters(i):
    want = len(rows)**min
    rows = sorted(i.rows, key=cmp2key(lambda r1,r2: r1.better(r2,i)))
    best = rows[-want:]
    rest = random.sample(rows[-want:], want*the.rest)
    for row in best: row.y=True
    for row in rest: row.y=False
    return i.clone(best), i.clone(rest)

#-------------------------------------------------------------------------------
def contrasts(data1,data2):
  data12 = data1.clone(data1.rows + data2.rows)
  for col in data12.x:
    for klass,rows in dict(best=data1.rows, rest=data2.rows).items():
      for row in rows:
        col.bin(row.cells[col.at], klass, row)
    for bin in col.merges(sorted(col.bins.values(),key=lambda b:b.lo)):
      bin.score = want(bin.ys.get("best",0), bin.ys.get("rest",0),
                       len(data1.rows), len(data2.rows))
      yield bin

def want(b,r,B,R):
  b, r = b/(B+1E-60), r/(R+1E-60)
  match the.want:
    case "plan":   return b**2/(b+r)
    case "watch":  return r**2/(b+r)
    case "xplore": return 1/(b+r)
    case "doubt":  return (b+r)/abs(b - r)

def rules(data1,data2):
  a = sorted((bin for bin in contrasts(data1,data2)),
             reversed=True, key=lambda x:x.score)
  print([x.score for x in a])



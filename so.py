#!/usr/bin/env python3 -B
# <!--- vim: set et sts=3 sw=3 ts=3 : --->
import fileinput, random, time,ast, sys, re
from collections import Counter
from copy import deepcopy
from math import sqrt,log

class box(dict):
   __setattr__ = dict.__setitem__
   __getattr__ = dict.get
   __repr__    = lambda i:showd(i)

class obj(object):
    def __repr__(i): return showd(i.__dict__,i.__class__.__name__)

the=box(
   Far	=	.9,
   Halves=	256,
   eg	   =	"help",
   file	=	"../data/auto93.csv",
   min	=	.5,
   p	   =	2,
   seed	=	1234567891
)
#---------------------------------------------
class COL(obj):
  def __init__(i,at=0,name=" "): i.at,i.name,i.n = at,name,0
  def adds(i,lst=[]): [i.add(x) for x in lst]; return i
  def dist(i,x,y):
     return 1 if x=="?" and y=="?" else i.dist1(x,y)
#---------------------------------------------
class SYM(COL):
  def __init__(i,*l,**kw):
    super().__init__(*l,**kw)
    i.has = Counter()
  def mid(i)  : return mode(i._has)
  def ent(i)  : return ent(i._has)
  def add(i,x):
     if x != "?": i.n+=1 ; i.has[x] += 1
  def dist1(i,x,y) : return 0 if x==y else 1
  #---------------------------------------------
class NUM(COL):
   def __init__(i,*l,**kw):
      super().__init__(*l,**kw)
      i.ok, i._has = True, []
      i.heaven = 0 if i.name[-1]=="-" else 1
   def mid(i)  : return mean(i.has)
   def div(i)  : return sd(i.has)
   def add(i,x):
      if x != "?": i.n += 1; i._has += [x]; i.ok= False
   @property
   def has(i):
      if not i.ok: i._has.sort(); i.ok = True
      return i._has
   def norm(i,x):
      a = i.has
      return x if x=="?" else (x-a[0])/(a[-1] - a[0] + 1E-30)
   def dist1(i,x,y):
      x, y = i.norm(x), i.norm(y)
      if x=="?": x= 0 if y > .5 else 1
      if y=="?": y= 0 if x > .5 else 1
      return abs(x - y)
   def d2h(i,row): return abs(i.heaven - i.norm(row[i.at]))
#---------------------------------------------
class COLS(obj):
   def __init__(i,a):
      i.x, i.y, i.names = [], [], a
      i.all = [(NUM if s[0].isupper() else SYM)(at=n,name=s) for n,s in enumerate(a)]
      for col in i.all:
         if col.name[-1] != "X":
            (i.y if col.name[-1] in "+-!" else i.x).append(col)

   def add(i,a):
      [col.add(a[col.at]) for cols in [i.x, i.y] for col in cols]
#---------------------------------------------
class SHEET(obj):
   def __init__(i, src):
     i.rows, i.cols = [],  None
     [i.add(row) for row in src]

   def add(i,row):
      if    i.cols: i.cols.add(row); i.rows += [row]
      else: i.cols = COLS(row)

   def clone(i, rows=[]):
      return SHEET([i.cols.names] + rows)

   def stats(i, cols="y", decs=2, want="mid"):
      return box(N=len(i.rows),
                   **{c.name:show(c.div() if want=="div" else c.mid(),decs)
                      for c in (i.cols.y if cols=="y" else i.cols.x)})

   def d2h(i,row):
      return (sum((col.d2h(row)**the.p for col in i.cols.y))/len(i.cols.y))**(1/the.p)

   def dist(i,row1,row2):
      return (sum(c.dist(row1[c.at],row2[c.at])**the.p
                  for c in i.cols.x )/len(i.cols.x))**(1/the.p)

   def far(i,rows,x):
      return sorted(rows,key=lambda y:i.dist(x,y))[int(len(rows)*the.Far)]

   def halve(i,rows, assess=False):
      some = rows if len(rows) <= the.Halves else random.sample(rows,k=the.Halves)
      D    = lambda row1,row2: i.dist(row1,row2)
      a    = i.far(some, random.choice(some))
      b    = i.far(some, a)
      C    = D(a,b)
      half1, half2 = [],[]
      if assess and i.d2h(b) < i.d2h(a):
        a,b=b,a
      rows = sorted(rows, key=lambda r: (D(r,a)**2 + C**2 - D(r,b)**2)/(2*C))
      mid  = len(rows)//2
      return a,b,rows[:mid],rows[mid:]

def tree(sheet0, assess=False):
  stop = len(sheet0.rows)**the.min
  def grow(sheet):
     node = box(here=sheet, lefts=None, rights=None)
     if len(sheet.rows) >= 2*stop:
        _,__,lefts,rights = sheet0.halve(sheet.rows,assess=assess)
        node.lefts  = grow(sheet0.clone(lefts))
        node.rights = grow(sheet0.clone(rights))
     return node
  return grow(sheet0)

def isLeaf(node): return not node.lefts and not node.rights

def nodes(node,depth=1):
   if node:
      yield node, depth
      for tmp in [node.lefts, node.rights]:
         for node1,depth1 in nodes(tmp, depth+1):
            yield node1,depth1
#---------------------------------------------
def cli(d):
   for k, v in d.items():
      s = str(v)
      for j, x in enumerate(sys.argv):
         if ("-"+k[0])==x or ("--"+k)==x:
            d[k] = coerce("True" if s=="False" else ("False" if s=="True" else sys.argv[j+1]))
   return d

R=random.random
def normal(mu=0,sd=1):
   return  mu+sd*sqrt(-2*log(R())) * cos(2*pi*R())

def coerce(x):
   try : return ast.literal_eval(x)
   except Exception: return x.strip()

def csv(file="-"):
   with  fileinput.FileInput(file) as src:
      for line in src:
         line = re.sub(r'([\n\t\r"\' ]|#.*)', '', line)
         if line: yield [coerce(x) for x in line.split(",")]

def showds(*ds):
   prints(*ds[0].keys())
   [prints(*d.values()) for d in ds]

def showd(d,pre=""):
   s = " ".join([f":{k} {show(v,3)}" for k,v in d.items() if k[0] != "_"])
   return pre +"{" + s + "}"

def show(x,decs=3):
  return x.__name__ if callable(x) else(round(x,decs) if decs and isinstance(x,float) else x)

def prints(*l): print(*[show(x) for x in l],sep="\t")

def mode(d): return max(d, key=d.get)

def ent(d):
   n = sum(d.values())
   return - sum(m/n*log(m/n,2) for m in d.values() if m > 0)

def per(a,p=.5): return a[int(p*len(a))]
def median(a):   return per(a,.5)
def mean(a):     return sum(a)/len(a)
def sd(a):       return (per(a,.9) - per(a,.1))/2.56
#---------------------------------------------
class EGS:
   _egs = locals()
   def All():
      "run all"
      sys.exit(sum((EGS._one(k) for k in EGS._egs if k!="all" and k[0].islower())))

   def _one(k):
      if k in EGS._egs:
         b4 = deepcopy(the)
         random.seed(the.seed)
         status = EGS._egs[k]()
         for k in b4: the[k] = b4[k]
         return status==False
      else:
         return print("usage: ./so.py -e help")

   def help():
      "show help"
      print("\n./so.py -e ACTION\n\nACTIONS:")
      [print(f"  -e {k:10} {f.__doc__}") for k,f in EGS._egs.items() if k[0] !="_"]

   def the(): 
      "what do the settings look like?"
      print(the)

   def num():
      "nums work?"
      n=NUM().adds([2,1,3,2,4])
      print(box(mid=n.mid(), div=n.div()))

   def csv():
      "can I load a csv file?"
      print(SHEET(csv(the.file)).cols.x)

   def dist():
      "do I know distances?"
      s = SHEET(csv(the.file))
      rows = sorted(s.rows, key=s.d2h)
      print(rows[0])
      for j in range(1, len(rows), 30):
         print(rows[j], s.dist(rows[1], rows[j]))

   def clone():
      "can i find a best region?"
      s = SHEET(csv(the.file))
      rows = sorted(s.rows, key=s.d2h)
      n = int(len(rows)**the.min)
      showds(s.clone(rows[:n]).stats(),
             s.clone(rows[-n:]).stats())

   def tree():
      "can i recursively clusters?"
      s = SHEET(csv(the.file))
      for n,d in nodes(tree(s,True)):
         print(('|.. '*d)+str(n.here.stats() if isLeaf(n) else ""))
      print("\n"+('    '*d)+str(s.stats()))

def go(): EGS._one(cli(the).eg)
#-----------------------------------
if __name__ == "__main__": go()

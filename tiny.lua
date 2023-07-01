#!/usr/bin/env lua
-- <!--- vim : set filetype=lua et sts=2 sw=2 ts=2 : --->
local l=require"lib"
local the,help = l.settings [[

tiny: multi-goal semi-supervised explanation
(c) 2023 Tim Menzies <timm@ieee.org> BSD-2
  
USAGE: ./tiny.lua [OPTIONS] [-g ACTIONS]
  
OPTIONS:
  -f  --file    data file                          = ../data/auto93.csv
  -g  --go      start-up action                    = nothing
  -G  --Goal    plan or monitor or xplore or doubt = plan
  -h  --help    show help                          = false
  -s  --seed    random number seed                 = 93716221]]

local o, obj, oo, rnd = l.o, l.obj, l.oo, l.rnd
local SYM,NUM,COLS,DATA = obj"SYM", obj"NUM", obj"COLS", obj"DATA"
local TEST,RULE = obj"TEST", obj"RULE"
local COL
-------------------------------------------------------------------------------
-- ### COLS

-- `COL`umns can be `NUM`eric or `SYM`bolic. Upper case names denote `NUM`s.
-- All `COL`s know their name, their column loc`at`ion, their count `n` of items seen.
function COL(n,s) 
  return (s or ""):find"^[A-Z]" and NUM(n,s) or SYM(n,s) end
-------------------------------------------------------------------------------
-- ### SYM

-- `SYM`s uses `has` to count symbols seen so far (and the most common symbol is the `mode`).
function SYM:new(n,s) 
  return {name=s or "", at=n or 0, n=0, has={}, most=0, mode=nil}  end

-- Update a `SYM`bol.
function SYM:add(x)
  if x=="?" then return end
  self.n      = 1 + self.n
  self.has[x] = 1 + (self.has[x] or 0)
  if self.has[x] > self.most then self.most,self.mode = self.has[x],x end end

-- `mid,div` returns central tendency  and diversity.
function SYM:mid(_) return self.mode end
function SYM:div(  nPlaces,     e) 
  e = 0
  for _,v in pairs(self.has) do e = e - v/self.n * math.log(v/self.n,2) end
  return nPlaces and rnd(e,nPlaces) or e end
-------------------------------------------------------------------------------
-- ### NUM

-- `NUM`s tracks the smallest and biggest number seen to far (in `lo` and `hi`) 
-- as well as the the mean `mu` and second moment `m2` (used to find standard deviation).
-- Also, `pretty` controls how we report numbers (and this switches to "%g" 
-- if we ever see a float).  Any name ending with `-` is something we want to _minimize_ 
-- (so we give it a non-positive weight).
function NUM:new(n,s) 
  return {name=s or "",  at=n or 0,  n=0, 
          lo=l.big, hi= -l.big, mu=0,  m2=0, 
          pretty="%.0f", want=(s or ""):find"-$" and 0 or 1} end

-- Update a `NUM`ber.
function NUM:add(n,    d)
  if n=="?" then return end
  self.n  = 1 + self.n
  self.lo = math.min(n, self.lo)
  self.hi = math.max(n, self.hi)
  d    = n - self.mu
  self.mu = self.mu + d/self.n
  self.m2 = self.m2 + d*(n - self.mu)
  if math.type(n) == "float" then self.pretty = "%g" end end

-- `mid,div` returns central tendency  and diversity.
function NUM:mid(  nPlaces) 
  return nPlaces and rnd(self.mu,nPlaces) or self.mu end
function NUM:div(  nPlaces,      sd)
  sd = (self.m2/(self.n - 1))^.5; return nPlaces and rnd(sd,nPlaces) or sd end

-- Return `n` mapped 0..1, min..max.
function NUM:norm(n)
  return n=="?" and x or (n - self.lo)/(self.hi - self.lo + 1/l.big) end

-- Return symbols more frequent in  `sym1` than `sym2`.
function SYM.keys(sym1,sym2,     t)
  t = {}
  for k,n1 in pairs(sym1.has) do 
    if n1/sym1.n > (sym2.has[k] or 0)/sym2.n then l.push(t,TEST(sym1,k,k)) end end
  return t end

-- Return numeric ranges frequent in  `sym1` than `sym2`.
local _cross
function NUM.keys(num1,num2,     a,z,mu,mid,d,tmp)
  a, z, mu = -1E30, 1E30, best.mu
  mid = _cross(num1.mu, num2.mu, num1:div(), num2:div())
  d   = math.abs(num1.mu - mid)
  tmp = mu < rest.mu and {{a, mu},{a, mu+d/2},{a, mu+d}} or {{mu, z},{mu-d/2, z},{mu-d, z}}
  for _,x in pairs{{mu-d, mu+d}, {mu-d/2, mu+d/2}} do 
    l.push(tmp,x) end
  return map(tmp, function(z) return TEST(num1,z[1],z[2]) end) end

function _cross(mu1,mu2,sd1,sd2,      a,b,c,x1,x2)
  if mu2 < mu1 then return _cross(mu2,mu1,sd2,sd1) end
  if sd1==0 or sd2==0 or sd1==sd2 then return (mu1+mu2)/2 end
  a  = 1/(2*sd1^2) - 1/(2*sd2^2)
  b  = mu2/(sd2^2) - mu1/(sd1^2)
  c  = mu1^2 /(2*sd1^2) - mu2^2 / (2*sd2^2) - math.log(sd2/sd1)
  x1 = (-b + (b^2 - 4*a*c)^.5)/(2*a)
  x2 = (-b - (b^2 - 4*a*c)^.5)/(2*a)
  return mu1 <= x1 <= mu2 and x1 or x2 end
-------------------------------------------------------------------------------
-- ### COLS

-- `COLS` convert  list of column names (as strings) into `SYM`s or `NUM`s. 
-- Column names ending in a goal symbol (`+-!`) are dependent `y` features 
-- (and the others are independent `x` features). 
function COLS:new(ss) 
  self.x, self.y, self.all, self.names = {},{},{},ss
  for n,s in pairs(ss) do
    local col = l.push(self.all, COL(n,s))
    if not s:find"X$" then 
      l.push(s:find"[!+-]$" and self.y or self.x, col)
      if s:find"!$" then self.klass=col end  end end  end

-- Update a `COL` with info from `t`.
function COLS:add(t)
  for _,cols in pairs{self.x, self.y} do
    for _,col in pairs(cols) do 
      col:add(t[col.at]) end end 
  return t end
-------------------------------------------------------------------------------
-- ### DATA
function DATA:new(  ts)
  self.rows,self.cols = {},nil
  if   type(ts)=="string" 
  then l.csv(ts, function(t) self:add(t) end)  
  else for _,t in pairs(ts or {}) do self:add(t) end end end

function DATA:add(t)
  if self.cols then l.push(self.rows, self.cols:add(t)) else self.cols=COLS(t) end end

function DATA:clone(  ts,     data1)
  data1 = DATA()
  data1.cols = COLS(self.cols.names)
  for _,t in pairs(ts or {}) do data1:add(t) end
  return data1 end

function DATA:d2h(t,     d)
  d = 0
  for _,col in pairs(self.cols.y) do d = d + (col.want - col:norm(t[col.at]))^2 end
  return d^.5 end

function DATA:sort()
  return l.sort(self.rows, function(t1,t2) return self:d2h(t1) < self:d2h(t2) end) end

function DATA:stats(  what,cols,nPlaces,     t)
  t = {N=#self.rows}
  for _,col in pairs(cols or self.cols.y) do
    t[col.name] =rnd(getmetatable(col)[what or "mid"](col),nPlaces) end
  return t end
-------------------------------------------------------------------------------
-- ### TEST

-- `TEST`s ask if a range `lo..hi` covers a  value `at` some column.
function TEST:new(col,lo,hi)
  return {at=col.at, b=0, r=0, lo=lo, hi=hi, name=col.name} end

-- Tests for coverage of data in `t`.
function TEST:covers(t)
  local x = t[self.at]
  if x=="?" or self.lo <= x and x <= self.hi then return t end end 

-- `RULE`s ask if a ranges in many `cols` covers some value
function RULE:new(tests)
  self.cols, self.b, self.r = {}, 0,0,0,0
  for _,test in pairs(tests or {}) do self:add(test) end end

-- disjunct, spread the area XXX
-- `TEST`s ask if a range `lo..hi` covers a  value `at` some column.
function RULE:add(test,      olds,skip)
  olds = self.cols[test.at] or {}
  skip = false
  for _,old in pairs(olds) do
    local a0, z0, a1, z1 = old.lo, old.hi, test.lo, test.hi
    if z1 >= a0 and z1 <= z0 and a0 <= a1 then old.lo = test.lo; skip = true end 
    if a1 >= a0 and a1 <= z0 and z1 >= z0 then old.hi = test.hi; skip = true end end
  if not skip then l.push(olds,new) end 
  self.cols[test.at] = olds end

function RULE:covers(t,    _ors)
  function _ors(tests)
    for _,test in pairs(tests) do 
      if test:covers(t) then return true end end end
  for _,tests in pairs(self.cols) do
    if not _ors(tests) then return nil end end
  return t end

local function br(thing,bests,rests,     B,R)
  B, R = #bests.rows, #rests.rows 
  bs   = map(bests.rows, function(t) return thing:covers(t) end)
  rs   = map(rests.rows, function(t) return thing:covers(t) end)
  thing.b, thing.r = #bs/(B + 1/l.big),  #rs/(R + 1/l.big) end

local function goal(thing,     b,r)
  b, r = thing.b, thing.r
  if the.Goal == "plan"    then return b^2/(b+r) end
  if the.Goal == "monitor" then return r^2/(b+r) end
  if the.Goal == "xplore"  then return 1/(b+r)   end
  if the.Goal == "doubt"   then return (b+r)/math.abs(b-r) end end

-------------------------------------------------------------------------------
-- ## Demos
 print(1)

local egs={all= {"the","rnd","rand","ent","cross",
                "cols","csv","data","slice","sort"}}

function egs.the() oo(the) end
function egs.rnd() return 3.14 == rnd(math.pi) end
function egs.num(     num,d) 
  num = NUM()
  for _ = 1,1000 do num:add(l.rand()^2) end
  d = num:div()
  return .3 < d and d < .31  end

function egs.ent(     sym,e,s) 
  sym = SYM()
  s="aaaabbc"
  for c in s:gmatch"." do sym:add(c) end
  e = sym:div()
  return 1.37 < e and e < 1.38 end

function egs.cross()
  return 3.75 == _cross(2.5,5,1,1) end

function egs.cols()
  l.map(COLS({"Name", "Age", "Mpg-", "room"}).all, print) end

function egs.csv()
  l.csv(the.file,oo) end

function egs.data(       data)
  data = DATA(the.file) 
  oo(data:stats()) end

function egs.slice(      t)
  t = {10,20,30,40,50,60,70,80,90,100}
  print(-2,"", o(l.slice(t,-2))) 
  print( 1, 2, o(l.slice(t,1,2))) 
  print( 2,"", o(l.slice(t,2)))  end

function egs.sort(       data,ts1,ts2,ts3)
  data = DATA(the.file) 
  ts1 = data:sort() 
  ts2 = l.slice(ts1,1,30)
  ts3 = l.slice(ts1,-120)
  print("all ", o(data:stats()))
  print("best", o(data:clone(ts2):stats()))
  print("rest", o(data:clone(ts3):stats())) end

-------------------------------------------------------------------------------
-- ## Start-up
if   not pcall(debug.getlocal,4,1) 
then the=l.cli(the, help); l.run(the,egs) end

return {COL=COL, COLS=COLS, DATA=DATA, NUM=NUM, SYM=SYM} 

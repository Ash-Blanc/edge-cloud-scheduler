import os,sys,random,math
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import sim
O=(467.2,56.9,0.0076435,0.0356911)
def make(seed):
 rng=random.Random(seed); arr=sorted((rng.uniform(0,10),rng.choice((512,1024,2048)),70) for _ in range(26))
 rows=[]
 for b,dp,dr in [(1,1,4),(2,3,4.5),(4,80,12),(8,120,24),(16,160,44),(32,240,84),(64,320,124),(128,400,164),(256,480,204),(512,560,244),(1024,640,284),(2048,720,324),(4096,800,364)]: rows.append((b,.3+.01*b,9+.08*b,.2+.005*b,dp,dr,dp))
 c=sim.Case(4,2,18.5,4,32768,8,O[0],O[1],rows,arr,.75,.25); ex1=(1669.941-O[0])/O[0]; ex2=(71.638-O[1])/O[1]; c.tp_base,c.tp_ub,c.dist_base=O[2],O[3],math.hypot(ex1,ex2)/(1-.8468); return c
for s in (44,91,201):
 c=make(s); print('seed',s)
 for b in sys.argv[1:]:
  m,_,_=sim.run(b,c); p,_,_,_=sim.score(c,m); print(b,'pts=%.2f tp=%.6f tdr=%.1f tpot=%.1f'%(p,m[0],m[1],m[2]))

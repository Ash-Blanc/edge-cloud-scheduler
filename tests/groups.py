import os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'recon_archive'))
import sim
from akd56_16063_ab import honest6,pin_official_constants
class T:
 def __init__(self): self.g=[]; self.p=[]
 def append(self,fr):
  for c in fr[1]:
   f=c.split()
   if f[:3]==['E','D','PRE']: self.g.append(int(f[4]))
   if len(f)>2 and f[1:3]==['D','PROC']: self.p.append(int(f[4]))
c=pin_official_constants(honest6(),6)
for b in sys.argv[1:]:
 t=T(); m,_,_=sim.run(b,c,trace=t)
 print(b,m,'dpre',len(t.g),sorted(t.g)[:10],sorted(t.g)[-10:],'dproc',len(t.p),sorted(t.p)[:10],sorted(t.p)[-10:])

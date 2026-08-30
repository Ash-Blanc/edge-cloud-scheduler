import os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from recon_archive import official48_recon as r
for t in (4,8):
 c=r.fitted4() if t==4 else r.fitted8(); print('CASE',t)
 for b in sys.argv[1:]:
  m,_,_=r.sim.run(b,c); p,_,_,_=r.sim.score(c,m); print(b,'pts=%.3f tp=%.6f tdr=%.2f tpot=%.2f'%(p,m[0],m[1],m[2]))

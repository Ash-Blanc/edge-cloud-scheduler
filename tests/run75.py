import os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),"recon_archive"))
import sim,akd56_16063_ab as r
for which in (5,6):
 base=r.pin_official_constants(r.honest5() if which==5 else r.honest6(),which)
 c=r.retarget(base,.75)
 print('CASE',which)
 for b in sys.argv[1:]:
  m,_,_=sim.run(b,c); p,_,_,_=sim.score(c,m); print(b,'pts=%.4f tp=%.6f tdr=%.2f tpot=%.2f'%(p,m[0],m[1],m[2]))

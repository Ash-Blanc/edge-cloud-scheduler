import os,sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'recon_archive'))
import sim
from akd56_16063_ab import honest6, pin_official_constants
c=pin_official_constants(honest6(),6)
for b in sys.argv[1:]:
 m,_,s=sim.run(b,c)
 print(b, m)
 print({k:tuple(round(x,3) for x in v) for k,v in s.stats.items()})

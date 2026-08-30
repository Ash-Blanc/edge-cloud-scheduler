import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "recon_archive"))
import sim
import akd56_16063_ab as r
bins = sys.argv[1:]
c = r.pin_official_constants(r.honest6(), 6)
for b in bins:
    m, _, _ = sim.run(b, c)
    pts, ntp, nc, dist = sim.score(c, m)
    print(b, "pts=%.6f tp=%.6f tdr=%.3f tpot=%.4f ntp=%.6f nc=%.6f" % (pts,m[0],m[1],m[2],ntp,nc))

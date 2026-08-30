import os, sys, types
_res = types.ModuleType("resource")
_res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path[:0] = ["tests", "tests/recon_archive"]
import sim
from akd56_16063_ab import honest5, honest6, pin_official_constants, retarget

OFFICIAL = 16125.629
BASE = r"C:\Users\hp\AppData\Local\Temp\ecs-bin\sol16125.exe"
CAND = r"C:\Users\hp\AppData\Local\Temp\ecs-bin\combo.exe"

def ev(b, c):
    m, _, _ = sim.run(b, c)
    pts, ntp, nc, _ = sim.score(c, m)
    return pts, ntp, nc, m

h5 = pin_official_constants(honest5(), 5)
h6 = pin_official_constants(honest6(), 6)
print(f"{'case':<22} {'base':>8} {'cand':>8} {'d':>8}")
tot = 0.0
for label, c in [
    ("#5 .80", h5),
    ("#6 .90", h6),
    (".00", retarget(h5, 0.0)),
    (".05", retarget(h5, 0.05)),
    (".15", retarget(h5, 0.15)),
    (".75", retarget(h5, 0.75)),
    (".98", retarget(h5, 0.98)),
]:
    pb, _, _, mb = ev(BASE, c)
    pc, _, _, mc = ev(CAND, c)
    print(f"{label:<22} {pb:8.2f} {pc:8.2f} {pc-pb:+8.2f}  tp={mc[0]:.4f}/{mb[0]:.4f}")
    if label.startswith("#"):
        tot += pc - pb
print(f"expected official {OFFICIAL+tot:.1f}  (5+6 d={tot:+.2f})")

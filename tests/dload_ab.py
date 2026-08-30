import sys, types, subprocess, os
_res = types.ModuleType("resource")
_res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path[:0] = ["tests", "tests/recon_archive"]
import sim
from akd56_16063_ab import honest5, honest6, pin_official_constants, retarget
from trace_compare import traced_run

SRC = r"C:\Users\hp\src\edge-cloud-scheduler\solution.cpp"
BIN = r"C:\Users\hp\AppData\Local\Temp\ecs-bin"
B = os.path.join(BIN, "sol16125.exe")
DLOAD = os.path.join(BIN, "dload.exe")

def ev(b, c):
    m, _, _ = sim.run(b, c)
    pts, ntp, nc, _ = sim.score(c, m)
    return pts, m

h5 = pin_official_constants(honest5(), 5)
h6 = pin_official_constants(honest6(), 6)
print("dload vs 16125")
for label, c in [("#5", h5), ("#6", h6)]:
    pb, mb = ev(B, c); pc, mc = ev(DLOAD, c)
    same = traced_run(B, c)[1][0] == traced_run(DLOAD, c)[1][0]
    print(f"  {label} d={pc-pb:+.2f} identical={same} dtp={mc[0]-mb[0]:+.4f} dtpot={mc[2]-mb[2]:+.3f}")
print("collateral")
for w in (0.0, 0.05, 0.15, 0.75, 0.80, 0.98):
    c = retarget(h5, w)
    same = traced_run(B, c)[1][0] == traced_run(DLOAD, c)[1][0]
    pb,_=ev(B,c); pc,_=ev(DLOAD,c)
    print(f"  w={w:g} identical={same} dpts={pc-pb:+.2f}")

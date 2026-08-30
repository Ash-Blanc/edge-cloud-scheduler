import sys, types
_res = types.ModuleType("resource")
_res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path[:0] = ["tests", "tests/recon_archive"]
import sim
from akd56_16063_ab import honest5, honest6, pin_official_constants, retarget
from trace_compare import traced_run

B = r"C:\Users\hp\AppData\Local\Temp\ecs-bin\sol16125.exe"
C = r"C:\Users\hp\AppData\Local\Temp\ecs-bin\khalf.exe"

def ev(b, c):
    m, _, _ = sim.run(b, c)
    pts, ntp, nc, _ = sim.score(c, m)
    return pts, m

h5 = pin_official_constants(honest5(), 5)
h6 = pin_official_constants(honest6(), 6)
print("informational #5/#6 (may invert on official)")
for label, c in [("#5", h5), ("#6", h6)]:
    pb, mb = ev(B, c); pc, mc = ev(C, c)
    print(f"  {label} base={pb:.2f} cand={pc:.2f} d={pc-pb:+.2f} dtp={mc[0]-mb[0]:+.4f} dtpot={mc[2]-mb[2]:+.3f}")
print("collateral")
dirty = 0
for w in (0.0, 0.05, 0.15, 0.25, 0.30, 0.45, 0.75, 0.98):
    c = retarget(h5, w)
    mb, tb = traced_run(B, c)
    mc, tc = traced_run(C, c)
    same = tb[0] == tc[0]
    pb, _ = ev(B, c); pc, _ = ev(C, c)
    if not same or abs(pc-pb)>0.05:
        dirty += 1
        print(f"  DIRTY w={w:g} identical={same} dpts={pc-pb:+.2f}")
    else:
        print(f"  clean w={w:g}")
print("DIRTY" if dirty else "ALL COLLATERAL CLEAN")

import sys, types
_res = types.ModuleType("resource")
_res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path[:0] = ["tests", "tests/recon_archive"]
import sim
from akd56_16063_ab import honest5, honest6, pin_official_constants, retarget

B = r"C:\Users\hp\AppData\Local\Temp\ecs-bin\sol16125.exe"
bins = [
    ("base", B),
    ("k2", r"C:\Users\hp\AppData\Local\Temp\ecs-bin\k_k2b.exe"),
    ("k4", r"C:\Users\hp\AppData\Local\Temp\ecs-bin\k_k4b.exe"),
    ("nocap", r"C:\Users\hp\AppData\Local\Temp\ecs-bin\k_nocap2.exe"),
    ("max90", r"C:\Users\hp\AppData\Local\Temp\ecs-bin\k_max902.exe"),
]
h5 = pin_official_constants(honest5(), 5)
h6 = pin_official_constants(honest6(), 6)

def ev(b, c):
    m, _, _ = sim.run(b, c)
    pts, ntp, nc, _ = sim.score(c, m)
    return pts, m

print(f"{'bin':<8} {'#5':>8} {'#6':>8} {'tp6':>8} {'tpot6':>8}")
for n, p in bins:
    p5, m5 = ev(p, h5)
    p6, m6 = ev(p, h6)
    print(f"{n:<8} {p5:8.2f} {p6:8.2f} {m6[0]:8.5f} {m6[2]:8.3f}")

print("collateral vs base on nocap/k2")
for n, p in bins[1:]:
    dirty = []
    for w in (0.0, 0.05, 0.15, 0.75, 0.98):
        c = retarget(h5, w)
        pb, _ = ev(B, c)
        pc, _ = ev(p, c)
        if abs(pc - pb) > 0.05:
            dirty.append(f"{w:g}{pc-pb:+.2f}")
    print(n, "CLEAN" if not dirty else dirty)

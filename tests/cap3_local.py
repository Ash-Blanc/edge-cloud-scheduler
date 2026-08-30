import os, sys, types
_res = types.ModuleType("resource")
_res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path[:0] = ["tests", "tests/recon_archive"]
import sim
from akd56_16063_ab import honest5, honest6, pin_official_constants

OFFICIAL = 16125.629
BASE = r"C:\Users\hp\AppData\Local\Temp\ecs-bin\sol16125.exe"
COMBO = r"C:\Users\hp\AppData\Local\Temp\ecs-bin\combo.exe"
CAP3 = r"C:\Users\hp\AppData\Local\Temp\ecs-bin\cap3.exe"

def ev(b, c):
    m, _, _ = sim.run(b, c)
    pts, ntp, nc, _ = sim.score(c, m)
    return pts, m

h5 = pin_official_constants(honest5(), 5)
h6 = pin_official_constants(honest6(), 6)
print(f"{'bin':<8} {'#5':>8} {'#6':>8} {'d5':>7} {'d6':>7} {'exp':>9}")
b5, _ = ev(BASE, h5); b6, _ = ev(BASE, h6)
for name, path in [("combo", COMBO), ("cap3", CAP3)]:
    p5, m5 = ev(path, h5); p6, m6 = ev(path, h6)
    print(f"{name:<8} {p5:8.2f} {p6:8.2f} {p5-b5:+7.2f} {p6-b6:+7.2f} {OFFICIAL+p5-b5+p6-b6:9.1f} tp6={m6[0]:.4f}")

# local suite: .80/.90/.98 cases, skip huge R
cases = [c for c in sim.build_cases() if abs(c.wtp - 0.80) < 1e-6 or abs(c.wtp - 0.90) < 1e-6 or abs(c.wtp - 0.98) < 1e-6]
cases = [c for c in cases if len(c.arrivals) <= 800]
print(f"\nlocal {len(cases)} cases w in .80/.90/.98 R<=800")
print(f"{'case':<22} {'w':>5} {'base':>8} {'combo':>8} {'d':>8}")
sd = 0.0
for c in cases:
    sim.calibrate(c, "ref_sequential.exe")
    pb, _ = ev(BASE, c); pc, _ = ev(COMBO, c)
    print(f"{c.name:<22} {c.wtp:5.2f} {pb:8.2f} {pc:8.2f} {pc-pb:+8.2f}")
    sd += pc - pb
print(f"local suite dpts sum {sd:+.1f}")

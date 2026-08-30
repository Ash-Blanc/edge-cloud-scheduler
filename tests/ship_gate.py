#!/usr/bin/env python3
import os, sys, types, subprocess
_res = types.ModuleType("resource")
_res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path[:0] = ["tests", "tests/recon_archive"]
import sim
from akd56_16063_ab import honest5, honest6, pin_official_constants, retarget
from trace_compare import traced_run

OFFICIAL = 16125.629
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\solution.cpp"
BIN = r"C:\Users\hp\AppData\Local\Temp\ecs-bin"
BASE = os.path.join(BIN, "sol16125.exe")
CAND = os.path.join(BIN, "sol_ship.exe")

def ev(b, c):
    m, _, _ = sim.run(b, c)
    pts, ntp, nc, _ = sim.score(c, m)
    return pts, m

def main():
    r = subprocess.run(["g++", "-O2", "-std=c++17", "-o", CAND, SRC],
                       capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-400:]); return
    h5 = pin_official_constants(honest5(), 5)
    h6 = pin_official_constants(honest6(), 6)
    b5, m5b = ev(BASE, h5); p5, m5 = ev(CAND, h5)
    b6, m6b = ev(BASE, h6); p6, m6 = ev(CAND, h6)
    print(f"#5 {p5-b5:+.2f} tp {m5b[0]:.4f}->{m5[0]:.4f}")
    print(f"#6 {p6-b6:+.2f} tp {m6b[0]:.4f}->{m6[0]:.4f}")
    dirty = []
    for w in (0.0, 0.05, 0.15, 0.25, 0.30, 0.45, 0.75, 0.80, 0.98):
        c = retarget(h5, w)
        same = traced_run(BASE, c)[1][0] == traced_run(CAND, c)[1][0]
        if not same:
            dirty.append(f"{w:g}")
    print("collateral dirty:", dirty or "CLEAN")
    print(f"expected official {OFFICIAL + max(0,p5-b5) + max(0,p6-b6):.1f} "
          f"(floor {OFFICIAL} if #6 inert)")

if __name__ == "__main__":
    main()

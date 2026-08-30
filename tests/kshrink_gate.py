#!/usr/bin/env python3
import os, sys, types, subprocess
_res = types.ModuleType("resource")
_res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path[:0] = ["tests", "tests/recon_archive"]
import sim
from akd56_16063_ab import honest5, honest6, pin_official_constants, retarget

SRC = r"C:\Users\hp\src\edge-cloud-scheduler\solution.cpp"
BIN = r"C:\Users\hp\AppData\Local\Temp\ecs-bin"
BASE = os.path.join(BIN, "sol16125.exe")

VARIANTS = [
    ("auto", []),
    ("k2", ["SAT_KFORCE=2"]),
    ("k3", ["SAT_KFORCE=3"]),
    ("k4", ["SAT_KFORCE=4"]),
    ("nocap", ["DROP_CAP80=1"]),
    ("max90", ["MAXREADY90=1"]),
    ("k2nocap", ["SAT_KFORCE=2", "DROP_CAP80=1"]),
]

def build(name, defs):
    out = os.path.join(BIN, f"k_{name}.exe")
    r = subprocess.run(
        ["g++", "-O2", "-std=c++17", "-o", out, SRC] + [f"-D{d}" for d in defs],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(name, "FAIL", r.stderr[-400:])
        return None
    return out

def ev(b, c):
    m, _, _ = sim.run(b, c)
    pts, ntp, nc, _ = sim.score(c, m)
    return pts, ntp, nc, m

def main():
    h5 = pin_official_constants(honest5(), 5)
    h6 = pin_official_constants(honest6(), 6)
    col_ws = (0.0, 0.05, 0.15, 0.45, 0.75, 0.98)
    print(f"{'var':<10} {'#5':>8} {'#6':>8}  collateral")
    for name, defs in VARIANTS:
        path = build(name, defs)
        if not path:
            continue
        p5, _, _, m5 = ev(path, h5)
        p6, _, _, m6 = ev(path, h6)
        b5, _, _, _ = ev(BASE, h5)
        b6, _, _, _ = ev(BASE, h6)
        bad = []
        for w in col_ws:
            c = retarget(h5, w)
            pb, _, _, _ = ev(BASE, c)
            pc, _, _, _ = ev(path, c)
            if abs(pc - pb) > 0.05:
                bad.append(f"w{w:g}={pc-pb:+.2f}")
        tag = "CLEAN" if not bad else "DIRTY " + ",".join(bad)
        print(f"{name:<10} {p5:8.2f} ({p5-b5:+.1f}) {p6:8.2f} ({p6-b6:+.1f})  {tag}  "
              f"tp5={m5[0]:.4f} tpot5={m5[2]:.2f} tp6={m6[0]:.4f} tpot6={m6[2]:.2f}")

if __name__ == "__main__":
    main()

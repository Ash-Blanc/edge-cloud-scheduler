#!/usr/bin/env python3
"""Assignment-only JSQ / P-PRE pick sweep vs 16125. Pipeline unchanged."""
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

VARIANTS = [
    ("cur", []),
    ("k2", ["AKD56_JSQ_KIND=2"]),
    ("k3", ["AKD56_JSQ_KIND=3"]),
    ("k4", ["AKD56_JSQ_KIND=4"]),
    ("k5", ["AKD56_JSQ_KIND=5"]),
    ("k6", ["AKD56_JSQ_KIND=6"]),
    ("k7", ["AKD56_JSQ_KIND=7"]),
    ("k8", ["AKD56_JSQ_KIND=8"]),
    ("k9", ["AKD56_JSQ_KIND=9"]),
    ("lpt", ["AKD56_PRE_PICK=1"]),
    ("spt", ["AKD56_PRE_PICK=2"]),
    ("lptk8", ["AKD56_PRE_PICK=1", "AKD56_JSQ_KIND=8"]),
    ("80k3", ["AKD56_JSQ_KIND=3", "AKD56_JSQ_W=80"]),
    ("80k2", ["AKD56_JSQ_KIND=2", "AKD56_JSQ_W=80"]),
    ("80k8", ["AKD56_JSQ_KIND=8", "AKD56_JSQ_W=80"]),
    ("80dl", ["AKD56_DECODE_LOAD_80=1"]),
]

def build(name, defs):
    out = os.path.join(BIN, f"jsq_{name}.exe")
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
    return pts, m

def main():
    h5 = pin_official_constants(honest5(), 5)
    h6 = pin_official_constants(honest6(), 6)
    b5, m5b = ev(BASE, h5)
    b6, m6b = ev(BASE, h6)
    print(f"base #5={b5:.2f} tp={m5b[0]:.4f}  #6={b6:.2f} tp={m6b[0]:.4f}")
    print(f"{'var':<8} {'d5':>8} {'d6':>8}  tp5     tp6     note")
    rows = []
    for name, defs in VARIANTS:
        path = build(name, defs)
        if not path:
            continue
        p5, m5 = ev(path, h5)
        p6, m6 = ev(path, h6)
        d5, d6 = p5 - b5, p6 - b6
        print(f"{name:<8} {d5:+8.2f} {d6:+8.2f}  {m5[0]:.4f} {m6[0]:.4f}")
        rows.append((name, path, d5, d6, m5, m6))
    print("-- collateral on non-losers --")
    best = (0.0, "cur")
    for name, path, d5, d6, m5, m6 in rows:
        if d5 < -0.05 or d6 < -0.05:
            print(f"{name:<8} SKIP (local loss)")
            continue
        dirty = []
        for w in (0.0, 0.05, 0.15, 0.25, 0.30, 0.45, 0.75, 0.98):
            c = retarget(h5, w)
            same = traced_run(BASE, c)[1][0] == traced_run(path, c)[1][0]
            if not same:
                dirty.append(f"{w:g}")
        ship = not dirty
        exp = OFFICIAL + max(0.0, d5) + max(0.0, d6)
        print(f"{name:<8} coll={'CLEAN' if ship else dirty} exp={exp:.1f}")
        if ship and (d5 + d6) > best[0]:
            best = (d5 + d6, name)
    print(f"BEST no-reg local-sum {best[1]} {best[0]:+.2f} -> {OFFICIAL+best[0]:.1f}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Cloud D-PROC-first and related assignment-only #5/#6 probes."""
import os, sys, types, subprocess
_res = types.ModuleType("resource")
_res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path[:0] = ["tests", "tests/recon_archive"]
import sim
from akd56_16063_ab import honest5, honest6, pin_official_constants, retarget
from trace_compare import traced_run
from official3_probe import recon as recon3

OFFICIAL = 16125.629
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\solution.cpp"
BIN = r"C:\Users\hp\AppData\Local\Temp\ecs-bin"
BASE = os.path.join(BIN, "sol16125.exe")

VARIANTS = [
    ("cur", []),
    ("df90", ["AKD56_DPROC_FIRST=1", "AKD56_DPROC_FIRST_W=90"]),
    ("df80", ["AKD56_DPROC_FIRST=1", "AKD56_DPROC_FIRST_W=80"]),
    ("dfboth", ["AKD56_DPROC_FIRST=1", "AKD56_DPROC_FIRST_W=0"]),
]

def build(name, defs):
    out = os.path.join(BIN, f"df_{name}.exe")
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
    c3 = recon3()
    b5, *_ = ev(BASE, h5)
    b6, *_ = ev(BASE, h6)
    p3b, *_, m3b = ev(BASE, c3)
    print(f"base #5={b5:.2f} #6={b6:.2f} #3recon={p3b:.2f} tdr={m3b[1]:.1f} tpot={m3b[2]:.2f}")
    rows = []
    for name, defs in VARIANTS:
        path = build(name, defs)
        if not path:
            continue
        p5, n5, c5, m5 = ev(path, h5)
        p6, n6, c6, m6 = ev(path, h6)
        d5, d6 = p5 - b5, p6 - b6
        print(f"{name:<8} d5={d5:+7.2f} d6={d6:+7.2f}  "
              f"tp5={m5[0]:.4f} nc5={c5:.4f} tp6={m6[0]:.4f} nc6={c6:.4f}")
        rows.append((name, path, d5, d6))
    print("-- collateral --")
    for name, path, d5, d6 in rows:
        if d5 < -0.05 or d6 < -0.05:
            print(f"{name:<8} SKIP loss")
            continue
        dirty = []
        for w in (0.0, 0.05, 0.15, 0.45, 0.75, 0.98):
            c = retarget(h5, w)
            same = traced_run(BASE, c)[1][0] == traced_run(path, c)[1][0]
            if not same:
                dirty.append(f"{w:g}")
        exp = OFFICIAL + max(0.0, d5) + max(0.0, d6)
        print(f"{name:<8} coll={'CLEAN' if not dirty else dirty} exp={exp:.1f}")

if __name__ == "__main__":
    main()

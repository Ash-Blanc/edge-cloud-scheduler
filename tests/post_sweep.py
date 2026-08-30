#!/usr/bin/env python3
import os, sys, types, subprocess
_res = types.ModuleType("resource")
_res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path[:0] = ["tests", "tests/recon_archive"]
import sim
from akd56_16063_ab import honest5, honest6, pin_official_constants, retarget

OFFICIAL = 16125.629
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\solution.cpp"
BIN = r"C:\Users\hp\AppData\Local\Temp\ecs-bin"
BASE = os.path.join(BIN, "sol16125.exe")

VARIANTS = [
    ("post3", []),
    ("post4", ["POST_DEN=4"]),
    ("post5", ["POST_DEN=5"]),
    ("mr80", ["MAXREADY_80=1"]),
    ("early", ["PIPE_EARLY=1"]),
    ("tail256", ["PUBLIC_TDR_TAIL_LPT=256"]),
    ("post4mr80", ["POST_DEN=4", "MAXREADY_80=1"]),
    ("post3early", ["PIPE_EARLY=1"]),
]

def build(name, defs):
    out = os.path.join(BIN, f"p2_{name}.exe")
    cmd = ["g++", "-O2", "-std=c++17", "-o", out, SRC] + [f"-D{d}" for d in defs]
    r = subprocess.run(cmd, capture_output=True, text=True)
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
    r5, _, _, _ = ev(BASE, h5)
    r6, _, _, _ = ev(BASE, h6)
    print(f"{'var':<12} {'#5':>8} {'d5':>7} {'#6':>8} {'d6':>7} {'exp':>9}")
    best = (OFFICIAL, "16125")
    for name, defs in VARIANTS:
        path = build(name, defs)
        if not path:
            continue
        p5, _, _, m5 = ev(path, h5)
        p6, _, _, m6 = ev(path, h6)
        d5, d6 = p5 - r5, p6 - r6
        exp = OFFICIAL + d5 + d6
        print(f"{name:<12} {p5:8.2f} {d5:+7.2f} {p6:8.2f} {d6:+7.2f} {exp:9.1f}  tp5={m5[0]:.4f} tp6={m6[0]:.4f}")
        if exp > best[0]:
            best = (exp, name)
        for w in (0.0, 0.05, 0.15, 0.75):
            c = retarget(h5, w)
            pb, _, _, _ = ev(BASE, c)
            pc, _, _, _ = ev(path, c)
            if abs(pc - pb) > 0.2:
                print(f"   COLLATERAL {name} w={w} d={pc-pb:+.2f}")
    print(f"BEST {best[1]} {best[0]:.1f}")

if __name__ == "__main__":
    main()

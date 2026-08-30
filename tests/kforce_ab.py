#!/usr/bin/env python3
"""Project official total from 16125 + local ntp/pts deltas on #5/#6."""
import sys, types, os, subprocess
_res = types.ModuleType("resource")
_res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path[:0] = ["tests", "tests/recon_archive"]
import sim
from akd56_16063_ab import honest5, honest6, pin_official_constants, retarget

OFFICIAL = 16125.629
W5, W6 = 0.80, 0.90
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\solution.cpp"
BIN = r"C:\Users\hp\AppData\Local\Temp\ecs-bin"
BASE = os.path.join(BIN, "sol16125.exe")

def build(name, defs):
    out = os.path.join(BIN, f"{name}.exe")
    cmd = ["g++", "-O2", "-std=c++17", "-o", out, SRC] + [f"-D{d}" for d in defs]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(name, "BUILD FAIL", r.stderr[-400:])
        return None
    return out

def ev(b, c):
    m, _, _ = sim.run(b, c)
    pts, ntp, nc, _ = sim.score(c, m)
    return pts, ntp, nc, m

def main():
    h5 = pin_official_constants(honest5(), 5)
    h6 = pin_official_constants(honest6(), 6)
    b5, n5, c5, m5 = ev(BASE, h5)
    b6, n6, c6, m6 = ev(BASE, h6)
    variants = [
        ("kauto", []),
        ("k1", ["SAT_KFORCE=1"]),
        ("k2", ["SAT_KFORCE=2"]),
        ("k3", ["SAT_KFORCE=3"]),
        ("k4", ["SAT_KFORCE=4"]),
        ("k8", ["SAT_KFORCE=8"]),
    ]
    # already-built current working tree is kauto if compiled as kshrink.exe
    pre = {"kauto": os.path.join(BIN, "kshrink.exe")}
    print(f"{'var':<8} {'#5':>8} {'d5':>7} {'#6':>8} {'d6':>7} {'exp':>9}  t5  t6")
    for name, defs in variants:
        path = pre.get(name) or build(name, defs)
        if not path:
            continue
        p5, nt5, nc5, mm5 = ev(path, h5)
        p6, nt6, nc6, mm6 = ev(path, h6)
        # official-shaped estimate: apply local dpts directly (pinned constants)
        exp = OFFICIAL + (p5 - b5) + (p6 - b6)
        print(f"{name:<8} {p5:8.2f} {p5-b5:+7.2f} {p6:8.2f} {p6-b6:+7.2f} {exp:9.1f}  "
              f"tp5={mm5[0]:.4f} tp6={mm6[0]:.4f} tpot5={mm5[2]:.2f} tpot6={mm6[2]:.2f}")
        # collateral .00 .75
        for w, src in ((0.0, h5), (0.75, h5), (0.98, h5)):
            c = retarget(src, w)
            pb, _, _, _ = ev(BASE, c)
            pc, _, _, _ = ev(path, c)
            if abs(pc - pb) > 0.05:
                print(f"   COLLATERAL w={w} d={pc-pb:+.2f}")

if __name__ == "__main__":
    main()

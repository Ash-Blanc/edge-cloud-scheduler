#!/usr/bin/env python3
import os, sys, types, subprocess
_res = types.ModuleType("resource")
_res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path[:0] = ["tests", "tests/recon_archive"]
import sim
from akd56_16063_ab import honest5, honest6, pin_official_constants, retarget
from official3_probe import recon as recon3, SLO1, SLO2, DBASE

OFFICIAL = 16125.629
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\solution.cpp"
BIN = r"C:\Users\hp\AppData\Local\Temp\ecs-bin"
BASE = os.path.join(BIN, "sol16125.exe")

VARIANTS = [
    ("cur", []),
    ("jsq3", ["AKD3_JSQ=1"]),
    ("spt3", ["AKD3_SPT=1"]),
    ("j3s3", ["AKD3_JSQ=1", "AKD3_SPT=1"]),
    ("p65", ["PUB65=1"]),
]

def build(name, defs):
    out = os.path.join(BIN, f"t3_{name}.exe")
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

def pts3(m):
    tp, tdr, tpot = m
    dist = ((max(0.0, (tdr - SLO1) / SLO1) ** 2) +
            (max(0.0, (tpot - SLO2) / SLO2) ** 2)) ** 0.5
    return 1000.0 * max(0.0, 1.0 - dist / DBASE), dist, tdr, tpot

def mk14():
    return sim.make_case("w65", 11, 4, 40, 24, 20.0, 0.65, 0.5, 0.5,
                         kind="gpu", lat=8.0, bw=8.0, lout_hi=64, lin_hi=1024)

def main():
    h5 = pin_official_constants(honest5(), 5)
    h6 = pin_official_constants(honest6(), 6)
    c3 = recon3()
    rows = sim.make_table("gpu", __import__("random").Random(1))
    c14 = sim.Case(4, 2.0, 20.0, 1.0, 32768, 8, 1.0, 1.0, rows, [(0.0, 256, 2)],
                   0.65, 0.35)
    c14.name = "single-lout2"
    c14.tp_base, c14.tp_ub, c14.dist_base = 0.001, 1.0, 12.0
    m14 = mk14()
    b5, *_ = ev(BASE, h5)
    b6, *_ = ev(BASE, h6)
    p3b, d3b, tdrb, tpotb = pts3(ev(BASE, c3)[3])
    p14b, *_, m14b = ev(BASE, c14)
    p65b, *_, m65b = ev(BASE, m14)
    print(f"base #5={b5:.2f} #6={b6:.2f} #3={p3b:.2f} dist={d3b:.4f} "
          f"tdr={tdrb:.1f} tpot={tpotb:.2f}")
    print(f"  single-lout2={p14b:.2f} tp={m14b[0]:.5f}  mk14={p65b:.2f} tp={m65b[0]:.5f}")
    print(f"{'var':<8} {'d5':>7} {'d6':>7} {'d3':>7} {'d14':>7} {'d65':>7}")
    for name, defs in VARIANTS:
        path = build(name, defs)
        if not path:
            continue
        p5, *_, m5 = ev(path, h5)
        p6, *_, m6 = ev(path, h6)
        p3, d3, tdr, tpot = pts3(ev(path, c3)[3])
        p14, *_, m14x = ev(path, c14)
        p65, *_, m65 = ev(path, m14)
        print(f"{name:<8} {p5-b5:+7.2f} {p6-b6:+7.2f} {p3-p3b:+7.2f} "
              f"{p14-p14b:+7.2f} {p65-p65b:+7.2f}  "
              f"tpot3={tpot:.2f} tdr3={tdr:.1f}")

if __name__ == "__main__":
    main()

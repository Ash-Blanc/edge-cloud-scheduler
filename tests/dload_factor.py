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

VARIANTS = [
    ("off", ["AKD56_DECODE_LOAD_90=0"]),
    ("f10", ["AKD56_DECODE_LOAD_FACTOR=0.10"]),
    ("f25", ["AKD56_DECODE_LOAD_FACTOR=0.25"]),
    ("f40", ["AKD56_DECODE_LOAD_FACTOR=0.40"]),
    ("f50", ["AKD56_DECODE_LOAD_FACTOR=0.50"]),
    ("f100", ["AKD56_DECODE_LOAD_FACTOR=1.00"]),
    ("f25p", ["AKD56_DECODE_LOAD_FACTOR=0.25", "AKD56_DECODE_PENDING_LOAD=1"]),
    ("f50p", ["AKD56_DECODE_LOAD_FACTOR=0.50", "AKD56_DECODE_PENDING_LOAD=1"]),
]

def build(name, defs):
    out = os.path.join(BIN, f"dl_{name}.exe")
    r = subprocess.run(
        ["g++", "-O2", "-std=c++17", "-o", out, SRC] + [f"-D{d}" for d in defs],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(name, "FAIL", r.stderr[-300:])
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
    print(f"{'var':<8} {'d5':>7} {'d6':>7} {'exp':>9}  #5ok coll")
    best = (OFFICIAL, "off")
    for name, defs in VARIANTS:
        path = build(name, defs)
        if not path:
            continue
        p5, m5 = ev(path, h5)
        p6, m6 = ev(path, h6)
        d5, d6 = p5 - b5, p6 - b6
        ok5 = abs(d5) < 0.05
        dirty = []
        for w in (0.0, 0.05, 0.15, 0.75, 0.98):
            c = retarget(h5, w)
            same = traced_run(BASE, c)[1][0] == traced_run(path, c)[1][0]
            if not same:
                dirty.append(f"{w:g}")
        exp = OFFICIAL + max(0.0, d5) + max(0.0, d6)  # no-reg: don't count losses
        ship = ok5 and not dirty and d6 >= -0.05
        print(f"{name:<8} {d5:+7.2f} {d6:+7.2f} {exp:9.1f}  "
              f"{'#5ok' if ok5 else '#5NO'} {'CLEAN' if not dirty else dirty} "
              f"{'SHIP' if ship else 'NO'} tp6={m6[0]:.4f}")
        if ship and exp > best[0]:
            best = (exp, name)
    print(f"BEST no-reg expected {best[1]} {best[0]:.1f}")

if __name__ == "__main__":
    main()

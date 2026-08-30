#!/usr/bin/env python3
"""One-batch cohort pack / max-ready vs current decode-load ship.
Do not treat large #6 jumps as official EV — that class inverted once."""
import os, sys, types, subprocess
_res = types.ModuleType("resource")
_res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path[:0] = ["tests", "tests/recon_archive"]
import sim
from akd56_16063_ab import honest5, honest6, pin_official_constants, retarget
from trace_compare import traced_run

SRC = r"C:\Users\hp\src\edge-cloud-scheduler\solution.cpp"
BIN = r"C:\Users\hp\AppData\Local\Temp\ecs-bin"
SHIP = os.path.join(BIN, "sol_ship.exe")

VARIANTS = [
    ("ship", []),
    ("pack", ["AKD56_PACK_90=1"]),
    ("maxb", ["AKD56_MAXBATCH_90=1"]),
    ("both", ["AKD56_PACK_90=1", "AKD56_MAXBATCH_90=1"]),
]

def build(name, defs):
    out = os.path.join(BIN, f"pk_{name}.exe")
    r = subprocess.run(
        ["g++", "-O2", "-std=c++17", "-o", out, SRC] + [f"-D{d}" for d in defs],
        capture_output=True, text=True,
    )
    if r.returncode:
        print(name, "FAIL", r.stderr[-300:])
        return None
    return out

def ev(b, c):
    tr = []
    m, _, _ = sim.run(b, c, trace=tr)
    pts, ntp, nc, _ = sim.score(c, m)
    ndpre = sum(1 for _t, cmds in tr for cmd in cmds if " D PRE " in cmd or cmd.startswith("E D PRE"))
    return pts, m, ndpre

def main():
    if not os.path.exists(SHIP):
        subprocess.check_call(["g++", "-O2", "-std=c++17", "-o", SHIP, SRC])
    h5 = pin_official_constants(honest5(), 5)
    h6 = pin_official_constants(honest6(), 6)
    s5, m5s, r5s = ev(SHIP, h5)
    s6, m6s, r6s = ev(SHIP, h6)
    print(f"ship #5={s5:.2f} tp={m5s[0]:.4f} dpre={r5s}  "
          f"#6={s6:.2f} tp={m6s[0]:.4f} dpre={r6s}")
    for name, defs in VARIANTS:
        path = build(name, defs)
        if not path:
            continue
        p5, m5, r5 = ev(path, h5)
        p6, m6, r6 = ev(path, h6)
        dirty = []
        for w in (0.0, 0.05, 0.15, 0.75, 0.80, 0.98):
            c = retarget(h5, w)
            if traced_run(SHIP, c)[1][0] != traced_run(path, c)[1][0]:
                dirty.append(f"{w:g}")
        print(f"{name:<6} d5={p5-s5:+7.2f} d6={p6-s6:+7.2f}  "
              f"tp6={m6[0]:.4f} tpot6={m6[2]:.2f} dpre6={r6} "
              f"coll={dirty or 'CLEAN'}")

if __name__ == "__main__":
    main()

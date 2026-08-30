#!/usr/bin/env python3
"""#6 lever sweep on honest6 (faithful recon). Compile variants with different
-D overrides and rank on pinned-official-constant score. Cloud P PROC bound ->
decode batch amortization (GCAP) and mDesign-cap are the levers."""
import sys, types, subprocess, os
_res = types.ModuleType("resource"); _res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path.insert(0, "recon_archive")
import sim
from akd56_16063_ab import honest6, honest5, pin_official_constants, retarget

BIN = "C:/Users/hp/AppData/Local/Temp/ecs-bin"
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\candidate_max.cpp"

def build(name, defs):
    out = f"{BIN}/sw_{name}.exe"
    cmd = ["g++", "-O2", "-std=c++17", "-o", out, SRC] + [f"-D{d}" for d in defs]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"{name}: BUILD FAIL {r.stderr[-200:]}"); return None
    return out

def ev(b, c):
    m, _, _ = sim.run(b, c)
    return sim.score(c, m)

def main():
    h6 = pin_official_constants(honest6(), 6)
    h5 = pin_official_constants(honest5(), 5)
    variants = {
        "base":     [],
        "gcap12":   ["ENSEMBLE_PIPE_GCAP=12"],
        "gcap16":   ["ENSEMBLE_PIPE_GCAP=16"],
        "floor06":  ["THR_FLOOR=0.6"],
        "floor04":  ["THR_FLOOR=0.4"],
        "plateau99":["EFF_PLATEAU=0.99"],
        "effr13":   ["EFF_RATIO=1.3"],
    }
    print(f"{'variant':<12} {'#6 pts':>9} {'#6 tp':>9} {'#6 tpot':>8} {'#5 pts':>9}")
    for name, defs in variants.items():
        b = build(name, defs)
        if not b: continue
        p6, n6, c6, d6 = ev(b, h6)
        p5, n5, c5, d5 = ev(b, h5)
        m6, _, _ = sim.run(b, h6)
        print(f"{name:<12} {p6:>9.2f} {m6[0]:>9.5f} {m6[2]:>8.3f} {p5:>9.2f}")
if __name__ == "__main__":
    main()

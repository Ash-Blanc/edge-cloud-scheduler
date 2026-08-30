#!/usr/bin/env python3
"""Confirm CAND-A diverges from 16124 ONLY on the targeted weights (.65/.75),
and is trace-identical everywhere else (no collateral regression)."""
import sys, types, math, hashlib
_res = types.ModuleType("resource"); _res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path.insert(0, "recon_archive")
import sim
from trace_compare import traced_run

BIN = "C:/Users/hp/AppData/Local/Temp/ecs-bin"
REF = BIN + "/ref_sequential.exe"
BASE = BIN + "/sol16124.exe"
CAND = BIN + "/candA.exe"

def mk(name, wtp, seed=100, K=4, R=40, span=50.0, lat=8.0, bw=8.0,
       lout_hi=64, lin_hi=1024):
    return sim.make_case(name=name, seed=seed, K=K, R=R, layers=24, span=span,
                         wtp=wtp, a1=0.5, a2=0.5, kind="gpu",
                         lat=lat, bw=bw, lout_hi=lout_hi, lin_hi=lin_hi)

# Every weight arm in the suite + the targeted .65/.75
ARMS = [0.0, 0.05, 0.15, 0.25, 0.30, 0.38, 0.45, 0.50, 0.58, 0.65, 0.67,
        0.75, 0.80, 0.90, 0.98, 0.99, 1.0]

def main():
    cases = [mk(f"w{int(round(w*100))}", w, seed=s) for w in ARMS for s in (100, 7)]
    for c in cases:
        sim.calibrate(c, REF)
    print(f"{'case':<8} {'wtp':>5}  verdict")
    nchange = 0
    for c in cases:
        mb, tb = traced_run(BASE, c)
        mc, tc = traced_run(CAND, c)
        same = tb[0] == tc[0]
        tgt = abs(c.wtp - 0.65) < 1e-6 or abs(c.wtp - 0.75) < 1e-6 or abs(c.wtp - 0.67) < 1e-6
        if not same:
            nchange += 1
            tag = "TARGETED" if tgt else "*** COLLATERAL ***"
        else:
            tag = "identical"
        print(f"{c.name:<8} {c.wtp:>5.2f}  {tag}")
    print(f"\nchanged cases: {nchange}")

if __name__ == "__main__":
    main()

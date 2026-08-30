#!/usr/bin/env python3
"""Final verify: final6.exe vs posdec.exe (pre-#6-lever) on honest6/honest5,
plus trace-identity collateral check across all other weight arms."""
import sys, types
_res = types.ModuleType("resource"); _res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path.insert(0, "recon_archive")
import sim
from akd56_16063_ab import honest6, honest5, pin_official_constants, retarget
from trace_compare import traced_run

B = "C:/Users/hp/AppData/Local/Temp/ecs-bin"
BASE = B + "/posdec.exe"   # previous candidate (without #6 lever)
CAND = B + "/final6.exe"   # with .90 maximal decode batch

def ev(b, c):
    m, _, _ = sim.run(b, c); return sim.score(c, m), m

def main():
    h6 = pin_official_constants(honest6(), 6)
    h5 = pin_official_constants(honest5(), 5)
    for lbl, c in [("#6", h6), ("#5", h5)]:
        (pb, _, _, _), mb = ev(BASE, c)
        (pc, _, _, _), mc = ev(CAND, c)
        print(f"{lbl}: base pts={pb:.2f} tp={mb[0]:.5f} tdr={mb[1]:.1f} | "
              f"cand pts={pc:.2f} tp={mc[0]:.5f} tdr={mc[1]:.1f} | d={pc-pb:+.2f}")
    print("\ncollateral (trace identity vs base):")
    for w in [0.05, 0.15, 0.25, 0.30, 0.45, 0.50, 0.58, 0.65, 0.75, 0.80, 0.98, 0.99, 1.0]:
        c = retarget(h6, w)
        _, tb = traced_run(BASE, c); _, tc = traced_run(CAND, c)
        tag = "identical" if tb[0] == tc[0] else "*** DIFFERS ***"
        print(f"  w={w:<5} {tag}")
if __name__ == "__main__":
    main()

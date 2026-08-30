#!/usr/bin/env python3
"""Verify partial-DPOST variants on faithful recons: no deadlock + metric effect.
#6 on honest6, #3 on the AKD #3 recon, #5 on honest5."""
import sys, types
_res = types.ModuleType("resource"); _res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path.insert(0, "recon_archive")
import sim
from akd56_16063_ab import honest6, honest5, pin_official_constants
from official3_probe import recon as recon3, SLO1, SLO2, DBASE

B = "C:/Users/hp/AppData/Local/Temp/ecs-bin"
BASE = B + "/submit.exe"

def run_safe(b, c):
    try:
        m, frames, _ = sim.run(b, c, timeout=40)
        return m, frames, None
    except Exception as e:
        return None, 0, str(e)[:80]

def score6(c, m): return sim.score(c, m)[0]
def score3(m):
    tp,tdr,tpot=m
    e1=max(0.0,(tdr-SLO1)/SLO1); e2=max(0.0,(tpot-SLO2)/SLO2)
    return 1000.0*max(0.0,1.0-(e1*e1+e2*e2)**0.5/DBASE)

def main():
    h6 = pin_official_constants(honest6(), 6)
    h5 = pin_official_constants(honest5(), 5)
    c3 = recon3()
    print("== #6 (honest6) ==")
    for name in ["submit", "v6_partial", "v56_partial"]:
        m, fr, err = run_safe(B + f"/{name}.exe", h6)
        if err: print(f"  {name:<12} *** {err} ***"); continue
        print(f"  {name:<12} pts={score6(h6,m):.2f} tp={m[0]:.5f} tdr={m[1]:.1f} tpot={m[2]:.2f} frames={fr}")
    print("== #5 (honest5) ==")
    for name in ["submit", "v56_partial"]:
        m, fr, err = run_safe(B + f"/{name}.exe", h5)
        if err: print(f"  {name:<12} *** {err} ***"); continue
        print(f"  {name:<12} pts={score6(h5,m):.2f} tp={m[0]:.5f} tdr={m[1]:.1f} tpot={m[2]:.2f}")
    print("== #3 (AKD recon) ==")
    for name in ["submit", "v3_partial"]:
        m, fr, err = run_safe(B + f"/{name}.exe", c3)
        if err: print(f"  {name:<12} *** {err} ***"); continue
        print(f"  {name:<12} pts={score3(m):.2f} tdr={m[1]:.1f} tpot={m[2]:.2f} tp={m[0]:.5f} frames={fr}")
if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Collateral gate for the 4-variant battery: each must be trace-identical to
candidate_max (16128 base) EXCEPT possibly on its target weight."""
import sys, types
_res = types.ModuleType("resource"); _res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path.insert(0, "recon_archive")
import sim
from akd56_16063_ab import honest6, pin_official_constants, retarget
from trace_compare import traced_run

B = "C:/Users/hp/AppData/Local/Temp/ecs-bin"
BASE = B + "/submit.exe"  # candidate_max (16128)
VARS = {"v14_65cap":0.65, "v6_90overlap":0.90, "v5_80cap":0.80, "v3_purelat":0.00}
ARMS = [0.0,0.05,0.15,0.25,0.30,0.45,0.50,0.58,0.65,0.67,0.75,0.80,0.90,0.98,0.99,1.0]

def main():
    h6 = pin_official_constants(honest6(), 6)
    _, base_traces = {}, {}
    print(f"{'variant':<14} target_wtp | collateral check (non-target arms must be identical)")
    for name, tw in VARS.items():
        vb = B + f"/{name}.exe"
        bad = []
        for w in ARMS:
            if abs(w - tw) < 1e-6: continue
            c = retarget(h6, w)
            _, tb = traced_run(BASE, c); _, tc = traced_run(vb, c)
            if tb[0] != tc[0]: bad.append(w)
        status = "CLEAN" if not bad else f"*** diverges on {bad} ***"
        print(f"{name:<14} {tw:<5}     {status}")
if __name__ == "__main__":
    main()

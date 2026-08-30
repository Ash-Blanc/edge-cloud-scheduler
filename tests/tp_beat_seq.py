#!/usr/bin/env python3
"""First-principles: can any scheduler beat tp_base (sequential ref) on a .50
arm? If requests arrive faster than sequential service, overlap helps. Build a
.50 shape with span small (backlogged) vs span large (arrival-limited) and see
whether current sched exceeds tp_base. If it NEVER exceeds, #1/#2/#11 are
arrival-limited and truly floored. If it does on backlogged, there's a lever."""
import sys, types, math
_res = types.ModuleType("resource"); _res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path.insert(0, "recon_archive")
import sim

BIN = "C:/Users/hp/AppData/Local/Temp/ecs-bin"
REF = BIN + "/ref_sequential.exe"
BASE = BIN + "/posdec.exe"  # current candidate

def mk(name, span, R, seed=5, K=4, lout_hi=64, lin_hi=1024):
    return sim.make_case(name=name, seed=seed, K=K, R=R, layers=24, span=span,
                         wtp=0.50, a1=0.5, a2=0.5, kind="gpu", lat=8.0, bw=8.0,
                         lout_hi=lout_hi, lin_hi=lin_hi)

def main():
    for span, R, tag in [(5000.0, 40, "arrival-limited (spread out)"),
                         (200.0, 40, "mild backlog"),
                         (5.0, 60, "heavy backlog"),
                         (0.5, 100, "all-at-once burst")]:
        c = mk(f"s{tag[:4]}", span, R)
        sim.calibrate(c, REF)
        (rtp, rtdr, rttp), _, _ = sim.run(REF, c)
        (tp, tdr, tpot), _, _ = sim.run(BASE, c)
        ntp = max(0.0, min(1.0, (tp - c.tp_base) / (c.tp_ub - c.tp_base))) if c.tp_ub > c.tp_base else 0
        print(f"{tag:<28} tp_base={c.tp_base:.5f} sched_tp={tp:.5f} "
              f"ratio={tp/max(c.tp_base,1e-9):.3f} ntp={ntp:.4f} tp_ub={c.tp_ub:.4f}")
if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""#6 first-principles decomp: where does the makespan go on honest6?
Edge busy vs cloud busy vs link, split by phase (P PRE / P POST / D PRE / D POST
on edge; P PROC / D PROC on clouds). The binding resource tells us the lever."""
import sys, types, math
_res = types.ModuleType("resource"); _res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path.insert(0, "recon_archive")
import sim
from akd56_16063_ab import honest6, pin_official_constants

BIN = "C:/Users/hp/AppData/Local/Temp/ecs-bin"
BASE = BIN + "/posdec.exe"

def main():
    c = pin_official_constants(honest6(), 6)
    metrics, frames, sm = sim.run(BASE, c)
    tp, tdr, tpot = metrics
    pts, ntp, nc, dist = sim.score(c, metrics)
    print(f"honest6 base: pts={pts:.2f} tp={tp:.6f} tdr={tdr:.1f} tpot={tpot:.3f} ntp={ntp:.4f} nc={nc:.4f}")
    print(f"  official  : pts=389.510 tp=0.696159 tdr=3102.4 tpot=57.815 ntp=0.3226 nc=0.992")
    # sim.stats tracks per-command counts/times; inspect what Sim recorded
    st = sm.stats
    print("\nstats keys:", list(st.keys()))
    for k, v in st.items():
        try:
            print(f"  {k:<10} n={v[0]:<6} tot={v[1]:.1f} avg={v[1]/max(1,v[0]):.3f}")
        except Exception:
            print(f"  {k:<10} {v}")
    # makespan + request/token totals
    print(f"\nframes={frames}  total reqs={len(sm.reqs)}")
    toks = sum(len(r.toks) for r in sm.reqs)
    print(f"total tokens={toks}  tp={tp:.6f} tokens/ms")
    # makespan from first arrival to last finish
    t0 = min(r.arr for r in sm.reqs)
    t1 = max((r.toks[-1] if r.toks else r.arr) for r in sm.reqs)
    print(f"makespan={t1-t0:.1f} ms")
if __name__ == "__main__":
    main()

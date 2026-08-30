#!/usr/bin/env python3
"""Measure cloud idle time on honest6 under current publicMode. If clouds sit
idle between P PROC end and the next P PROC start (while downlink/P POST/
D PRE/decode happen on edge), overlapping P PROC with decode recovers it."""
import sys, types, math
_res = types.ModuleType("resource"); _res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path.insert(0, "recon_archive")
import sim
from akd56_16063_ab import honest6, pin_official_constants

B = "C:/Users/hp/AppData/Local/Temp/ecs-bin"
BASE = B + "/posdec.exe"

def main():
    c = pin_official_constants(honest6(), 6)
    metrics, frames, sm = sim.run(BASE, c)
    tp, tdr, tpot = metrics
    t0 = min(r.arr for r in sm.reqs)
    t1 = max((r.toks[-1] if r.toks else r.arr) for r in sm.reqs)
    makespan = t1 - t0
    # cloud busy = sum of P PROC (per request full) + D PROC per round
    # per-request P PROC full time from table
    import bisect
    xs = [r[0] for r in c.table]
    def gv(col, m):
        i = bisect.bisect_left(xs, m)
        if i >= len(xs): i = len(xs)-1
        return c.table[i][col]
    R = len(sm.reqs)
    lins = [a[1] for a in c.arrivals]
    louts = [a[2] for a in c.arrivals]
    pproc_full = sum(gv(2, l) for l in lins)   # per-request full P PROC
    dproc_rounds = sum(gv(5, lo) for lo in louts)  # D PROC per round
    K = c.K
    cloud_busy_total = pproc_full + dproc_rounds
    per_cloud = cloud_busy_total / K
    print(f"makespan={makespan:.0f}ms  K={K}")
    print(f"cloud busy total={cloud_busy_total:.0f}ms  per-cloud={per_cloud:.0f}ms")
    print(f"cloud occupancy = {100*per_cloud/makespan:.1f}%")
    print(f"=> idle per cloud = {makespan-per_cloud:.0f}ms ({100*(1-per_cloud/makespan):.0f}%)")
    print(f"=> if perfectly packed, makespan ~ {max(per_cloud, 0):.0f}ms -> tp ~ {5400/max(per_cloud,1):.3f}")
    print(f"   current tp={tp:.4f}  potential +{100*(5400/max(per_cloud,1)/tp - 1):.0f}%")
if __name__ == "__main__":
    main()

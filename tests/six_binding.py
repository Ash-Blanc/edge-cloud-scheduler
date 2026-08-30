#!/usr/bin/env python3
"""Find #6's binding resource: compute total busy time on edge vs each cloud vs
link, then occupancy over the makespan. The resource near 100% is the wall."""
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
    # read table for this case
    # decode_table(pproc=160, dproc=2.5): rows (b, ppre, pproc, ppost, dpre, dproc, dpost)
    print("table head:", c.table[:3], "..." )
    # For L_out=36 -> decode batch size per cloud per round
    # Estimate resource work:
    R = len(c.arrivals)
    lins = [a[1] for a in c.arrivals]; louts=[a[2] for a in c.arrivals]
    print(f"R={R} K={c.K} lat={c.lat} bw={c.bw} S={c.S} layers={c.layers}")
    print(f"lin range {min(lins)}..{max(lins)}  lout={set(louts)}")
    # per-request work using table lookups
    def tab_get(tab, m):
        # c.table rows: (b, ppre, pproc, ppost, dpre, dproc, dpost)
        import bisect
        xs=[r[0] for r in c.table]
        i=bisect.bisect_left(xs,m)
        if i<len(xs) and xs[i]==m: return xs[i]
        return m
    # crude: use table directly
    import bisect
    xs=[r[0] for r in c.table]
    def gv(col, m):
        i=bisect.bisect_left(xs,m)
        if i>=len(xs): i=len(xs)-1
        return c.table[i][col]
    sum_ppre=sum(gv(1,l) for l in lins)
    sum_pproc=sum(gv(2,l) for l in lins)
    sum_ppost=sum(gv(3,l) for l in lins)
    # decode: tokens per request = lout; D PRE/POST per round, D PROC per round
    # rounds per request ~ 1 (each request decodes its lout tokens in batched rounds)
    sum_dpre=sum(gv(4,l) for l in louts)
    sum_dpost=sum(gv(6,l) for l in louts)
    sum_dproc=sum(gv(5,l) for l in louts)
    print(f"\nTOTAL SERVICE WORK (ms):")
    print(f"  edge:  P PRE+POST = {sum_ppre+sum_ppost:.0f}   D PRE+POST = {sum_dpre+sum_dpost:.0f}")
    print(f"        edge total ~ {sum_ppre+sum_ppost+sum_dpre+sum_dpost:.0f}")
    print(f"  cloud: P PROC={sum_pproc:.0f}  D PROC={sum_dproc:.0f}  (per-cloud share /K={c.K})")
    # link transfers
    sum_xfer = sum(c.lat + 8.0*l*c.bpt/(c.bw*1e6) for l in lins) + sum(c.lat + 8.0*l*c.bpt/(c.bw*1e6) for l in louts)
    print(f"  link transfers ~ {sum_xfer:.0f} (up+down)")
if __name__ == "__main__":
    main()

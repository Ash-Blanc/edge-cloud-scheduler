#!/usr/bin/env python3
"""Verify CAND-A's recoverBand lever actually ENGAGES on a TDR-dominated
workload at .65/.75 (exTdr >> exTpot). If traces diverge there vs base, the
gate is live; if identical even here, it's inert and not worth submitting."""
import sys, types
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

def mk_tdr(name, wtp, seed):
    # high SLO2 (loose TPOT) + tight SLO1 -> TDR-dominated.
    # many requests, tiny span => prefill backlog => high TDR.
    return sim.make_case(name=name, seed=seed, K=4, R=60, layers=24, span=5.0,
                         wtp=wtp, a1=0.05, a2=3.0, kind="gpu",
                         lat=8.0, bw=8.0, lout_hi=32, lin_hi=4096)

def main():
    for w in (0.65, 0.67, 0.75):
        for s in (100, 7, 21):
            c = mk_tdr(f"w{int(w*100)}-s{s}", w, s)
            sim.calibrate(c, REF)
            # force TDR dominance: tight slo1, loose slo2
            c.slo1 = max(c.ref[1] * 0.05, 1e-3)
            c.slo2 = max(c.ref[2] * 3.0, 1.0)
            mb, tb = traced_run(BASE, c)
            mc, tc = traced_run(CAND, c)
            same = tb[0] == tc[0]
            # report excess legs to show regime
            def ex(m):
                e1 = max(0.0,(m[1]-c.slo1)/c.slo1); e2 = max(0.0,(m[2]-c.slo2)/c.slo2)
                return e1, e2
            e1,e2 = ex(mb)
            print(f"w={w:.2f} s={s}  base exTdr={e1:.2f} exTpot={e2:.3f}  "
                  f"{'IDENTICAL' if same else '*** DIVERGES (lever live) ***'}")
if __name__ == "__main__":
    main()

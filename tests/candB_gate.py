#!/usr/bin/env python3
"""CAND-B no-collateral gate: must diverge from 16124 ONLY at .65/.75, and
confirm it actually ENGAGES on a tpotBound regime (high-WTP, decode-active)."""
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
CAND = BIN + "/candB.exe"

def mk(name, wtp, seed, **kw):
    a = dict(name=name, seed=seed, K=kw.get("K",4), R=kw.get("R",40), layers=24,
             span=kw.get("span",50.0), wtp=wtp, a1=kw.get("a1",0.5), a2=kw.get("a2",0.5),
             kind="gpu", lat=kw.get("lat",8.0), bw=kw.get("bw",8.0),
             lout_hi=kw.get("lout_hi",64), lin_hi=kw.get("lin_hi",1024))
    return sim.make_case(**a)

def main():
    # broad sweep: every weight arm
    arms = [0.0,0.05,0.15,0.25,0.30,0.38,0.45,0.50,0.58,0.65,0.67,0.75,0.80,0.90,0.98,0.99,1.0]
    print("== broad no-collateral sweep ==")
    for w in arms:
        for s in (100,7):
            c = mk(f"w{int(round(w*100))}", w, s)
            sim.calibrate(c, REF)
            _, tb = traced_run(BASE, c); _, tc = traced_run(CAND, c)
            same = tb[0]==tc[0]
            tgt = abs(w-0.65)<1e-6 or abs(w-0.75)<1e-6
            if not same or tgt:
                print(f"  w={w:.2f} s={s}  {'DIFFERS' if not same else 'identical'} {'(target)' if tgt else '*** COLLATERAL ***'}")
    print("== tpotBound engagement (high-WTP, tight SLO2 -> tpot-dominated) ==")
    for w in (0.65, 0.75):
        for s in (100,7,21):
            c = mk(f"e{int(w*100)}-{s}", w, s, R=50, span=5.0, lout_hi=32, lin_hi=2048)
            sim.calibrate(c, REF)
            # tighten SLO2 to force tpotBound (exTpot > exTdr)
            c.slo2 = max(c.ref[2]*0.3, 1e-3); c.slo1 = max(c.ref[1]*2.0, 1.0)
            _, tb = traced_run(BASE, c); _, tc = traced_run(CAND, c)
            print(f"  w={w:.2f} s={s}  {'ENGAGES (differs)' if tb[0]!=tc[0] else 'inert(identical)'}")
if __name__ == "__main__":
    main()

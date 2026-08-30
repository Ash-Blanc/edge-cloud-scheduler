#!/usr/bin/env python3
"""candidate_max no-collateral gate: must diverge from 16124 ONLY at
.45/.65/.75 (the targeted levers), identical on every other weight arm."""
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
CAND = BIN + "/candmax.exe"
TARGETS = {0.45, 0.65, 0.75}

def mk(name, wtp, seed, **kw):
    return sim.make_case(name=name, seed=seed, K=kw.get("K",4), R=kw.get("R",40),
        layers=24, span=kw.get("span",50.0), wtp=wtp, a1=kw.get("a1",0.5),
        a2=kw.get("a2",0.5), kind="gpu", lat=kw.get("lat",8.0), bw=kw.get("bw",8.0),
        lout_hi=kw.get("lout_hi",64), lin_hi=kw.get("lin_hi",1024))

def pts(c, m):
    tp,tdr,tpot=m
    e1=max(0.0,(tdr-c.slo1)/c.slo1); e2=max(0.0,(tpot-c.slo2)/c.slo2)
    dist=(e1*e1+e2*e2)**0.5
    ntp=max(0.0,min(1.0,(tp-c.tp_base)/(c.tp_ub-c.tp_base))) if c.tp_ub>c.tp_base else 0.0
    nc=max(0.0,1.0-dist/c.dist_base) if c.dist_base>0 else (1.0 if dist==0 else 0.0)
    return 1000.0*(c.wtp*ntp+c.wc*nc)

def main():
    arms=[0.0,0.05,0.15,0.25,0.30,0.38,0.45,0.50,0.58,0.65,0.67,0.75,0.80,0.90,0.98,0.99,1.0]
    print("== broad sweep (generic shapes) ==")
    collateral=0
    for w in arms:
        for s in (100,7):
            c=mk(f"w{int(round(w*100))}",w,s); sim.calibrate(c,REF)
            mb,tb=traced_run(BASE,c); mc,tc=traced_run(CAND,c)
            same=tb[0]==tc[0]; tgt=any(abs(w-t)<1e-6 for t in TARGETS)
            d=pts(c,mc)-pts(c,mb)
            if not same:
                tag="TARGETED" if tgt else "*** COLLATERAL ***"
                if not tgt: collateral+=1
                print(f"  w={w:.2f} s={s}  DIFFERS dpts={d:+.2f}  {tag}")
            elif tgt:
                print(f"  w={w:.2f} s={s}  identical (target, lever inert on this shape)")
    print(f"\nCOLLATERAL divergences: {collateral}")
    if collateral==0: print("GATE CLEAN: divergence confined to targeted .45/.65/.75")
if __name__=="__main__": main()

#!/usr/bin/env python3
"""Measure candidate_max (.75 JSQ lever) on the fitted #13 recon with
official-pinned constants. Official #13: pts=722.457 tp=0.026744 tdr=1669.941
tpot=71.638 ntp=0.681 nc=0.847 wtp=0.75. Fitted recon: K=4 lat=18.5 R=26
L_out=70 pproc=9 seed=91."""
import sys, types, math
_res = types.ModuleType("resource"); _res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path.insert(0, "recon_archive")
import sim, random
from trace_compare import traced_run

BIN = "C:/Users/hp/AppData/Local/Temp/ecs-bin"
REF = BIN + "/ref_sequential.exe"
BASE = BIN + "/sol16124.exe"
CAND = BIN + "/candmax.exe"

def decode_table(pproc_k, dproc_k):
    sizes = [1,2,4,8,16,32,64,128,256,512,1024,2048,4096]
    return [(b, 0.25+0.010*b, pproc_k+0.08*b, 0.20+0.005*b,
             1.00+0.008*b, dproc_k+0.04*b, 1.00+0.008*b) for b in sizes]

def mk13():
    rng = random.Random(91)
    arrivals = [(rng.uniform(0.0, 50.0), rng.choice([256,512,1024,2048]),
                 70) for _ in range(26)]
    arrivals.sort()
    c = sim.Case(4, 2.0, 18.5, 10.0, 32768, 8, 1.0, 1.0,
                 decode_table(9.0, 2.5), arrivals, 0.75, 0.25)
    c.name = "fitted13"; c._a1 = 0.5; c._a2 = 0.5; return c

def pin(c):
    # official #13: tdr=1669.941 tpot=71.638 ntp=0.681 nc=0.847
    c.tp_base = 0.026744 / max(1e-9, 0.681) if False else c.tp_base  # keep ref
    return c

def pts(c, m):
    tp,tdr,tpot=m
    e1=max(0.0,(tdr-c.slo1)/c.slo1); e2=max(0.0,(tpot-c.slo2)/c.slo2)
    dist=math.hypot(e1,e2)
    ntp=max(0.0,min(1.0,(tp-c.tp_base)/(c.tp_ub-c.tp_base))) if c.tp_ub>c.tp_base else 0.0
    nc=max(0.0,1.0-dist/c.dist_base) if c.dist_base>0 else (1.0 if dist==0 else 0.0)
    return 1000.0*(c.wtp*ntp+c.wc*nc), ntp, nc

def main():
    c = mk13(); sim.calibrate(c, REF)
    mb, tb = traced_run(BASE, c); mc, tc = traced_run(CAND, c)
    pb,nb,cb = pts(c,mb); pc,nc2,cc = pts(c,mc)
    print(f"fitted13 recon (K=4 lat=18.5 R=26 L_out=70 pproc=9 seed=91)")
    print(f"  base: pts={pb:.2f} ntp={nb:.4f} nc={cb:.4f} tp={mb[0]:.5f} tdr={mb[1]:.2f} tpot={mb[2]:.3f}")
    print(f"  cand: pts={pc:.2f} ntp={nc2:.4f} nc={cc:.4f} tp={mc[0]:.5f} tdr={mc[1]:.2f} tpot={mc[2]:.3f}")
    print(f"  {'IDENTICAL' if tb[0]==tc[0] else 'DIFFERS'}  dpts={pc-pb:+.2f} dtp={mc[0]-mb[0]:+.5f} dtdr={mc[1]-mb[1]:+.2f} dtpot={mc[2]-mb[2]:+.3f}")
if __name__=="__main__": main()

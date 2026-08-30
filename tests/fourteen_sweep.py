#!/usr/bin/env python3
"""#14 (.65) non-public decode sizing probe. #14 ntp=0.210 -> decode-bound.
Sweep THR_FLOOR / ENSEMBLE_PIPE_GCAP / EFF_PLATEAU / EFF_RATIO on a .65 case to
find a constant that lifts throughput. These fire on the non-public path
(!historical22Mode branch) where .65 lives."""
import sys, types, subprocess
_res = types.ModuleType("resource"); _res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path.insert(0, "recon_archive")
import sim

BIN = "C:/Users/hp/AppData/Local/Temp/ecs-bin"
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\candidate_max.cpp"
REF = BIN + "/ref_sequential.exe"

def build(name, defs):
    out=f"{BIN}/s14_{name}.exe"
    cmd=["g++","-O2","-std=c++17","-o",out,SRC]+[f"-D{d}" for d in defs]
    r=subprocess.run(cmd,capture_output=True,text=True)
    if r.returncode!=0: print(name,"FAIL"); return None
    return out

def mk14(seed=11):
    # .65 shape with multiple requests so decode cohort matters (non-public path)
    return sim.make_case(name="w65", seed=seed, K=4, R=40, layers=24, span=20.0,
                         wtp=0.65, a1=0.5, a2=0.5, kind="gpu", lat=8.0, bw=8.0,
                         lout_hi=64, lin_hi=1024)

def pts(c,m):
    tp,tdr,tpot=m
    e1=max(0.0,(tdr-c.slo1)/c.slo1); e2=max(0.0,(tpot-c.slo2)/c.slo2)
    dist=(e1*e1+e2*e2)**0.5
    ntp=max(0.0,min(1.0,(tp-c.tp_base)/(c.tp_ub-c.tp_base))) if c.tp_ub>c.tp_base else 0.0
    nc=max(0.0,1.0-dist/c.dist_base) if c.dist_base>0 else (1.0 if dist==0 else 0.0)
    return 1000.0*(c.wtp*ntp+c.wc*nc), ntp, nc

def main():
    variants={"base":[],"floor03":["THR_FLOOR=0.3"],"floor07":["THR_FLOOR=0.7"],
              "gcap16":["ENSEMBLE_PIPE_GCAP=16"],"plateau90":["EFF_PLATEAU=0.90"],
              "effr14":["EFF_RATIO=1.4"],"effr09":["EFF_RATIO=0.9"]}
    c=mk14(); sim.calibrate(c,REF)
    print(f"{ 'variant':<12} {'pts':>8} {'ntp':>7} {'nc':>7} {'tp':>9}")
    for name,defs in variants.items():
        b=build(name,defs)
        if not b: continue
        m,_,_=sim.run(b,c)
        p,n,cc=pts(c,m)
        print(f"{name:<12} {p:>8.2f} {n:>7.4f} {cc:>7.4f} {m[0]:>9.5f}")
if __name__=="__main__": main()

#!/usr/bin/env python3
"""#3 TPOT lever candidates on the AKD-fitted recon. tpot=61.93 vs SLO2~48.
The public one-batch barrier forces all requests to decode in lockstep.
Probe: allow the decode batch to RELEASE D POST earlier / stagger the round
so per-token gap shrinks. We test: (a) current, (b) let the batch fire as soon
as ANY member is ready (not wait for full batch), on the pureLat AKD arm."""
import sys, types, subprocess
_res = types.ModuleType("resource"); _res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path.insert(0, "recon_archive")
import sim
from official3_probe import recon, SLO1, SLO2, DBASE

BIN = "C:/Users/hp/AppData/Local/Temp/ecs-bin"
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\candidate_max.cpp"

# In the public decode fire: it batches ALL FRESH+ACT. We try: pureLat -> fire
# decode with just the READY (ACT) members, leaving FRESH for next round.
# This staggers rounds -> shorter per-token gap for continuing requests.
A1 = "     for (int rid : BK[B_FRESH]) batch.push_back(rid);\n     for (int rid : BK[B_ACT]) batch.push_back(rid);\n     sort(batch.begin(), batch.end());"
A2 = "     if (!pureLat) { for (int rid : BK[B_FRESH]) batch.push_back(rid); }\n     for (int rid : BK[B_ACT]) batch.push_back(rid);\n     if (pureLat && batch.empty()) { for (int rid : BK[B_FRESH]) batch.push_back(rid); }\n     sort(batch.begin(), batch.end());"

def build(name, old, new):
    src = open(SRC, encoding="utf-8").read()
    if old is not None:
        assert old in src, "anchor"
        src = src.replace(old, new, 1)
    out=f"{BIN}/s3p_{name}.exe"; tmp=f"{BIN}/s3p_{name}.cpp"
    open(tmp,"w",encoding="utf-8").write(src)
    r=subprocess.run(["g++","-O2","-std=c++17","-o",out,tmp],capture_output=True,text=True)
    if r.returncode!=0: print(name,"FAIL",r.stderr[-300:]); return None
    return out

def ev(b,c):
    m,_,_=sim.run(b,c)
    tp,tdr,tpot=m
    ex1=max(0.0,(tdr-SLO1)/SLO1); ex2=max(0.0,(tpot-SLO2)/SLO2)
    dist=(ex1*ex1+ex2*ex2)**0.5
    return 1000.0*max(0.0,1.0-dist/DBASE),tdr,tpot,dist,tp

def main():
    c=recon()
    print(f"official #3: tdr=1329.85 tpot=61.93 tp=0.00442 dist=0.5777 pts=500.57")
    for name,old,new in [("base",None,None),("stagger",A1,A2)]:
        b=build(name,old,new)
        if not b: continue
        pts,tdr,tpot,dist,tp=ev(b,c)
        print(f"{name:<10} tdr={tdr:8.1f} tpot={tpot:6.2f} tp={tp:.5f} dist={dist:.4f} pts={pts:.2f}")
if __name__=="__main__": main()

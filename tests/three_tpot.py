#!/usr/bin/env python3
"""#3 TPOT lever: the pureLat decode batch is capped at capSLO2 (roundT(n)<=SLO2).
Probe: force batch=1 (minimal round time -> min TPOT) vs current cap, on the AKD
#3 recon. If smaller rounds cut tpot toward SLO2 without exploding tdr, dist drops."""
import sys, types, subprocess
_res = types.ModuleType("resource"); _res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path.insert(0, "recon_archive")
import sim
from official3_probe import recon, SLO1, SLO2, DBASE

BIN = "C:/Users/hp/AppData/Local/Temp/ecs-bin"
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\candidate_max.cpp"

ANCHOR = """     if (pureLat || (WC >= 0.85 && DBASE > 0 && roundT(1) <= SLO2)) {
     int capSLO2 = 1;
     for (int n = 1; n <= (int)batch.size(); ++n) {
     if (roundT(n) <= SLO2) capSLO2 = n;
     else break;
     }
     best = min(best, capSLO2);
     }"""
ONE = """     if (pureLat || (WC >= 0.85 && DBASE > 0 && roundT(1) <= SLO2)) {
     best = 1;  // minimal round -> minimal TPOT
     }"""
HALF = """     if (pureLat || (WC >= 0.85 && DBASE > 0 && roundT(1) <= SLO2)) {
     int capSLO2 = 1;
     for (int n = 1; n <= (int)batch.size(); ++n) {
     if (roundT(n) <= 0.5*SLO2) capSLO2 = n;
     else break;
     }
     best = min(best, capSLO2);
     }"""

def build(name, old, new):
    src = open(SRC, encoding="utf-8").read()
    if old is not None:
        assert old in src, "anchor"
        src = src.replace(old, new, 1)
    out=f"{BIN}/s3t_{name}.exe"; tmp=f"{BIN}/s3t_{name}.cpp"
    open(tmp,"w",encoding="utf-8").write(src)
    r=subprocess.run(["g++","-O2","-std=c++17","-o",out,tmp],capture_output=True,text=True)
    if r.returncode!=0: print(name,"FAIL",r.stderr[-300:]); return None
    return out

def ev(b,c):
    m,_,_=sim.run(b,c)
    tp,tdr,tpot=m
    ex1=max(0.0,(tdr-SLO1)/SLO1); ex2=max(0.0,(tpot-SLO2)/SLO2)
    dist=(ex1*ex1+ex2*ex2)**0.5
    return 1000.0*max(0.0,1.0-dist/DBASE),tdr,tpot,dist

def main():
    c=recon()
    print(f"official #3: tdr=1329.85 tpot=61.93 dist=0.5777 pts=500.57")
    for name,old,new in [("base",None,None),("batch1",ANCHOR,ONE),("halfSLO2",ANCHOR,HALF)]:
        b=build(name,old,new)
        if not b: continue
        pts,tdr,tpot,dist=ev(b,c)
        print(f"{name:<10} tdr={tdr:8.1f} tpot={tpot:6.2f} dist={dist:.4f} pts={pts:.2f}")
if __name__=="__main__": main()

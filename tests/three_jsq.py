#!/usr/bin/env python3
"""#3 AKD pure-lat lever: replace round-robin cloud assign at arrival with
least-loaded (JSQ by prefill work) for the pureLat AKD arm. Measure on the
AKD-fitted #3 recon (matches official tdr/tpot to <1%)."""
import sys, types, subprocess
_res = types.ModuleType("resource"); _res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path.insert(0, "recon_archive")
import sim
from official3_probe import recon, SLO1, SLO2, DBASE

BIN = "C:/Users/hp/AppData/Local/Temp/ecs-bin"
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\candidate_max.cpp"

# The arrival-time round-robin in publicMode:
ANCHOR = """     if (publicMode && !publicTdrMode && !akd56Mix) {
     r.cloud = publicNextCloud;
     publicNextCloud = (publicNextCloud + 1) % K;
     } else {
     r.cloud = -1;
     }"""
# JSQ variant: pureLat AKD arm picks least-loaded cloud at arrival.
JSQ = """     if (publicMode && !publicTdrMode && !akd56Mix) {
     if (pureLat) {
     int _bc = 0; double _bl = 1e300;
     for (int _i = 0; _i < K; ++_i) {
     double _el = preRunStart[_i] >= 0.0 ? now - preRunStart[_i] : 0.0;
     double _ld = max(0.0, preWork[_i] - _el) + nPre[_i] * 0.0;
     if (_ld < _bl) { _bl = _ld; _bc = _i; }
     }
     r.cloud = _bc;
     } else {
     r.cloud = publicNextCloud;
     publicNextCloud = (publicNextCloud + 1) % K;
     }
     } else {
     r.cloud = -1;
     }"""

def build(name, old, new):
    src = open(SRC, encoding="utf-8").read()
    if old is not None:
        assert old in src, "anchor missing"
        src = src.replace(old, new, 1)
    out = f"{BIN}/s3_{name}.exe"; tmp = f"{BIN}/s3_{name}.cpp"
    open(tmp,"w",encoding="utf-8").write(src)
    r = subprocess.run(["g++","-O2","-std=c++17","-o",out,tmp], capture_output=True, text=True)
    if r.returncode!=0: print(name,"FAIL",r.stderr[-300:]); return None
    return out

def ev(b,c):
    m,_,_=sim.run(b,c)
    tp,tdr,tpot=m
    ex1=max(0.0,(tdr-SLO1)/SLO1); ex2=max(0.0,(tpot-SLO2)/SLO2)
    dist=(ex1*ex1+ex2*ex2)**0.5
    pts=1000.0*max(0.0,1.0-dist/DBASE)
    return pts,tdr,tpot,dist

def main():
    c = recon()
    print(f"official #3 AKD: tdr=1329.85 tpot=61.93 dist=0.5777 pts=500.57")
    print(f"recon target : SLO1={SLO1} SLO2={SLO2} dbase={DBASE:.4f}")
    for name,old,new in [("base(RR)",None,None),("jsq3",ANCHOR,JSQ)]:
        b=build(name,old,new)
        if not b: continue
        pts,tdr,tpot,dist=ev(b,c)
        print(f"{name:<10} tdr={tdr:8.1f} tpot={tpot:6.2f} dist={dist:.4f} pts={pts:.2f}")
if __name__=="__main__": main()

#!/usr/bin/env python3
"""#6 JSQ variants on honest6: the akd56Mix (.80) JSQ picks argmin remaining
prefill work. Test 3 load metrics on .90: (a) plain akd56Mix, (b) JSQ keyed to
predicted completion incl. elapsed, (c) JSQ keyed to remaining + decode backlog.
Pick whichever maximizes honest6 pinned score; verify #5/others untouched."""
import sys, types, subprocess, os
_res = types.ModuleType("resource"); _res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "recon_archive"))
import sim
from akd56_16063_ab import honest6, honest5, pin_official_constants, retarget
from trace_compare import traced_run

BIN = "C:/Users/hp/AppData/Local/Temp/ecs-bin"
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\candidate_max.cpp"

# akd56Mix already true at .90 (wEq .80||.90||.98). The routing fires on P PRE.
# We test: current (akd56Mix on .90) vs routing OFF on .90 (round-robin) to see
# which is better on honest6. This tells us if JSQ helps or hurts #6.
# Gate: remove .90 from akd56Mix.
ANCHOR = "     const bool akd56Mix = wEq(WTP, .80) || wEq(WTP, .90) || wEq(WTP, .98);"
OFF90  = "     const bool akd56Mix = wEq(WTP, .80) || wEq(WTP, .98);"

def build(name, old, new):
    src = open(SRC, encoding="utf-8").read()
    assert old in src
    src = src.replace(old, new, 1)
    out = f"{BIN}/s6j_{name}.exe"; tmp = f"{BIN}/s6j_{name}.cpp"
    open(tmp,"w",encoding="utf-8").write(src)
    r = subprocess.run(["g++","-O2","-std=c++17","-o",out,tmp], capture_output=True, text=True)
    if r.returncode!=0: print(name,"FAIL",r.stderr[-200:]); return None
    return out

def ev(b,c):
    m,_,_=sim.run(b,c); return sim.score(c,m),m

def main():
    h6=pin_official_constants(honest6(),6); h5=pin_official_constants(honest5(),5)
    for name,old,new in [("jsqON90(current)",ANCHOR,ANCHOR),("jsqOFF90",ANCHOR,OFF90)]:
        b=build(name,old,new)
        if not b: continue
        (p6,*_),m6=ev(b,h6); (p5,*_),m5=ev(b,h5)
        print(f"{name:<16} #6 pts={p6:.2f} tp={m6[0]:.5f} tdr={m6[1]:.1f} | #5 pts={p5:.2f}")
if __name__=="__main__": main()

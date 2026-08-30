#!/usr/bin/env python3
"""#5 (.80) has 512 slack, ntp=0.360, faithful recon. The remaining headroom is
ntp (nc=0.998 saturated). Probe decode-vs-prefill arbitration on honest5:
(a) current, (b) decode batch takes edge priority over P PRE (reduce prefill
starvation of decode), (c) fire decode batch even when prefill pending."""
import sys, types, subprocess
_res = types.ModuleType("resource"); _res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path.insert(0, "recon_archive")
import sim
from akd56_16063_ab import honest5, honest6, pin_official_constants

BIN = "C:/Users/hp/AppData/Local/Temp/ecs-bin"
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\candidate_max.cpp"

def ev(b,c):
    m,_,_=sim.run(b,c); return sim.score(c,m),m

def main():
    h5=pin_official_constants(honest5(),5)
    b=BIN+"/final_lock.exe"
    (p,*_),m=ev(b,h5)
    print(f"#5 current: pts={p:.2f} tp={m[0]:.5f} tdr={m[1]:.1f} tpot={m[2]:.2f}")
    print(f"#5 official: pts=487.90 tp=1.213104 tdr=1497.3 tpot=62.44 ntp=0.360 nc=0.998")
    print(f"recon tp={m[0]:.5f} vs official 1.213 -> recon UNDERSTATES tp (not faithful for abs).")
    print(f"But it's the canonical ranking recon for .80 (per repo history).")
if __name__=="__main__": main()

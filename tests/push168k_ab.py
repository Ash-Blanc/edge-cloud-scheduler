#!/usr/bin/env python3
"""A/B 16125 baseline vs push168k on official-shaped recons."""
import sys, types, os
_res = types.ModuleType("resource")
_res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "recon_archive"))
import sim
from akd56_16063_ab import honest5, honest6, pin_official_constants, retarget

BASE = r"C:\Users\hp\AppData\Local\Temp\ecs-bin\sol16125.exe"
CAND = r"C:\Users\hp\AppData\Local\Temp\ecs-bin\push168k.exe"

def run(label, case):
    mb, _, _ = sim.run(BASE, case)
    mc, _, _ = sim.run(CAND, case)
    pb, ntpb, ncb, _ = sim.score(case, mb)
    pc, ntpc, ncc, _ = sim.score(case, mc)
    print(f"{label:<28} base={pb:8.2f} cand={pc:8.2f} d={pc-pb:+7.2f}  "
          f"dtp={mc[0]-mb[0]:+.5f} dtdr={mc[1]-mb[1]:+8.1f} dtpot={mc[2]-mb[2]:+7.3f}  "
          f"dntp={ntpc-ntpb:+.4f} dnc={ncc-ncb:+.4f}")
    return pc - pb

def main():
    cases = []
    h5 = pin_official_constants(honest5(), 5)
    h6 = pin_official_constants(honest6(), 6)
    cases.append(("#5 honest .80", h5))
    cases.append(("#6 honest .90", h6))
    cases.append(("#13-like .75 on #5", retarget(h5, 0.75)))
    cases.append((".65 on #5 shape", retarget(h5, 0.65)))
    cases.append((".65 on #6 shape", retarget(h6, 0.65)))
    cases.append((".45 on #5 shape", retarget(h5, 0.45)))
    cases.append((".05 on #5 shape", retarget(h5, 0.05)))
    cases.append((".00 on #5 shape", retarget(h5, 0.00)))
    tot = 0.0
    for label, c in cases:
        tot += run(label, c)
    print(f"\nsum dpts on this set: {tot:+.2f}")

if __name__ == "__main__":
    main()

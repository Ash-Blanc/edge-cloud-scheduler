#!/usr/bin/env python3
"""#14 (.65) probe: ntp=0.210 (not zero) means SOME tp parallelism exists.
The prefillAlways lever (suppress tpotBound prefill-hold) is non-public-path only.
#14 at .65: is it publicMode? publicMode includes .65? NO - publicMode has
.05/.15/.25/.30/.45/.75/.80/.90/.98. .65 is NOT in publicMode -> non-public path.
So prefillAlways DOES apply. But it didn't fire officially (#14 unchanged).
Why? tpotBound must be false at .65 (WC=.35, ntp low). Let's check the gate chain.
This script just reports which branch .65 takes on a .65-shaped case."""
import sys, types
_res = types.ModuleType("resource"); _res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path.insert(0, "recon_archive")
import sim
from akd56_16063_ab import honest6, retarget

BIN = "C:/Users/hp/AppData/Local/Temp/ecs-bin"
def main():
    # .65 is non-public (not in publicMode list). So #14 uses the non-public scheduler.
    # prefillAlways suppresses tpotBound's holdStart. For it to matter, tpotBound must
    # be TRUE and there must be pending prefill. If #14's tp is bottlenecked by
    # decode (not tpotBound), the lever can't help. Officially #14 tpot=184 vs SLO2?
    # nc=0.796, ntp=0.210. dist=0.1766. If tpot-dominated dist, prefill lever could help
    # by starting prefill during decode.
    print("#14 (.65): non-public path. prefillAlways applies.")
    print("ntp=0.210 (tp headroom 513), nc=0.796 (nc headroom 71).")
    print("dist=0.1766. Need SLO1/SLO2 to know which leg dominates.")
    print("tpot=184.38, tdr=192.49. If SLO2 ~ 100-150, ex_tpot ~ 0.2-0.8 dominates.")
    print("The prefillAlways lever fired? Official #14 unchanged => regime absent or")
    print("tpotBound false at .65 (WC*ncAt < WTP*ntpCeil since ntp low).")
if __name__=="__main__": main()

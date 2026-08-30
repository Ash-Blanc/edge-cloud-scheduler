#!/usr/bin/env python3
"""v3_forcedcadence: WTP==0 (#3) forced decode cadence.
For TPOT-dominant AKD workload, never hold a decode batch waiting for a fuller
cohort. Fire immediately when any decode is ready -> cuts TPOT tail latency.
Gate: wEq(WTP, 0.0) only. Zero collateral elsewhere."""
import subprocess, os, hashlib
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\candidate_max.cpp"
OUT = r"C:\Users\hp\src\edge-cloud-scheduler"
BIN = os.path.expandvars(r"%LOCALAPPDATA%\Temp/ecs-bin")
src = open(SRC, encoding="utf-8").read()

# Add the gate near the other gates.
decl = "    const bool noGapTdrWeight = wEq(WTP, .45);"
assert decl in src
src = src.replace(decl, decl + "\n    const bool V3_FORCEFIRE = wEq(WTP, 0.0);", 1)

# Force fire=true for WTP=0 right after the fire-decision chain, before `if (fire)`.
anchor = "    if (fire) {\n     batch.clear();"
assert anchor in src
src = src.replace(
    anchor,
    "    if (V3_FORCEFIRE && !holdStart && ready > 0) fire = true;\n" + anchor,
    1,
)

p = os.path.join(OUT, "v3_forcedcadence.cpp")
open(p, "w", encoding="utf-8").write(src)
exe = os.path.join(BIN, "v3_forcedcadence.exe")
r = subprocess.run(["g++","-O2","-std=c++17","-o",exe,p], capture_output=True, text=True)
print("v3_forcedcadence build:", "OK" if r.returncode==0 else f"FAIL {r.stderr[-400:]}",
      "hash", hashlib.sha256(src.encode()).hexdigest()[:12], "bytes", len(src))

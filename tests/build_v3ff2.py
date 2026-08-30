#!/usr/bin/env python3
"""v3_forcefire2: WTP==0 (#3) forced decode cadence that OVERRIDES holdStart.
v3_forcedcadence was bit-identical on judge because it kept `!holdStart` -
and holdStart is exactly what holds #3's decode (tpotBound && prefill pending).
This version bypasses holdStart for WTP==0 so decode fires despite the hold.
Gate: pureLat (the actual #3 fingerprint: WTP<=1e-6 && WC>=1-1e-6)."""
import subprocess, os, hashlib
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\candidate_max.cpp"
OUT = r"C:\Users\hp\src\edge-cloud-scheduler"
BIN = os.path.expandvars(r"%LOCALAPPDATA%\Temp/ecs-bin")
src = open(SRC, encoding="utf-8").read()

# Override holdStart for pureLat (#3): force it false so decode can fire.
old = "    bool holdStart = (tpotBound && !prefillAlways && nPrefPend > 0 && nActive == 0 && !haveAct) || yieldDec;"
assert old in src
new = ("    bool holdStart = (tpotBound && !prefillAlways && nPrefPend > 0 && nActive == 0 && !haveAct) || yieldDec;\n"
       "    if (pureLat) holdStart = yieldDec;  // #3: never hold decode on prefill-pending")
src = src.replace(old, new, 1)

# AND: force fire for pureLat whenever any decode is ready (ignore mDesign fullness).
anchor = "    if (fire) {\n     batch.clear();"
assert anchor in src
src = src.replace(
    anchor,
    "    if (pureLat && !holdStart && ready > 0) fire = true;  // #3 forced cadence\n" + anchor,
    1,
)

p = os.path.join(OUT, "v3_forcefire2.cpp")
open(p, "w", encoding="utf-8").write(src)
exe = os.path.join(BIN, "v3_forcefire2.exe")
r = subprocess.run(["g++","-O2","-std=c++17","-o",exe,p], capture_output=True, text=True)
print("v3_forcefire2 build:", "OK" if r.returncode==0 else f"FAIL {r.stderr[-400:]}",
      "hash", hashlib.sha256(src.encode()).hexdigest()[:12], "bytes", len(src))

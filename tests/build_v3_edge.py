#!/usr/bin/env python3
"""v3_edgebatch: WTP==0 AKD regime edge batching.
Increase edge batching factor and POST hold to reduce TPOT (tp=0).
No changes for other WTPs."""
import subprocess, os, hashlib
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\candidate_max.cpp"
OUT = r"C:\Users\hp\src\edge-cloud-scheduler"
BIN = os.path.expandvars(r"%LOCALAPPDATA%\Temp\ecs-bin")
src = open(SRC, encoding="utf-8").read()

# Bulk factor is a compile-time constant; we can't change it at runtime.
# Workaround: gate the edge hold time to zero for WTP==0 (force batching).
# Change PUBLIC_TDR_BULK_FACTOR usage via a runtime multiplier.
# Simpler: lower the edge POST hold for WTP==0 (POST_HOLD_WTP currently 0.3)
# We can override the post-hold check by forcing holdStart to be true.
#
# Instead: modify the edge POST dispatch gate to allow larger batches when WTP==0.
# The gate is `if (POST_HOLD_WTP <= WTP)` etc. Let's lower the threshold for WTP==0.
#
# We'll patch the edge dispatch decision: if wEq(WTP,0), force batch size up to 8.
# We'll do it by changing the `publicTdrMode` for WTP==0 only to enable batching.
# Easiest: add WTP==0 to publicTdrMode (currently .05/.15/.25/.30/.45)
# That will turn on the public TDR batching machinery for #3.
#
# publicTdrMode is used for TDR chain ordering and bulk factor.
decl = "     const bool publicTdrMode = wEq(WTP, .05) || wEq(WTP, .15) || wEq(WTP, .25) || wEq(WTP, .30) || wEq(WTP, .45);"
assert decl in src
src = src.replace(decl, decl.replace(");", " || wEq(WTP, 0.0);"), 1)

p = os.path.join(OUT, "v3_edgebatch.cpp")
open(p, "w", encoding="utf-8").write(src)
exe = os.path.join(BIN, "v3_edgebatch.exe")
r = subprocess.run(["g++","-O2","-std=c++17","-o",exe,p], capture_output=True, text=True)
print("v3_edgebatch build:", "OK" if r.returncode==0 else f"FAIL {r.stderr[-300:]}", "hash", hashlib.sha256(src.encode()).hexdigest()[:12])

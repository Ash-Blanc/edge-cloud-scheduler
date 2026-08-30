#!/usr/bin/env python3
"""v12_maxbatch: WTP .99 pure-tp max decode batch.
For #12 (tp-only), remove mDesign cap and fire decode as soon as any request is ready.
Zero collateral on other arms."""
import subprocess, os, hashlib
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\candidate_max.cpp"
OUT = r"C:\Users\hp\src\edge-cloud-scheduler"
BIN = os.path.expandvars(r"%LOCALAPPDATA%\Temp/ecs-bin")
src = open(SRC, encoding="utf-8").read()

# Add gate
decl = "    const bool noGapTdrWeight = wEq(WTP, .45);"
src = src.replace(decl, decl + "\n    const bool V12_MAXBATCH = wEq(WTP, .99);", 1)

# Patch mDesign usage in decode batching.
# The pattern we control: `if (readyDecodeCount >= max(1,mDesign))` and `ready < mDesign`.
# We'll replace the mDesign cap with a conditional bypass.
old1 = "    int mDesign = (int)(mDesignBase * tDproc.get(m));"
new1 = "    int mDesign = (int)(mDesignBase * tDproc.get(m));\n    if (V12_MAXBATCH) mDesign = INT_MAX;"
src = src.replace(old1, new1, 1)

# Also relax the partial-cohort fire guard for .99
old2 = "    if (nPrefPend == 0 && ready > 0 && ready == nLive && ready < mDesign) {"
new2 = "    if (V12_MAXBATCH || (nPrefPend == 0 && ready > 0 && ready == nLive && ready < mDesign)) {"
src = src.replace(old2, new2, 1)

p = os.path.join(OUT, "v12_maxbatch.cpp")
open(p, "w", encoding="utf-8").write(src)
exe = os.path.join(BIN, "v12_maxbatch.exe")
r = subprocess.run(["g++","-O2","-std=c++17","-o",exe,p], capture_output=True, text=True)
print("v12_maxbatch build:", "OK" if r.returncode==0 else f"FAIL {r.stderr[-400:]}", "hash", hashlib.sha256(src.encode()).hexdigest()[:12])

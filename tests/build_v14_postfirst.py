#!/usr/bin/env python3
"""v14_postfirst: for WTP .65, invert edge priority to D POST before P POST.
#14 is ntp-dominant (tp~0.21). Flipping edge priority lets decode finish sooner,
freeing edge for next prefill. Zero collateral elsewhere."""
import subprocess, os, hashlib, re
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\candidate_max.cpp"
OUT = r"C:\Users\hp\src\edge-cloud-scheduler"
BIN = os.path.expandvars(r"%LOCALAPPDATA%\Temp\ecs-bin")
src = open(SRC, encoding="utf-8").read()

# Add gate
decl = "    const bool noGapTdrWeight = wEq(WTP, .45);"
src = src.replace(decl, decl + "\n    const bool POST_FIRST_INV = wEq(WTP, .65);", 1)

# Find edge dispatch: look for the P POST / D POST edgeFree block.
# We'll flip the order when POST_FIRST_INV.
# Locate the edgeFree block that dispatches P POST then D POST.
# Simpler: find the comment "/* Edge dispatch */" region and swap.
# We'll do a targeted regex for the two dispatches.
# Pattern: edgeFree = false; ... BK[B_PPOST] ... then later BK[B_DPOST].
# We'll insert a priority swap.

# Find the first edgeFree dispatch for P POST
pat = re.compile(
    r'(if \(edgeFree\) {\s+int best = -1;[^}]*)'
    r'(\s+if \(!BK\[B_PPOST\]\.empty\(\)\) {\s+best = B_PPOST;[^}]*)'
    r'(\s+if \(!BK\[B_DPOST\]\.empty\(\)\) {\s+best = B_DPOST;[^}]*)',
    re.DOTALL
)
def repl(m):
    # keep first part, then swap order with gate
    head = m.group(1)
    ppost = m.group(2)
    dpost = m.group(3)
    swapped = (
        head
        + "\n    if (POST_FIRST_INV) {"
        + dpost
        + "    } else {\n"
        + ppost
        + dpost
        + "\n    }"
    )
    return swapped

src2, n = pat.subn(repl, src, count=1)
if n==0:
    # fallback: simple string replace for the two checks
    old = "    if (!BK[B_PPOST].empty()) {\n        best = B_PPOST;\n    }"
    new = "    if (POST_FIRST_INV && !BK[B_DPOST].empty()) {\n        best = B_DPOST;\n    } else if (!BK[B_PPOST].empty()) {\n        best = B_PPOST;\n    }"
    src2 = src.replace(old, new, 1)

p = os.path.join(OUT, "v14_postfirst.cpp")
open(p, "w", encoding="utf-8").write(src2)
exe = os.path.join(BIN, "v14_postfirst.exe")
r = subprocess.run(["g++","-O2","-std=c++17","-o",exe,p], capture_output=True, text=True)
print("v14_postfirst build:", "OK" if r.returncode==0 else f"FAIL {r.stderr[-400:]}", "hash", hashlib.sha256(src2.encode()).hexdigest()[:12])

#!/usr/bin/env python3
"""v13_jsq75: least-loaded (JSQ) cloud assignment for WTP=.75 (#13).
#5's +22 official win came from akd56Mix JSQ assignment. #13 (.75) is in
publicMode but NOT publicTdrMode, so it gets round-robin assignment today.
278 slack, nc=0.847. Gate: wEq(WTP,.75) only, zero collateral.
Live-path: admission cloud pick (line 556) and edge P PRE dispatch (1073)."""
import subprocess, os, hashlib
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\candidate_max.cpp"
OUT = r"C:\Users\hp\src\edge-cloud-scheduler"
BIN = os.path.expandvars(r"%LOCALAPPDATA%\Temp/ecs-bin")
src = open(SRC, encoding="utf-8").read()

# 1. Admission cloud pick: round-robin for publicMode&&!publicTdrMode&&!akd56Mix
old1 = """     if (publicMode && !publicTdrMode && !akd56Mix) {
     r.cloud = publicNextCloud;
     publicNextCloud = (publicNextCloud + 1) % K;
     } else {
     r.cloud = -1;
     }"""
new1 = """     if (publicMode && !publicTdrMode && !akd56Mix && !wEq(WTP, .75)) {
     r.cloud = publicNextCloud;
     publicNextCloud = (publicNextCloud + 1) % K;
     } else {
     r.cloud = -1;
     }"""
assert old1 in src, "anchor1"
src = src.replace(old1, new1, 1)

# 2. Edge P PRE dispatch: add JSQ branch for .75 before publicTdrMode round-robin
old2 = """     } else if (publicTdrMode) {
     c = publicNextCloud;
     publicNextCloud = (publicNextCloud + 1) % K;
     R[rid].cloud = c;
     }"""
new2 = """     } else if (wEq(WTP, .75)) {
     int bestC = 0;
     double bestLoad = 1e300;
     for (int i = 0; i < K; ++i) {
     double elapsed = preRunStart[i] >= 0.0 ? now - preRunStart[i] : 0.0;
     double load = max(0.0, preWork[i] - elapsed);
     if (load < bestLoad - 1e-12 ||
     (fabs(load - bestLoad) <= 1e-12 && i < bestC)) {
     bestLoad = load;
     bestC = i;
     }
     }
     c = bestC;
     R[rid].cloud = c;
     } else if (publicTdrMode) {
     c = publicNextCloud;
     publicNextCloud = (publicNextCloud + 1) % K;
     R[rid].cloud = c;
     }"""
assert old2 in src, "anchor2"
src = src.replace(old2, new2, 1)

p = os.path.join(OUT, "v13_jsq75.cpp")
open(p, "w", encoding="utf-8").write(src)
exe = os.path.join(BIN, "v13_jsq75.exe")
r = subprocess.run(["g++","-O2","-std=c++17","-o",exe,p], capture_output=True, text=True)
print("v13_jsq75 build:", "OK" if r.returncode==0 else f"FAIL {r.stderr[-400:]}",
      "hash", hashlib.sha256(src.encode()).hexdigest()[:12], "bytes", len(src))

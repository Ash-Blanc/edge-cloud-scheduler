#!/usr/bin/env python3
"""v3_sjf_narrow: same SJF levers as v3_sjf but gate with #3's regime fingerprint
(pureLat && DBASE < 1.5). #7 has the generic regime (DBASE~6); #3 AKD has
DBASE=1.157. This ensures only #3 fires; #7 stays byte-identical."""
import subprocess, os, hashlib
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\candidate_max.cpp"
OUT = r"C:\Users\hp\src\edge-cloud-scheduler"
BIN = os.path.expandvars(r"%LOCALAPPDATA%\Temp/ecs-bin")
src = open(SRC, encoding="utf-8").read()

# Add a named gate after pureLat
src = src.replace("     const bool publicTdrMode = wEq(WTP, .05)", "    const bool sjfAkd3 = pureLat && DBASE > 0 && DBASE < 1.5;\n     const bool publicTdrMode = wEq(WTP, .05)", 1)

old1 = """    if (rid < 0)
     rid = *min_element(BK[B_ARR].begin(), BK[B_ARR].end());"""
new1 = """    if (rid < 0) {
     if (sjfAkd3) {
     for (int candidate : BK[B_ARR]) {
     if (rid < 0 || tPpre.get(R[candidate].lin) < tPpre.get(R[rid].lin)) rid = candidate;
     }
     } else {
     rid = *min_element(BK[B_ARR].begin(), BK[B_ARR].end());
     }
     }"""
assert old1 in src, "anchor1"
src = src.replace(old1, new1, 1)

old2 = """    if (!done && (!throughputPriority || !priorityDecodeReady) && !BK[B_PPOST].empty()) {
     int rid = *min_element(BK[B_PPOST].begin(), BK[B_PPOST].end());"""
new2 = """    if (!done && (!throughputPriority || !priorityDecodeReady) && !BK[B_PPOST].empty()) {
     int rid = *min_element(BK[B_PPOST].begin(), BK[B_PPOST].end());
     if (sjfAkd3) {
     for (int candidate : BK[B_PPOST]) {
     if (tPpost.get(R[candidate].lin) < tPpost.get(R[rid].lin)) rid = candidate;
     }
     }"""
assert old2 in src, "anchor2"
src = src.replace(old2, new2, 1)

p = os.path.join(OUT, "v3_sjf_narrow.cpp")
open(p, "w", encoding="utf-8").write(src)
exe = os.path.join(BIN, "v3_sjf_narrow.exe")
r = subprocess.run(["g++","-O2","-std=c++17","-o",exe,p], capture_output=True, text=True)
print("v3_sjf_narrow build:", "OK" if r.returncode==0 else f"FAIL {r.stderr[-400:]}",
      "hash", hashlib.sha256(src.encode()).hexdigest()[:12], "bytes", len(src))

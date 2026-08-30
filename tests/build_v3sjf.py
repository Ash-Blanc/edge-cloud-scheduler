#!/usr/bin/env python3
"""v3_sjf: SJF ordering on the LIVE publicMode path for #3 (pureLat).
#3's dominant loss is TDR (50.6% excess vs TPOT 27.9%). The scheduler admits
new prefills and P POSTs in min-rid order (FIFO). Official FIFO/SJF gap=1.55
=> SJF admission should cut TDR ~859 (under SLO1 -> ex1=0 -> ~+250 pts).
Two changes, both gated to pureLat only:
 1. admission from B_ARR: pick min tPpre (SJF) instead of min rid
 2. P POST pick: min tPpost (SJF) instead of min rid"""
import subprocess, os, hashlib
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\candidate_max.cpp"
OUT = r"C:\Users\hp\src\edge-cloud-scheduler"
BIN = os.path.expandvars(r"%LOCALAPPDATA%\Temp/ecs-bin")
src = open(SRC, encoding="utf-8").read()

# 1. admission order: line 1039-1040
old1 = """    if (rid < 0)
     rid = *min_element(BK[B_ARR].begin(), BK[B_ARR].end());"""
new1 = """    if (rid < 0) {
     if (pureLat) {
     for (int candidate : BK[B_ARR]) {
     if (rid < 0 || tPpre.get(R[candidate].lin) < tPpre.get(R[rid].lin)) rid = candidate;
     }
     } else {
     rid = *min_element(BK[B_ARR].begin(), BK[B_ARR].end());
     }
     }"""
assert old1 in src, "anchor1"
src = src.replace(old1, new1, 1)

# 2. P POST order: line 990
old2 = """    if (!done && (!throughputPriority || !priorityDecodeReady) && !BK[B_PPOST].empty()) {
     int rid = *min_element(BK[B_PPOST].begin(), BK[B_PPOST].end());"""
new2 = """    if (!done && (!throughputPriority || !priorityDecodeReady) && !BK[B_PPOST].empty()) {
     int rid = *min_element(BK[B_PPOST].begin(), BK[B_PPOST].end());
     if (pureLat) {
     for (int candidate : BK[B_PPOST]) {
     if (tPpost.get(R[candidate].lin) < tPpost.get(R[rid].lin)) rid = candidate;
     }
     }"""
assert old2 in src, "anchor2"
src = src.replace(old2, new2, 1)

p = os.path.join(OUT, "v3_sjf.cpp")
open(p, "w", encoding="utf-8").write(src)
exe = os.path.join(BIN, "v3_sjf.exe")
r = subprocess.run(["g++","-O2","-std=c++17","-o",exe,p], capture_output=True, text=True)
print("v3_sjf build:", "OK" if r.returncode==0 else f"FAIL {r.stderr[-400:]}",
      "hash", hashlib.sha256(src.encode()).hexdigest()[:12], "bytes", len(src))

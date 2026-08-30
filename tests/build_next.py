#!/usr/bin/env python3
"""Combine the two clean verified-positive structural levers, gated disjointly:
  - partial D POST on .90 (v6_partial)   -> #6
  - partial D POST on .80 (v56_partial)  -> #5
Both share the same partial-release machinery; enable for .80||.90.
#3 pureLat partial was inert on recon -> skip (avoid risk).
This is the next submission after the 16128.43 base."""
import subprocess, os, hashlib
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\candidate_max.cpp"
OUT = r"C:\Users\hp\src\edge-cloud-scheduler"
BIN = os.path.expandvars(r"%LOCALAPPDATA%\Temp\ecs-bin")
base = open(SRC, encoding="utf-8").read()

OLD = """     bool batchReady = publicBatchActive;
     if (batchReady) {
     for (int rid : publicBatch) {
     if (R[rid].st != ST_DPOST_READY) {
     batchReady = false;
     break;
     }
     }
     }"""
NEW = """     bool batchReady = publicBatchActive;
     if (batchReady && PARTIAL_DPOST) {
     batch.clear();
     for (int rid : publicBatch) if (R[rid].st == ST_DPOST_READY) batch.push_back(rid);
     if (batch.empty()) batchReady = false;
     } else if (batchReady) {
     for (int rid : publicBatch) {
     if (R[rid].st != ST_DPOST_READY) {
     batchReady = false;
     break;
     }
     }
     }"""
OLD2 = """     auto dispatchPublicPost = [&]() {
     as("E D POST -1 ");
     ai((long long)publicBatch.size());
     for (int rid : publicBatch) {
     ac(' ');
     ai(rid);
     setSt(rid, ST_DPOST_RUN);
     bmove(rid, -1);
     }
     ac('\\n');
     edgeFree = false;
     running++;
     nAssigned++;
     publicBatch.clear();
     publicBatchActive = false;
     done = true;
     };"""
NEW2 = """     auto dispatchPublicPost = [&]() {
     if (PARTIAL_DPOST) {
     as("E D POST -1 ");
     ai((long long)batch.size());
     vector<int> rest;
     for (int rid : publicBatch) {
     if (R[rid].st == ST_DPOST_READY) { ac(' '); ai(rid); setSt(rid, ST_DPOST_RUN); bmove(rid, -1); }
     else rest.push_back(rid);
     }
     ac('\\n');
     publicBatch = rest;
     publicBatchActive = !rest.empty();
     } else {
     as("E D POST -1 ");
     ai((long long)publicBatch.size());
     for (int rid : publicBatch) {
     ac(' ');
     ai(rid);
     setSt(rid, ST_DPOST_RUN);
     bmove(rid, -1);
     }
     ac('\\n');
     publicBatch.clear();
     publicBatchActive = false;
     }
     edgeFree = false;
     running++;
     nAssigned++;
     done = true;
     };"""

src = base
decl = "     const bool noGapTdrWeight = wEq(WTP, .45);"
assert decl in src and OLD in src and OLD2 in src
src = src.replace(decl, decl + "\n     const bool PARTIAL_DPOST = wEq(WTP, .80) || wEq(WTP, .90);", 1)
src = src.replace(OLD, NEW, 1)
src = src.replace(OLD2, NEW2, 1)
p = os.path.join(OUT, "v_next.cpp")
open(p, "w", encoding="utf-8").write(src)
exe = os.path.join(BIN, "v_next.exe")
r = subprocess.run(["g++","-O2","-std=c++17","-o",exe,p], capture_output=True, text=True)
print("v_next build:", "OK" if r.returncode==0 else f"FAIL {r.stderr[-300:]}", "hash", hashlib.sha256(src.encode()).hexdigest()[:12])

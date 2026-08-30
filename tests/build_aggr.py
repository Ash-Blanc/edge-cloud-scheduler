#!/usr/bin/env python3
"""AGGRESSIVE stacked variant: combine all correctness-safe positive levers.
  1. partial D POST on .80/.90/#3-pureLat/#14-.65 (overlap decode output)
  2. .90: D PROC before P PROC (keep short decode flowing ahead of long prefill)
  3. .65: drop SLO2 decode cap (bigger cohorts -> throughput)
All gates disjoint by WTP; none touch the publicBatch overwrite (no deadlock)."""
import subprocess, os, hashlib
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\candidate_max.cpp"
OUT = r"C:\Users\hp\src\edge-cloud-scheduler"
BIN = os.path.expandvars(r"%LOCALAPPDATA%\Temp\ecs-bin")
src = open(SRC, encoding="utf-8").read()

# --- 1. partial D POST machinery, gated broadly: .80/.90/.65/pureLat ---
decl = "     const bool noGapTdrWeight = wEq(WTP, .45);"
assert decl in src
src = src.replace(decl, decl +
  "\n     const bool PARTIAL_DPOST = wEq(WTP, .80) || wEq(WTP, .90) || wEq(WTP, .65) || pureLat;", 1)

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
assert OLD in src; src = src.replace(OLD, NEW, 1)

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
assert OLD2 in src; src = src.replace(OLD2, NEW2, 1)

# --- 2. .90 D PROC before P PROC ---
OLDP = """     for (int c = 0; c < K; ++c) {
     if (!cloudFree[c]) continue;
     if (!BK[B_PPROC + c].empty()) {"""
NEWP = """     for (int c = 0; c < K; ++c) {
     if (!cloudFree[c]) continue;
     if (wEq(WTP,.90) && !BK[B_DPROC + c].empty()) {
     batch = BK[B_DPROC + c];
     sort(batch.begin(), batch.end());
     as("C"); ai(c); as(" D PROC "); ai(c); ac(' ');
     ai((long long)batch.size());
     for (int rid : batch) {
     ac(' '); ai(rid);
     if (nDecPend[c] > 0) nDecPend[c]--;
     setSt(rid, ST_DPROC_RUN); bmove(rid, -1);
     }
     ac('\\n');
     cloudFree[c] = 0; running++; decProcRun++; nAssigned++;
     continue;
     }
     if (!BK[B_PPROC + c].empty()) {"""
assert OLDP in src; src = src.replace(OLDP, NEWP, 1)

# --- 3. .65 drop SLO2 decode cap (batch-cap occurrence only) ---
OLDC = """     if (pureLat || (WC >= 0.85 && DBASE > 0 && roundT(1) <= SLO2)) {
     int capSLO2 = 1;"""
NEWC = """     if (pureLat || (WC >= 0.85 && !wEq(WTP,.65) && DBASE > 0 && roundT(1) <= SLO2)) {
     int capSLO2 = 1;"""
assert OLDC in src; src = src.replace(OLDC, NEWC, 1)

p = os.path.join(OUT, "v_aggr.cpp")
open(p, "w", encoding="utf-8").write(src)
exe = os.path.join(BIN, "v_aggr.exe")
r = subprocess.run(["g++","-O2","-std=c++17","-o",exe,p], capture_output=True, text=True)
print("v_aggr build:", "OK" if r.returncode==0 else f"FAIL {r.stderr[-300:]}", "hash", hashlib.sha256(src.encode()).hexdigest()[:12], "bytes", len(src))

#!/usr/bin/env python3
"""Correct overlap variants: partial D POST release (release ready tokens instead
of waiting for the whole batch). This overlaps decode output with the next round
WITHOUT the publicBatch overwrite deadlock. Gate to .90 (#6) and pureLat (#3)."""
import subprocess, os, hashlib

SRC = r"C:\Users\hp\src\edge-cloud-scheduler\candidate_max.cpp"
OUT = r"C:\Users\hp\src\edge-cloud-scheduler"
BIN = os.path.expandvars(r"%LOCALAPPDATA%\Temp\ecs-bin")
base = open(SRC, encoding="utf-8").read()

# Current: batchReady requires ALL publicBatch members in ST_DPOST_READY.
# Fix: release the SUBSET that is ready, keep the rest pending.
# Replace the batchReady gate + dispatchPublicPost with a partial-release version.
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

# dispatchPublicPost must release only the ready subset and keep the rest active.
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

def make(name, gate):
    src = base
    assert OLD in src and OLD2 in src, f"anchor missing {name}"
    # declare PARTIAL_DPOST near other gates
    decl = "     const bool noGapTdrWeight = wEq(WTP, .45);"
    src = src.replace(decl, decl + f"\n     const bool PARTIAL_DPOST = {gate};", 1)
    src = src.replace(OLD, NEW, 1)
    src = src.replace(OLD2, NEW2, 1)
    return src

variants = {
    "v6_partial":  make("v6_partial",  "wEq(WTP, .90)"),
    "v3_partial":  make("v3_partial",  "pureLat"),
    "v56_partial": make("v56_partial", "wEq(WTP, .90) || wEq(WTP, .80)"),
}
for name, content in variants.items():
    p = os.path.join(OUT, f"{name}.cpp")
    open(p, "w", encoding="utf-8").write(content)
    exe = os.path.join(BIN, f"{name}.exe")
    r = subprocess.run(["g++","-O2","-std=c++17","-o",exe,p], capture_output=True, text=True)
    ok = "OK" if r.returncode==0 else f"FAIL {r.stderr[-300:]}"
    print(f"{name:<12} build={ok} hash={hashlib.sha256(content.encode()).hexdigest()[:12]}")

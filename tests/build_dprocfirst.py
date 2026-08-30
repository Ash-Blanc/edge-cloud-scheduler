#!/usr/bin/env python3
"""#6 cloud-priority lever: in publicMode, when a cloud frees and has BOTH a
queued P PROC and a queued D PROC, current code does P PROC first (blocks the
short decode behind a long prefill). Probe: at .90, run D PROC first (short
decode keeps token flow going, then prefill). Decode is tiny vs prefill, so
this shouldn't hurt prefill throughput but keeps the token pipeline full."""
import subprocess, os, hashlib
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\candidate_max.cpp"
OUT = r"C:\Users\hp\src\edge-cloud-scheduler"
BIN = os.path.expandvars(r"%LOCALAPPDATA%\Temp\ecs-bin")
base = open(SRC, encoding="utf-8").read()

# publicMode cloud loop: P PROC branch first, then D PROC. Swap priority at .90:
# if D PROC ready AND .90, do D PROC before P PROC.
OLD = """     for (int c = 0; c < K; ++c) {
     if (!cloudFree[c]) continue;
     if (!BK[B_PPROC + c].empty()) {"""
NEW = """     for (int c = 0; c < K; ++c) {
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

def make(name, old, new):
    assert old in base
    return base.replace(old, new, 1)

v = make("v6_dprocfirst", OLD, NEW)
p = os.path.join(OUT, "v6_dprocfirst.cpp")
open(p, "w", encoding="utf-8").write(v)
exe = os.path.join(BIN, "v6_dprocfirst.exe")
r = subprocess.run(["g++","-O2","-std=c++17","-o",exe,p], capture_output=True, text=True)
print("build:", "OK" if r.returncode==0 else f"FAIL {r.stderr[-300:]}", "hash", hashlib.sha256(v.encode()).hexdigest()[:12])

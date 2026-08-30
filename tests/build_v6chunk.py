#!/usr/bin/env python3
"""v6_chunk90: .90 chunked P PROC interleave.
On .90, when a freed cloud has BOTH a queued P PROC and a queued D PROC,
do a partial P PROC chunk (first half of remaining layers) then let the
cloud free to run the pending D PROC — keeps decode tokens flowing during
prefill instead of blocking the whole batch behind one long prefill.
Chunks are strictly contiguous [ls, ls+take); TDN handler already requeues
partial chunks (line 608-618). Gate: wEq(WTP,.90) only, byte-identical else."""
import subprocess, os, hashlib
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\candidate_max.cpp"
OUT = r"C:\Users\hp\src\edge-cloud-scheduler"
BIN = os.path.expandvars(r"%LOCALAPPDATA%\Temp/ecs-bin")
src = open(SRC, encoding="utf-8").read()

# publicMode cloud loop (line ~1150): whole-chunk P PROC dispatch.
old = """     if (!BK[B_PPROC + c].empty()) {
     int rid = BK[B_PPROC + c][0];
     for (int candidate : BK[B_PPROC + c]) {
     if (tPproc.get(R[candidate].lin) < tPproc.get(R[rid].lin))
     rid = candidate;
     }
     Req& r = R[rid];
     as("C");
     ai(c);
     as(" P PROC 0 ");
     ai(LAYERS);
     ac(' ');
     ai(c);
     ac(' ');
     ai(rid);
     ac('\\n');
     r.next_ls = LAYERS;
     nPre[c]--;
     nDec[c]++;
     setSt(rid, ST_PPROC_RUN);
     bmove(rid, -1);
     cloudFree[c] = 0;
     preRunStart[c] = now;
     running++;
     nAssigned++;
     continue;
     }"""
new = """     if (!BK[B_PPROC + c].empty()) {
     int rid = BK[B_PPROC + c][0];
     for (int candidate : BK[B_PPROC + c]) {
     if (tPproc.get(R[candidate].lin) < tPproc.get(R[rid].lin))
     rid = candidate;
     }
     Req& r = R[rid];
     int ls = r.next_ls, remain = LAYERS - ls, take = remain;
     if (wEq(WTP, .90) && remain > 1 && !BK[B_DPROC + c].empty()) {
     take = (remain + 1) / 2;
     }
     int le = ls + take;
     as("C");
     ai(c);
     as(" P PROC ");
     ai(ls);
     ac(' ');
     ai(le);
     ac(' ');
     ai(c);
     ac(' ');
     ai(rid);
     ac('\\n');
     r.next_ls = le;
     if (le >= LAYERS) {
     nPre[c]--;
     nDec[c]++;
     }
     setSt(rid, ST_PPROC_RUN);
     bmove(rid, -1);
     cloudFree[c] = 0;
     preRunStart[c] = now;
     running++;
     nAssigned++;
     continue;
     }"""
assert old in src, "anchor missing"
src = src.replace(old, new, 1)

p = os.path.join(OUT, "v6_chunk90.cpp")
open(p, "w", encoding="utf-8").write(src)
exe = os.path.join(BIN, "v6_chunk90.exe")
r = subprocess.run(["g++","-O2","-std=c++17","-o",exe,p], capture_output=True, text=True)
print("v6_chunk90 build:", "OK" if r.returncode==0 else f"FAIL {r.stderr[-400:]}",
      "hash", hashlib.sha256(src.encode()).hexdigest()[:12], "bytes", len(src))

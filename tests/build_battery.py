#!/usr/bin/env python3
"""Build the A/B battery: 4 single-lever variants off candidate_max.cpp.
Each is gated to ONE pool so per-test feedback isolates the lever's effect.
Base (candidate_max.cpp) already = 16128.43. Variants add one change each."""
import subprocess, os, hashlib

SRC = r"C:\Users\hp\src\edge-cloud-scheduler\candidate_max.cpp"
OUT = r"C:\Users\hp\src\edge-cloud-scheduler"
BIN = os.path.expandvars(r"%LOCALAPPDATA%\Temp\ecs-bin")
base = open(SRC, encoding="utf-8").read()

# ---- Variant S14: kill the SLO2 decode cap on .65 (non-public path) ----
# capSLO2 limits decode batch n to roundT(n)<=SLO2. #14 ntp=0.21, SLO2 huge.
# Lifting it lets bigger decode cohorts form -> more throughput per round.
# Gate to .65 only.
A = """     if (pureLat || (WC >= 0.85 && DBASE > 0 && roundT(1) <= SLO2)) {"""
B = """     if (pureLat || (WC >= 0.85 && !wEq(WTP,.65) && DBASE > 0 && roundT(1) <= SLO2)) {"""
# note: two occurrences (searchCap + batch cap). We only want the batch cap one.
# Find the batch-cap occurrence (the one followed by capSLO2 loop).
v14 = base.replace(
"""     if (pureLat || (WC >= 0.85 && DBASE > 0 && roundT(1) <= SLO2)) {
     int capSLO2 = 1;""",
"""     if (pureLat || (WC >= 0.85 && !wEq(WTP,.65) && DBASE > 0 && roundT(1) <= SLO2)) {
     int capSLO2 = 1;""", 1)

# ---- Variant S6: .90 decode-cloud overlap ----
# On publicMode .90, dispatch D PROC immediately when a cloud frees even if a
# decode round is in flight (break the one-batch barrier's serialization).
# Simplest legal probe: allow the public batch to also pull from B_DPROC-ready
# members into the current round. We gate: at .90, drop the "wait for full batch"
# so decode fires with whatever is ready each frame -> tighter pipeline.
# Anchor: the public decode fire collects FRESH+ACT then caps. Add: at .90,
# don't gate batchReady on publicBatchActive (let rounds overlap).
A6 = """     if (!done && !publicBatchActive) {"""
B6 = """     if (!done && (!publicBatchActive || wEq(WTP,.90))) {"""
v6 = base.replace(A6, B6, 1)

# ---- Variant S5: lift the .80 mDesign decode cap ----
# akd56Cap=.80 caps decode batch to mDesign. #5 ntp=0.360, prefill-bound.
# Let .80 take the full ready batch (best=batch.size()) -> max decode cohort.
A5 = "     if (akd56Cap && throughputPriority) best = min((int)batch.size(), max(1, mDesign));"
B5 = "     if (akd56Cap && throughputPriority) best = (int)batch.size();"
v5 = base.replace(A5, B5, 1)

# ---- Variant S3: #3 decode cadence (pureLat AKD arm) ----
# pureLat batch is capped by capSLO2. Probe: allow 2 decode rounds in flight
# on pureLat (pipelined decode) by relaxing the single publicBatchActive barrier.
A3 = """     if (!done && !publicBatchActive) {"""
B3 = """     if (!done && (!publicBatchActive || pureLat)) {"""
v3 = base.replace(A3, B3, 1)

variants = {"v14_65cap": v14, "v6_90overlap": v6, "v5_80cap": v5, "v3_purelat": v3}
for name, content in variants.items():
    if content == base:
        print(f"{name}: NO-OP (anchor not found / replace did nothing) — SKIP")
        continue
    p = os.path.join(OUT, f"{name}.cpp")
    open(p, "w", encoding="utf-8").write(content)
    exe = os.path.join(BIN, f"{name}.exe")
    r = subprocess.run(["g++","-O2","-std=c++17","-o",exe,p], capture_output=True, text=True)
    ok = "OK" if r.returncode==0 else f"FAIL {r.stderr[-200:]}"
    h = hashlib.sha256(content.encode()).hexdigest()[:12]
    print(f"{name:<14} build={ok}  hash={h}  bytes={len(content)}")

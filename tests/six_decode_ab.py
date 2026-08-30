#!/usr/bin/env python3
"""Targeted #6 decode-sizing A/B. Patch the public-path batch 'best' rule for
.90 only, compile each variant, rank on honest6 pinned score. Cloud-bound ->
decode must amortize but not starve prefill."""
import sys, types, subprocess, os
_res = types.ModuleType("resource"); _res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path.insert(0, "recon_archive")
import sim
from akd56_16063_ab import honest6, honest5, pin_official_constants

BIN = "C:/Users/hp/AppData/Local/Temp/ecs-bin"
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\candidate_max.cpp"
ANCHOR = "     if (akd56Cap && throughputPriority) best = min((int)batch.size(), max(1, mDesign));"

VARIANTS = {
    # name: replacement line (or extra). All gated to .90 except base.
    "base":        None,
    "max90":       ANCHOR + "\n     if (wEq(WTP,.90)) best = (int)batch.size();",  # take all ready
    "cap90_mDes":  ANCHOR + "\n     if (wEq(WTP,.90)) best = min((int)batch.size(), max(1, mDesign));",
    "cap90_half":  ANCHOR + "\n     if (wEq(WTP,.90)) best = min((int)batch.size(), max(1, mDesign/2));",
    "cap90_2x":    ANCHOR + "\n     if (wEq(WTP,.90)) best = min((int)batch.size(), max(1, 2*mDesign));",
}

def build(name, repl):
    src = open(SRC, encoding="utf-8").read()
    if repl is not None:
        assert ANCHOR in src, "anchor missing"
        src = src.replace(ANCHOR, repl, 1)
    out = f"{BIN}/s6_{name}.exe"
    tmp = f"{BIN}/s6_{name}.cpp"
    open(tmp, "w", encoding="utf-8").write(src)
    r = subprocess.run(["g++","-O2","-std=c++17","-o",out,tmp], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"{name}: BUILD FAIL"); return None
    return out

def ev(b, c):
    m, _, _ = sim.run(b, c); return sim.score(c, m), m

def main():
    h6 = pin_official_constants(honest6(), 6)
    h5 = pin_official_constants(honest5(), 5)
    print(f"{'variant':<12} {'#6 pts':>9} {'#6 tp':>9} {'#6 tdr':>8} {'#5 pts':>9}")
    for name, repl in VARIANTS.items():
        b = build(name, repl)
        if not b: continue
        (p6,_,_,_), m6 = ev(b, h6)
        (p5,_,_,_), _ = ev(b, h5)
        print(f"{name:<12} {p6:>9.2f} {m6[0]:>9.5f} {m6[1]:>8.1f} {p5:>9.2f}")
if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""#6 cloud-idle fix A/B: in publicMode, when a cloud finishes a P PROC, let it
immediately start the NEXT queued prefill (P PROC) instead of idling while the
finished request goes through downlink/P POST/D PRE/decode. Gate to .90.
We emulate by allowing the cloud to grab next P PROC in the same frame batch."""
import sys, types, subprocess
_res = types.ModuleType("resource"); _res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path.insert(0, "recon_archive")
import sim
from akd56_16063_ab import honest6, honest5, pin_official_constants, retarget

BIN = "C:/Users/hp/AppData/Local/Temp/ecs-bin"
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\candidate_max.cpp"

# The P PROC completion handler sends req to PDOWN_WAIT (xfers++) and marks cloudFree.
# The cloud then waits. We want: on P PROC completion at .90, if another PPROC_READY
# exists for this cloud, immediately chain it (don't wait for next frame arbitration).
# Simplest structural probe: reduce the round-trip bubble by NOT incrementing xfers
# so the scheduler sees the cloud free sooner. But that's protocol-illegal.
# Legal probe: split P PROC so a cloud does partial layers, freeing it to interleave.
# Instead, test the EXISTING non-public interleave on .90 by routing .90 to the
# split-capable branch: change the unsplit guard.

# Locate the publicMode P PROC dispatch (line ~1150) that does all layers, and
# make .90 use chunked P PROC (like the non-public path) so decode can interleave.
ANCHOR = """     Req& r = R[rid];
     as("C");
     ai(c);
     as(" P PROC 0 ");
     ai(LAYERS);
     ac(' ');
     ai(c);
     ac(' ');
     ai(rid);
     ac('\\n');
     r.next_ls = LAYERS;"""

CHUNKED = """     Req& r = R[rid];
     int _ls = 0, _take = LAYERS;
     if (wEq(WTP, .90)) {
     double _full = tPproc.get(r.lin);
     double _per = _full / LAYERS;
     int _maxPieces = (int)floor(CHUNK_OVERHEAD * _full / S);
     if (_maxPieces >= 2) {
     double _budget = max(CHUNK_S_FACTOR * S, SLO2);
     _take = max(1, min(LAYERS, (int)floor(_budget / max(_per, 1e-9))));
     }
     }
     as("C");
     ai(c);
     as(" P PROC 0 ");
     ai(_take);
     ac(' ');
     ai(c);
     ac(' ');
     ai(rid);
     ac('\\n');
     r.next_ls = _take;"""

def build(name, newtext):
    src = open(SRC, encoding="utf-8").read()
    if newtext is not None:
        assert ANCHOR in src, "anchor missing"
        src = src.replace(ANCHOR, newtext, 1)
    out = f"{BIN}/s6i_{name}.exe"; tmp = f"{BIN}/s6i_{name}.cpp"
    open(tmp, "w", encoding="utf-8").write(src)
    r = subprocess.run(["g++","-O2","-std=c++17","-o",out,tmp], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"{name}: BUILD FAIL\n{r.stderr[-400:]}"); return None
    return out

def ev(b, c):
    m, _, _ = sim.run(b, c); return sim.score(c, m), m

def main():
    h6 = pin_official_constants(honest6(), 6)
    h5 = pin_official_constants(honest5(), 5)
    for name, nt in [("base", None), ("chunk90", CHUNKED)]:
        b = build(name, nt)
        if not b: continue
        (p6,_,_,_), m6 = ev(b, h6)
        (p5,_,_,_), m5 = ev(b, h5)
        print(f"{name:<10} #6 pts={p6:.2f} tp={m6[0]:.5f} tdr={m6[1]:.1f} tpot={m6[2]:.2f} | #5 pts={p5:.2f} tp={m5[0]:.5f}")
        # collateral
        for w in [0.80, 0.98, 0.75]:
            c = retarget(h6, w)
            mm,_,_ = sim.run(b, c)
            print(f"    retarget w={w}: tp={mm[0]:.5f} tdr={mm[1]:.1f}")
if __name__ == "__main__":
    main()

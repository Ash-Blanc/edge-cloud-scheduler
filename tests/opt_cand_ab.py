#!/usr/bin/env python3
"""A/B opt_cand vs base across the weight arms the candidate widened."""
import sys, types, math
_res = types.ModuleType("resource"); _res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
import sim

BIN = "C:/Users/hp/AppData/Local/Temp/ecs-bin"
REF = BIN + "/ref_sequential.exe"
BASE = BIN + "/base.exe"
CAND = BIN + "/opt_cand.exe"

def mk(name, wtp, seed=100, K=4, R=40, span=50.0, lat=8.0, bw=8.0,
       lout_hi=64, lin_hi=1024):
    return sim.make_case(name=name, seed=seed, K=K, R=R, layers=24, span=span,
                         wtp=wtp, a1=0.5, a2=0.5, kind="gpu",
                         lat=lat, bw=bw, lout_hi=lout_hi, lin_hi=lin_hi)

ARMS = [0.05, 0.15, 0.25, 0.30, 0.80, 0.90, 0.98]

def pts(case, m):
    tp, tdr, tpot = m
    ex1 = max(0.0, (tdr - case.slo1) / case.slo1)
    ex2 = max(0.0, (tpot - case.slo2) / case.slo2)
    dist = math.hypot(ex1, ex2)
    ntp = (tp - case.tp_base) / (case.tp_ub - case.tp_base) if case.tp_ub > case.tp_base else 0.0
    ntp = max(0.0, min(1.0, ntp))
    nc = max(0.0, 1.0 - dist / case.dist_base) if case.dist_base > 0 else (1.0 if dist == 0 else 0.0)
    return 1000.0 * (case.wtp * ntp + case.wc * nc)

def main():
    cases = []
    for w in ARMS:
        for tag, kw in [("a", {}), ("b", {"seed": 7, "K": 8, "R": 60, "lout_hi": 64}),
                        ("c", {"seed": 21, "K": 2, "R": 30, "lat": 14.0, "lout_hi": 2})]:
            cases.append(mk(f"w{int(round(w*100))}-{tag}", w, **kw))
    for c in cases:
        sim.calibrate(c, REF)
    print(f"{'case':<10} {'wtp':>5} {'base':>9} {'cand':>9} {'dpts':>8}  verdict")
    worst = 0.0; nreg = 0; ngain = 0; nsame = 0
    for c in cases:
        mb, _, _ = sim.run(BASE, c)
        mc, _, _ = sim.run(CAND, c)
        pb, pc = pts(c, mb), pts(c, mc)
        d = pc - pb; worst = min(worst, d)
        if abs(d) < 1e-6: v = "SAME"; nsame += 1
        elif d > 0: v = "GAIN"; ngain += 1
        else: v = "REGRESS"; nreg += 1
        print(f"{c.name:<10} {c.wtp:>5.2f} {pb:>9.2f} {pc:>9.2f} {d:>8.2f}  {v}")
    print(f"\nSAME={nsame} GAIN={ngain} REGRESS={nreg}  WORST DELTA: {worst:.3f}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""A/B reconstructed 16063 vs d202b1a, and gated variants.

Honest recons (k-shrink-identical ABSOLUTE metrics of d202b1a):
  #5 seed=711 R=100 L=96 pp=165 span=15 bw=14 lat=5
     MATCHES official BEFORE tp/tdr/tpot, but gated 5d830a0b is IDENTICAL
     to d202b1a — does NOT reproduce official +0.092 tp. Thrown out as a
     ranking recon for skipP+mDesign-cap. Mechanism that does fire: same
     shape with quadratic D PRE q=3e-4 (efficiency 64 → cap 100, TDR same,
     +55% tp). That magnitude is not the official +8%.
  #6 seed=812 R=150 L=36 pp=160 span=4 bw=11 lat=4.4
     ungated 16063 IDENTICAL to d202b1a (official no-op on #6).
"""
from __future__ import annotations

import copy
import math
import random
import sys

import sim
from trace_compare import traced_run

OFFICIAL = {
    5: dict(wtp=0.80, pts=465.593, tp=1.121008, tdr=1497.256, tpot=60.081,
            ntp=0.3326, nc=0.9977, tp_base=0.022737, tp_ub=3.32417,
            slo1=309.6, slo2=45.8),
    6: dict(wtp=0.90, pts=389.543, tp=0.696236, tdr=3102.232, tpot=57.814,
            ntp=0.3226, nc=0.9921, tp_base=0.021842, tp_ub=2.11234,
            slo1=505.0, slo2=64.4),
    13: dict(wtp=0.75, pts=722.457, tp=0.026744, tdr=None, tpot=71.638),
}


def decode_table(pproc_k, dproc_k, dpre_k=1.00, dpre_s=0.008, dproc_s=0.04):
    sizes = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]
    return [
        (
            b,
            0.25 + 0.010 * b,
            pproc_k + 0.08 * b,
            0.20 + 0.005 * b,
            dpre_k + dpre_s * b,
            dproc_k + dproc_s * b,
            dpre_k + dpre_s * b,
        )
        for b in sizes
    ]


def make_case(name, wtp, **kw):
    rng = random.Random(kw["seed"])
    lins = kw["lin"]
    louts = kw["lout"]
    if isinstance(louts, int):
        louts = (louts,)
    arrivals = [
        (rng.uniform(0.0, kw["span"]), rng.choice(lins), rng.choice(louts))
        for _ in range(kw["R"])
    ]
    arrivals.sort()
    case = sim.Case(
        kw["K"], kw["S"], kw["lat"], kw["bw"], kw.get("bpt", 32768),
        kw["layers"], kw.get("slo1", 1.0), kw.get("slo2", 1.0),
        decode_table(kw["pproc"], kw["dproc"], kw.get("dpre_k", 1.00),
                     kw.get("dpre_s", 0.008), kw.get("dproc_s", 0.04)),
        arrivals, wtp, 1.0 - wtp,
    )
    case.tp_base = kw.get("tp_base", 0.05)
    case.tp_ub = kw.get("tp_ub", 3.40)
    case.dist_base = kw.get("dist_base", 12.0)
    case.name = name
    return case


def official5(**override):
    kw = dict(K=8, R=100, lout=96, lat=5.0, bw=8.0, S=2.0, layers=8,
              span=8.0, lin=(256, 512, 1024), seed=701, pproc=44, dproc=2.5,
              slo1=1500, slo2=60.2, tp_base=0.05, tp_ub=3.40, dist_base=12.0)
    kw.update(override)
    return make_case(f"official5-s{kw['seed']}", 0.80, **kw)


def official6(**override):
    kw = dict(K=8, R=150, lout=36, lat=4.4, bw=11.0, S=2.0, layers=8,
              span=4.0, lin=(512, 1024, 2048), seed=812, pproc=160, dproc=2.5,
              slo1=3200, slo2=58.0, tp_base=0.03, tp_ub=2.16, dist_base=12.0)
    kw.update(override)
    return make_case(f"official6-s{kw['seed']}", 0.90, **kw)


def honest5():
    return official5(seed=711, R=100, lout=96, pproc=165, span=15.0,
                     bw=14.0, lat=5.0)


def honest6():
    return official6(seed=812, R=150, lout=36, pproc=160, span=4.0,
                     bw=11.0, lat=4.4)


def pin_official_constants(case, test):
    o = OFFICIAL[test]
    case.wtp = o["wtp"]
    case.wc = 1.0 - o["wtp"]
    if "tp_base" in o:
        case.tp_base = o["tp_base"]
        case.tp_ub = o["tp_ub"]
        case.slo1 = o["slo1"]
        case.slo2 = o["slo2"]
        ex1 = max(0.0, (o["tdr"] - o["slo1"]) / o["slo1"])
        ex2 = max(0.0, (o["tpot"] - o["slo2"]) / o["slo2"])
        dist = math.hypot(ex1, ex2)
        case.dist_base = dist / max(1e-12, 1.0 - o["nc"])
    return case


def retarget(case, wtp):
    c = copy.deepcopy(case)
    c.wtp = wtp
    c.wc = 1.0 - wtp
    c.name = f"{case.name}-w{wtp:g}"
    return c


def summarize(label, binary, case):
    metrics, frames, sm = sim.run(binary, case)
    pts, ntp, nc, dist = sim.score(case, metrics)
    dpre = sm.stats["D PRE"]
    print(
        f"  {label:<18} pts={pts:8.2f} ntp={ntp:.4f} nc={nc:.4f} "
        f"tp={metrics[0]:.6f} tdr={metrics[1]:.3f} tpot={metrics[2]:.4f} "
        f"dpre_n={dpre[0]} dpre_g={dpre[1]/max(1,dpre[0]):.2f} frames={frames}"
    )
    return metrics, pts, ntp, nc, frames


def compare(label, case, base, cand):
    bm, bpts, bntp, bnc, _ = summarize("base", base, case)
    cm, cpts, cntp, cnc, _ = summarize("cand", cand, case)
    bt = traced_run(base, case)
    ct = traced_run(cand, case)
    same = bt[1][0] == ct[1][0]
    dtp = cm[0] - bm[0]
    print(
        f"  {label:<18} {'IDENTICAL' if same else 'DIFFERS'} "
        f"dpts={cpts-bpts:+.3f} dtp={dtp:+.6f} ({100*dtp/max(bm[0],1e-12):+.2f}%) "
        f"dtdr={cm[1]-bm[1]:+.3f} dtpot={cm[2]-bm[2]:+.4f} "
        f"dntp={cntp-bntp:+.4f} nc={cnc:.4f}"
    )
    return same, bm, cm, bpts, cpts, bnc, cnc


def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: akd56_16063_ab.py BASE CAND [CAND2=path ...]")
    base = sys.argv[1]
    cand = sys.argv[2]
    extra = []
    for arg in sys.argv[3:]:
        if "=" in arg:
            extra.append(tuple(arg.split("=", 1)))
        else:
            extra.append((arg.split("/")[-1], arg))

    cases = []
    h5 = pin_official_constants(honest5(), 5)
    h6 = pin_official_constants(honest6(), 6)
    cases.append(("#5 honest", h5))
    cases.append(("#6 honest", h6))
    cases.append(("#13-like .75 on #5 shape", retarget(h5, 0.75)))
    cases.append((".75 on #6 shape", retarget(h6, 0.75)))
    for w in (0.05, 0.15, 0.25, 0.30, 0.98, 0.99, 1.0):
        cases.append((f"#5 retarget w={w:g}", retarget(h5, w)))
        cases.append((f"#6 retarget w={w:g}", retarget(h6, w)))

    print(f"BASE={base}\nCAND={cand}")
    for label, case in cases:
        print(f"\n=== {label}  {case.name} wtp={case.wtp} ===")
        compare(label, case, base, cand)
        for name, path in extra:
            print(f"  -- vs extra {name} --")
            compare(f"{label}/{name}", case, cand if "16063" in cand else base, path)


if __name__ == "__main__":
    raise SystemExit(main())

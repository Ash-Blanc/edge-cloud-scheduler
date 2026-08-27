#!/usr/bin/env python3
"""Reconstruct official #5/#6/#13 and sweep non-pipelined AKD cohort / assignment.

Does NOT enable D POST overlap. Variants are compile-time AKD_TP_* probes
gated to w_tp in {.75, .80, .90}.

Usage:
  python3 tests/official_cohort_sweep.py BASE VARIANT [VARIANT ...]
"""
from __future__ import annotations

import math
import random
import sys

import sim

OFFICIAL = {
    5: dict(wtp=0.80, pts=465.593, tp=1.121008, tdr=1497.256, tpot=60.081,
            ntp=0.3326, nc=0.9977, tp_base=0.022737, tp_ub=3.32417,
            slo1=309.6, slo2=45.8),
    6: dict(wtp=0.90, pts=389.543, tp=0.696236, tdr=3102.232, tpot=57.814,
            ntp=0.3226, nc=0.9921, tp_base=0.021842, tp_ub=2.11234,
            slo1=505.0, slo2=64.4),
    13: dict(wtp=0.75, pts=722.457, tp=0.026744, tdr=1669.941, tpot=71.638,
             ntp=0.6810, nc=0.8468, tp_base=0.0076435, tp_ub=0.0356911,
             slo1=467.2, slo2=56.9),
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


def official5(seed=701, **override):
    kw = dict(K=8, R=100, lout=96, lat=5.0, bw=8.0, S=2.0, layers=8,
              span=8.0, lin=(256, 512, 1024), seed=seed, pproc=44, dproc=2.5,
              slo1=1500, slo2=60.2, tp_base=0.05, tp_ub=3.40, dist_base=12.0)
    kw.update(override)
    return make_case(f"official5-s{kw['seed']}", 0.80, **kw)


def official6(seed=802, **override):
    kw = dict(K=8, R=140, lout=46, lat=4.4, bw=8.0, S=2.0, layers=8,
              span=4.0, lin=(512, 1024, 2048), seed=seed, pproc=90, dproc=2.5,
              slo1=3200, slo2=58.0, tp_base=0.03, tp_ub=2.16, dist_base=12.0)
    kw.update(override)
    return make_case(f"official6-s{kw['seed']}", 0.90, **kw)


def official13(seed=1301, **override):
    kw = dict(K=4, R=80, lout=8, lat=12.0, bw=2.0, S=3.0, layers=8,
              span=20.0, lin=(128, 256, 512), seed=seed, pproc=30, dproc=8.0,
              dpre_k=2.0, dpre_s=0.02, dproc_s=0.15,
              slo1=1700, slo2=72.0, tp_base=0.008, tp_ub=0.036, dist_base=16.0)
    kw.update(override)
    return make_case(f"official13-s{kw['seed']}", 0.75, **kw)


def pin_official_constants(case, test):
    o = OFFICIAL[test]
    case.wtp = o["wtp"]
    case.wc = 1.0 - o["wtp"]
    case.tp_base = o["tp_base"]
    case.tp_ub = o["tp_ub"]
    case.slo1 = o["slo1"]
    case.slo2 = o["slo2"]
    ex1 = max(0.0, (o["tdr"] - o["slo1"]) / o["slo1"])
    ex2 = max(0.0, (o["tpot"] - o["slo2"]) / o["slo2"])
    dist = math.hypot(ex1, ex2)
    case.dist_base = dist / max(1e-12, 1.0 - o["nc"])
    return case


def ratio_err(metrics, test):
    o = OFFICIAL[test]
    tp, tdr, tpot = metrics
    keys = {
        "tp": (tp, o["tp"]),
        "tdr": (tdr, o["tdr"]),
        "tpot": (tpot, o["tpot"]),
    }
    err = 0.0
    rel = {}
    for k, (g, w) in keys.items():
        r = abs(g - w) / max(abs(w), 1e-12)
        rel[k] = r
        err += r
    return err, rel


def summarize(label, binary, case, test=None):
    metrics, frames, sm = sim.run(binary, case)
    pts, ntp, nc, dist = sim.score(case, metrics)
    extra = ""
    if test:
        err, rel = ratio_err(metrics, test)
        extra = (f" fit={err:.3f} dtp={100 * rel['tp']:+.1f}%"
                 f" dtdr={100 * rel['tdr']:+.1f}% dtpot={100 * rel['tpot']:+.1f}%")
    print(
        f"  {label:<18} pts={pts:8.2f} ntp={ntp:.3f} nc={nc:.3f} "
        f"tp={metrics[0]:.4f} tdr={metrics[1]:.1f} tpot={metrics[2]:.2f} "
        f"frames={frames} cpu={sm.cpu:.2f}s{extra}"
    )
    return metrics, pts, ntp, nc


def seed_grid(builder, test, seeds):
    out = []
    for seed in seeds:
        case = builder(seed=seed)
        pin_official_constants(case, test)
        out.append((test, case))
    return out


def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: official_cohort_sweep.py BASE VARIANT [VARIANT ...]")
    base = sys.argv[1]
    variants = sys.argv[2:]

    print("=== ratio fit of reconstructions vs official tp/tdr/tpot ===")
    recon = [
        (5, pin_official_constants(official5(), 5)),
        (6, pin_official_constants(official6(), 6)),
        (13, pin_official_constants(official13(), 13)),
    ]
    for test, case in recon:
        o = OFFICIAL[test]
        print(f"\n#{test} want tp={o['tp']:.4f} tdr={o['tdr']:.1f} tpot={o['tpot']:.2f} "
              f"ntp={o['ntp']:.3f} nc={o['nc']:.3f}")
        summarize("base", base, case, test)

    print("\n=== multi-seed A/B (pinned official scoring constants) ===")
    cases = []
    cases.extend(seed_grid(official5, 5, (701, 702, 711, 721, 731)))
    cases.extend(seed_grid(official6, 6, (802, 803, 812, 822, 832)))
    cases.extend(seed_grid(official13, 13, (1301, 1302, 1311)))
    # broader shapes at the same weights, still one-batch / no POST pipeline
    for seed, K, R, lout, lat in (
        (901, 8, 200, 64, 5.0),
        (902, 8, 80, 128, 8.0),
        (903, 4, 120, 96, 5.0),
        (904, 16, 160, 48, 3.0),
        (905, 8, 300, 32, 2.0),
    ):
        case = official5(seed=seed, K=K, R=R, lout=lout, lat=lat)
        pin_official_constants(case, 5)
        case.name = f"sat5-var-K{K}-R{R}-L{lout}-s{seed}"
        cases.append((5, case))

    by_var = {v: [] for v in variants}
    failures = 0
    for test, case in cases:
        print(f"\n{case.name}  wtp={case.wtp:.2f} K={case.K} R={len(case.arrivals)}")
        b_m, b_pts, b_ntp, b_nc = summarize("base", base, case, test)
        for var in variants:
            name = var.split("/")[-1]
            try:
                m, pts, ntp, nc = summarize(name, var, case, test)
            except Exception as e:
                print(f"  {name:<18} FAIL {e}")
                failures += 1
                continue
            dpts = pts - b_pts
            dtp = m[0] - b_m[0]
            flag = ""
            if nc + 1e-9 < 0.99 and test in (5, 6):
                flag = "  NC<0.99"
                failures += 1
            if abs(dtp) > 1e-6 or abs(dpts) > 0.05:
                flag += "  DIFFERS"
            else:
                flag += "  SAME"
            print(f"           delta pts={dpts:+8.2f} tp={dtp:+.4f} tpot={m[2] - b_m[2]:+.2f}{flag}")
            by_var[var].append((case.name, dpts, dtp, nc, b_nc))

    print("\n=== variant totals vs base ===")
    for var in variants:
        rows = by_var[var]
        if not rows:
            continue
        dpts = sum(r[1] for r in rows)
        wins = sum(1 for r in rows if r[1] > 1.0)
        losses = sum(1 for r in rows if r[1] < -1.0)
        nc_slip = sum(1 for r in rows if r[3] + 1e-9 < 0.99)
        print(f"  {var.split('/')[-1]:<18} sum_dpts={dpts:+8.1f} "
              f"wins={wins} losses={losses} nc_lt_0.99={nc_slip} n={len(rows)}")
    if failures:
        print(f"{failures} hard failure(s) (nc slip or crash)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

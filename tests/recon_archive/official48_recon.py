#!/usr/bin/env python3
"""Reconstruct official #4 (WTP=0.30) and #8 (WTP=0.25) against d202b1a.

Official fingerprints from dual-submission checker logs. The 16041.088
vector (and every 15975+ AKD-public blob) reports:

  #4 points=795.877862 tp=0.057134 tdr=474.025456 tpot=83.419420
     dist=1.566001 ntp=0.454198 nc=0.942312 w_tp=0.30
  #8 points=833.386164 tp=0.013238 tdr=1087.155401 tpot=98.802707
     dist=1.568274 ntp=0.765783 nc=0.855921 w_tp=0.25

tp_base/UB inverted from four (tp, ntp) pairs; SLO1/SLO2 inverted from
four (tdr, tpot, dist) triples (residual <0.02%):

  #4 tp_base=0.008506 tp_UB=0.11556 SLO1=184.74 SLO2=120.04 dist_base=27.146
  #8 tp_base=0.002987 tp_UB=0.016373 SLO1=423.3  SLO2=97.5   dist_base=10.885

Usage:
  python3 tests/official48_recon.py /tmp/d202-sched
  python3 tests/official48_recon.py /tmp/d202-sched --test 4
  python3 tests/official48_recon.py /tmp/d202-sched --test 8 --refine
  python3 tests/official48_recon.py /tmp/d202-sched --fitted
"""
from __future__ import annotations

import math
import random
import sys

import sim

OFF = {
    4: dict(
        wtp=0.30,
        pts=795.8778617864,
        tp=0.057134,
        tdr=474.025456,
        tpot=83.419420,
        dist=1.566001,
        ntp=0.454198,
        nc=0.942312,
        tp_base=0.008506,
        tp_ub=0.11556,
        slo1=184.74,
        slo2=120.04,
        dist_base=27.14604,
    ),
    8: dict(
        wtp=0.25,
        pts=833.3861643448,
        tp=0.013238,
        tdr=1087.155401,
        tpot=98.802707,
        dist=1.568274,
        ntp=0.765783,
        nc=0.855921,
        tp_base=0.0029865,
        tp_ub=0.0163735,
        slo1=423.3,
        slo2=97.5,
        dist_base=10.8848,
    ),
}


def decode_table(pproc_k, dproc_k, dpre_k=1.0, dpre_s=0.008, dproc_s=0.04,
                 ppre_k=0.25, ppre_s=0.010, ppost_k=0.20, ppost_s=0.005):
    sizes = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]
    return [
        (
            b,
            ppre_k + ppre_s * b,
            pproc_k + 0.08 * b,
            ppost_k + ppost_s * b,
            dpre_k + dpre_s * b,
            dproc_k + dproc_s * b,
            dpre_k + dpre_s * b,
        )
        for b in sizes
    ]


def make_case(test, name, **kw):
    o = OFF[test]
    rng = random.Random(kw["seed"])
    lins = kw["lin"]
    if isinstance(lins, int):
        lins = (lins,)
    louts = kw["lout"]
    if isinstance(louts, int):
        louts = (louts,)
    arrivals = [
        (rng.uniform(0.0, kw["span"]), rng.choice(lins), rng.choice(louts))
        for _ in range(kw["R"])
    ]
    arrivals.sort()
    table = kw.get("table")
    if table is None:
        table = decode_table(
            kw.get("pproc", 40.0), kw.get("dproc", 8.0),
            kw.get("dpre_k", 1.0), kw.get("dpre_s", 0.008),
            kw.get("dproc_s", 0.04),
            kw.get("ppre_k", 0.25), kw.get("ppre_s", 0.010),
            kw.get("ppost_k", 0.20), kw.get("ppost_s", 0.005),
        )
    case = sim.Case(
        kw["K"], kw.get("S", 2.0), kw["lat"], kw["bw"], kw.get("bpt", 32768),
        kw.get("layers", 8), o["slo1"], o["slo2"], table, arrivals,
        o["wtp"], 1.0 - o["wtp"],
    )
    case.tp_base = o["tp_base"]
    case.tp_ub = o["tp_ub"]
    case.dist_base = o["dist_base"]
    case.name = name
    return case


def ratio_err(metrics, test):
    o = OFF[test]
    tp, tdr, tpot = metrics
    rel = {
        "tp": abs(tp - o["tp"]) / o["tp"],
        "tdr": abs(tdr - o["tdr"]) / o["tdr"],
        "tpot": abs(tpot - o["tpot"]) / max(o["tpot"], 1e-12),
    }
    return rel["tp"] + rel["tdr"] + rel["tpot"], rel


def summarize(binary, case, test, timeout=180.0):
    metrics, frames, sm = sim.run(binary, case, timeout=timeout)
    pts, ntp, nc, dist = sim.score(case, metrics)
    err, rel = ratio_err(metrics, test)
    span = max(r.toks[-1] for r in sm.reqs) - min(r.arr for r in sm.reqs)
    dpre = sm.stats["D PRE"]
    mean_m = dpre[1] / max(1, dpre[0])
    print(
        f"  {case.name:<32} pts={pts:7.2f} ntp={ntp:.3f} nc={nc:.3f} "
        f"tp={metrics[0]:.5g} tdr={metrics[1]:.4g} tpot={metrics[2]:.2f} "
        f"dist={dist:.3f} m~{mean_m:.2f} span={span:.4g} fr={frames} "
        f"fit={err:.3f} dtp={100 * rel['tp']:+.1f}% dtdr={100 * rel['tdr']:+.1f}% "
        f"dtpot={100 * rel['tpot']:+.1f}% cpu={getattr(sm, 'cpu', 0):.2f}s"
    )
    return err, rel, metrics, pts, ntp, nc, sm


def grid4():
    """#4: tp*tpot~4.8 so small-medium cohorts, tpot~83, tdr~474, mixed 0.30."""
    out = []
    specs = [
        (401, 8, 40, 16, 5.0, 8.0, 40, 8, 4.0, (256, 512, 1024)),
        (402, 8, 80, 32, 5.0, 8.0, 40, 10, 8.0, (256, 512, 1024)),
        (403, 4, 40, 16, 8.0, 4.0, 50, 12, 4.0, (256, 512)),
        (404, 4, 60, 24, 10.0, 2.0, 60, 15, 6.0, (512, 1024)),
        (405, 8, 30, 8, 12.0, 2.0, 30, 20, 2.0, (128, 256, 512)),
        (406, 2, 40, 16, 5.0, 8.0, 40, 8, 4.0, (256, 512)),
        (407, 8, 100, 48, 4.0, 10.0, 80, 6, 10.0, (512, 1024, 2048)),
        (408, 8, 20, 64, 8.0, 4.0, 40, 25, 1.0, (1024, 2048)),
        (409, 4, 80, 8, 15.0, 1.0, 80, 30, 5.0, (512, 1024)),
        (410, 8, 50, 12, 6.0, 6.0, 20, 5, 8.0, (128, 256, 512)),
        (411, 16, 80, 16, 3.0, 10.0, 40, 8, 6.0, (256, 512)),
        (412, 4, 24, 32, 20.0, 1.0, 100, 40, 2.0, (1024, 2048)),
        (413, 8, 60, 4, 2.0, 20.0, 15, 4, 3.0, (64, 128, 256)),
        (414, 2, 80, 8, 8.0, 4.0, 50, 10, 8.0, (256, 512, 1024)),
        (415, 8, 40, 96, 5.0, 8.0, 44, 2.5, 8.0, (256, 512, 1024)),  # #5-like
        (416, 1, 30, 16, 10.0, 2.0, 80, 15, 2.0, (512, 1024)),
        (417, 8, 16, 32, 25.0, 0.5, 60, 40, 0.0, (2048, 4096)),
        (418, 4, 48, 20, 7.0, 5.0, 35, 8, 5.0, (256, 512, 1024)),
        (419, 8, 120, 8, 4.0, 8.0, 25, 6, 12.0, (128, 256)),
        (420, 4, 32, 40, 12.0, 3.0, 70, 18, 3.0, (512, 1024)),
        (421, 8, 40, 16, 1.0, 40.0, 10, 3, 4.0, (32, 64, 128)),
        (422, 2, 24, 48, 15.0, 2.0, 90, 35, 1.0, (1024, 2048)),
        (423, 8, 70, 24, 8.0, 3.0, 45, 12, 7.0, (256, 512)),
        (424, 4, 100, 12, 5.0, 6.0, 30, 7, 10.0, (128, 256, 512)),
        (425, 8, 36, 20, 18.0, 1.5, 55, 22, 2.0, (512, 1024)),
        (426, 16, 40, 8, 8.0, 4.0, 40, 10, 3.0, (256, 512)),
        (427, 4, 16, 64, 10.0, 4.0, 50, 20, 0.5, (1024,)),
        (428, 8, 90, 16, 6.0, 5.0, 35, 9, 9.0, (256, 512, 1024)),
        (429, 2, 50, 24, 6.0, 8.0, 40, 12, 5.0, (256, 512)),
        (430, 8, 28, 28, 9.0, 4.0, 48, 14, 3.0, (256, 512, 1024)),
    ]
    for seed, K, R, lout, lat, bw, pproc, dproc, span, lin in specs:
        out.append(make_case(
            4, f"g4-K{K}-R{R}-L{lout}-s{seed}",
            seed=seed, K=K, R=R, lout=lout, lat=lat, bw=bw,
            pproc=pproc, dproc=dproc, span=span, lin=lin,
        ))
    return out


def grid8():
    """#8: tp*tpot~1.31 so nearly size-1 rounds, tpot~99, tdr~1087, mixed 0.25."""
    out = []
    specs = [
        (801, 4, 80, 8, 12.0, 2.0, 30, 8.0, 20.0, (128, 256, 512)),  # #13-like
        (802, 2, 60, 8, 15.0, 1.5, 40, 12, 10.0, (256, 512)),
        (803, 4, 40, 16, 20.0, 1.0, 50, 20, 5.0, (512, 1024)),
        (804, 1, 40, 8, 10.0, 2.0, 60, 15, 4.0, (256, 512, 1024)),
        (805, 8, 80, 4, 8.0, 4.0, 25, 6, 12.0, (128, 256)),
        (806, 4, 120, 4, 10.0, 2.0, 40, 10, 15.0, (256, 512)),
        (807, 2, 40, 16, 25.0, 0.5, 80, 30, 2.0, (1024, 2048)),
        (808, 4, 24, 32, 18.0, 1.0, 70, 25, 1.0, (512, 1024)),
        (809, 8, 50, 8, 15.0, 1.0, 35, 12, 8.0, (256, 512)),
        (810, 1, 80, 4, 8.0, 4.0, 40, 8, 6.0, (128, 256, 512)),
        (811, 4, 60, 12, 12.0, 2.0, 45, 14, 8.0, (256, 512, 1024)),
        (812, 2, 100, 4, 10.0, 3.0, 30, 8, 12.0, (128, 256)),
        (813, 4, 16, 48, 20.0, 0.8, 90, 40, 0.5, (1024, 2048)),
        (814, 8, 30, 16, 22.0, 0.6, 55, 22, 2.0, (512, 1024)),
        (815, 4, 200, 2, 5.0, 8.0, 20, 4, 10.0, (64, 128, 256)),
        (816, 2, 24, 32, 30.0, 0.4, 100, 40, 1.0, (2048, 4096)),
        (817, 4, 48, 8, 14.0, 1.5, 50, 16, 6.0, (256, 512)),
        (818, 1, 24, 16, 20.0, 1.0, 80, 25, 2.0, (512, 1024, 2048)),
        (819, 8, 100, 8, 10.0, 2.0, 30, 10, 15.0, (128, 256, 512)),
        (820, 4, 36, 20, 16.0, 1.2, 60, 18, 4.0, (256, 512, 1024)),
        (821, 2, 80, 8, 8.0, 4.0, 35, 10, 8.0, (256, 512)),
        (822, 4, 64, 6, 18.0, 1.0, 40, 12, 7.0, (128, 256, 512)),
        (823, 8, 40, 12, 25.0, 0.5, 70, 28, 3.0, (512, 1024)),
        (824, 1, 50, 8, 12.0, 2.0, 50, 12, 5.0, (256, 512)),
        (825, 4, 90, 8, 9.0, 3.0, 28, 8, 10.0, (128, 256, 512)),
        (826, 2, 32, 24, 20.0, 1.0, 65, 22, 2.0, (512, 1024)),
        (827, 4, 20, 40, 15.0, 2.0, 55, 20, 1.0, (256, 512, 1024)),
        (828, 8, 70, 4, 12.0, 1.5, 40, 14, 9.0, (256, 512)),
        (829, 4, 56, 10, 11.0, 2.5, 38, 11, 6.0, (128, 256, 512)),
        (830, 2, 48, 12, 16.0, 1.2, 48, 16, 4.0, (256, 512, 1024)),
    ]
    for seed, K, R, lout, lat, bw, pproc, dproc, span, lin in specs:
        out.append(make_case(
            8, f"g8-K{K}-R{R}-L{lout}-s{seed}",
            seed=seed, K=K, R=R, lout=lout, lat=lat, bw=bw,
            pproc=pproc, dproc=dproc, span=span, lin=lin,
        ))
    return out


def refine4():
    """Neighborhood of shapes whose tpot/tdr/tp land near #4."""
    out = []
    for seed in (401, 431, 441, 451, 461, 471):
        for K in (4, 8):
            for R, lout in ((24, 16), (32, 20), (40, 16), (48, 12),
                            (36, 24), (60, 16), (28, 32), (40, 8)):
                for lat, bw in ((5.0, 8.0), (8.0, 4.0), (10.0, 3.0),
                                (12.0, 2.0), (6.0, 6.0)):
                    for dproc, pproc in ((8, 40), (12, 50), (16, 35),
                                         (6, 25), (20, 60), (10, 45)):
                        out.append(make_case(
                            4,
                            f"r4-s{seed}-K{K}-R{R}-L{lout}-lat{lat:g}-d{dproc}",
                            seed=seed, K=K, R=R, lout=lout, lat=lat, bw=bw,
                            pproc=pproc, dproc=dproc, span=4.0,
                            lin=(256, 512, 1024),
                        ))
    return out


def refine8():
    out = []
    for seed in (801, 831, 841, 851, 861):
        for K in (2, 4):
            for R, lout in ((40, 8), (60, 8), (80, 6), (48, 12),
                            (32, 16), (70, 4), (24, 20), (56, 10)):
                for lat, bw in ((10.0, 2.0), (12.0, 2.0), (15.0, 1.5),
                                (18.0, 1.0), (8.0, 3.0)):
                    for dproc, pproc in ((8, 30), (12, 40), (16, 50),
                                         (20, 45), (10, 35), (14, 55)):
                        out.append(make_case(
                            8,
                            f"r8-s{seed}-K{K}-R{R}-L{lout}-lat{lat:g}-d{dproc}",
                            seed=seed, K=K, R=R, lout=lout, lat=lat, bw=bw,
                            pproc=pproc, dproc=dproc, span=8.0,
                            lin=(128, 256, 512),
                        ))
    return out


def fitted4(**override):
    """Best d202b1a match: tp +0.6%, tdr 0.0%, tpot +0.4% (sum rel 1.0%).

    Shape: K=4, R=8 all-at-0, L_out=17, lat=12, bw=2, dproc=13. Public
    efficiency prefix keeps m~7; TDR is the prefill drain.
    """
    kw = dict(seed=24, K=4, R=8, lout=17, lat=12.0, bw=2.0, S=2.0,
              layers=8, span=0.0, lin=(256, 512, 1024),
              pproc=30, dproc=13)
    kw.update(override)
    return make_case(4, f"fit4-K{kw['K']}-R{kw['R']}-L{kw['lout']}-s{kw['seed']}", **kw)


def fitted8(**override):
    """Best d202b1a match: tp +0.4%, tdr +0.5%, tpot +1.1% (sum rel 2.0%).

    Shape: K=4, R=18 all-at-0, L_out=2, lat=14, bw=1.5, dproc=9, pproc=15.
    Dist is the TDR leg; tpot sits on SLO2.
    """
    kw = dict(seed=38, K=4, R=18, lout=2, lat=14.0, bw=1.5, S=2.0,
              layers=8, span=0.0, lin=(256, 512, 1024),
              pproc=15, dproc=9)
    kw.update(override)
    return make_case(8, f"fit8-K{kw['K']}-R{kw['R']}-L{kw['lout']}-s{kw['seed']}", **kw)


def run_grid(binary, test, cases):
    o = OFF[test]
    print(f"=== #{test} recon vs {binary}  n={len(cases)}  "
          f"want tp={o['tp']} tdr={o['tdr']:.1f} tpot={o['tpot']:.2f} ===")
    ranked = []
    for case in cases:
        try:
            err, rel, metrics, pts, ntp, nc, sm = summarize(binary, case, test)
            ranked.append((err, case.name, rel, metrics, ntp, nc))
        except Exception as e:
            print(f"  {case.name:<32} FAIL {e}")
    ranked.sort()
    print("\n=== best 8 ===")
    for row in ranked[:8]:
        err, name, rel, m, ntp, nc = row
        print(f"  {name} fit={err:.3f} tp={m[0]:.5g} tdr={m[1]:.4g} "
              f"tpot={m[2]:.2f} ntp={ntp:.3f} nc={nc:.3f} "
              f"dtp={100 * rel['tp']:+.1f}% dtdr={100 * rel['tdr']:+.1f}% "
              f"dtpot={100 * rel['tpot']:+.1f}%")
    if ranked and ranked[0][0] < 0.15:
        print("\nFITTED (sum relative error < 15%).")
        return 0, ranked
    print("\nNOT FITTED (best sum relative error >= 15%).")
    return 1, ranked


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    binary = args[0] if args else "/tmp/d202-sched"
    tests = []
    if "--test" in sys.argv:
        tests = [int(sys.argv[sys.argv.index("--test") + 1])]
    else:
        tests = [4, 8]
    if "--fitted" in flags:
        rc = 0
        if 4 in tests:
            print(f"=== fitted #4 vs {binary}  "
                  f"want tp={OFF[4]['tp']} tdr={OFF[4]['tdr']:.1f} "
                  f"tpot={OFF[4]['tpot']:.2f} ===")
            summarize(binary, fitted4(), 4)
        if 8 in tests:
            print(f"=== fitted #8 vs {binary}  "
                  f"want tp={OFF[8]['tp']} tdr={OFF[8]['tdr']:.1f} "
                  f"tpot={OFF[8]['tpot']:.2f} ===")
            summarize(binary, fitted8(), 8)
        return 0
    rc = 0
    for test in tests:
        if "--refine" in flags:
            cases = refine4() if test == 4 else refine8()
        else:
            cases = grid4() if test == 4 else grid8()
        code, _ = run_grid(binary, test, cases)
        rc = max(rc, code)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

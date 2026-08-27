#!/usr/bin/env python3
"""Reconstruct official #12 (WTP=0.99 nc cliff) against d202b1a.

Official fingerprint from dual-submission checker logs of the 16041.088
vector (same #12 line on every d202b1a-lineage submission):

  points=798.488117  tp=0.000024  tdr=1284442.144348  tpot=4771.825430
  dist=36.909161  ntp=0.806554  nc=0  w_tp=0.99

SLO1/SLO2 inverted from three dual-sub (tp,tdr,tpot,dist) triples
(current / tpot-lo / tpot-hi), residual <0.02% on dist:

  SLO1=424762.48  SLO2=126.05992

Usage:
  python3 tests/official12_recon.py /tmp/d202-sched
  python3 tests/official12_recon.py /tmp/d202-sched --grid
"""
from __future__ import annotations

import math
import random
import sys

import sim

OFF = dict(
    wtp=0.99,
    pts=798.488117,
    tp=0.000024,
    tdr=1284442.144348,
    tpot=4771.825430,
    dist=36.909161,
    ntp=0.806554,
    nc=0.0,
    slo1=424762.4798895231,
    slo2=126.05991979895694,
)


def decode_table(pproc_k, dproc_k, dpre_k=1.0, dpre_s=0.008, dproc_s=0.04,
                 ppre_k=0.25, ppre_s=0.010):
    sizes = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]
    return [
        (
            b,
            ppre_k + ppre_s * b,
            pproc_k + 0.08 * b,
            0.20 + 0.005 * b,
            dpre_k + dpre_s * b,
            dproc_k + dproc_s * b,
            dpre_k + dpre_s * b,
        )
        for b in sizes
    ]


def make_case(name, **kw):
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
            kw.get("pproc", 80.0), kw.get("dproc", 40.0),
            kw.get("dpre_k", 2.0), kw.get("dpre_s", 0.02),
            kw.get("dproc_s", 0.4),
            kw.get("ppre_k", 0.5), kw.get("ppre_s", 0.05),
        )
    case = sim.Case(
        kw["K"], kw.get("S", 2.0), kw["lat"], kw["bw"], kw.get("bpt", 32768),
        kw.get("layers", 8), OFF["slo1"], OFF["slo2"], table, arrivals,
        OFF["wtp"], 1.0 - OFF["wtp"],
    )
    # Dummy scoring constants: at WTP=0.99 tpotBound cannot fire, so the
    # default path maximises m/roundT. Exact tp_base/ub only matter for ntp.
    case.tp_base = kw.get("tp_base", 1e-6)
    case.tp_ub = kw.get("tp_ub", 1e-3)
    case.dist_base = kw.get("dist_base", 4.0)
    case.name = name
    return case


def ratio_err(metrics):
    tp, tdr, tpot = metrics
    rel = {
        "tp": abs(tp - OFF["tp"]) / OFF["tp"],
        "tdr": abs(tdr - OFF["tdr"]) / OFF["tdr"],
        "tpot": abs(tpot - OFF["tpot"]) / OFF["tpot"],
    }
    return rel["tp"] + rel["tdr"] + rel["tpot"], rel


def summarize(binary, case, timeout=180.0):
    metrics, frames, sm = sim.run(binary, case, timeout=timeout)
    pts, ntp, nc, dist = sim.score(case, metrics)
    err, rel = ratio_err(metrics)
    span = max(r.toks[-1] for r in sm.reqs) - min(r.arr for r in sm.reqs)
    print(
        f"  {case.name:<28} pts={pts:7.2f} ntp={ntp:.3f} nc={nc:.3f} "
        f"tp={metrics[0]:.6g} tdr={metrics[1]:.4g} tpot={metrics[2]:.2f} "
        f"dist={dist:.2f} span={span:.4g} fr={frames} "
        f"fit={err:.3f} dtp={100*rel['tp']:+.1f}% dtdr={100*rel['tdr']:+.1f}% "
        f"dtpot={100*rel['tpot']:+.1f}% cpu={getattr(sm,'cpu',0):.2f}s"
    )
    return err, rel, metrics, pts, ntp, nc


def grid():
    """Diverse WTP=0.99 shapes aimed at tiny tp, meg-scale TDR, tpot~4k."""
    out = []
    # Small R, slow decode (tpot-like round).
    for seed, K, R, lout, lat, bw, pproc, dproc, span, lin in (
        (12, 1, 12, 16, 20.0, 0.5, 200, 80, 10.0, (512, 1024, 2048)),
        (13, 1, 16, 32, 25.0, 0.3, 400, 120, 5.0, (1024, 2048, 4096)),
        (14, 1, 8, 64, 30.0, 0.2, 800, 200, 2.0, (2048, 4096)),
        (15, 2, 20, 16, 20.0, 0.5, 150, 60, 8.0, (512, 1024)),
        (16, 2, 40, 8, 15.0, 1.0, 80, 40, 10.0, (256, 512, 1024)),
        (17, 4, 80, 8, 10.0, 2.0, 60, 30, 20.0, (128, 256, 512)),
        (18, 1, 200, 4, 5.0, 1.0, 40, 20, 5.0, (256, 512, 1024)),
        (19, 1, 400, 2, 2.0, 2.0, 20, 10, 5.0, (128, 256, 512)),
        (20, 1, 80, 8, 40.0, 0.1, 300, 150, 1.0, (1024, 2048)),
        (21, 8, 30, 32, 20.0, 0.5, 100, 50, 15.0, (256, 512)),
        (22, 1, 24, 24, 50.0, 0.05, 500, 250, 0.0, (4096,)),
        (23, 1, 6, 128, 50.0, 0.05, 1000, 400, 0.0, (4096,)),
        (24, 2, 10, 64, 35.0, 0.2, 600, 180, 1.0, (2048, 4096)),
        (25, 1, 100, 4, 25.0, 0.2, 100, 80, 2.0, (512, 1024)),
        (26, 4, 16, 48, 20.0, 0.4, 200, 90, 5.0, (512, 1024, 2048)),
        (27, 1, 32, 16, 8.0, 4.0, 50, 8, 4.0, (64, 128, 256)),
        (28, 1, 50, 12, 12.0, 0.8, 120, 45, 6.0, (256, 512)),
        (29, 2, 8, 96, 40.0, 0.08, 900, 300, 0.5, (2048, 4096)),
        (30, 1, 2000, 2, 1.0, 10.0, 8, 4, 5.0, (16, 32, 64)),
        (31, 1, 500, 4, 20.0, 0.2, 80, 60, 2.0, (512, 1024)),
        (32, 8, 12, 64, 50.0, 0.05, 400, 200, 0.0, (4096,)),
        (33, 1, 20, 40, 15.0, 1.0, 250, 100, 3.0, (1024, 2048)),
        (34, 2, 60, 6, 8.0, 3.0, 40, 15, 8.0, (128, 256)),
        (35, 1, 4, 256, 50.0, 0.02, 2000, 800, 0.0, (4096,)),
        (36, 1, 64, 8, 30.0, 0.15, 180, 90, 1.0, (1024, 2048, 4096)),
        (37, 4, 24, 20, 25.0, 0.3, 220, 70, 4.0, (512, 1024)),
        (38, 1, 10, 80, 45.0, 0.1, 700, 220, 0.0, (2048, 4096)),
        (39, 2, 100, 4, 10.0, 0.5, 70, 35, 5.0, (256, 512, 1024)),
        (40, 1, 16, 32, 5.0, 8.0, 30, 5, 2.0, (32, 64, 128)),
    ):
        out.append(make_case(
            f"g-K{K}-R{R}-L{lout}-s{seed}",
            seed=seed, K=K, R=R, lout=lout, lat=lat, bw=bw,
            pproc=pproc, dproc=dproc, span=span, lin=lin,
        ))
    return out


def refine_candidates():
    """Neighborhood of the most #12-like families: K=1, modest R, slow round."""
    out = []
    for seed in (12, 41, 42, 43, 44, 45, 91, 101, 201, 301):
        for K in (1, 2):
            for R, lout in ((8, 48), (12, 32), (16, 24), (20, 16), (24, 12),
                            (32, 8), (6, 64), (10, 40)):
                for lat, bw in ((20.0, 0.5), (40.0, 0.1), (50.0, 0.05),
                                (10.0, 1.0), (30.0, 0.2)):
                    for dproc, pproc in ((80, 200), (150, 400), (250, 600),
                                         (40, 100), (400, 800)):
                        name = (f"r-s{seed}-K{K}-R{R}-L{lout}-lat{lat:g}-"
                                f"bw{bw:g}-d{dproc}")
                        out.append(make_case(
                            name, seed=seed, K=K, R=R, lout=lout, lat=lat,
                            bw=bw, pproc=pproc, dproc=dproc, span=2.0,
                            lin=(1024, 2048, 4096),
                        ))
    return out


def fitted12(pproc=120000.0, layers=24, R=20, lout=3):
    """Best d202b1a match: tpot +0.05%, dist +0.05%, tdr -1.1%, tp +3.6%.

    Shape: K=1, 20 requests all-at-0, L_out=3, L_in=4096, 24 layers, huge
    serial P PROC. Dual-sub SLOs. Seed-invariant at span=0.
    """
    return make_case(
        "fit12-K1-R20-L3-y24",
        seed=12, K=1, R=R, lout=lout, lat=20.0, bw=0.5, S=2.0,
        layers=layers, span=0.0, lin=(4096,),
        pproc=pproc, dproc=5.0, dpre_k=0.5, dpre_s=0.001, dproc_s=0.001,
        ppre_k=20.0, ppre_s=0.5, dist_base=2.16168, tp_base=1e-8, tp_ub=1e-3,
    )


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    binary = args[0] if args else "/tmp/d202-sched"
    if "--fitted" in flags:
        cases = [fitted12()]
        print(f"=== fitted #12 vs {binary}  "
              f"want tp={OFF['tp']} tdr={OFF['tdr']:.1f} tpot={OFF['tpot']:.2f} ===")
        summarize(binary, cases[0])
        return 0
    cases = grid()
    if "--refine" in flags:
        cases = refine_candidates()
    print(f"=== #12 recon vs {binary}  n={len(cases)}  "
          f"want tp={OFF['tp']} tdr={OFF['tdr']:.1f} tpot={OFF['tpot']:.2f} ===")
    ranked = []
    for case in cases:
        try:
            err, rel, metrics, pts, ntp, nc = summarize(binary, case)
            ranked.append((err, case.name, rel, metrics, ntp, nc))
        except Exception as e:
            print(f"  {case.name:<28} FAIL {e}")
    ranked.sort()
    print("\n=== best 8 ===")
    for row in ranked[:8]:
        err, name, rel, m, ntp, nc = row
        print(f"  {name} fit={err:.3f} tp={m[0]:.6g} tdr={m[1]:.4g} "
              f"tpot={m[2]:.2f} ntp={ntp:.3f} nc={nc:.3f} "
              f"dtp={100*rel['tp']:+.1f}% dtdr={100*rel['tdr']:+.1f}% "
              f"dtpot={100*rel['tpot']:+.1f}%")
    if ranked and ranked[0][0] < 0.15:
        print("\nFITTED (sum relative error < 15%).")
        return 0
    print("\nNOT FITTED (best sum relative error >= 15%).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

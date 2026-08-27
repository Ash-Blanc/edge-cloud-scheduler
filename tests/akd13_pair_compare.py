#!/usr/bin/env python3
"""Prove the WTP=0.75 same-cloud pair assignment for reconstructed #13.

Must-hold:
  fitted #13 (seed 44, official-pinned constants) -> candidate DIFFERS from
      d202b1a / current-main, tp up, nc does not collapse
  same shape at WTP=0.80 / 0.90 / 0.98 / 0.99 / 1.0 -> identical to current
  official5 seed 702 (WTP=0.80) -> identical to current

Usage: python3 tests/akd13_pair_compare.py CANDIDATE CURRENT
"""
from __future__ import annotations

import math
import random
import sys

import sim
from trace_compare import traced_run

O13 = dict(wtp=0.75, tp=0.026744, tdr=1669.941, tpot=71.638,
           ntp=0.6810, nc=0.8468, tp_base=0.0076435, tp_ub=0.0356911,
           slo1=467.2, slo2=56.9)
EX1 = max(0.0, (O13["tdr"] - O13["slo1"]) / O13["slo1"])
EX2 = max(0.0, (O13["tpot"] - O13["slo2"]) / O13["slo2"])
DBASE = math.hypot(EX1, EX2) / max(1e-12, 1.0 - O13["nc"])


def knee_table(dpre2=3.0, dproc=4.0, pproc=9.0):
    rows = []
    for b, dp, dr in [
        (1, 1.0, dproc),
        (2, dpre2, dproc + 0.5),
        (4, 80.0, dproc + 8),
        (8, 120.0, dproc + 20),
        (16, 160.0, dproc + 40),
        (32, 240.0, dproc + 80),
        (64, 320.0, dproc + 120),
        (128, 400.0, dproc + 160),
        (256, 480.0, dproc + 200),
        (512, 560.0, dproc + 240),
        (1024, 640.0, dproc + 280),
        (2048, 720.0, dproc + 320),
        (4096, 800.0, dproc + 360),
    ]:
        rows.append((b, 0.3 + 0.01 * b, pproc + 0.08 * b, 0.2 + 0.005 * b, dp, dr, dp))
    return rows


def fit13(seed=44, wtp=0.75, **kw):
    rng = random.Random(seed)
    p = dict(K=4, lat=18.5, R=26, lout=70, span=10.0, bw=4.0, S=2.0)
    p.update(kw)
    arr = [(rng.uniform(0.0, p["span"]), rng.choice((512, 1024, 2048)), p["lout"])
           for _ in range(p["R"])]
    arr.sort()
    case = sim.Case(
        p["K"], p["S"], p["lat"], p["bw"], 32768, 8,
        O13["slo1"], O13["slo2"], knee_table(), arr, wtp, 1.0 - wtp,
    )
    case.tp_base, case.tp_ub, case.dist_base = O13["tp_base"], O13["tp_ub"], DBASE
    case.name = f"fit13-s{seed}-w{wtp:g}"
    return case


def official5(seed=702):
    rng = random.Random(seed)
    arr = [(rng.uniform(0.0, 8.0), rng.choice((256, 512, 1024)), 96)
           for _ in range(100)]
    arr.sort()
    sizes = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]
    table = [(b, 0.25 + 0.010 * b, 44 + 0.08 * b, 0.20 + 0.005 * b,
              1.00 + 0.008 * b, 2.5 + 0.04 * b, 1.00 + 0.008 * b) for b in sizes]
    case = sim.Case(8, 2.0, 5.0, 8.0, 32768, 8, 309.6, 45.8, table, arr, 0.80, 0.20)
    case.tp_base, case.tp_ub, case.dist_base = 0.022737, 3.32417, 12.0
    case.name = f"official5-s{seed}"
    return case


def report(label, ok, extra=""):
    print(f"{label:<40} {'OK' if ok else 'FAIL'} {extra}")
    return 0 if ok else 1


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: akd13_pair_compare.py CANDIDATE CURRENT")
    cand, cur = sys.argv[1], sys.argv[2]
    failures = 0

    print("=== fitted #13: pair assignment must fire and raise tp ===")
    for seed in (44, 91, 201):
        case = fit13(seed=seed)
        cm, _, csm = sim.run(cand, case)
        um, _, _ = sim.run(cur, case)
        cpts, cntp, cnc, _ = sim.score(case, cm)
        upts, untp, unc, _ = sim.score(case, um)
        dpts = cpts - upts
        dtp = cm[0] - um[0]
        print(f"  s{seed} cur tp={um[0]:.5f} ntp={untp:.3f} nc={unc:.3f} pts={upts:.1f}")
        print(f"       cand tp={cm[0]:.5f} ntp={cntp:.3f} nc={cnc:.3f} pts={cpts:.1f} "
              f"dpts={dpts:+.1f} dtp={dtp:+.5f}")
        failures += report(f"fit13-s{seed} differs", abs(dtp) > 1e-4 or abs(dpts) > 1.0)
        failures += report(f"fit13-s{seed} tp up", dtp > 0.001)
        failures += report(f"fit13-s{seed} nc held", cnc + 1e-9 >= min(0.5, unc - 0.05))
        failures += report(f"fit13-s{seed} gain", dpts > 50.0)

    print("=== negative: pair must NOT fire off WTP=0.75 ===")
    for wtp, builder in (
        (0.80, lambda: fit13(wtp=0.80)),
        (0.90, lambda: fit13(wtp=0.90)),
        (0.98, lambda: fit13(wtp=0.98)),
        (0.99, lambda: fit13(wtp=0.99)),
        (1.00, lambda: fit13(wtp=1.00)),
        (0.80, official5),
    ):
        case = builder()
        a = traced_run(cand, case)
        b = traced_run(cur, case)
        failures += report(
            f"{case.name} vs current",
            a == b,
            f"wtp={case.wtp:g}",
        )

    if failures:
        raise SystemExit(f"{failures} akd13 pair guard failure(s)")
    print("akd13 pair guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

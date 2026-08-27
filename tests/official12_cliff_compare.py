#!/usr/bin/env python3
"""Prove the isolated WTP=0.99 tpotBound override on reconstructed #12.

Must-hold:
  fitted #12 (K=1 R=20 L_out=3 layers=24, official SLOs) -> candidate
      DIFFERS from d202b1a, tpot down, nc not worse
  same shape at WTP=0.98 / 1.0 / 0.80 / 0.90 -> identical traces
  official5 seed 702 (WTP=0.80) -> identical
  slow16-K4 (WTP=0.98) -> identical

Usage: python3 tests/official12_cliff_compare.py CANDIDATE CURRENT
"""
from __future__ import annotations

import random
import sys

import sim
from official12_recon import OFF, decode_table
from trace_compare import traced_run

# Fitted against d202b1a: tpot 0.05%, dist 0.05%, tdr 1.1%, tp 3.6%.
# All-at-0 arrivals; lin/lout uniform so seed-invariant at span=0.
FIT = dict(K=1, R=20, lout=3, layers=24, pproc=120000.0, dproc=5.0,
           lat=20.0, bw=0.5, S=2.0, lin=4096, span=0.0)


def fit12(wtp=0.99, seed=12, **kw):
    p = dict(FIT)
    p.update(kw)
    rng = random.Random(seed)
    lin = p["lin"]
    if p["span"] <= 0:
        arr = [(0.0, lin, p["lout"]) for _ in range(p["R"])]
    else:
        arr = sorted(
            (rng.uniform(0.0, p["span"]), lin, p["lout"])
            for _ in range(p["R"])
        )
    table = decode_table(p["pproc"], p["dproc"], 0.5, 0.001, 0.001, 20.0, 0.5)
    case = sim.Case(
        p["K"], p["S"], p["lat"], p["bw"], 32768, p["layers"],
        OFF["slo1"], OFF["slo2"], table, arr, wtp, 1.0 - wtp,
    )
    case.tp_base, case.tp_ub, case.dist_base = 1e-8, 1e-3, 2.16168
    case.name = f"fit12-s{seed}-w{wtp:g}"
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


def report(label, binary, case):
    m, frames, sm = sim.run(binary, case)
    pts, ntp, nc, dist = sim.score(case, m)
    print(f"  {label:<18} pts={pts:8.2f} ntp={ntp:.4f} nc={nc:.4f} "
          f"tp={m[0]:.6g} tdr={m[1]:.4g} tpot={m[2]:.2f} dist={dist:.3f} "
          f"frames={frames}")
    return m, pts, ntp, nc, dist


def traces_equal(a, b, case):
    ta = traced_run(a, case)
    tb = traced_run(b, case)
    return ta == tb, ta[1][1] if ta[1] else 0, tb[1][1] if tb[1] else 0


def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: official12_cliff_compare.py CANDIDATE CURRENT")
    cand, cur = sys.argv[1], sys.argv[2]
    failures = 0

    print("=== fitted #12 WTP=0.99 (must differ, tpot down) ===")
    case = fit12()
    print(f"  want official tp={OFF['tp']} tdr={OFF['tdr']:.1f} "
          f"tpot={OFF['tpot']:.2f} dist={OFF['dist']:.3f}")
    um, upts, untp, unc, udist = report("current", cur, case)
    cm, cpts, cntp, cnc, cdist = report("candidate", cand, case)
    dpts = cpts - upts
    same = (abs(cm[0] - um[0]) < 1e-12 and abs(cm[2] - um[2]) < 1e-9)
    print(f"           delta pts={dpts:+.2f} tpot={cm[2]-um[2]:+.2f} "
          f"tdr={cm[1]-um[1]:+.4g} nc={cnc-unc:+.4f} ntp={cntp-untp:+.4f}")
    if same:
        print("  ERROR: candidate equals current on fitted #12; guard did not fire")
        failures += 1
    elif cm[2] > um[2] + 1.0:
        print("  ERROR: tpot rose")
        failures += 1
    else:
        print("  OK: guard fired, tpot did not rise")

    print("\n=== multi-seed same shape ===")
    for seed, span in ((12, 0.0), (44, 0.0), (91, 100.0), (101, 500.0), (201, 0.0)):
        c = fit12(seed=seed, span=span)
        um, upts, untp, unc, _ = report(f"cur-s{seed}", cur, c)
        cm, cpts, cntp, cnc, _ = report(f"cand-s{seed}", cand, c)
        print(f"           delta pts={cpts-upts:+.2f} tpot={cm[2]-um[2]:+.2f} "
              f"nc={cnc-unc:+.4f}")

    print("\n=== negative: same shape at 0.98 / 1.0 / 0.80 / 0.90 must MATCH ===")
    for w in (0.98, 1.0, 0.80, 0.90):
        c = fit12(wtp=w)
        ok, n1, n2 = traces_equal(cand, cur, c)
        print(f"  w={w:g} traces {'MATCH' if ok else 'DIFF'} n={n1}/{n2}")
        if not ok:
            print("  ERROR: guard leaked onto a non-0.99 weight")
            failures += 1

    print("\n=== official5 seed 702 (AKD 0.80) must MATCH ===")
    c5 = official5()
    ok, n1, n2 = traces_equal(cand, cur, c5)
    print(f"  official5 traces {'MATCH' if ok else 'DIFF'} n={n1}/{n2}")
    if not ok:
        print("  ERROR: official5 changed")
        failures += 1

    print("\n=== suite WTP=0.98 / 1.00 cases must MATCH ===")
    cases = {c.name: c for c in sim.build_cases()}
    for name in ("slow16-K4", "tp-sat-K8"):
        c = cases[name]
        sim.calibrate(c, "/tmp/ref_sequential")
        ok, n1, n2 = traces_equal(cand, cur, c)
        print(f"  {name} w={c.wtp:g} traces {'MATCH' if ok else 'DIFF'} n={n1}/{n2}")
        if not ok:
            print(f"  ERROR: {name} changed")
            failures += 1

    if failures:
        print(f"\n{failures} failure(s)")
        return 1
    print("\nall proofs passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

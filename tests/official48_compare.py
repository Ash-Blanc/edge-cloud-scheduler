#!/usr/bin/env python3
"""A/B probes for fitted official #4 / #8 against d202b1a.

Variants are compile-time AKD4_* / AKD8_* binaries. Default d202b1a
must stay trace-identical on non-target weights.

Usage:
  python3 tests/official48_compare.py BASE VARIANT [VARIANT ...]
"""
from __future__ import annotations

import sys

import sim
from official48_recon import OFF, fitted4, fitted8, summarize
from trace_compare import traced_run
from ensemble_compare import test17_case, test22_case


def seed_cases(test, seeds):
    builder = fitted4 if test == 4 else fitted8
    out = []
    for seed in seeds:
        case = builder(seed=seed)
        out.append((test, case))
    return out


def extra_shapes(test):
    builder = fitted4 if test == 4 else fitted8
    out = []
    if test == 4:
        variants = (
            dict(K=4, R=8, lout=16, lat=12.0, dproc=13),
            dict(K=4, R=10, lout=17, lat=12.0, dproc=13),
            dict(K=8, R=8, lout=17, lat=12.0, dproc=13),
            dict(K=4, R=8, lout=17, lat=8.0, dproc=13),
            dict(K=4, R=8, lout=24, lat=12.0, dproc=10),
            dict(K=2, R=8, lout=17, lat=12.0, dproc=13),
        )
    else:
        variants = (
            dict(K=4, R=16, lout=2, lat=14.0, dproc=9, pproc=15),
            dict(K=4, R=20, lout=2, lat=14.0, dproc=9, pproc=15),
            dict(K=8, R=18, lout=2, lat=14.0, dproc=9, pproc=15),
            dict(K=4, R=18, lout=2, lat=12.0, dproc=9, pproc=20),
            dict(K=2, R=18, lout=2, lat=14.0, dproc=9, pproc=15),
            dict(K=4, R=18, lout=4, lat=14.0, dproc=9, pproc=15),
        )
    for i, kw in enumerate(variants, 1):
        case = builder(seed=1000 + i, **kw)
        case.name = f"shape{test}-{i}-K{kw['K']}-R{kw['R']}"
        out.append((test, case))
    return out


def other_weight_cases():
    """Weights that must stay byte-identical to d202b1a."""
    from official_cohort_sweep import official5, official6, official13, pin_official_constants
    out = []
    c = official5(seed=702)
    pin_official_constants(c, 5)
    out.append(("w.80-#5", c))
    c = official6(seed=802)
    pin_official_constants(c, 6)
    out.append(("w.90-#6", c))
    c = official13(seed=1301)
    pin_official_constants(c, 13)
    out.append(("w.75-#13", c))
    # local suite cases at protected weights
    by = {c.name: c for c in sim.build_cases()}
    for name, w in (
        ("lat-heavy-K8", 0.05),
        ("lat-mid-K4", 0.15),
        ("tp-sat-K4", 0.98),
        ("tp-sat-K8", 1.00),
        ("hi-lat-K4", 0.65),
    ):
        case = by[name]
        sim.calibrate(case, "/tmp/ref_sequential")
        out.append((f"{name}-w{w:.2f}", case))
    out.append(("test17", test17_case()))
    out.append(("test22", test22_case()))
    return out


def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: official48_compare.py BASE VARIANT [VARIANT ...]")
    base = sys.argv[1]
    variants = sys.argv[2:]

    print("=== fitted reconstructions vs official ===")
    for test, case in ((4, fitted4()), (8, fitted8())):
        o = OFF[test]
        print(f"\n#{test} want tp={o['tp']:.5f} tdr={o['tdr']:.1f} tpot={o['tpot']:.2f} "
              f"ntp={o['ntp']:.3f} nc={o['nc']:.3f}")
        summarize(base, case, test)

    cases = []
    cases.extend(seed_cases(4, (24, 25, 26, 34, 44)))
    cases.extend(seed_cases(8, (38, 39, 48, 58, 68)))
    cases.extend(extra_shapes(4))
    cases.extend(extra_shapes(8))

    print("\n=== multi-seed + shape A/B ===")
    by_var = {v: [] for v in variants}
    failures = 0
    for test, case in cases:
        print(f"\n{case.name}  wtp={case.wtp:.2f} K={case.K} R={len(case.arrivals)}")
        b_m, frames, sm = sim.run(base, case)
        b_pts, b_ntp, b_nc, _ = sim.score(case, b_m)
        print(f"  {'base':<18} pts={b_pts:8.2f} ntp={b_ntp:.3f} nc={b_nc:.3f} "
              f"tp={b_m[0]:.5f} tdr={b_m[1]:.1f} tpot={b_m[2]:.2f}")
        for var in variants:
            name = var.split("/")[-1]
            try:
                m, _, _ = sim.run(var, case)
                pts, ntp, nc, _ = sim.score(case, m)
            except Exception as e:
                print(f"  {name:<18} FAIL {e}")
                failures += 1
                continue
            dpts = pts - b_pts
            flag = ""
            if nc + 1e-9 < b_nc - 0.02:
                flag = "  NC_DROP"
                failures += 1
            if abs(dpts) > 0.05:
                flag += "  DIFFERS"
            else:
                flag += "  SAME"
            print(f"  {name:<18} pts={pts:8.2f} ntp={ntp:.3f} nc={nc:.3f} "
                  f"tp={m[0]:.5f} tdr={m[1]:.1f} tpot={m[2]:.2f} "
                  f"dpts={dpts:+7.2f}{flag}")
            by_var[var].append((case.name, test, dpts, ntp, nc, b_nc))

    print("\n=== variant totals vs base ===")
    for var in variants:
        rows = by_var[var]
        if not rows:
            continue
        dpts = sum(r[2] for r in rows)
        wins = sum(1 for r in rows if r[2] > 1.0)
        losses = sum(1 for r in rows if r[2] < -1.0)
        print(f"  {var.split('/')[-1]:<18} sum_dpts={dpts:+8.1f} "
              f"wins={wins} losses={losses} n={len(rows)}")

    print("\n=== trace identity on non-target weights ===")
    for label, case in other_weight_cases():
        w = case.wtp
        # skip target weights
        if abs(w - 0.30) <= 1e-6 or abs(w - 0.25) <= 1e-6:
            continue
        base_t = traced_run(base, case)
        for var in variants:
            cand_t = traced_run(var, case)
            ok = cand_t == base_t
            if not ok:
                failures += 1
            print(f"  {label:<24} {var.split('/')[-1]:<18} "
                  f"{'IDENTICAL' if ok else 'DIFFERS'} wtp={w:.2f}")

    if failures:
        print(f"{failures} failure(s)")
        return 1
    print("no nc-collapse / trace-identity failures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""A/B isolated unique-weight probes for fitted official #17 / #18.

Variants are compile-time AKD17_* / AKD18_* binaries. Default d202b1a
must stay trace-identical on non-target weights (.05 .15 .25 .30 .75
.80 .90 .98, #3, #19, #22).

Usage:
  python3 tests/official1718_compare.py BASE VARIANT [VARIANT ...]
"""
from __future__ import annotations

import copy
import sys

import sim
from official1718_recon import OFF, fitted17, fitted18, summarize
from trace_compare import traced_run
from ensemble_compare import test17_case, test22_case


def high_cv18(**kw):
    case = fitted18(R=400, pproc=78375.0, pproc_s=30.0, **kw)
    case.name = f"hcv18-s{kw.get('seed', 18)}"
    return case


def other_weight_cases():
    out = []
    by = {c.name: c for c in sim.build_cases()}
    for name in (
        "lat-heavy-K8",   # .05
        "lat-mid-K4",     # .15
        "sat5-K8",        # .80
        "sat6-K8",        # .90
        "tp-sat-K4",      # .98
        "tp-sat-K8",      # 1.00 #19
        "tp-burst-K2",    # .80
        "hi-lat-K4",      # .65
        "bal-K8-cpu",     # .45
        "bk-big-K4",      # .45
    ):
        case = by[name]
        sim.calibrate(case, "/tmp/ref_sequential")
        out.append((name, case))
    lat = copy.deepcopy(by["lat-only-K4"])
    lat.dist_base = 1.16
    lat.name = "akd3-dbase1.16"
    out.append(("akd3", lat))
    p25 = copy.deepcopy(by["bal-K4"])
    p25.wtp, p25.wc = 0.25, 0.75
    p25.name = "wtp-0.25"
    out.append(("w.25", p25))
    p30 = copy.deepcopy(by["bal-K4"])
    p30.wtp, p30.wc = 0.30, 0.70
    p30.name = "wtp-0.30"
    out.append(("w.30", p30))
    p75 = copy.deepcopy(by["bal-K4"])
    p75.wtp, p75.wc = 0.75, 0.25
    p75.name = "wtp-0.75"
    out.append(("w.75", p75))
    out.append(("test17-ens", test17_case()))
    out.append(("test22", test22_case()))
    return out


def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: official1718_compare.py BASE VARIANT [VARIANT ...]")
    base = sys.argv[1]
    variants = sys.argv[2:]

    print("=== fitted reconstructions vs official ===")
    summarize(base, fitted17(), 17)
    summarize(base, fitted18(), 18)

    targets = []
    for seed in (17, 99, 1234):
        targets.append(("17", fitted17(seed=seed)))
    for seed in (18, 181, 182, 183, 184):
        c = fitted18(seed=seed)
        c.name = f"fit18-s{seed}"
        targets.append(("18", c))
    for seed in (18, 181, 182):
        targets.append(("18", high_cv18(seed=seed)))
    # extra #17 L_out/R nearby shapes
    for i, kw in enumerate((
        dict(R=511, lout=58, pproc=113400, layers=8),
        dict(R=511, lout=60, pproc=113400, layers=8),
        dict(R=480, lout=59, pproc=120000, layers=8),
    ), 1):
        c = fitted17(**kw)
        c.name = f"shape17-{i}"
        targets.append(("17", c))

    print("\n=== multi-seed + shape A/B ===")
    failures = 0
    by_var = {v: [] for v in variants}
    for test, case in targets:
        print(f"\n{case.name}  wtp={case.wtp:.2f} K={case.K} R={len(case.arrivals)}")
        b_m, _, _ = sim.run(base, case)
        b_pts, b_ntp, b_nc, _ = sim.score(case, b_m)
        print(
            f"  {'base':<18} pts={b_pts:8.2f} ntp={b_ntp:.3f} nc={b_nc:.3f} "
            f"tp={b_m[0]:.5g} tdr={b_m[1]:.1f} tpot={b_m[2]:.2f}"
        )
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
            print(
                f"  {name:<18} pts={pts:8.2f} ntp={ntp:.3f} nc={nc:.3f} "
                f"tp={m[0]:.5g} tdr={m[1]:.1f} tpot={m[2]:.2f} "
                f"dpts={dpts:+7.2f}{flag}"
            )
            by_var[var].append((case.name, test, dpts, ntp, nc, b_nc))

    print("\n=== variant totals vs base ===")
    for var in variants:
        rows = by_var[var]
        if not rows:
            continue
        dpts = sum(r[2] for r in rows)
        wins = sum(1 for r in rows if r[2] > 1.0)
        losses = sum(1 for r in rows if r[2] < -1.0)
        print(
            f"  {var.split('/')[-1]:<18} sum_dpts={dpts:+8.1f} "
            f"wins={wins} losses={losses} n={len(rows)}"
        )

    print("\n=== trace identity on non-target weights ===")
    for label, case in other_weight_cases():
        w = case.wtp
        if abs(w - 0.67) <= 1e-6 or abs(w - 0.58) <= 1e-6:
            continue
        base_t = traced_run(base, case)
        for var in variants:
            cand_t = traced_run(var, case)
            ok = cand_t == base_t
            if not ok:
                failures += 1
            print(
                f"  {label:<24} {var.split('/')[-1]:<18} "
                f"{'IDENTICAL' if ok else 'DIFFERS'} wtp={w:.2f}"
            )

    if failures:
        print(f"{failures} failure(s)")
        return 1
    print("no nc-collapse / trace-identity failures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""A/B isolated wEq(WTP,.25) probes vs d202b1a on the fitted #8 recon.

Usage: python3 tests/official8_compare.py BASE VAR=path [VAR=path ...]
"""
from __future__ import annotations

import copy
import sys

import sim
from akd3_guard_compare import official5
from ensemble_compare import test17_case, test22_case
from historical22_trace_compare import historical_replay
from official48_recon import OFF, fitted4, fitted8, summarize
from trace_compare import traced_run


def retarget(case, wtp, name):
    c = copy.deepcopy(case)
    c.wtp = wtp
    c.wc = 1.0 - wtp
    c.name = name
    return c


def compare(label, case, base, var):
    ma, ta = traced_run(var, case)
    mb, tb = traced_run(base, case)
    same = ma == mb and ta == tb
    pts_a, ntp_a, nc_a, _ = sim.score(case, ma)
    pts_b, ntp_b, nc_b, _ = sim.score(case, mb)
    print(
        f"{label:<28} {'IDENTICAL' if same else 'DIFFERS':<10} "
        f"pts {pts_b:.2f}->{pts_a:.2f} ({pts_a - pts_b:+.2f}) "
        f"ntp {ntp_b:.3f}->{ntp_a:.3f} nc {nc_b:.3f}->{nc_a:.3f} "
        f"tp {mb[0]:.6f}->{ma[0]:.6f} tdr {mb[1]:.1f}->{ma[1]:.1f} "
        f"tpot {mb[2]:.3f}->{ma[2]:.3f}"
    )
    return same, pts_a - pts_b, nc_a - nc_b, ma, mb


def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: official8_compare.py BASE NAME=PATH [...]")
    base = sys.argv[1]
    variants = []
    for arg in sys.argv[2:]:
        if "=" not in arg:
            raise SystemExit(f"bad variant spec {arg}")
        name, path = arg.split("=", 1)
        variants.append((name, path))

    print("=== fitted #8 vs official fingerprint ===")
    print(
        f"want tp={OFF[8]['tp']} tdr={OFF[8]['tdr']:.3f} tpot={OFF[8]['tpot']:.3f} "
        f"ntp={OFF[8]['ntp']:.3f} nc={OFF[8]['nc']:.3f}"
    )
    summarize(base, fitted8(), 8)

    print("\n=== target .25 A/B ===")
    seeds = [fitted8(seed=s) for s in (38, 39, 48, 58, 68)]
    shapes = [
        fitted8(seed=1001, K=4, R=16, lout=2, lat=14.0, dproc=9, pproc=15),
        fitted8(seed=1002, K=4, R=20, lout=2, lat=14.0, dproc=9, pproc=15),
        fitted8(seed=1003, K=2, R=18, lout=2, lat=14.0, dproc=9, pproc=15),
        fitted8(seed=1004, K=8, R=18, lout=2, lat=14.0, dproc=9, pproc=15),
    ]
    targets = seeds + shapes
    summary = {name: [] for name, _ in variants}
    for case in targets:
        print(f"\n{case.name} K={case.K} R={len(case.arrivals)}")
        for name, path in variants:
            same, dpts, dnc, _, _ = compare(name, case, base, path)
            summary[name].append((case.name, same, dpts, dnc))

    print("\n=== variant totals on .25 ===")
    for name, _ in variants:
        rows = summary[name]
        dpts = sum(r[2] for r in rows)
        wins = sum(1 for r in rows if r[2] > 1.0)
        losses = sum(1 for r in rows if r[2] < -1.0)
        ident = sum(1 for r in rows if r[1])
        print(
            f"  {name:<16} sum_dpts={dpts:+7.2f} wins={wins} losses={losses} "
            f"identical={ident}/{len(rows)}"
        )

    print("\n=== trace identity off .25 ===")
    cases = sim.build_cases()
    for c in cases:
        sim.calibrate(c, "/tmp/ref_sequential")
    protected = []
    fit8 = fitted8()
    fit4 = fitted4()
    for w, tag in (
        (0.05, "w.05"), (0.15, "w.15"), (0.30, "w.30"), (0.75, "w.75"),
        (0.80, "w.80"), (0.90, "w.90"), (0.98, "w.98"), (0.99, "w.99"),
        (1.00, "w1.0"),
    ):
        protected.append(retarget(fit8, w, f"fit8-{tag}"))
        protected.append(retarget(fit4, w, f"fit4-{tag}"))
    protected.append(official5())
    protected.append(next(c for c in cases if c.name == "sat5-K8"))
    protected.append(next(c for c in cases if c.name == "sat6-K8"))
    protected.append(next(c for c in cases if c.name == "lat-only-K4"))
    protected.append(test17_case())
    protected.append(test22_case())
    protected.append(historical_replay())

    failures = 0
    for case in protected:
        for name, path in variants:
            same, _, _, _, _ = compare(f"{name}:{case.name}", case, base, path)
            if not same:
                failures += 1
                print(f"  ERROR {name} moved {case.name}")
    if failures:
        raise SystemExit(f"{failures} identity failure(s)")
    print("all off-target traces identical")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Prove the hardened #3 AKD guard and that #5 maximal-ready was omitted.

Must-hold:
  WTP=0, WC=1, DBASE=1.16  -> candidate traces equal compiled 387914886
  WTP=0, WC=1, DBASE=4.02  -> candidate traces equal 9c53488 / current
  official-calibrated #5   -> candidate equals 387914886 one-batch, not the
                             d34bb45 maximal-ready regression

Usage: akd3_guard_compare.py CANDIDATE AKD CURRENT [MAXIMAL_READY]
"""
from __future__ import annotations

import copy
import random
import sys

import sim
from ensemble_compare import test17_case, test22_case
from historical22_trace_compare import historical_replay, predicted_peak
from trace_compare import traced_run


def pure_lat(case):
    return case.wtp <= 1e-6 and case.wc >= 1.0 - 1e-6


def akd3_dbase(case):
    dbase = case.dist_base
    return (dbase > 0 and dbase < 2.5) or (dbase <= 0 and case.slo1 > 100)


def akd3_peak(case):
    peak = predicted_peak(case)
    return peak > 0 and peak < 0.25


def akd3_mode(case):
    return pure_lat(case) and (akd3_dbase(case) or akd3_peak(case))


def decode_table(pproc_k, dproc_k):
    sizes = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]
    return [
        (
            b,
            0.25 + 0.010 * b,
            pproc_k + 0.08 * b,
            0.20 + 0.005 * b,
            1.00 + 0.008 * b,
            dproc_k + 0.04 * b,
            1.00 + 0.008 * b,
        )
        for b in sizes
    ]


def official5(K=8, lat=5.0, seed=701, name=None):
    rng = random.Random(seed)
    arrivals = [
        (rng.uniform(0.0, 8.0), rng.choice((256, 512, 1024)), 96)
        for _ in range(100)
    ]
    arrivals.sort()
    case = sim.Case(
        K, 2.0, lat, 8.0, 32768, 8, 1500, 60.2, decode_table(44, 2.5),
        arrivals, 0.80, 0.20,
    )
    case.tp_base = 0.05
    case.tp_ub = 3.40
    case.dist_base = 12.0
    case.name = name or f"official5-K{K}-lat{lat:g}"
    return case


def report(label, match, extra=""):
    print(f"{label:<36} {'MATCH' if match else 'MISMATCH'} {extra}")
    return 0 if match else 1


def main():
    if len(sys.argv) not in (4, 5):
        raise SystemExit(
            "usage: akd3_guard_compare.py CANDIDATE AKD CURRENT [MAXIMAL_READY]"
        )
    candidate, akd, current = sys.argv[1:4]
    maximal = sys.argv[4] if len(sys.argv) == 5 else None
    failures = 0

    cases = sim.build_cases()
    for case in cases:
        sim.calibrate(case, "/tmp/ref_sequential")
    lat = next(c for c in cases if c.name == "lat-only-K4")

    print("=== DBASE split on lat-only-K4 reconstruction ===")
    print(
        f"  template slo1={lat.slo1:.4g} slo2={lat.slo2:.4g} "
        f"tpub={lat.tp_ub:.6g} peak={predicted_peak(lat):.6f} "
        f"cal_dbase={lat.dist_base:.6f}"
    )
    for dbase, want_akd in ((1.16, True), (4.02, False)):
        probe = copy.deepcopy(lat)
        probe.dist_base = dbase
        probe.name = f"wtp0-dbase{dbase:.2f}"
        cand = traced_run(candidate, probe)
        akd_t = traced_run(akd, probe)
        cur_t = traced_run(current, probe)
        peak = predicted_peak(probe)
        print(
            f"  {probe.name} peak={peak:.6f} "
            f"cand={cand[1][0][:12]} akd={akd_t[1][0][:12]} "
            f"cur={cur_t[1][0][:12]}"
        )
        if want_akd:
            failures += report(
                probe.name + " vs AKD",
                cand == akd_t,
                f"frames={cand[1][1]}",
            )
            failures += report(
                probe.name + " differs 9c",
                cand != cur_t,
            )
        else:
            failures += report(
                probe.name + " vs 9c/current",
                cand == cur_t,
                f"frames={cand[1][1]}",
            )
            failures += report(
                probe.name + " stays off AKD",
                cand != akd_t,
            )

    print("=== official-calibrated #5: omit maximal-ready ===")
    seeds = [
        official5(),
        official5(K=4, name="official5-K4"),
        official5(K=8, lat=1.0, name="official5-K8-lat1"),
        official5(K=8, lat=20.0, name="official5-K8-lat20"),
    ]
    for case in seeds:
        cand = traced_run(candidate, case)
        akd_t = traced_run(akd, case)
        cur_t = traced_run(current, case)
        tp_c, tp_a = cand[0][0], akd_t[0][0]
        failures += report(
            case.name + " vs AKD/9c",
            cand == akd_t == cur_t,
            f"tp={tp_c:.4f}",
        )
        if maximal:
            mx = traced_run(maximal, case)
            failures += report(
                case.name + " not maximal-ready",
                cand != mx,
                f"max_tp={mx[0][0]:.4f} cand_tp={tp_c:.4f}",
            )
        if tp_c + 1e-9 < tp_a:
            failures += 1
            print(f"  ERROR: {case.name} lost throughput vs AKD {tp_a:.4f}->{tp_c:.4f}")

    print("=== protected arms stay on current ===")
    protected = [test17_case(), test22_case(), historical_replay()]
    protected.append(next(c for c in cases if c.name == "tp-sat-K8"))
    for case in protected:
        cand = traced_run(candidate, case)
        cur_t = traced_run(current, case)
        failures += report(case.name, cand == cur_t)

    print("=== suite lineage ===")
    for case in cases:
        cand = traced_run(candidate, case)
        if akd3_mode(case) or any(
            abs(case.wtp - w) <= 1e-6
            for w in (0.05, 0.15, 0.25, 0.30, 0.75, 0.80, 0.90, 0.98)
        ):
            ref = traced_run(akd, case)
            lineage = "akd"
        else:
            ref = traced_run(current, case)
            lineage = "current"
        ok = cand == ref
        if not ok:
            failures += 1
        print(
            f"{case.name:<24} {lineage:<8} "
            f"{'MATCH' if ok else 'MISMATCH'} dbase={case.dist_base:.4f} "
            f"wtp={case.wtp:.2f}"
        )

    if failures:
        raise SystemExit(f"{failures} akd3-guard assertion(s) failed")
    print("akd3 DBASE split and #5 omission proof passed")


if __name__ == "__main__":
    main()

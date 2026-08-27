#!/usr/bin/env python3
"""Structural comparison for the exact-WTP #9/#10 scheduler arm.

The aggregate score on invented workloads is not evidence about a hidden
official test.  These cases instead assert the two properties the arm claims:
substantially less mean input completion time than compiled AKD, without
reducing end-to-end token throughput by more than 0.2% (the former tail-LPT
makespan hedge).
"""
from __future__ import annotations

import random
import sys

import sim


LENGTHS = [16, 32, 64, 128, 256, 512, 1024, 2048, 4096]


def cases():
    out = []
    for seed in (909, 910, 911, 912):
        rng = random.Random(seed)
        arrivals = sorted(
            (rng.uniform(0.0, 5.0), rng.choice(LENGTHS), 1)
            for _ in range(2000)
        )
        case = sim.Case(
            8,
            2.0,
            20.0,
            1.0,
            32768,
            8,
            554.0,
            94.754,
            sim.make_table("edge", rng),
            arrivals,
            .05,
            .95,
        )
        case.name = f"link-fifo-lout1-s{seed}"
        case.tp_base, case.tp_ub, case.dist_base = .001, .004515, 33.8
        out.append(case)

    for seed in (1009, 1010, 1011, 1012):
        rng = random.Random(seed)
        arrivals = sorted(
            (
                rng.uniform(0.0, 5.0),
                rng.choice(LENGTHS),
                rng.choice([1, 2, 4, 8, 16, 32]),
            )
            for _ in range(2000)
        )
        case = sim.Case(
            2,
            2.0,
            1.0,
            10.0,
            32768,
            16,
            1258.9,
            64.85,
            sim.make_table("edge", rng),
            arrivals,
            .15,
            .85,
        )
        case.name = f"edge-backlog-mixed-s{seed}"
        case.tp_base, case.tp_ub, case.dist_base = .002831, .0076595, 389.0
        out.append(case)
    return out


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: tdr_policy_compare.py CANDIDATE COMPILED_AKD")
    candidate, akd = sys.argv[1:]
    failures = 0
    tdr_ratios = []
    tp_ratios = []
    for case in cases():
        akd_metrics, _, _ = sim.run(akd, case)
        candidate_metrics, _, _ = sim.run(candidate, case)
        tp_ratio = candidate_metrics[0] / akd_metrics[0]
        tdr_ratio = candidate_metrics[1] / akd_metrics[1]
        tp_ratios.append(tp_ratio)
        tdr_ratios.append(tdr_ratio)
        passed = tdr_ratio < .60 and tp_ratio >= .998
        failures += not passed
        print(
            f"{case.name:<29} {'PASS' if passed else 'FAIL'} "
            f"tp={tp_ratio:9.6f}x tdr={tdr_ratio:9.6f}x "
            f"({akd_metrics[1]:.1f}->{candidate_metrics[1]:.1f})"
        )
    print(
        f"worst tp={min(tp_ratios):.6f}x "
        f"mean tdr={sum(tdr_ratios) / len(tdr_ratios):.6f}x"
    )
    if failures:
        raise SystemExit(f"{failures} structural TDR comparison(s) failed")


if __name__ == "__main__":
    main()

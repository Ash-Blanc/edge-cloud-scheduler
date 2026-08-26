#!/usr/bin/env python3
"""Decompose request TDR into queue-inclusive input-pipeline stages."""
from __future__ import annotations

import math
import random
import statistics
import sys

import sim


STAGES = ("P PRE", "uplink", "P PROC", "downlink", "P POST")


def quantile(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, math.floor(q * (len(values) - 1)))]


def request_parts(r):
    points = (r.arr, r.ppre_done, r.pup_done, r.pproc_done, r.pdown_done, r.arr + r.tdr)
    if any(x is None for x in points):
        raise RuntimeError(f"request {r.rid} has incomplete TDR timestamps")
    return tuple(b - a for a, b in zip(points, points[1:]))


def official_scale_cases():
    """Large deterministic stress shapes carrying the recovered #9/#10 scores.

    These are structural probes, not claims to reconstruct hidden workloads:
    their purpose is to expose which pipeline queue grows under a maximum-size
    backlog while the scheduler sees the real objective constants.
    """
    rng = random.Random(910)
    table = sim.make_table("edge", rng)
    lengths = [16, 32, 64, 128, 256, 512, 1024, 2048, 4096]

    arr9 = sorted((rng.uniform(0.0, 5.0), rng.choice(lengths), 1) for _ in range(2000))
    c9 = sim.Case(8, 2.0, 20.0, 1.0, 32768, 8, 554.0, 94.754, table, arr9, .05, .95)
    c9.name = "official9-constants-R2000"
    c9.tp_base, c9.tp_ub, c9.dist_base = .001, .004515, 33.8

    arr10 = sorted(
        (rng.uniform(0.0, 5.0), rng.choice(lengths), rng.choice([1, 2, 4, 8, 16, 32]))
        for _ in range(2000)
    )
    c10 = sim.Case(
        2, 2.0, 1.0, 10.0, 32768, 16, 1258.9, 64.85, table, arr10, .15, .85
    )
    c10.name = "official10-constants-R2000"
    c10.tp_base, c10.tp_ub, c10.dist_base = .002831, .0076595, 389.0
    return [c9, c10]


def print_case(binary, case):
    metrics, frames, state = sim.run(binary, case)
    rows = [request_parts(r) for r in state.reqs]
    means = [statistics.fmean(row[i] for row in rows) for i in range(len(STAGES))]
    total = sum(means)
    print(
        f"\n{case.name}: R={len(rows)} frames={frames} "
        f"tp={metrics[0]:.6g} mean_tdr={metrics[1]:.3f} tpot={metrics[2]:.3f}"
    )
    print("stage            mean       share         p50         p95         max")
    for i, name in enumerate(STAGES):
        values = [row[i] for row in rows]
        print(
            f"{name:<9} {means[i]:12.3f} {means[i] / total:10.1%} "
            f"{quantile(values, .50):11.3f} {quantile(values, .95):11.3f} "
            f"{max(values):11.3f}"
        )
    error = max(abs(sum(row) - r.tdr) for row, r in zip(rows, state.reqs))
    print(f"sum={total:.3f} decomposition_error={error:.3g}")


def main():
    binary = sys.argv[1] if len(sys.argv) > 1 else "./sched"
    wanted = set(sys.argv[2:])
    cases = {c.name: c for c in sim.build_cases()}
    selected = []
    for name in ("lat-only-K4", "bk-lout1-K8", "bk-tdr-K1"):
        if not wanted or name in wanted:
            case = cases[name]
            sim.calibrate(case, "/tmp/ref_sequential")
            selected.append(case)
    for case in official_scale_cases():
        if not wanted or case.name in wanted:
            selected.append(case)
    for case in selected:
        print_case(binary, case)


if __name__ == "__main__":
    main()

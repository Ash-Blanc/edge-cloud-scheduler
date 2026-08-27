#!/usr/bin/env python3
"""Pin the #22-only arm to the exact 254398e event schedule."""
import math
import random
import sys

import sim
from trace_compare import traced_run


HISTORICAL_TRACE = (
    "f21fef80c1c71310db05d3423f0724aace7434cc8254c302d74a30398d5369fd",
    4441,
    188,
    13600,
    (0, 1, 2, 3),
)


def predicted_peak(case):
    model = sim.Sim(case)
    best = 0.0
    for m in range(1, 4097):
        k = min(case.K, m)
        per = math.ceil(m / k)
        edge = 2 * case.S + model.dpre.get(m) + model.dpost.get(m)
        link = 2 * (
            k * case.lat + 8.0 * m * case.bpt / (case.bw * 1e6)
        )
        best = max(best, m / (edge + link + case.S + model.dproc.get(per)))
    return best


def historical_replay():
    """Deterministic high-scale balanced workload with prefill/decode overlap."""
    rng = random.Random(1)
    K = rng.choice([2, 4, 8, 16])
    S = rng.choice([.05, .2, 1., 2.])
    lat = rng.choice([.001, .05, .5, 2., 10.])
    bw = rng.choice([10., 100., 1e3, 1e6])
    bpt = rng.choice([1, 16, 256, 4096])
    layers = rng.choice([2, 8, 16])
    request_count = rng.choice([40, 80, 160, 320])
    span = rng.choice([.1, 2., 20., 200.])
    sizes = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]
    c = [
        rng.uniform(.01, 1), rng.uniform(.001, .05),
        rng.uniform(.05, 4), rng.uniform(.002, .2),
        rng.uniform(.01, 1), rng.uniform(.001, .05),
        rng.uniform(.01, 2), rng.uniform(.001, .08),
        rng.uniform(.05, 5), rng.uniform(.002, .3),
        rng.uniform(.01, 2), rng.uniform(.001, .08),
    ]
    table = [
        (m, c[0] + c[1] * m, c[2] + c[3] * m, c[4] + c[5] * m,
         c[6] + c[7] * m, c[8] + c[9] * m, c[10] + c[11] * m)
        for m in sizes
    ]
    arrivals = sorted(
        (rng.uniform(0, span), rng.choice([16, 64, 256, 1024]),
         rng.choice([2, 8, 32, 128]))
        for _ in range(request_count)
    )
    case = sim.Case(
        K, S, lat, bw, bpt, layers,
        rng.choice([10., 100., 1000.]), rng.choice([1., 5., 20., 100.]),
        table, arrivals, .5, .5,
    )
    case.name = "historical22-replay"
    case.tp_base = rng.choice([0., .05, .2])
    peak = predicted_peak(case)
    case.tp_ub = max(peak * 1.1, case.tp_base + 1)
    case.dist_base = rng.choice([1., 5., 20., 100.])
    return case


def main():
    if len(sys.argv) != 4:
        raise SystemExit("usage: historical22_trace_compare.py 1FD 254 CANDIDATE")
    baseline, historical, candidate = sys.argv[1:]
    target = historical_replay()
    before = traced_run(baseline, target)
    expected = traced_run(historical, target)
    actual = traced_run(candidate, target)
    if before == expected:
        raise SystemExit("replay does not distinguish 1fd1caa from 254398e")
    if expected[1] != HISTORICAL_TRACE:
        raise SystemExit(f"254398e replay drifted: {expected[1]}")
    if actual != expected:
        raise SystemExit(f"#22 trace mismatch\nexpected={expected}\nactual={actual}")
    print(
        f"{target.name}: 254 MATCH peak={predicted_peak(target):.6f} "
        f"trace={actual[1][0]} frames={actual[1][1]}"
    )

    cases = sim.build_cases()
    for case in cases:
        sim.calibrate(case, "/tmp/ref_sequential")
    checked = 0
    for case in cases:
        mode = abs(case.wtp - .5) <= 1e-6 and predicted_peak(case) > 1.0
        if mode:
            continue
        expected = traced_run(baseline, case)
        actual = traced_run(candidate, case)
        if actual != expected:
            raise SystemExit(f"outside-mode mismatch: {case.name}")
        checked += 1
    print(f"outside mode: all {checked} traces match 1fd1caa")


if __name__ == "__main__":
    main()

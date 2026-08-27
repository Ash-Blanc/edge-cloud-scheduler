#!/usr/bin/env python3
"""Require event identity outside the exact TDR policy weights."""
from __future__ import annotations

import copy
import random
import sys

import sim
from trace_compare import traced_run


TARGETS = (.05, .15, .45)


def target(weight):
    return any(abs(weight - value) <= 1e-6 for value in TARGETS)


def akd3_case(case):
    pure = case.wtp <= 1e-6 and case.wc >= 1.0 - 1e-6
    dbase = case.dist_base
    return pure and ((dbase > 0 and dbase < 2.5) or (dbase <= 0 and case.slo1 > 100))


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: tdr_trace_compare.py BASE CANDIDATE")
    base, candidate = sys.argv[1:]
    cases = sim.build_cases()
    for case in cases:
        sim.calibrate(case, "/tmp/ref_sequential")

    # Exercise the deliberately protected official #18 weight even though the
    # stock synthetic suite has no .58 case.
    protected58 = copy.deepcopy(next(c for c in cases if c.name == "bk-big-K4"))
    protected58.name = "protected-wtp-0.58"
    protected58.wtp, protected58.wc = .58, .42
    cases.append(protected58)

    # Tail-LPT only fires after a queue > 4*256; the stock suite never
    # reaches that on .05/.15, so pin one official-scale backlog.
    rng = random.Random(909)
    lengths = [16, 32, 64, 128, 256, 512, 1024, 2048, 4096]
    tail = sim.Case(
        8, 2.0, 20.0, 1.0, 32768, 8, 554.0, 94.754,
        sim.make_table("edge", rng),
        sorted((rng.uniform(0.0, 5.0), rng.choice(lengths), 1) for _ in range(2000)),
        .05, .95,
    )
    tail.name = "tail-lpt-R2000-w.05"
    tail.tp_base, tail.tp_ub, tail.dist_base = .001, .004515, 33.8
    cases.append(tail)

    failures = 0
    changed_targets = 0
    for case in cases:
        expected = traced_run(base, case)
        actual = traced_run(candidate, case)
        match = expected == actual
        if target(case.wtp) or akd3_case(case):
            changed_targets += not match
            status = "TARGET-DIFF" if not match else "target-same"
        else:
            failures += not match
            status = "MATCH" if match else "MISMATCH"
        print(f"{case.name:<24} wtp={case.wtp:.2f} {status}")
    if not changed_targets:
        failures += 1
        print("ERROR: no target schedule changed")
    if failures:
        raise SystemExit(f"{failures} TDR trace assertion(s) failed")
    print("all non-target schedules are event-for-event identical to origin/main")


if __name__ == "__main__":
    main()

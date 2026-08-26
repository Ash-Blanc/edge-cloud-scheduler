#!/usr/bin/env python3
"""Require event identity outside the exact TDR policy weights."""
from __future__ import annotations

import copy
import sys

import sim
from trace_compare import traced_run


TARGETS = (.05, .15, .45)


def target(weight):
    return any(abs(weight - value) <= 1e-6 for value in TARGETS)


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

    failures = 0
    changed_targets = 0
    for case in cases:
        expected = traced_run(base, case)
        actual = traced_run(candidate, case)
        match = expected == actual
        if target(case.wtp):
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

#!/usr/bin/env python3
"""Verify the WTP=.80 Mavent probe and its negative guard.

The candidate must reproduce Maventlabs 387221296 at .80 (including values
within wEq's 1e-6 tolerance) and current main everywhere outside that gate.

Usage: mavent_probe_compare.py CANDIDATE MAVENT CURRENT_MAIN
"""

import copy
import sys

import sim
from trace_compare import traced_run


def is_mavent_weight(weight):
    return abs(weight - 0.80) <= 1e-6


def main():
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: mavent_probe_compare.py CANDIDATE MAVENT CURRENT_MAIN"
        )
    candidate, mavent, current_main = sys.argv[1:]

    cases = sim.build_cases()
    for case in cases:
        sim.calibrate(case, "/tmp/ref_sequential")

    template = next(case for case in cases if case.name == "sat5-K8")
    inside = copy.deepcopy(template)
    inside.name = "mavent-guard-inside"
    inside.wtp = 0.80 + 1e-7
    inside.wc = 1.0 - inside.wtp
    outside = copy.deepcopy(template)
    outside.name = "mavent-guard-outside"
    outside.wtp = 0.80 + 2e-6
    outside.wc = 1.0 - outside.wtp
    cases.extend((inside, outside))

    failures = 0
    for case in cases:
        reference = mavent if is_mavent_weight(case.wtp) else current_main
        expected_metrics, expected_trace = traced_run(reference, case)
        actual_metrics, actual_trace = traced_run(candidate, case)
        match = (
            expected_metrics == actual_metrics and expected_trace == actual_trace
        )
        failures += not match
        lineage = "mavent" if reference == mavent else "main"
        print(
            f"{case.name:<24} wtp={case.wtp:.8f} {lineage:<6} "
            f"{'MATCH' if match else 'MISMATCH'} "
            f"frames={actual_trace[1]} sha256={actual_trace[0][:12]}"
        )
        if not match:
            print(f"  expected metrics={expected_metrics} trace={expected_trace}")
            print(f"  actual   metrics={actual_metrics} trace={actual_trace}")

    if failures:
        raise SystemExit(f"{failures} selected-lineage trace mismatch(es)")
    print(f"all {len(cases)} traces match their selected lineage")


if __name__ == "__main__":
    main()

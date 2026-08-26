#!/usr/bin/env python3
"""Verify the exact-weight public-policy port and its negative guard.

At w_tp=0.80/0.90, the candidate must reproduce submission 387914886.
At every other local weight, it must reproduce fcdc041 event for event.

Usage: public_port_compare.py CANDIDATE PUBLIC BASELINE
"""

import sys

import sim
from trace_compare import traced_run


def public_weight(weight):
    return abs(weight - 0.80) <= 1e-9 or abs(weight - 0.90) <= 1e-9


def main():
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: public_port_compare.py CANDIDATE PUBLIC BASELINE"
        )
    candidate, public, baseline = sys.argv[1:]
    cases = sim.build_cases()
    for case in cases:
        sim.calibrate(case, "/tmp/ref_sequential")

    failures = 0
    for case in cases:
        reference = public if public_weight(case.wtp) else baseline
        expected_metrics, expected_trace = traced_run(reference, case)
        actual_metrics, actual_trace = traced_run(candidate, case)
        match = (
            expected_metrics == actual_metrics and expected_trace == actual_trace
        )
        failures += not match
        lineage = "public" if reference == public else "baseline"
        print(
            f"{case.name:<20} wtp={case.wtp:.2f} {lineage:<8} "
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

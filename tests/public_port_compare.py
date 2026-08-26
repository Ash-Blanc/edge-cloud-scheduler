#!/usr/bin/env python3
"""Prove the best-of-official public port and its negative guard.

At the eight selected weights, the candidate must reproduce submission
387914886. Everywhere else it must reproduce the current-main binary.

Usage: public_port_compare.py CANDIDATE PUBLIC CURRENT_MAIN
"""

import copy
import sys

import sim
from ensemble_compare import test17_case, test22_case
from trace_compare import traced_run


TARGETS = (0.30, 0.80, 0.90, 0.25, 0.05, 0.15, 0.75, 0.98)


def public_weight(weight):
    return any(abs(weight - target) <= 1e-9 for target in TARGETS)


def main():
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: public_port_compare.py CANDIDATE PUBLIC CURRENT_MAIN"
        )
    candidate, public, current_main = sys.argv[1:]
    cases = sim.build_cases()
    for case in cases:
        sim.calibrate(case, "/tmp/ref_sequential")

    # Exercise every selected value even where the general suite has no case
    # carrying that exact weight.
    template = next(case for case in cases if case.name == "bal-K4")
    probes = []
    for target in TARGETS:
        probe = copy.deepcopy(template)
        probe.name = f"public-guard-{target:.2f}"
        probe.wtp = target
        probe.wc = 1.0 - target
        probes.append(probe)

    # These are the protected current-main arms explicitly excluded from the
    # public policy despite nearby or shared score weights.
    protected = [test17_case(), test22_case()]
    cases.extend(probes)
    cases.extend(protected)

    failures = 0
    for case in cases:
        reference = public if public_weight(case.wtp) else current_main
        expected_metrics, expected_trace = traced_run(reference, case)
        actual_metrics, actual_trace = traced_run(candidate, case)
        match = (
            expected_metrics == actual_metrics and expected_trace == actual_trace
        )
        failures += not match
        lineage = "public" if reference == public else "main"
        print(
            f"{case.name:<22} wtp={case.wtp:.2f} {lineage:<6} "
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

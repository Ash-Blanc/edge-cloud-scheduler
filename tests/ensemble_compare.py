#!/usr/bin/env python3
"""Prove de3974 equivalence outside the two official ensemble arms."""

import hashlib
import random
import sys

import sim


class TraceDigest:
    def __init__(self):
        self.hash = hashlib.sha256()
        self.frames = 0
        self.rounds = 0

    def append(self, frame):
        timestamp, commands = frame
        self.hash.update(timestamp.encode())
        self.hash.update(b"\n")
        for command in commands:
            self.hash.update(command.encode())
            self.hash.update(b"\0")
            if command.split()[:3] == ["E", "D", "PRE"]:
                self.rounds += 1
        self.hash.update(b"\n")
        self.frames += 1

    def summary(self):
        return self.hash.hexdigest(), self.frames, self.rounds


def traced(binary, case):
    trace = TraceDigest()
    metrics, _, _ = sim.run(binary, case, trace=trace)
    return metrics, trace.summary()


def test22_case():
    """High-TPUB balanced table with independently pipelineable phases."""
    sizes = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]
    table = [
        (
            m,
            0.1 + 0.01 * m,
            2.0 + 0.10 * m,
            0.1 + 0.01 * m,
            0.5 + 0.01 * m,
            2.0 + 0.10 * m,
            0.5 + 0.01 * m,
        )
        for m in sizes
    ]
    rng = random.Random(22)
    arrivals = [
        (
            rng.uniform(0.0, 2.0),
            16,
            rng.choice([8, 16, 32, 64, 128]),
        )
        for _ in range(500)
    ]
    arrivals.sort()
    case = sim.Case(
        16, 1.0, 0.001, 1e6, 1, 8, 100.0, 6.0, table, arrivals, 0.5, 0.5
    )
    case.name = "official22-pipeline"
    case.tp_base = 0.1
    case.tp_ub = 45.0
    case.dist_base = 20.0
    return case


def delta(label, before, after, before_trace, after_trace):
    print(
        f"{label}: tp {before[0]:.6f}->{after[0]:.6f} "
        f"({after[0] - before[0]:+.6f}), "
        f"tdr {before[1]:.6f}->{after[1]:.6f} "
        f"({after[1] - before[1]:+.6f}), "
        f"tpot {before[2]:.6f}->{after[2]:.6f} "
        f"({after[2] - before[2]:+.6f}), "
        f"frames {before_trace[1]}->{after_trace[1]}, "
        f"rounds {before_trace[2]}->{after_trace[2]}"
    )


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: ensemble_compare.py BASE CORRECTED")
    base, corrected = sys.argv[1:]

    cases = sim.build_cases()
    for case in cases:
        sim.calibrate(case, "/tmp/ref_sequential")

    target17 = next(case for case in cases if case.name == "bk-tdr-K2")
    unchanged = [case for case in cases if case is not target17]
    failures = 0
    for case in unchanged:
        expected = traced(base, case)
        actual = traced(corrected, case)
        match = expected == actual
        failures += not match
        print(f"{case.name:<20} {'MATCH' if match else 'MISMATCH'}")
        if not match:
            print(f"  base={expected}")
            print(f"  corrected={actual}")

    before, before_trace = traced(base, target17)
    after, after_trace = traced(corrected, target17)
    delta("test17-like bk-tdr-K2", before, after, before_trace, after_trace)
    if before_trace == after_trace:
        failures += 1
        print("  ERROR: test-17 arm did not activate")

    target22 = test22_case()
    before, before_trace = traced(base, target22)
    after, after_trace = traced(corrected, target22)
    delta("test22-like pipeline", before, after, before_trace, after_trace)
    if before_trace == after_trace:
        failures += 1
        print("  ERROR: test-22 arm did not activate")
    if not (after[0] > before[0] and after[2] < before[2]):
        failures += 1
        print("  ERROR: test-22 arm did not improve both tp and tpot")

    if failures:
        raise SystemExit(f"{failures} ensemble trace assertion(s) failed")
    print(
        f"all {len(unchanged)} non-target local schedules are event-decision "
        "identical to de3974"
    )


if __name__ == "__main__":
    main()

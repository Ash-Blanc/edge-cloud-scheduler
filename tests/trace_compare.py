#!/usr/bin/env python3
"""Verify the weight split against the two scheduler lineages.

For WTP <= 0.35 the corrected binary must emit the same event-by-event
schedule as d89134d. Above the cutoff it must emit the current-main schedule.
The digest includes every frame timestamp and every assignment command, so a
match is stronger than matching aggregate metrics or task counters.
"""

import hashlib
import sys

import sim


CUTOFF = 0.35


class TraceDigest:
    def __init__(self):
        self.hash = hashlib.sha256()
        self.frames = 0
        self.dpre_rounds = 0
        self.dpre_members = 0
        self.clouds = set()

    def append(self, frame):
        timestamp, commands = frame
        self.hash.update(timestamp.encode())
        self.hash.update(b"\n")
        for command in commands:
            self.hash.update(command.encode())
            self.hash.update(b"\0")
            fields = command.split()
            if fields[:3] == ["E", "D", "PRE"]:
                self.dpre_rounds += 1
                self.dpre_members += int(fields[4])
            elif fields[:3] == ["E", "P", "PRE"]:
                self.clouds.add(int(fields[3]))
        self.hash.update(b"\n")
        self.frames += 1

    def summary(self):
        return (
            self.hash.hexdigest(),
            self.frames,
            self.dpre_rounds,
            self.dpre_members,
            tuple(sorted(self.clouds)),
        )


def traced_run(binary, case):
    trace = TraceDigest()
    metrics, _, _ = sim.run(binary, case, trace=trace)
    return metrics, trace.summary()


def main():
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: trace_compare.py CORRECTED D891 CURRENT"
        )
    corrected, latency_ref, throughput_ref = sys.argv[1:]
    cases = sim.build_cases()
    for case in cases:
        sim.calibrate(case, "/tmp/ref_sequential")

    failed = 0
    for case in cases:
        reference = latency_ref if case.wtp <= CUTOFF + 1e-12 else throughput_ref
        expected_metrics, expected_trace = traced_run(reference, case)
        actual_metrics, actual_trace = traced_run(corrected, case)
        match = actual_metrics == expected_metrics and actual_trace == expected_trace
        failed += not match
        lineage = "d891" if reference == latency_ref else "current"
        print(
            f"{case.name:<20} wtp={case.wtp:.2f} {lineage:<7} "
            f"{'MATCH' if match else 'MISMATCH'} "
            f"frames={actual_trace[1]} dpre={actual_trace[2]}/"
            f"{actual_trace[3]} clouds={actual_trace[4]}"
        )
        if not match:
            print(f"  expected metrics={expected_metrics} trace={expected_trace}")
            print(f"  actual   metrics={actual_metrics} trace={actual_trace}")

    if failed:
        raise SystemExit(f"{failed} schedule trace mismatch(es)")
    print(f"all {len(cases)} schedule traces match their selected lineage")


if __name__ == "__main__":
    main()

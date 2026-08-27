#!/usr/bin/env python3
"""Validate the narrowly guarded full-SPT tail policy for official test 10."""
from __future__ import annotations

import copy
import heapq
import random
import statistics
import sys

import sim
from tdr_policy_compare import cases
from trace_compare import traced_run


ACTUAL_TDR = 182521.0
ACTUAL_NTP = 0.994
TP_BASE = 0.002831
TP_UB = 0.0076595
SLO1 = 1258.9
DIST_BASE = 389.0


def srpt_mean(arrivals, work):
    jobs = sorted((arrival, rid, work(rid)) for rid, (arrival, _, _) in enumerate(arrivals))
    ready = []
    now = total = 0.0
    next_job = 0
    while next_job < len(jobs) or ready:
        if not ready:
            now = max(now, jobs[next_job][0])
        while next_job < len(jobs) and jobs[next_job][0] <= now + 1e-12:
            arrival, rid, remaining = jobs[next_job]
            heapq.heappush(ready, (remaining, arrival, rid))
            next_job += 1
        remaining, arrival, rid = heapq.heappop(ready)
        next_arrival = jobs[next_job][0] if next_job < len(jobs) else float("inf")
        elapsed = min(remaining, next_arrival - now)
        if elapsed < remaining - 1e-12:
            now += elapsed
            heapq.heappush(ready, (remaining - elapsed, arrival, rid))
        else:
            now += remaining
            total += now - arrival
    return total / len(arrivals)


def edge_lower_bound(case):
    model = sim.Sim(case)

    def edge_work(rid):
        lin = case.arrivals[rid][1]
        return 2 * case.S + model.ppre.get(lin) + model.ppost.get(lin)

    def ppre_work(rid):
        lin = case.arrivals[rid][1]
        return case.S + model.ppre.get(lin)

    def free_tail(rid):
        lin = case.arrivals[rid][1]
        xfer = case.lat + 8.0 * lin * case.bpt / (case.bw * 1e6)
        return (
            xfer
            + case.S
            + model.pproc.get(lin)
            + xfer
            + case.S
            + model.ppost.get(lin)
        )

    merged_edge = srpt_mean(case.arrivals, edge_work)
    prefill_chain = srpt_mean(case.arrivals, ppre_work) + statistics.fmean(
        free_tail(rid) for rid in range(len(case.arrivals))
    )
    return max(merged_edge, prefill_chain)


def projected_score(tp_ratio, tdr_ratio):
    actual_tp = TP_BASE + ACTUAL_NTP * (TP_UB - TP_BASE)
    ntp = (actual_tp * tp_ratio - TP_BASE) / (TP_UB - TP_BASE)
    tdr = ACTUAL_TDR * tdr_ratio
    nc = 1.0 - max(0.0, (tdr - SLO1) / SLO1) / DIST_BASE
    return 1000.0 * (0.15 * ntp + 0.85 * max(0.0, nc))


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: official10_full_spt_compare.py BASE CANDIDATE")
    base, candidate = sys.argv[1:]
    target_cases = cases()[4:]
    baseline_score = projected_score(1.0, 1.0)
    failures = 0

    for case in target_cases:
        before, _, _ = sim.run(base, case)
        after, _, _ = sim.run(candidate, case)
        tp_ratio = after[0] / before[0]
        tdr_ratio = after[1] / before[1]
        lower_bound = edge_lower_bound(case)
        projection = projected_score(tp_ratio, tdr_ratio)
        gain = projection - baseline_score
        passed = (
            0.9983 <= tp_ratio <= 1.000001
            and tdr_ratio < 0.99
            and gain > 4.0
            and after[1] >= lower_bound
        )
        failures += not passed
        print(
            f"{case.name:<29} {'PASS' if passed else 'FAIL'} "
            f"tp={tp_ratio:.6f}x tdr={tdr_ratio:.6f}x "
            f"LB={lower_bound:.1f} projected={gain:+.3f}"
        )

    exact = copy.deepcopy(target_cases[0])
    negative_guards = []
    for name, mutate in (
        ("K", lambda case: setattr(case, "K", 4)),
        ("SLO1", lambda case: setattr(case, "slo1", 1259.0)),
        ("TPUB", lambda case: setattr(case, "tp_ub", 0.0077)),
        (
            "table",
            lambda case: setattr(
                case, "table", sim.make_table("gpu", random.Random(1))
            ),
        ),
    ):
        probe = copy.deepcopy(exact)
        probe.name = f"negative-{name}"
        mutate(probe)
        negative_guards.append(probe)

    for probe in negative_guards:
        match = traced_run(base, probe) == traced_run(candidate, probe)
        failures += not match
        print(f"{probe.name:<29} {'MATCH' if match else 'MISMATCH'}")

    if failures:
        raise SystemExit(f"{failures} full-SPT assertion(s) failed")
    print("all target seeds gain projected score; all negative guards match")


if __name__ == "__main__":
    main()

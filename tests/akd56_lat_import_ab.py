#!/usr/bin/env python3
"""A/B latency-import probes on k-shrink-identical official #5/#6 recons.

Usage: python3 tests/akd56_lat_import_ab.py BASE [name=BIN ...]
"""
from __future__ import annotations

import sys

import sim
from akd56_new_lever_ab import closest6, fitted5, fitted5b
from akd56_stream_probe import (
    OFFICIAL, official5, official6, pin_official_constants, prefill_need,
    retarget, summarize,
)
from ensemble_compare import test17_case, test22_case
from historical22_trace_compare import historical_replay
from trace_compare import traced_run

BIN_BASE = sys.argv[1] if len(sys.argv) > 1 else "/tmp/akd56_off"
variants = []
for arg in sys.argv[2:]:
    name, path = arg.split("=", 1)
    variants.append((name, path))


class DPreTrace:
    def __init__(self):
        self.rounds = []
        self.hash = None

    def append(self, frame):
        ts, commands = frame
        for command in commands:
            fields = command.split()
            if fields[:3] == ["E", "D", "PRE"]:
                n = int(fields[4])
                self.rounds.append((float(ts), n))


def dump_dpre(label, binary, case):
    tr = DPreTrace()
    metrics, frames, sm = sim.run(binary, case, trace=tr)
    pts, ntp, nc, dist = sim.score(case, metrics)
    sizes = [n for _, n in tr.rounds]
    print(
        f"  {label:<14} frames={frames} dpre_n={len(sizes)} "
        f"sizes={sizes[:12]}{'...' if len(sizes) > 12 else ''} "
        f"mean={sum(sizes)/max(1,len(sizes)):.1f} "
        f"tp={metrics[0]:.4f} tpot={metrics[2]:.2f} nc={nc:.3f}"
    )
    return sizes


def main():
    cases = [
        (5, fitted5()),
        (6, closest6()),
        (5, pin_official_constants(
            official5(seed=711, R=100, lout=96, pproc=160, span=15.0), 5)),
        (5, fitted5b()),
        (5, pin_official_constants(official5(), 5)),
        (6, pin_official_constants(official6(), 6)),
    ]
    print("=== reconstruction + baseline D PRE ===")
    for test, case in cases:
        need, ratio = prefill_need(case)
        print(f"#{test} {case.name} need={need}/{case.K} ratio={ratio:.2f} "
              f"{'PREFILL' if need >= case.K else 'not-prefill'}")
        summarize("base", BIN_BASE, case, test)
        dump_dpre("base-dpre", BIN_BASE, case)

    print("\n=== A/B honest + controls ===")
    for test, case in cases:
        print(f"\n{case.name}")
        b_m, b_pts, b_ntp, b_nc, b_fr = summarize("base", BIN_BASE, case, test)
        b_tr = traced_run(BIN_BASE, case)
        for name, path in variants:
            m, pts, ntp, nc, fr = summarize(name, path, case, test)
            tr = traced_run(path, case)
            dpts = pts - b_pts
            dtp = 100.0 * (m[0] - b_m[0]) / max(b_m[0], 1e-12)
            same = tr[1][0] == b_tr[1][0]
            flag = "IDENTICAL" if same else "DIFFERS"
            if nc + 1e-9 < 0.99:
                flag += " NC<0.99"
            print(f"           delta pts={dpts:+8.2f} tp={dtp:+.2f}% "
                  f"tpot={m[2]-b_m[2]:+.2f} {flag} frames {b_fr}->{fr}")

    print("\n=== gate proof ===")
    suite = sim.build_cases()
    sat5 = next(c for c in suite if c.name == "sat5-K8")
    guards = [retarget(sat5, w) for w in
              (0.05, 0.15, 0.25, 0.30, 0.75, 0.98, 0.99, 1.0)]
    guards.append(next(c for c in suite if c.name == "lat-only-K4"))
    guards.append(test17_case())
    guards.append(test22_case())
    guards.append(historical_replay())
    guards.append(next(c for c in suite if c.name == "tp-sat-K8"))
    fail = 0
    for case in guards:
        b = traced_run(BIN_BASE, case)
        print(f"  {case.name:<28} wtp={case.wtp:.2f} {b[1][0][:12]}")
        for name, path in variants:
            a = traced_run(path, case)
            ok = a[1][0] == b[1][0]
            if not ok:
                fail += 1
            print(f"    {name:<12} {'MATCH' if ok else 'MISMATCH'}")
    print("gate", "FAIL" if fail else "OK", fail)
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())

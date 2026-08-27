#!/usr/bin/env python3
"""A/B per-cloud decode-tail probes on k-shrink-identical official #5/#6.

CLOUDTAIL: after ARR empty and no remaining P PROC, drop the global wait-all
and cycle D PRE/D PROC/D POST per cloud.
CLOUDPRE: same trigger, per-cloud D PRE / independent D PROC, still global
wait-all D POST.

Usage: python3 tests/akd56_cloudtail_ab.py BASE [name=BIN ...]
"""
from __future__ import annotations

import sys

import sim
from akd56_new_lever_ab import closest6, fitted5
from akd56_stream_probe import (
    OFFICIAL, official5, official6, pin_official_constants, prefill_need,
    retarget, summarize,
)
from ensemble_compare import test17_case, test22_case
from historical22_trace_compare import historical_replay
from trace_compare import traced_run

BIN_BASE = sys.argv[1] if len(sys.argv) > 1 else "/tmp/base-d202b1a"
variants = []
for arg in sys.argv[2:]:
    name, path = arg.split("=", 1)
    variants.append((name, path))


class DecodeTrace:
    def __init__(self):
        self.dpre = []
        self.dpost = []
        self.ppre = 0
        self.ppost = 0
        self.hash = None

    def append(self, frame):
        ts, commands = frame
        t = float(ts)
        for command in commands:
            fields = command.split()
            if fields[:3] == ["E", "D", "PRE"]:
                n = int(fields[4])
                self.dpre.append((t, n))
            elif fields[:3] == ["E", "D", "POST"]:
                n = int(fields[4])
                self.dpost.append((t, n))
            elif fields[:3] == ["E", "P", "PRE"]:
                self.ppre += 1
            elif fields[:3] == ["E", "P", "POST"]:
                self.ppost += 1


def last_prefill_time(tr: DecodeTrace):
    return None


def describe_dpre(tr: DecodeTrace, inflight_posts):
    sizes = [n for _, n in tr.dpre]
    if not sizes:
        return "dpre_n=0"
    first = sizes[:8]
    tail = sizes[8:]
    mean_tail = sum(tail) / len(tail) if tail else 0.0
    unique_tail = sorted(set(tail))[:8]
    max_in = 0
    open_pre = 0
    post_i = 0
    for t, n in tr.dpre:
        open_pre += 1
        while post_i < len(tr.dpost) and tr.dpost[post_i][0] <= t + 1e-12:
            open_pre -= 1
            post_i += 1
        if open_pre > max_in:
            max_in = open_pre
    return (
        f"dpre_n={len(sizes)} first={first} tail_mean={mean_tail:.1f} "
        f"tail_uniq={unique_tail} max_inflight_pre={max_in} "
        f"dpost_n={len(tr.dpost)}"
    )


def dump_case(label, binary, case):
    tr = DecodeTrace()
    metrics, frames, sm = sim.run(binary, case, trace=tr)
    pts, ntp, nc, dist = sim.score(case, metrics)
    print(
        f"  {label:<12} frames={frames} tp={metrics[0]:.4f} "
        f"tdr={metrics[1]:.1f} tpot={metrics[2]:.2f} nc={nc:.3f} "
        f"{describe_dpre(tr, 0)}"
    )
    return tr, metrics, pts, ntp, nc, frames


def canon5():
    case = official5(seed=711, R=100, lout=96, pproc=165, span=15.0,
                     bw=14.0, lat=5.0)
    pin_official_constants(case, 5)
    case.name = "canon5-R100-L96-pp165-bw14"
    return case


def canon6():
    case = official6(seed=812, R=150, lout=36, pproc=160, span=4.0,
                     bw=11.0, lat=4.4)
    pin_official_constants(case, 6)
    case.name = "canon6-R150-L36-pp160-bw11"
    return case


def main():
    honest = [(5, canon5()), (6, canon6())]
    print("=== honest recons ===")
    for test, case in honest:
        need, ratio = prefill_need(case)
        print(f"#{test} {case.name} need={need}/{case.K} ratio={ratio:.2f}")
        summarize("base", BIN_BASE, case, test)
        dump_case("base", BIN_BASE, case)

    print("\n=== A/B honest + event DIFF ===")
    for test, case in honest:
        print(f"\n{case.name}")
        b_tr, b_m, b_pts, b_ntp, b_nc, b_fr = dump_case("base", BIN_BASE, case)
        b_ev = traced_run(BIN_BASE, case)
        for name, path in variants:
            tr, m, pts, ntp, nc, fr = dump_case(name, path, case)
            ev = traced_run(path, case)
            dpts = pts - b_pts
            dtp = 100.0 * (m[0] - b_m[0]) / max(b_m[0], 1e-12)
            dtdr = 100.0 * (m[1] - b_m[1]) / max(b_m[1], 1e-12)
            dtpot = 100.0 * (m[2] - b_m[2]) / max(b_m[2], 1e-12)
            same = ev[1][0] == b_ev[1][0]
            flag = "IDENTICAL" if same else "DIFFERS"
            if nc + 1e-9 < 0.99:
                flag += " NC<0.99"
            first_same = (
                [n for _, n in tr.dpre[:1]] == [n for _, n in b_tr.dpre[:1]]
            )
            print(
                f"           delta pts={dpts:+8.2f} ntp={ntp-b_ntp:+.4f} "
                f"tp={dtp:+.2f}% tdr={dtdr:+.2f}% tpot={dtpot:+.2f}% "
                f"{flag} frames {b_fr}->{fr} first_dpre_same={first_same}"
            )

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

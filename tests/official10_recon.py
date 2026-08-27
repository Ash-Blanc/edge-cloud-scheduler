#!/usr/bin/env python3
"""Fitted official #10 recon and edge-SPT mean-completion floor.

Official #10 (16041 vector): WTP=0.15 tp=0.007628 tdr=182521.13 tpot=86.987
ntp=0.994 nc=0.630. d202b1a on the homogeneous-Lin recon matches those
three metrics within a few percent and sits 0.09% above the single-edge
SPT bound of (P PRE + P POST).

Usage: python3 tests/official10_recon.py /tmp/d202-sched
"""
from __future__ import annotations

import random
import sys

import sim
from tdr_decomp import request_parts, request_service, STAGES

OFF = dict(
    wtp=0.15, tp=0.007628, tdr=182521.13, tpot=86.987,
    ntp=0.9943, nc=0.6298, slo1=1258.9, slo2=64.85,
    tp_base=0.0028312, tp_ub=0.0076595, dist_base=389.0, pts=684.426,
)
SIZES = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]


def decode_table(ppre_k, ppre_s, pproc_k=8.0, pproc_s=0.02,
                 ppost_k=4.0, ppost_s=0.01, dpre_k=0.7, dpre_s=0.014,
                 dproc_k=2.1, dproc_s=0.014, dpost_k=0.7, dpost_s=0.014):
    return [
        (b, ppre_k + ppre_s * b, pproc_k + pproc_s * b, ppost_k + ppost_s * b,
         dpre_k + dpre_s * b, dproc_k + dproc_s * b, dpost_k + dpost_s * b)
        for b in SIZES
    ]


def pin(case):
    case.wtp, case.wc = OFF["wtp"], 1.0 - OFF["wtp"]
    case.slo1, case.slo2 = OFF["slo1"], OFF["slo2"]
    case.tp_base, case.tp_ub = OFF["tp_base"], OFF["tp_ub"]
    case.dist_base = OFF["dist_base"]
    return case


def xfer(c, n):
    return c.lat + 8.0 * n * c.bpt / (c.bw * 1e6)


def spt_mean(ps):
    t = acc = 0.0
    for p in sorted(ps):
        t += p
        acc += t
    return acc / len(ps) if ps else 0.0


def edge_spt_bound(case):
    """Single-resource mean-completion floor: edge owns P PRE and P POST."""
    s = sim.Sim(case)
    edge = []
    for (_t, lin, _l) in case.arrivals:
        edge.append((case.S + s.ppre.get(lin)) + (case.S + s.ppost.get(lin)))
    return spt_mean(edge)


def fitted10(seed=1009, lin=128, ppre=180.0):
    ppre_s = ppre / (lin + 40.0)
    ppre_k = ppre - ppre_s * lin
    rng = random.Random(seed)
    arrivals = sorted(
        (rng.uniform(0.0, 5.0), lin, rng.choice((1, 2)))
        for _ in range(2000)
    )
    case = sim.Case(
        2, 2.0, 1.0, 10.0, 32768, 16,
        OFF["slo1"], OFF["slo2"], decode_table(ppre_k, ppre_s),
        arrivals, OFF["wtp"], 1.0 - OFF["wtp"],
    )
    case.name = f"fitted10-lin{lin}-s{seed}"
    return pin(case)


def rel(metrics):
    tp, tdr, tpot = metrics
    return (
        abs(tp / OFF["tp"] - 1.0),
        abs(tdr / OFF["tdr"] - 1.0),
        abs(tpot / OFF["tpot"] - 1.0),
    )


def main():
    binary = sys.argv[1] if len(sys.argv) > 1 else "/tmp/d202-sched"
    print(
        f"official #10 tp={OFF['tp']} tdr={OFF['tdr']} tpot={OFF['tpot']} "
        f"ntp={OFF['ntp']} nc={OFF['nc']}"
    )
    worst = 0.0
    for seed in (1009, 1010, 1011):
        case = fitted10(seed=seed)
        metrics, frames, state = sim.run(binary, case)
        etp, etdr, etpot = rel(metrics)
        emax = max(etp, etdr, etpot)
        worst = max(worst, emax)
        pts, ntp, nc, dist = sim.score(case, metrics)
        lb = edge_spt_bound(case)
        print(
            f"{case.name}: tp={metrics[0]:.6g} ({etp*100:+.2f}%) "
            f"tdr={metrics[1]:.1f} ({etdr*100:+.2f}%) "
            f"tpot={metrics[2]:.3f} ({etpot*100:+.2f}%) "
            f"ntp={ntp:.4f} nc={nc:.4f} pts={pts:.2f} "
            f"edge_spt={lb:.1f} TDR/LB={metrics[1]/lb:.4f} frames={frames}"
        )
        if seed == 1009:
            rows = [request_parts(r) for r in state.reqs]
            svc = [request_service(r) for r in state.reqs]
            n = len(rows)
            for i, name in enumerate(STAGES):
                mean = sum(row[i] for row in rows) / n
                service = sum(row[i] for row in svc) / n
                queue = mean - service
                print(
                    f"  {name:<9} mean={mean:10.1f} queue={queue:10.1f} "
                    f"svc={service:8.1f} q%={queue / mean if mean else 0:6.1%}"
                )
        if emax > 0.08:
            raise SystemExit(f"{case.name} not within 8% of official (emax={emax:.3f})")
        if metrics[1] / lb > 1.01:
            raise SystemExit(
                f"{case.name} more than 1% above edge SPT ({metrics[1]/lb:.4f})"
            )
    print(f"worst rel-err {worst:.3f}; all seeds on the edge-SPT floor")


if __name__ == "__main__":
    main()

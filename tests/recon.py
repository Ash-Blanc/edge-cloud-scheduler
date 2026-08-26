#!/usr/bin/env python3
"""Reconstructions of the saturated-throughput judge tests (#5/#6/#13/#14/#16)
plus a sharper combined lower bound than lbcheck.py.

lbcheck.py prices each resource with the *input stage's* work only, plus a
"dec" floor that assumes strictly serial decode rounds. Here each resource is
priced with its prefill work AND its decode work at the best cohort size m, so
the bound reflects that the edge/clouds/links carry both stages. The serial
floor (edge+link+proc summed per round) is reported separately: it binds the
current one-cohort-at-a-time design but NOT a pipelined one, so the gap between
them is exactly what round pipelining could recover.

Usage: python3 tests/recon.py <bin> [bin2 ...]
"""
from __future__ import annotations

import math
import sys

import sim


def combined_lb(c):
    """Per-resource floor including decode work, minimized over cohort size."""
    s = sim.Sim(c)
    pe = pc = pu = pd = 0.0
    for (_t, lin, _l) in c.arrivals:
        pe += 2 * c.S + s.ppre.get(lin) + s.ppost.get(lin)
        pc += c.S + s.pproc.get(lin)
        pu += c.lat + 8.0 * lin * c.bpt / (c.bw * 1e6)
        pd += c.lat + 8.0 * lin * c.bpt / (c.bw * 1e6)
    T = sum(l for (_t, _i, l) in c.arrivals)
    # Hard per-request chain: tokens of one request are strictly sequential, so
    # the longest output pays at least lout gaps of the cheapest possible round.
    r1 = (2 * c.S + s.dpre.get(1) + s.dpost.get(1)
          + 2 * (c.lat + 8.0 * c.bpt / (c.bw * 1e6)) + c.S + s.dproc.get(1))
    chain = max(l for (_t, _i, l) in c.arrivals) * r1
    best = None
    for m in [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]:
        k = min(c.K, m)
        rounds = T / m
        de = rounds * (2 * c.S + s.dpre.get(m) + s.dpost.get(m))
        du = rounds * (k * c.lat + 8.0 * m * c.bpt / (c.bw * 1e6))
        dc = rounds * k * (c.S + s.dproc.get(math.ceil(m / k))) / c.K
        fl = {"edge": pe + de, "cloud": pc / c.K + dc, "up": pu + du,
              "down": pd + du, "chain": chain}
        serial = rounds * (2 * c.S + s.dpre.get(m) + s.dpost.get(m)
                           + 2 * (k * c.lat + 8.0 * m * c.bpt / (c.bw * 1e6))
                           + c.S + s.dproc.get(math.ceil(m / k)))
        lb = max(fl.values())
        if best is None or lb < best[0]:
            best = (lb, max(fl, key=fl.get), m, serial, fl)
    return best


NAMES = ["sat5-K8", "sat5-K4", "sat6-K8", "sat6-K4", "single-lout2", "slow16-K4"]


def cases():
    by = {c.name: c for c in sim.build_cases()}
    return [by[n] for n in NAMES]


def main():
    args = sys.argv[1:]
    trace = "--trace" in args
    if trace:
        args.remove("--trace")
    bins = args or ["/tmp/base6c6"]
    for c in cases():
        sim.calibrate(c, "/tmp/ref_sequential")
        lb, which, mstar, serial, fl = combined_lb(c)
        print(f"\n{c.name}: K={c.K} R={len(c.arrivals)} "
              f"T={sum(l for _, _, l in c.arrivals)} slo1={c.slo1:.1f} "
              f"slo2={c.slo2:.1f} dbase={c.dist_base:.2f} "
              f"tp_base={c.tp_base:.4f} tp_ub={c.tp_ub:.4f}")
        print(f"  combined LB={lb:.4g} ({which}, m*={mstar})  "
              f"serial-round makespan at m*={serial + lb - max(fl.values()) + 0:.4g}  "
              f"floors: " + " ".join(f"{k}={v:.4g}" for k, v in fl.items()))
        for b in bins:
            m, _f, sm = sim.run(b, c)
            pts, ntp, nc, dist = sim.score(c, m)
            span = max(r.toks[-1] for r in sm.reqs) - min(r.arr for r in sm.reqs)
            print(f"  {b.split('/')[-1]:<16} pts={pts:7.1f} ntp={ntp:.3f} "
                  f"nc={nc:.3f} tp={m[0]:.4f} tdr={m[1]:.1f} tpot={m[2]:.2f} "
                  f"x{span / lb:.2f} of LB  (tdr/slo1={m[1] / c.slo1:.1f} "
                  f"tpot/slo2={m[2] / c.slo2:.2f})")
            if trace:
                import diag
                s, acc = diag.run_traced(b, c)
                sp = acc["span"]
                print(f"      edge: busy_pref={100 * acc['edge_busy_pref'] / sp:5.1f}% "
                      f"busy_dec={100 * acc['edge_busy_dec'] / sp:5.1f}% "
                      f"idle_with_work={100 * acc['edge_idle_work'] / sp:5.1f}%  "
                      f"mean_free_clouds={acc['cloud_idle_work'] / sp:5.2f}/{c.K}")
                for k, (n, g, tsum) in s.stats.items():
                    if n:
                        print(f"      {k:<7} tasks={n:6d} mean_group={g / n:8.2f} "
                              f"busy={tsum:10.1f}")


if __name__ == "__main__":
    main()

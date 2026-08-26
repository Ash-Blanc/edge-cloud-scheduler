#!/usr/bin/env python3
"""Scan a grid of workload shapes and report makespan against the hard
lower bound implied by unbatchable input-stage work. Regimes where the ratio is
well above 1 are the only ones where a scheduling change can raise throughput."""
from __future__ import annotations

import itertools
import math
import random
import sys

import sim


def mk(name, seed, K, R, layers, span, wtp, a1, a2, kind="gpu", lat=1.0, bw=10.0,
       bpt=32768, S=2.0, lin_lo=16, lin_hi=1024, lout_lo=1, lout_hi=128):
    rng = random.Random(seed)
    table = sim.make_table(kind, rng)
    arrivals = []
    lins = [x for x in [16, 32, 64, 128, 256, 512, 1024, 2048, 4096] if lin_lo <= x <= lin_hi]
    louts = [x for x in [1, 2, 4, 8, 16, 32, 64, 128, 256, 512] if lout_lo <= x <= lout_hi]
    for _ in range(R):
        arrivals.append((rng.uniform(0.0, span), rng.choice(lins), rng.choice(louts)))
    arrivals.sort(key=lambda x: x[0])
    c = sim.Case(K, S, lat, bw, bpt, layers, 1.0, 1.0, table, arrivals, wtp, 1.0 - wtp)
    c.name = name
    c._a1, c._a2 = a1, a2
    return c


def floors(c):
    s = sim.Sim(c)
    edge = up = cloud = 0.0
    for (_t, lin, _lout) in c.arrivals:
        edge += 2 * c.S + s.ppre.get(lin) + s.ppost.get(lin)
        cloud += c.S + s.pproc.get(lin)
        up += c.lat + 8.0 * lin * c.bpt / (c.bw * 1e6)
    # decode floor: total tokens at the best achievable per-token rate
    tot = sum(l for (_t, _i, l) in c.arrivals)
    best = 0.0
    for m in [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]:
        k = min(c.K, m)
        per = math.ceil(m / k)
        e = 2 * c.S + s.dpre.get(m) + s.dpost.get(m)
        ln = 2 * (k * c.lat + 8.0 * m * c.bpt / (c.bw * 1e6))
        best = max(best, m / (e + ln + c.S + s.dproc.get(per)))
    return {"edge": edge, "cloud": cloud / c.K, "up": up, "down": up,
            "dec": tot / best}


def main():
    bins = sys.argv[1:] or ["/tmp/base"]
    rows = []
    seed = 5000
    grid = itertools.product(
        [1, 2, 4, 8, 16],                 # K
        [400, 2000],                      # R
        ["gpu", "cpu", "flat"],           # table
        [(1.0, 10.0), (20.0, 1.0), (0.5, 100.0)],   # (lat, bw)
        [2.0, 40.0],                      # S
        [(16, 1024), (2048, 4096)],       # lin range
    )
    for (K, R, kind, (lat, bw), S, (llo, lhi)) in grid:
        seed += 1
        name = f"K{K}-R{R}-{kind}-l{lat}-b{bw}-S{int(S)}-i{lhi}"
        c = mk(name, seed, K, R, 32, 400.0, 1.00, 0.05, 0.05, kind=kind,
               lat=lat, bw=bw, S=S, lin_lo=llo, lin_hi=lhi, lout_hi=64)
        fl = floors(c)
        lb = max(fl.values())
        which = max(fl, key=fl.get)
        cells = []
        for b in bins:
            try:
                m, frames, sm = sim.run(b, c)
                span = max(r.toks[-1] for r in sm.reqs) - min(r.arr for r in sm.reqs)
                cells.append((span / lb, m[1], m[2], sm.edge_busy / span,
                              sm.cloud_busy / (span * c.K)))
            except Exception as e:
                cells.append(("FAIL", str(e)[:20], 0, 0, 0))
        rows.append((name, which, lb, cells))
    rows.sort(key=lambda r: -(r[3][0][0] if isinstance(r[3][0][0], float) else 0))
    print(f"{'case':<40} {'bound':>6} {'LB':>10}  " +
          "  ".join(f"{b.split('/')[-1]:>22}" for b in bins))
    for name, which, lb, cells in rows:
        txt = []
        for cc in cells:
            if isinstance(cc[0], float):
                txt.append(f"{cc[0]:6.2f} e{100*cc[3]:4.0f} c{100*cc[4]:4.0f}")
            else:
                txt.append(f"FAIL {cc[1]:<17}")
        print(f"{name:<40} {which:>6} {lb:10.4g}  " + "  ".join(txt))


if __name__ == "__main__":
    main()

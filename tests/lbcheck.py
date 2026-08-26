#!/usr/bin/env python3
"""Report every suite case's makespan against the hard lower bound implied by
unbatchable input-stage work and the best achievable decode rate, so it is clear
which cases still have scheduling slack and which are structurally capped."""
from __future__ import annotations

import math
import sys

import sim


def main():
    bins = sys.argv[1:] or ["./sched"]
    cases = sim.build_cases()
    for c in cases:
        sim.calibrate(c, "/tmp/ref_sequential")
    print(f"{'case':<18}{'w_tp':>5}{'LB':>10}{'bound':>7}  " +
          "  ".join(f"{b.split('/')[-1]:>26}" for b in bins))
    for c in cases:
        s = sim.Sim(c)
        edge = cloud = up = 0.0
        for (_t, lin, _l) in c.arrivals:
            edge += 2 * c.S + s.ppre.get(lin) + s.ppost.get(lin)
            cloud += c.S + s.pproc.get(lin)
            up += c.lat + 8.0 * lin * c.bpt / (c.bw * 1e6)
        tot = sum(l for (_t, _i, l) in c.arrivals)
        best = 0.0
        for m in [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]:
            k = min(c.K, m)
            per = math.ceil(m / k)
            e = 2 * c.S + s.dpre.get(m) + s.dpost.get(m)
            ln = 2 * (k * c.lat + 8.0 * m * c.bpt / (c.bw * 1e6))
            best = max(best, m / (e + ln + c.S + s.dproc.get(per)))
        fl = {"edge": edge, "cloud": cloud / c.K, "up": up, "down": up, "dec": tot / best}
        lb = max(fl.values())
        cells = []
        for b in bins:
            m, _f, sm = sim.run(b, c)
            span = max(r.toks[-1] for r in sm.reqs) - min(r.arr for r in sm.reqs)
            pts, ntp, nc, dist = sim.score(c, m)
            cells.append(f"{pts:7.1f} x{span/lb:5.2f} ntp{ntp:6.3f}")
        print(f"{c.name:<18}{c.wtp:5.2f}{lb:10.4g}{max(fl, key=fl.get):>7}  " +
              "  ".join(cells))


if __name__ == "__main__":
    main()

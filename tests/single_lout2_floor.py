#!/usr/bin/env python3
"""Judge #14: is a single-request / L_out=2 workload already at its floor?

For one request there is no batching, no cloud choice that matters (the clouds
are identical and P PROC pieces are pinned to the assigned cloud), and no
ordering.  Every operation is forced, so both scored quantities have a closed
form:

    TDR_floor  = 3S + P_PRE(Lin) + P_PROC(Lin) + P_POST(Lin) + 2*xfer(Lin)
    ROUND_floor= 3S + D_PRE(1)   + D_PROC(1)   + D_POST(1)   + 2*xfer(1)

TDR_floor assumes P PROC is issued as a single [0, num_layers) piece; each extra
piece adds exactly S.  ROUND_floor is the token-to-token gap, so mean TPOT for
L_out=2 is one round.  Any schedule can only *add* idle time or extra S to
these, so a binary that reaches them exactly has nothing left to win.

Usage: single_lout2_floor.py BIN [BIN ...]
"""
from __future__ import annotations

import sys

import sim


def floors(case):
    s = sim.Sim(case)
    _t, lin, _l = case.arrivals[0]
    tdr = (3 * case.S + s.ppre.get(lin) + s.pproc.get(lin) + s.ppost.get(lin)
           + 2 * s.xfer(lin))
    rnd = (3 * case.S + s.dpre.get(1) + s.dproc.get(1) + s.dpost.get(1)
           + 2 * s.xfer(1))
    return tdr, rnd


def make(name, K, S, lat, bw, bpt, layers, lin, lout, kind, wtp, seed=1):
    import random
    rows = sim.make_table(kind, random.Random(seed))
    c = sim.Case(K, S, lat, bw, bpt, layers, 1.0, 1.0, rows,
                 [(0.0, lin, lout)], wtp, 1.0 - wtp)
    c.name = name
    c._a1, c._a2 = 1.5, 1.2
    return c


def grid():
    out = []
    for kind in ("gpu", "cpu", "flat", "edge"):
        for K in (1, 2, 4, 8, 16):
            for S in (0.5, 2.0, 9.0):
                for lat, bw in ((1.0, 10.0), (20.0, 1.0), (35.0, 0.5)):
                    for lin in (16, 256, 4096):
                        for layers in (1, 8, 64):
                            out.append(make(
                                f"{kind}-K{K}-S{S}-lat{lat}-lin{lin}-L{layers}",
                                K, S, lat, bw, 32768, layers, lin, 2, kind,
                                0.65))
    return out


def main():
    bins = sys.argv[1:] or ["./sched"]
    cases = grid()
    print(f"single-request L_out=2 floor check over {len(cases)} shapes")
    for b in bins:
        worst_tdr = worst_rnd = 0.0
        worst_name = ""
        bad = 0
        for c in cases:
            tdr_f, rnd_f = floors(c)
            (tp, tdr, tpot), _frames, _sm = sim.run(b, c)
            dt = tdr - tdr_f
            dr = tpot - rnd_f
            if dt > 1e-9 or dr > 1e-9:
                bad += 1
                if dt + dr > worst_tdr + worst_rnd:
                    worst_tdr, worst_rnd, worst_name = dt, dr, c.name
            # throughput must then also be forced
            span_f = tdr_f + 2 * rnd_f
            if abs(2.0 / span_f - tp) > 1e-9 and dt <= 1e-9 and dr <= 1e-9:
                print(f"  {c.name}: tp {tp} != forced {2.0 / span_f}")
        name = b.split("/")[-1]
        if bad:
            print(f"  {name:<20} {bad}/{len(cases)} above floor; worst "
                  f"{worst_name} dTDR={worst_tdr:.6g} dROUND={worst_rnd:.6g}")
        else:
            print(f"  {name:<20} AT FLOOR on all {len(cases)} shapes "
                  f"(TDR and TPOT both exactly forced)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Search #5/#6 reconstructions that are prefill-bound (need>=K) AND
match official tp/tdr/tpot. Prints the Pareto front. Does not ship.
"""
from __future__ import annotations

import math
import sys

import sim
from akd56_stream_probe import (
    OFFICIAL, official5, official6, pin_official_constants, prefill_need,
    summarize,
)

BIN = sys.argv[1] if len(sys.argv) > 1 else "/tmp/base"
FEW = 0.05


def rel(m, o):
    return {
        "tp": abs(m[0] - o["tp"]) / o["tp"],
        "tdr": abs(m[1] - o["tdr"]) / o["tdr"],
        "tpot": abs(m[2] - o["tpot"]) / max(o["tpot"], 1e-12),
    }


def eval_case(test, case, note):
    pin_official_constants(case, test)
    need, ratio = prefill_need(case)
    o = OFFICIAL[test]
    m, fr, sm = sim.run(BIN, case)
    r = rel(m, o)
    fit = r["tp"] + r["tdr"] + r["tpot"]
    ppost = max(x.tdr + x.arr for x in sm.reqs)
    last = max(x.toks[-1] for x in sm.reqs)
    first = min(x.arr for x in sm.reqs)
    tail = last - ppost
    span = last - first
    pref = ppost - first
    dpre = sm.stats["D PRE"]
    bound = need >= case.K
    box = r["tp"] <= FEW and r["tdr"] <= FEW and r["tpot"] <= FEW
    print(
        f"#{test} {case.name} {note}\n"
        f"  K={case.K} R={len(case.arrivals)} need={need}/{case.K} "
        f"ratio={ratio:.2f} {'PREFILL' if bound else 'not-prefill'} "
        f"{'IN-BOX' if box else 'out'}\n"
        f"  tp={m[0]:.4f} ({100*r['tp']:+.1f}%) tdr={m[1]:.1f} "
        f"({100*r['tdr']:+.1f}%) tpot={m[2]:.2f} ({100*r['tpot']:+.1f}%) "
        f"fit={fit:.3f}\n"
        f"  pref={pref:.0f} tail={tail:.0f} tail/span={tail/max(span,1e-9):.2f} "
        f"dpre_n={dpre[0]} g={dpre[1]/max(1,dpre[0]):.1f}"
    )
    return dict(test=test, name=case.name, note=note, need=need, K=case.K,
                bound=bound, box=box, fit=fit, rel=r, m=m,
                tail_frac=tail / max(span, 1e-9), case=case)


def main():
    rows = []
    # known points
    known = [
        (5, official5(), "lat5 default LAT-bound"),
        (5, official5(seed=702), "seed702"),
        (5, official5(seed=711, lout=128, pproc=207.5, span=50.0), "pproc207"),
        (6, official6(), "off6 default"),
        (6, official6(seed=812, pproc=250.0, span=20.0, lat=1.0), "off6 pproc250"),
    ]
    # analytical island #5: R~150 lout~42 pproc~160 span small
    for R in (120, 150, 180):
        for lout in (32, 42, 56):
            for pproc in (140, 165, 190):
                for span in (1.0, 8.0):
                    known.append((5, official5(
                        seed=711, R=R, lout=lout, pproc=pproc, span=span),
                        f"isl5 R{R} L{lout} pp{pproc} sp{span:g}"))
    for R, lout, pproc, span in (
        (147, 42, 155, 2.0), (150, 42, 161, 4.0), (160, 48, 170, 8.0),
        (130, 48, 175, 4.0), (170, 36, 150, 2.0), (100, 64, 190, 8.0),
        (200, 32, 150, 1.0), (110, 56, 185, 6.0), (90, 80, 210, 10.0),
        (80, 96, 220, 8.0), (220, 24, 140, 1.0), (250, 20, 130, 2.0),
        (147, 42, 155, 8.0), (147, 42, 180, 2.0), (160, 40, 155, 4.0),
        (140, 48, 160, 12.0), (100, 48, 200, 20.0), (80, 64, 230, 30.0),
    ):
        known.append((5, official5(seed=711, R=R, lout=lout, pproc=pproc,
                                   span=span),
                      f"foc5 R{R} L{lout} pp{pproc} sp{span:g}"))
    for lin in ((64, 128, 256), (128, 256, 512), (512, 1024)):
        known.append((5, official5(seed=711, R=150, lout=42, pproc=160, span=4,
                                   lin=lin), f"lin{lin[0]}"))
        known.append((5, official5(seed=711, R=150, lout=42, pproc=120, span=4,
                                   lin=lin, lat=3.0), f"lin{lin[0]}lat3pp120"))
    # #6 island: R~300 lout~16 pproc~160
    for R in (240, 300, 360):
        for lout in (12, 16, 24):
            for pproc in (150, 180):
                for span in (2.0, 12.0):
                    known.append((6, official6(
                        seed=812, R=R, lout=lout, pproc=pproc, span=span),
                        f"isl6 R{R} L{lout} pp{pproc} sp{span:g}"))
    for R, lout, pproc, span, lat in (
        (300, 16, 160, 4.0, 4.4), (304, 16, 163, 2.0, 4.4),
        (280, 18, 170, 8.0, 5.0), (250, 20, 180, 4.0, 4.4),
        (200, 24, 190, 4.0, 4.0), (180, 28, 200, 8.0, 4.4),
        (140, 46, 90, 4.0, 4.4), (160, 32, 210, 12.0, 2.0),
        (120, 40, 250, 20.0, 1.0), (320, 14, 155, 6.0, 4.4),
        (200, 16, 200, 30.0, 4.4), (100, 32, 240, 8.0, 4.4),
    ):
        known.append((6, official6(seed=812, R=R, lout=lout, pproc=pproc,
                                   span=span, lat=lat),
                      f"foc6 R{R} L{lout} pp{pproc} lat{lat:g}"))

    # de-dup names
    seen = set()
    uniq = []
    for test, case, note in known:
        pin_official_constants(case, test)
        key = (test, case.name, note)
        if key in seen:
            continue
        seen.add(key)
        uniq.append((test, case, note))

    print(f"evaluating {len(uniq)} shapes on {BIN}\n")
    for test, case, note in uniq:
        pin_official_constants(case, test)
        need, ratio = prefill_need(case)
        # Island/focus shapes: skip the sim if they cannot be ranking recons.
        if note.startswith(("isl", "foc", "lin")) and need < case.K:
            print(f"skip {note} need={need}/{case.K} ratio={ratio:.2f}")
            continue
        try:
            rows.append(eval_case(test, case, note))
        except Exception as e:
            print(f"FAIL {case.name} {note}: {e}")

    print("\n=== IN-BOX prefill-bound ===")
    inbox = [r for r in rows if r["bound"] and r["box"]]
    if not inbox:
        print("NONE")
    else:
        inbox.sort(key=lambda r: r["fit"])
        for r in inbox:
            print(f"  {r['name']} fit={r['fit']:.3f} tail={r['tail_frac']:.2f} {r['note']}")

    print("\n=== Pareto among prefill-bound (minimize tp/tdr/tpot rel, keep all non-dominated) ===")
    pref = [r for r in rows if r["bound"]]
    pareto = []
    for r in pref:
        dom = False
        for o in pref:
            if o is r:
                continue
            if (o["rel"]["tp"] <= r["rel"]["tp"] + 1e-12 and
                o["rel"]["tdr"] <= r["rel"]["tdr"] + 1e-12 and
                o["rel"]["tpot"] <= r["rel"]["tpot"] + 1e-12 and
                (o["rel"]["tp"] < r["rel"]["tp"] - 1e-12 or
                 o["rel"]["tdr"] < r["rel"]["tdr"] - 1e-12 or
                 o["rel"]["tpot"] < r["rel"]["tpot"] - 1e-12)):
                dom = True
                break
        if not dom:
            pareto.append(r)
    pareto.sort(key=lambda r: r["fit"])
    for r in pareto:
        print(
            f"  #{r['test']} {r['name']} fit={r['fit']:.3f} "
            f"dtp={100*r['rel']['tp']:+.1f} dtdr={100*r['rel']['tdr']:+.1f} "
            f"dtpot={100*r['rel']['tpot']:+.1f} tail={r['tail_frac']:.2f} "
            f"{r['note']}"
        )

    print("\n=== best fit overall (any bound) ===")
    best = sorted(rows, key=lambda r: r["fit"])[:12]
    for r in best:
        print(
            f"  #{r['test']} bound={r['bound']} box={r['box']} fit={r['fit']:.3f} "
            f"dtp={100*r['rel']['tp']:+.1f} dtdr={100*r['rel']['tdr']:+.1f} "
            f"dtpot={100*r['rel']['tpot']:+.1f} {r['note']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

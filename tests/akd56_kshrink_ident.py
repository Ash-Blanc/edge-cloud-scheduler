#!/usr/bin/env python3
"""Find #5/#6 shapes where d202b1a matches official metrics AND the
.80/.90 k-shrink blob is event-identical (official no-op fingerprint).

Usage: python3 tests/akd56_kshrink_ident.py
"""
from __future__ import annotations

import sys

import sim
from akd56_stream_probe import (
    OFFICIAL, official5, official6, pin_official_constants, prefill_need,
)
from trace_compare import traced_run

BASE = sys.argv[1] if len(sys.argv) > 1 else "/tmp/base-d202b1a"
KSHRINK = sys.argv[2] if len(sys.argv) > 2 else "/tmp/kshrink"
FEW = 0.05


def rel(m, o):
    return (
        abs(m[0] - o["tp"]) / o["tp"],
        abs(m[1] - o["tdr"]) / o["tdr"],
        abs(m[2] - o["tpot"]) / max(o["tpot"], 1e-12),
    )


def eval_case(label, case, test, do_ident=True):
    pin_official_constants(case, test)
    need, ratio = prefill_need(case)
    mb, tb = traced_run(BASE, case)
    same = None
    if do_ident:
        ma, ta = traced_run(KSHRINK, case)
        same = mb == ma and tb == ta
    r = rel(mb, OFFICIAL[test])
    box = all(x <= FEW for x in r)
    fit = sum(r)
    flag = "IDENTICAL" if same else ("DIFFERS" if same is False else "?")
    print(
        f"{label:52} need={need:2}/{case.K} {ratio:5.2f} fit={fit:.4f} "
        f"dtp={100*r[0]:+6.2f} dtdr={100*r[1]:+6.2f} dtpot={100*r[2]:+6.2f} "
        f"{'IN-BOX' if box else 'out':6} {flag} "
        f"tp={mb[0]:.6f} tdr={mb[1]:.2f} tpot={mb[2]:.4f}"
    )
    return dict(label=label, need=need, K=case.K, ratio=ratio, fit=fit,
                box=box, same=same, m=mb, r=r, case=case, test=test)


def main():
    rows = []
    print("=== suspects / defaults (must show SAT_TP fires) ===")
    rows.append(eval_case(
        "fitted5 old R100 L96 pp160 sp15 bw8",
        official5(seed=711, R=100, lout=96, pproc=160, span=15), 5))
    rows.append(eval_case("pproc207", official5(
        seed=711, lout=128, pproc=207.5, span=50.0), 5))
    rows.append(eval_case("off5 default LAT-bound", official5(), 5))
    rows.append(eval_case("off6 default", official6(), 6))
    rows.append(eval_case("off6 pp190", official6(pproc=190), 6))

    print("\n=== #5 canonical neighborhood ===")
    for bw, lat, pp in (
        (14, 5.0, 165), (14, 5.0, 164), (14, 5.0, 166),
        (13, 5.0, 165), (12, 5.0, 160), (12, 5.0, 165),
        (10, 4.9, 160), (11, 5.0, 160), (14, 4.95, 165),
        (15, 5.0, 165), (14, 5.05, 165),
    ):
        rows.append(eval_case(
            f"fit5 bw{bw:g} lat{lat:g} pp{pp:g}",
            official5(seed=711, R=100, lout=96, pproc=pp, span=15,
                      bw=bw, lat=lat), 5))

    print("\n=== #6 expand generator (bw/bpt/layers/lin/R/lout/pproc/S/K) ===")
    specs = []
    for R in (120, 140, 160):
        for lout in (32, 46, 64, 96):
            for pproc in (90, 140, 190, 240):
                for bw in (8, 10, 12):
                    specs.append(dict(
                        seed=812, R=R, lout=lout, pproc=pproc, bw=bw,
                        lat=4.4, span=4.0))
    for lin in ((256,), (512,), (1024,), (2048,),
                (256, 512), (512, 1024), (1024, 2048),
                (256, 512, 1024), (512, 1024, 2048),
                (128, 256, 512, 1024, 2048)):
        specs.append(dict(seed=812, R=140, lout=46, pproc=90, lin=lin, bw=8))
        specs.append(dict(seed=812, R=140, lout=46, pproc=160, lin=lin, bw=8))
        specs.append(dict(seed=812, R=140, lout=46, pproc=90, lin=lin, bw=16))
    for bpt in (4096, 8192, 16384, 32768, 65536, 131072):
        specs.append(dict(seed=812, R=140, lout=46, pproc=90, bpt=bpt))
        specs.append(dict(seed=812, R=140, lout=46, pproc=180, bpt=bpt))
    for layers in (1, 2, 4, 8, 16, 32, 64):
        specs.append(dict(seed=812, R=140, lout=46, pproc=90, layers=layers))
        specs.append(dict(seed=812, R=140, lout=46, pproc=180, layers=layers))
    for S in (0.5, 1.0, 2.0, 4.0, 8.0):
        specs.append(dict(seed=812, R=140, lout=46, pproc=90, S=S))
        specs.append(dict(seed=812, R=140, lout=46, pproc=180, S=S, bw=12))
    for K in (4, 6, 8, 12, 16):
        specs.append(dict(seed=812, R=140, lout=46, pproc=90, K=K))
        specs.append(dict(seed=812, R=140, lout=46, pproc=180, K=K))
    for span in (0.0, 1.0, 4.0, 20.0, 80.0, 200.0, 500.0):
        specs.append(dict(seed=812, R=140, lout=46, pproc=90, span=span))
        specs.append(dict(seed=812, R=140, lout=46, pproc=190, span=span))
    for dproc in (1.0, 2.5, 4.0, 8.0):
        specs.append(dict(seed=812, R=140, lout=46, pproc=90, dproc=dproc))
        specs.append(dict(seed=812, R=140, lout=46, pproc=180, dproc=dproc))

    # focused island: prefill-bound + low tp via large lin or large pproc
    for R, lout, pproc, bw, lat, lin, span in (
        (140, 46, 190, 8, 4.4, (512, 1024, 2048), 4.0),
        (140, 80, 190, 8, 4.4, (512, 1024, 2048), 4.0),
        (140, 96, 190, 8, 4.4, (512, 1024, 2048), 4.0),
        (180, 46, 160, 8, 4.4, (512, 1024, 2048), 4.0),
        (100, 64, 220, 8, 4.4, (1024, 2048), 8.0),
        (140, 46, 90, 7, 4.4, (512, 1024, 2048), 4.0),
        (140, 46, 90, 9, 4.4, (512, 1024, 2048), 4.0),
        (140, 46, 150, 10, 4.4, (1024, 2048, 4096), 4.0),
        (160, 40, 200, 8, 4.0, (512, 1024, 2048), 10.0),
        (200, 32, 180, 8, 4.4, (1024,), 4.0),
        (80, 96, 250, 8, 5.0, (512, 1024), 15.0),
        (140, 46, 90, 8, 4.4, (512, 1024, 2048), 0.0),
        (140, 46, 210, 8, 4.4, (256, 512, 1024), 4.0),
        (130, 46, 190, 8, 4.4, (512, 1024, 2048), 50.0),
        (140, 46, 90, 8, 3.8, (512, 1024, 2048), 4.0),
        (140, 46, 90, 8, 5.0, (512, 1024, 2048), 4.0),
    ):
        specs.append(dict(seed=812, R=R, lout=lout, pproc=pproc, bw=bw,
                          lat=lat, lin=lin, span=span))

    seen = set()
    uniq = []
    for sp in specs:
        key = tuple(sorted(sp.items()))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(sp)

    print(f"evaluating {len(uniq)} #6 specs\n")
    hits = []
    for i, sp in enumerate(uniq):
        case = official6(**sp)
        # cheap skip: if need < K-1 we almost surely DIFFERS; still eval
        # a sample of those for the fingerprint. Always eval when need>=K.
        need, ratio = prefill_need(pin_official_constants(case, 6))
        # skip very far analytical hopeless: but we don't have metrics yet.
        # Run all need>=K plus every 4th other.
        if need < case.K and (i % 4):
            continue
        rec = eval_case(case.name + " " + str(sp), case, 6)
        rows.append(rec)
        if rec["box"] and rec["same"]:
            hits.append(rec)

    print("\n=== IN-BOX + IDENTICAL ===")
    inbox = [r for r in rows if r["box"] and r["same"]]
    if not inbox:
        print("NONE")
    else:
        inbox.sort(key=lambda r: r["fit"])
        for r in inbox:
            print(f"  #{r['test']} fit={r['fit']:.4f} {r['label']}")

    print("\n=== best IDENTICAL (any box) by fit ===")
    ident = [r for r in rows if r["same"]]
    ident.sort(key=lambda r: r["fit"])
    for r in ident[:20]:
        print(
            f"  #{r['test']} box={r['box']} fit={r['fit']:.4f} "
            f"dtp={100*r['r'][0]:+.1f} dtdr={100*r['r'][1]:+.1f} "
            f"dtpot={100*r['r'][2]:+.1f} {r['label'][:60]}"
        )

    print(f"\nhits in-box+identical: {len(inbox)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

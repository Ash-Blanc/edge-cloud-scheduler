#!/usr/bin/env python3
"""Fingerprint A/B mixed-L_out packing vs 5d830a0b floor.

Cases: A (24/48/96), B (32/48/64/96), honest #5/#6, and a few retargets.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sim
from akd56_16063_ab import (
    fingerprint5_pct,
    fingerprint5_tdr,
    honest5,
    honest6,
    pin_official_constants,
    retarget,
)
from trace_compare import traced_run


def summarize(label, binary, case):
    metrics, frames, sm = sim.run(binary, case)
    pts, ntp, nc, dist = sim.score(case, metrics)
    dpre = sm.stats["D PRE"]
    print(
        f"  {label:<18} pts={pts:8.2f} ntp={ntp:.4f} nc={nc:.4f} "
        f"tp={metrics[0]:.6f} tdr={metrics[1]:.3f} tpot={metrics[2]:.4f} "
        f"dpre_n={dpre[0]} dpre_g={dpre[1]/max(1,dpre[0]):.2f} frames={frames}"
    )
    return metrics, pts, ntp, nc, frames


def compare(label, case, base, cand):
    bm, bpts, bntp, bnc, _ = summarize("base", base, case)
    cm, cpts, cntp, cnc, _ = summarize("cand", cand, case)
    bt = traced_run(base, case)
    ct = traced_run(cand, case)
    same = bt[1][0] == ct[1][0]
    dtp = cm[0] - bm[0]
    print(
        f"  {label:<18} {'IDENTICAL' if same else 'DIFFERS'} "
        f"dpts={cpts-bpts:+.3f} dtp={dtp:+.6f} ({100*dtp/max(bm[0],1e-12):+.2f}%) "
        f"dtdr={cm[1]-bm[1]:+.3f} dtpot={cm[2]-bm[2]:+.4f} "
        f"dntp={cntp-bntp:+.4f} nc={cnc:.4f}"
    )
    return same, bm, cm, bpts, cpts, bnc, cnc


def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: akd56_mix_ab.py BASE CAND [CAND2=path ...]")
    base = sys.argv[1]
    cand = sys.argv[2]
    extra = []
    for arg in sys.argv[3:]:
        if "=" in arg:
            extra.append(tuple(arg.split("=", 1)))
        else:
            extra.append((arg.split("/")[-1], arg))

    fp_pct = pin_official_constants(fingerprint5_pct(), 5)
    fp_tdr = pin_official_constants(fingerprint5_tdr(), 5)
    h5 = pin_official_constants(honest5(), 5)
    h6 = pin_official_constants(honest6(), 6)
    cases = [
        ("A fp+8.8%", fp_pct),
        ("B fp tdr1498", fp_tdr),
        ("#5 honest uniform", h5),
        ("#6 honest", h6),
        (".90 on A", retarget(fp_pct, 0.90)),
        (".75 on A", retarget(fp_pct, 0.75)),
        (".30 on A", retarget(fp_pct, 0.30)),
        (".98 on A", retarget(fp_pct, 0.98)),
    ]

    print(f"BASE={base}\nCAND={cand}")
    for label, case in cases:
        print(f"\n=== {label}  {case.name} wtp={case.wtp} ===")
        compare(label, case, base, cand)
        for name, path in extra:
            print(f"  -- vs extra {name} --")
            compare(f"{label}/{name}", case, base, path)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate and probe the fitted official #3 recon.

Fit: K=4 R=8 span=0 pp=700 dp=14 lin=512/1024/2048 lout~[1,1,1,2,2]
     lat=8 bw=8 seed=304  ->  AKD: tdr=1331.9(+0.2%) tpot=62.39(+0.7%)

Validation: with SLO1=882.93 SLO2=48.44 dbase=1.1568,
  AKD policy  must give dist ~= 0.5777 (official 500.568)
  pre-AKD generic (9c53488) must give dist ~= 0.6109 (implied 471.905)

Usage: official3_probe.py AKD_BIN GEN_BIN [EXTRA ...]
"""
from __future__ import annotations

import math
import random
import sys

import sim

SLO1, SLO2 = 882.93, 48.44
DBASE = 0.577735 / (1.0 - 0.500568)


def decode_table(pproc_k, dproc_k):
    sizes = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]
    return [
        (b,
         0.25 + 0.010 * b,
         pproc_k + 0.08 * b,
         0.20 + 0.005 * b,
         1.00 + 0.008 * b,
         dproc_k + 0.04 * b,
         1.00 + 0.008 * b)
        for b in sizes
    ]


def recon(seed=304, K=4, R=8, span=0.0, pp=700.0, dp=14.0,
          lins=(512, 1024, 2048), louts=(1, 1, 1, 2, 2), lat=8.0, bw=8.0):
    rng = random.Random(seed)
    arrivals = sorted(
        (rng.uniform(0.0, span), rng.choice(lins), rng.choice(louts))
        for _ in range(R))
    c = sim.Case(K, 2.0, lat, bw, 32768, 8, SLO1, SLO2,
                 decode_table(pp, dp), arrivals, 0.00, 1.00)
    c.tp_base = 0.001
    c.tp_ub = 1.0
    c.dist_base = DBASE
    c.name = f"official3-s{seed}"
    return c


def report(label, binary, case):
    m, frames, sm = sim.run(binary, case)
    tp, tdr, tpot = m
    ex1 = max(0.0, (tdr - SLO1) / SLO1)
    ex2 = max(0.0, (tpot - SLO2) / SLO2)
    dist = math.hypot(ex1, ex2)
    pts = 1000.0 * max(0.0, 1.0 - dist / DBASE)
    print(f"{label:<14} tdr={tdr:9.2f} tpot={tpot:7.3f} ex1={ex1:.4f} "
          f"ex2={ex2:.4f} dist={dist:.4f} pts={pts:8.2f} frames={frames}")
    return m, pts, sm


def main():
    akd, gen = sys.argv[1], sys.argv[2]
    extras = sys.argv[3:]
    print("official targets: AKD dist=0.577735 pts=500.568 | "
          "generic dist=0.6109 pts=471.905")
    seeds = [304, 300, 301, 302, 303, 305]
    for seed in seeds:
        c = recon(seed=seed)
        print(f"\n=== seed={seed} ===")
        report("AKD", akd, c)
        report("GEN(9c)", gen, c)
        for i, extra in enumerate(extras):
            report(f"extra{i}", extra, c)


if __name__ == "__main__":
    main()

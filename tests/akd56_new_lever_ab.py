#!/usr/bin/env python3
"""A/B new AKD56 levers on the fitted in-box prefill-bound #5 recon."""
from __future__ import annotations

import copy
import math
import sys

import sim
from akd56_stream_probe import (
    OFFICIAL, official5, official6, pin_official_constants, prefill_need,
    retarget, summarize,
)
from ensemble_compare import test17_case, test22_case
from historical22_trace_compare import historical_replay
from trace_compare import traced_run

BIN_BASE = sys.argv[1] if len(sys.argv) > 1 else "/tmp/akd56_off"
variants = []
for arg in sys.argv[2:]:
    name, path = arg.split("=", 1)
    variants.append((name, path))


def fitted5():
    case = official5(seed=711, R=100, lout=96, pproc=160, span=15.0)
    pin_official_constants(case, 5)
    case.name = "fit5-R100-L96-pp160-sp15"
    return case


def fitted5b():
    case = official5(seed=711, R=150, lout=42, pproc=120, span=4.0,
                     lin=(128, 256, 512), lat=4.0, dproc=5.5, dpre_k=2.0)
    pin_official_constants(case, 5)
    case.name = "fit5-lat4-dpre2-dp5.5"
    return case


def closest6():
    case = official6(seed=812, R=130, lout=46, pproc=190, span=50.0)
    pin_official_constants(case, 6)
    case.name = "fit6-closest-pp190"
    return case


def main():
    cases = [
        (5, fitted5()),
        (5, fitted5b()),
        (6, closest6()),
        (5, pin_official_constants(official5(), 5)),
        (6, pin_official_constants(official6(), 6)),
    ]
    print("=== reconstruction status ===")
    for test, case in cases:
        need, ratio = prefill_need(case)
        print(f"#{test} {case.name} need={need}/{case.K} ratio={ratio:.2f} "
              f"{'PREFILL' if need >= case.K else 'not-prefill'}")
        summarize("base", BIN_BASE, case, test)

    print("\n=== A/B ===")
    for test, case in cases:
        print(f"\n{case.name}")
        b_m, b_pts, b_ntp, b_nc, b_fr = summarize("base", BIN_BASE, case, test)
        b_tr = traced_run(BIN_BASE, case)
        for name, path in variants:
            m, pts, ntp, nc, fr = summarize(name, path, case, test)
            tr = traced_run(path, case)
            dpts = pts - b_pts
            dtp = 100.0 * (m[0] - b_m[0]) / max(b_m[0], 1e-12)
            same = tr[1][0] == b_tr[1][0]
            flag = "IDENTICAL" if same else "DIFFERS"
            if nc + 1e-9 < 0.99:
                flag += " NC<0.99"
            print(f"           delta pts={dpts:+8.2f} tp={dtp:+.1f}% "
                  f"tpot={m[2]-b_m[2]:+.2f} {flag} frames {b_fr}->{fr}")

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
            print(f"    {name:<10} {'MATCH' if ok else 'MISMATCH'}")
    print("gate", "FAIL" if fail else "OK", fail)
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Windows-friendly A/B runner for the local judge suite.

Stubs the Unix-only `resource` module and lets the sequential reference
binary be passed in, then reproduces sim.py's main() table for any number
of scheduler binaries.

Usage:
    python tests/local_ab.py REF_BIN SCHED_A [SCHED_B ...]
    python tests/local_ab.py --cases name1,name2 REF_BIN SCHED_A SCHED_B
"""
from __future__ import annotations

import os
import sys
import types

# --- Unix-only module shim (CPU accounting is not meaningful on Windows) ---
_res = types.ModuleType("resource")
_res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim  # noqa: E402


def main():
    args = sys.argv[1:]
    only = None
    if args and args[0] == "--cases":
        only = args[1].split(",")
        args = args[2:]
    if len(args) < 2:
        raise SystemExit(__doc__)
    ref, bins = args[0], args[1:]
    cases = sim.build_cases()
    if only:
        cases = [c for c in cases if c.name in only]
        if not cases:
            raise SystemExit("no matching cases")
    print("calibrating tp_base / dist_base against the sequential reference ...")
    for c in cases:
        sim.calibrate(c, ref)

    totals = {b: 0.0 for b in bins}
    fails = {b: 0 for b in bins}
    nw = max(len(c.name) for c in cases) + 1
    names = [os.path.basename(b) for b in bins]
    print()
    print(f"{'case':<{nw}} {'w_tp':>5} {'dbase':>8}  " +
          "  ".join(f"{n:^34}" for n in names))
    print(f"{'':<{nw}} {'':>5} {'':>8}  " +
          "  ".join(f"{'pts':>7} {'tp':>9} {'tdr':>8} {'tpot':>7}" for _ in names))
    print("-" * (nw + 18 + 36 * len(names)))
    for c in cases:
        cells = []
        for b in bins:
            try:
                m, frames, sm = sim.run(b, c)
                if m is None:
                    raise RuntimeError("unfinished")
                pts, ntp, nc, dist = sim.score(c, m)
                totals[b] += pts
                tp, tdr, tpot = m
                cells.append(f"{pts:7.1f} {tp:9.4f} {tdr:8.1f} {tpot:7.2f}")
            except Exception as e:
                fails[b] += 1
                cells.append(f"{('FAIL ' + str(e))[:34]:<34}")
        print(f"{c.name:<{nw}} {c.wtp:5.2f} {c.dist_base:8.2f}  " + "  ".join(cells))
    print("-" * (nw + 18 + 36 * len(names)))
    base = totals[bins[0]]
    print(f"{'TOTAL':<{nw}} {'':>5} {'':>8}  " +
          "  ".join(f"{totals[b]:>10.1f} ({fails[b]} fail)        " for b in bins))
    for b in bins[1:]:
        d = totals[b] - base
        print(f"  delta vs {names[0]}: {d:+.1f} total  ({d/len(cases):+.1f} per case)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Official-metric reconstructions of judge #5 / #6 and overlap-decode proof.

Old sat5/sat6 in sim.py are prefill-bound and do not reproduce official tp/tpot.
These cases are calibrated so the one-batch public scheduler lands near:

  #5 w_tp=0.80 tp=1.121 tdr=1497 tpot=60.08 nc=0.998
  #6 w_tp=0.90 tp=0.696 tdr=3102 tpot=57.81 nc=0.992

Usage: python3 tests/calibrate_official56.py BASE CANDIDATE
"""
from __future__ import annotations

import random
import subprocess
import sys

import sim


def decode_table(pproc_k, dproc_k):
    sizes = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]
    rows = []
    for b in sizes:
        rows.append(
            (
                b,
                0.25 + 0.010 * b,
                pproc_k + 0.08 * b,
                0.20 + 0.005 * b,
                1.00 + 0.008 * b,
                dproc_k + 0.04 * b,
                1.00 + 0.008 * b,
            )
        )
    return rows


def make(name, wtp, **kw):
    rng = random.Random(kw["seed"])
    arrivals = [
        (rng.uniform(0.0, kw["span"]), rng.choice(kw["lin"]), kw["lout"])
        for _ in range(kw["R"])
    ]
    arrivals.sort()
    case = sim.Case(
        kw["K"],
        kw["S"],
        kw["lat"],
        kw["bw"],
        32768,
        kw["layers"],
        kw["slo1"],
        kw["slo2"],
        decode_table(kw["pproc"], kw["dproc"]),
        arrivals,
        wtp,
        1.0 - wtp,
    )
    case.tp_base = kw["tp_base"]
    case.tp_ub = kw["tp_ub"]
    case.dist_base = kw["dist_base"]
    case.name = name
    return case


def official5():
    return make(
        "official5-cal",
        0.80,
        K=8,
        R=100,
        lout=96,
        lat=5.0,
        bw=8.0,
        S=2.0,
        layers=8,
        span=8.0,
        lin=(256, 512, 1024),
        seed=701,
        pproc=44,
        dproc=2.5,
        slo1=1500,
        slo2=60.2,
        tp_base=0.05,
        tp_ub=3.40,
        dist_base=12.0,
    )


def official6():
    return make(
        "official6-cal",
        0.90,
        K=8,
        R=140,
        lout=46,
        lat=4.4,
        bw=8.0,
        S=2.0,
        layers=8,
        span=4.0,
        lin=(512, 1024, 2048),
        seed=802,
        pproc=90,
        dproc=2.5,
        slo1=3200,
        slo2=58.0,
        tp_base=0.03,
        tp_ub=2.16,
        dist_base=12.0,
    )


def busy_trace(binary, case):
    simu = sim.Sim(case)
    proc = subprocess.Popen(
        [binary], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1
    )
    hdr = [
        f"{case.K} {case.S:.9f} {case.lat:.9f} {case.bw:.9f} {case.bpt} {case.layers}",
        f"{case.slo1:.9f} {case.slo2:.9f} {case.tp_ub:.9f} {case.tp_base:.9f} "
        f"{case.dist_base:.9f} {case.wtp:.9f} {case.wc:.9f}",
        str(len(case.table)),
    ]
    for row in case.table:
        hdr.append(f"{row[0]} " + " ".join(f"{v:.9f}" for v in row[1:]))
    proc.stdin.write("\n".join(hdr) + "\n")
    proc.stdin.flush()
    acc = dict(
        edge_busy=0.0,
        edge_idle_dec=0.0,
        cloud_busy=0.0,
        up_busy=0.0,
        down_busy=0.0,
        span=0.0,
    )
    prev = None
    while True:
        if not simu.ev:
            if simu.reqs and all(r.st == "fin" for r in simu.reqs):
                proc.stdin.write("END\n")
                proc.stdin.flush()
                proc.stdin.close()
                proc.wait(timeout=30)
                return simu, acc
            raise RuntimeError("stuck")
        t, evs = simu.frame()
        simu.t = t
        if prev is not None:
            dt = t - prev[0]
            for key, val in prev[1].items():
                acc[key] += dt * val
            acc["span"] += dt
        lines = []
        for kind, payload in evs:
            lines.extend(simu.apply(kind, payload))
        proc.stdin.write(f"{t:.9f}\n{len(lines)}\n" + "\n".join(lines) + "\n")
        proc.stdin.flush()
        ncmd = int(proc.stdout.readline().strip())
        for _ in range(ncmd):
            simu.assign(proc.stdout.readline().strip())
        inflight = any(
            r.st
            in (
                "dpre",
                "dup",
                "dproc_ready",
                "dproc",
                "ddown",
                "dpost_ready",
                "dpost",
                "didle",
            )
            for r in simu.reqs
        )
        idle_edge = simu.edge_task is None
        ncloud = sum(1.0 for task in simu.cloud_task if task is not None)
        st = {
            "edge_busy": 0.0 if idle_edge else 1.0,
            "edge_idle_dec": 1.0 if idle_edge and inflight else 0.0,
            "cloud_busy": ncloud / case.K,
            "up_busy": 1.0 if simu.up_free - t > 1e-9 else 0.0,
            "down_busy": 1.0 if simu.down_free - t > 1e-9 else 0.0,
        }
        prev = (t, st)


def summarize(label, binary, case):
    metrics, frames, sm = sim.run(binary, case)
    pts, ntp, nc, dist = sim.score(case, metrics)
    _, acc = busy_trace(binary, case)
    span = acc["span"]
    print(
        f"{label}: pts={pts:.2f} ntp={ntp:.3f} nc={nc:.3f} dist={dist:.4f} "
        f"tp={metrics[0]:.4f} tdr={metrics[1]:.1f} tpot={metrics[2]:.2f} "
        f"cpu={sm.cpu:.3f}s frames={frames}"
    )
    print(
        f"  span={span:.1f} edge_busy={100 * acc['edge_busy'] / span:5.1f}% "
        f"edge_idle_with_decode={100 * acc['edge_idle_dec'] / span:5.1f}% "
        f"cloud_busy={100 * acc['cloud_busy'] / span:5.1f}% "
        f"up_busy={100 * acc['up_busy'] / span:5.1f}% "
        f"down_busy={100 * acc['down_busy'] / span:5.1f}%"
    )
    return metrics, pts, ntp, nc


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: calibrate_official56.py BASE CANDIDATE")
    base, cand = sys.argv[1], sys.argv[2]
    failed = 0
    for case in (official5(), official6()):
        print(f"\n=== {case.name} w_tp={case.wtp:.2f} ===")
        b_m, _, _, b_nc = summarize("base", base, case)
        c_m, _, _, c_nc = summarize("cand", cand, case)
        dtp = c_m[0] - b_m[0]
        print(f"  delta tp={dtp:+.4f} tpot={c_m[2] - b_m[2]:+.2f} nc {b_nc:.3f}->{c_nc:.3f}")
        if dtp <= 1e-6:
            print("  REJECT: no throughput increase")
            failed += 1
        if c_nc < 0.99:
            print("  REJECT: nc < 0.99")
            failed += 1
    if failed:
        raise SystemExit(f"{failed} calibrated-case check(s) failed")
    print("\ncalibrated #5/#6: tp rose and nc stayed >= 0.99")


if __name__ == "__main__":
    main()

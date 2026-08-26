#!/usr/bin/env python3
"""Timeline diagnostic: for one workload, measure how much of the makespan the
edge / uplink / downlink / clouds spend idle *while eligible work exists*."""
from __future__ import annotations

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


CASES = {
    "hilat-K16": dict(seed=6001, K=16, R=400, kind="gpu", lat=20.0, bw=1.0, S=2.0,
                      lin_lo=16, lin_hi=1024, lout_hi=64),
    "hilat-K8-R2000": dict(seed=6002, K=8, R=2000, kind="flat", lat=20.0, bw=1.0, S=2.0,
                           lin_lo=16, lin_hi=1024, lout_hi=64),
    "hilat-K1": dict(seed=6003, K=1, R=400, kind="gpu", lat=20.0, bw=1.0, S=2.0,
                     lin_lo=16, lin_hi=1024, lout_hi=64),
    "lolat-K8": dict(seed=6004, K=8, R=400, kind="gpu", lat=1.0, bw=10.0, S=2.0,
                     lin_lo=16, lin_hi=1024, lout_hi=64),
    "cloudbound-K1": dict(seed=6005, K=1, R=2000, kind="cpu", lat=1.0, bw=10.0, S=2.0,
                          lin_lo=4096, lin_hi=4096, lout_hi=64),
}


def build(name):
    kw = dict(CASES[name])
    seed = kw.pop("seed")
    return mk(name, seed, kw.pop("K"), kw.pop("R"), 32, 400.0, 1.00, 0.05, 0.05, **kw)


def run_traced(binary, c):
    """Re-implementation of sim.run that samples resource occupancy per frame."""
    import resource
    import subprocess
    s = sim.Sim(c)
    proc = subprocess.Popen([binary], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            text=True, bufsize=1)
    hdr = [f"{c.K} {c.S:.9f} {c.lat:.9f} {c.bw:.9f} {c.bpt} {c.layers}",
           f"{c.slo1:.9f} {c.slo2:.9f} {c.tp_ub:.9f} {c.tp_base:.9f} {c.dist_base:.9f} "
           f"{c.wtp:.9f} {c.wc:.9f}",
           str(len(c.table))]
    for row in c.table:
        hdr.append(f"{row[0]} " + " ".join(f"{v:.9f}" for v in row[1:]))
    proc.stdin.write("\n".join(hdr) + "\n")
    proc.stdin.flush()

    acc = dict(edge_idle_work=0.0, edge_idle_pref=0.0, up_idle_pref=0.0,
               cloud_idle_work=0.0, dec_inflight=0.0, span=0.0, edge_busy_dec=0.0,
               edge_busy_pref=0.0)
    prev = None
    while True:
        if not s.ev:
            if s.reqs and all(r.st == "fin" for r in s.reqs):
                proc.stdin.write("END\n")
                proc.stdin.flush()
                proc.stdin.close()
                proc.wait(timeout=10)
                return s, acc
            raise RuntimeError("stuck")
        t, evs = s.frame()
        if prev is not None:
            dt = t - prev[0]
            for k, v in prev[1].items():
                acc[k] += dt * v
            acc["span"] += dt
        s.t = t
        lines = []
        for kind, p in evs:
            lines.extend(s.apply(kind, p))
        proc.stdin.write(f"{t:.9f}\n{len(lines)}\n" + "\n".join(lines) + "\n")
        proc.stdin.flush()
        head = proc.stdout.readline()
        if not head:
            raise RuntimeError("closed")
        n = int(head.strip())
        for _ in range(n):
            s.assign(proc.stdout.readline().strip())
        # sample state right after assignment decisions
        st = {}
        pref_ready = sum(1 for r in s.reqs if r.st in ("new", "ppost_ready") and r.arr <= t)
        dec_ready = sum(1 for r in s.reqs if r.st in ("didle", "dpost_ready"))
        edge_idle = 1.0 if s.edge_task is None else 0.0
        st["edge_idle_work"] = edge_idle if (pref_ready or dec_ready) else 0.0
        st["edge_idle_pref"] = edge_idle if pref_ready else 0.0
        st["up_idle_pref"] = 1.0 if (s.up_free <= t and pref_ready) else 0.0
        st["cloud_idle_work"] = sum(1.0 for x in s.cloud_task if x is None)
        st["dec_inflight"] = sum(1.0 for r in s.reqs
                                 if r.st in ("dpre", "dup", "dproc_ready", "dproc", "ddown"))
        if s.edge_task is not None:
            f = s.edge_task.split()
            if f[0] == "D":
                st["edge_busy_dec"] = 1.0
            else:
                st["edge_busy_pref"] = 1.0
        prev = (t, st)


def main():
    name = sys.argv[1]
    bins = sys.argv[2:]
    c = build(name)
    sim.calibrate(c, "/tmp/ref_sequential")
    s0 = sim.Sim(c)
    edge = cloud = up = 0.0
    for (_t, lin, _l) in c.arrivals:
        edge += 2 * c.S + s0.ppre.get(lin) + s0.ppost.get(lin)
        cloud += c.S + s0.pproc.get(lin)
        up += c.lat + 8.0 * lin * c.bpt / (c.bw * 1e6)
    tot = sum(l for (_t, _i, l) in c.arrivals)
    best = 0.0
    for m in [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]:
        k = min(c.K, m)
        per = math.ceil(m / k)
        e = 2 * c.S + s0.dpre.get(m) + s0.dpost.get(m)
        ln = 2 * (k * c.lat + 8.0 * m * c.bpt / (c.bw * 1e6))
        best = max(best, m / (e + ln + c.S + s0.dproc.get(per)))
    print(f"{name}: K={c.K} R={len(c.arrivals)} tokens={tot} "
          f"floors edge={edge:.4g} cloud/K={cloud/c.K:.4g} up={up:.4g} "
          f"dec={tot/best:.4g} (best_rate={best:.4g})")
    for b in bins:
        s, acc = run_traced(b, c)
        sp = acc["span"]
        m = s.metrics()
        print(f"  {b.split('/')[-1]:<18} makespan={sp:.4g} tp={m[0]:.5g} "
              f"tdr={m[1]:.4g} tpot={m[2]:.4g}")
        print(f"      edge: busy_pref={100*acc['edge_busy_pref']/sp:5.1f}% "
              f"busy_dec={100*acc['edge_busy_dec']/sp:5.1f}% "
              f"idle_with_work={100*acc['edge_idle_work']/sp:5.1f}% "
              f"idle_with_prefill={100*acc['edge_idle_pref']/sp:5.1f}%")
        print(f"      up_idle_with_prefill={100*acc['up_idle_pref']/sp:5.1f}%  "
              f"mean_free_clouds={acc['cloud_idle_work']/sp:5.2f}/{c.K}  "
              f"mean_dec_inflight={acc['dec_inflight']/sp:7.2f}")
        for k, (n, g, tsum) in s.stats.items():
            if n:
                print(f"      {k:<7} tasks={n:6d} mean_group={g/n:8.2f} busy={tsum:10.1f}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Re-derive #14 min-round and #10/#15 mean-completion lower bounds.

Official fingerprints (submission 16041.088):
  #14 w=0.65 pts=415.267 tp=0.003564 tdr=192.489397 tpot=184.378198
      dist=0.176642 ntp=0.2103 nc=0.7959
  #10 w=0.15 pts~684.42 tp=0.007628 tdr=182521.13 tpot=86.987
      ntp=0.9943 nc=0.6298 SLO1=1258.9 SLO2=64.85
      tp_base=0.0028312 tp_UB=0.0076595
  #15 w=0.45 tp=0.000009 tdr=19297351.06 tpot=0 ntp=0.9796 nc=0.4958
"""
from __future__ import annotations

import math
import random
import sys

import sim

sys.stdout.reconfigure(line_buffering=True)


OFF14 = dict(wtp=0.65, pts=415.267, tp=0.003564, tdr=192.489397,
             tpot=184.378198, dist=0.176642, ntp=0.2103, nc=0.7959)
OFF10 = dict(wtp=0.15, tp=0.007628, tdr=182521.13, tpot=86.987,
             ntp=0.9943, nc=0.6298, slo1=1258.9, slo2=64.85,
             tp_base=0.0028312, tp_ub=0.0076595)
OFF15 = dict(wtp=0.45, tp=0.000009, tdr=19297351.06, tpot=0.0,
             ntp=0.9796, nc=0.4958)

BASE = sys.argv[1] if len(sys.argv) > 1 else "/tmp/tdr-base"
AKD = sys.argv[2] if len(sys.argv) > 2 else "/tmp/bin-akd"
REF = sys.argv[3] if len(sys.argv) > 3 else "/tmp/tdr-ref"


def xfer(c, n):
    return c.lat + 8.0 * n * c.bpt / (c.bw * 1e6)


def floors_one(c):
    """Closed-form TDR and decode-round floors for a single request, unsplit."""
    s = sim.Sim(c)
    _t, lin, _l = c.arrivals[0]
    tdr = (3 * c.S + s.ppre.get(lin) + s.pproc.get(lin) + s.ppost.get(lin)
           + 2 * xfer(c, lin))
    rnd = (3 * c.S + s.dpre.get(1) + s.dproc.get(1) + s.dpost.get(1)
           + 2 * xfer(c, 1))
    return tdr, rnd


def official14_case():
    """Single request, L_out=2, table/hardware chosen so the forced chain
    reproduces official tdr/tpot exactly when the binary adds no idle/S."""
    want_tdr = OFF14["tdr"]
    want_rnd = OFF14["tpot"]
    S, lat, bw, bpt, layers, lin = 2.0, 20.0, 1.0, 32768, 8, 256
    bit = 8.0 * bpt / (bw * 1e6)
    x1 = lat + bit
    xlin = lat + lin * bit
    # Split decode compute equally; leftover after 3S+2*xfer is the table sum.
    dec_sum = want_rnd - 3 * S - 2 * x1
    pref_sum = want_tdr - 3 * S - 2 * xlin
    dpre = dpost = max(0.05, dec_sum * 0.12)
    dproc = max(0.05, dec_sum - dpre - dpost)
    ppre = ppost = max(0.05, pref_sum * 0.15)
    pproc = max(0.05, pref_sum - ppre - ppost)
    sizes = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]
    rows = []
    for b in sizes:
        # Prefill scales with tokens; decode of a singleton is pinned at b=1.
        scale = b / float(lin)
        rows.append((
            b,
            ppre * scale if b != 1 else ppre * (1.0 / lin),
            pproc * scale if b != 1 else pproc * (1.0 / lin),
            ppost * scale if b != 1 else ppost * (1.0 / lin),
            dpre if b == 1 else dpre * (1.0 + 0.002 * (b - 1)),
            dproc if b == 1 else dproc * (1.0 + 0.01 * (b - 1)),
            dpost if b == 1 else dpost * (1.0 + 0.002 * (b - 1)),
        ))
    # Force exact values at the used sizes via piecewise-linear knots.
    def set_at(b, vals):
        for i, row in enumerate(rows):
            if row[0] == b:
                rows[i] = (b,) + vals
                return
    set_at(1, (ppre / lin, pproc / lin, ppost / lin, dpre, dproc, dpost))
    set_at(lin, (ppre, pproc, ppost, dpre * 1.5, dproc * 3.0, dpost * 1.5))
    c = sim.Case(4, S, lat, bw, bpt, layers, 1.0, 1.0, rows,
                 [(0.0, lin, 2)], 0.65, 0.35)
    c.name = "official14-lout2"
    c._a1, c._a2 = 1.5, 1.2
    return c


def score14(tp, tdr, tpot, tp_base, tp_ub, dbase, slo1, slo2):
    ntp = 0.0
    if tp_ub > tp_base:
        ntp = max(0.0, min(1.0, (tp - tp_base) / (tp_ub - tp_base)))
    ex1 = max(0.0, (tdr - slo1) / slo1)
    ex2 = max(0.0, (tpot - slo2) / slo2)
    dist = math.hypot(ex1, ex2)
    nc = max(0.0, 1.0 - dist / dbase) if dbase > 0 else (1.0 if dist <= 1e-12 else 0.0)
    pts = 1000.0 * (0.65 * ntp + 0.35 * nc)
    return pts, ntp, nc, dist


def spt_mean(ps):
    """Non-preemptive SPT mean completion, all jobs available at 0."""
    n = len(ps)
    if n == 0:
        return 0.0
    order = sorted(ps)
    t = 0.0
    acc = 0.0
    for p in order:
        t += p
        acc += t
    return acc / n


def resource_work(c):
    s = sim.Sim(c)
    jobs = []
    for (arr, lin, _l) in c.arrivals:
        ppre = c.S + s.ppre.get(lin)
        pproc = c.S + s.pproc.get(lin)
        ppost = c.S + s.ppost.get(lin)
        up = xfer(c, lin)
        jobs.append(dict(arr=arr, lin=lin, ppre=ppre, pproc=pproc,
                         ppost=ppost, up=up, chain=ppre + pproc + ppost + 2 * up))
    return jobs


def mean_completion_lbs(c):
    jobs = resource_work(c)
    n = len(jobs)
    chain = sum(j["chain"] for j in jobs) / n
    edge_p = [j["ppre"] + j["ppost"] for j in jobs]
    pre_p = [j["ppre"] for j in jobs]
    post_p = [j["ppost"] for j in jobs]
    cloud_p = [j["pproc"] for j in jobs]
    link_p = [j["up"] for j in jobs]
    edge_spt = spt_mean(edge_p)
    pre_spt = spt_mean(pre_p)
    post_spt = spt_mean(post_p)
    cloud_speedk = spt_mean([p / max(c.K, 1) for p in cloud_p])
    up_spt = spt_mean(link_p)
    down_spt = up_spt
    rest_after_pre = sum(j["up"] + j["pproc"] + j["up"] + j["ppost"] for j in jobs) / n
    rest_after_up = sum(j["pproc"] + j["up"] + j["ppost"] for j in jobs) / n
    rest_after_proc = sum(j["up"] + j["ppost"] for j in jobs) / n
    rest_after_down = sum(j["ppost"] for j in jobs) / n
    lbs = {
        "chain": chain,
        "pre_spt+rest": pre_spt + rest_after_pre,
        "up_spt+rest": up_spt + rest_after_up,
        "cloud_spt+rest": cloud_speedk + rest_after_proc,
        "down_spt+rest": down_spt + rest_after_down,
        "post_spt": post_spt,
        "edge_spt": edge_spt,
        "cloud_spt": cloud_speedk,
        "up_spt": up_spt,
    }
    keys = ("chain", "pre_spt+rest", "up_spt+rest", "cloud_spt+rest",
            "down_spt+rest", "post_spt")
    lbs["best"] = max(lbs[k] for k in keys)
    lbs["which"] = max(keys, key=lambda k: lbs[k])
    return lbs
    lbs = {
        "chain": chain,
        "edge_spt": edge_spt,
        "cloud_spt": cloud_speedk,
        "up_spt": up_spt,
        "down_spt": down_spt,
    }
    lbs["best"] = max(lbs[k] for k in ("chain", "edge_spt", "cloud_spt", "up_spt"))
    lbs["which"] = max(
        ("chain", "edge_spt", "cloud_spt", "up_spt"),
        key=lambda k: lbs[k],
    )
    return lbs


def official10_cases(seeds):
    out = []
    lengths = [16, 32, 64, 128, 256, 512, 1024, 2048, 4096]
    for seed in seeds:
        rng = random.Random(seed)
        arr = sorted(
            (rng.uniform(0.0, 5.0), rng.choice(lengths),
             rng.choice([1, 2, 4, 8, 16, 32]))
            for _ in range(2000)
        )
        c = sim.Case(2, 2.0, 1.0, 10.0, 32768, 16,
                     OFF10["slo1"], OFF10["slo2"],
                     sim.make_table("edge", rng), arr, .15, .85)
        c.name = f"official10-s{seed}"
        c.tp_base, c.tp_ub, c.dist_base = OFF10["tp_base"], OFF10["tp_ub"], 389.0
        out.append(c)
    return out


def official15_cases(seeds):
    """L_out=1, TDR-only, large backlog. Hardware is searched-for later; this
    is the structural family (edge-bound or link-bound, all outputs 1)."""
    out = []
    lengths = [16, 32, 64, 128, 256, 512, 1024, 2048, 4096]
    for seed in seeds:
        rng = random.Random(seed)
        arr = sorted(
            (rng.uniform(0.0, 5.0), rng.choice(lengths), 1)
            for _ in range(2000)
        )
        c = sim.Case(4, 2.0, 20.0, 1.0, 32768, 8,
                     1.0, 1.0, sim.make_table("edge", rng), arr, .45, .55)
        c.name = f"official15-edge-s{seed}"
        c.tp_base, c.tp_ub, c.dist_base = 1e-6, 1e-3, 40.0
        out.append(c)
    return out


def report_run(label, binary, case):
    m, frames, sm = sim.run(binary, case)
    tp, tdr, tpot = m
    pts, ntp, nc, dist = sim.score(case, m)
    span = max(r.toks[-1] for r in sm.reqs) - min(r.arr for r in sm.reqs)
    print(f"  {label:<18} pts={pts:8.3f} ntp={ntp:.4f} nc={nc:.4f} "
          f"tp={tp:.6g} tdr={tdr:.6g} tpot={tpot:.6g} "
          f"span={span:.6g} frames={frames} cpu={getattr(sm,'cpu',0):.3f}")
    return m, frames, sm, pts


def main():
    print("=" * 72)
    print("TARGET A — official #14 arithmetic")
    print("=" * 72)
    tdr, tpot, tp = OFF14["tdr"], OFF14["tpot"], OFF14["tp"]
    span = tdr + 2 * tpot
    print(f"  tdr + 2*tpot = {tdr:.9f} + 2*{tpot:.9f} = {span:.9f}")
    print(f"  2/span       = {2.0 / span:.12f}  official tp={tp:.9f}  "
          f"err={2.0 / span - tp:.3e}")
    print(f"  dist_base from nc: {OFF14['dist'] / max(1e-12, 1.0 - OFF14['nc']):.6f}")
    print(f"  nc check: 0.65*{OFF14['ntp']}+0.35*{OFF14['nc']} = "
          f"{1000*(0.65*OFF14['ntp']+0.35*OFF14['nc']):.3f} vs pts={OFF14['pts']}")

    c14 = official14_case()
    tdr_f, rnd_f = floors_one(c14)
    print(f"\n  calibrated floor tdr={tdr_f:.9f} (want {tdr:.9f})  "
          f"d={tdr_f - tdr:.3e}")
    print(f"  calibrated floor rnd={rnd_f:.9f} (want {tpot:.9f})  "
          f"d={rnd_f - tpot:.3e}")
    print(f"  min round formula: 2S + D_PRE(1)+D_POST(1) + S+D_PROC(1) + "
          f"2*(LAT+8*BPT/(BW*1e6))")
    print(f"                     = {rnd_f:.9f}")
    print(f"  observed official tpot - floor (on this recon) = "
          f"{tpot - rnd_f:.3e}")
    print("  If a binary matches tdr_f and rnd_f, it is AT the forced-chain "
          "floor: extra S (chunking) and idle can only raise both.")

    print("\n  sequential ref / current / AKD on the calibrated recon:")
    sim.calibrate(c14, REF)
    print(f"  judge constants: slo1={c14.slo1:.6g} slo2={c14.slo2:.6g} "
          f"tp_base={c14.tp_base:.6g} tp_ub={c14.tp_ub:.6g} "
          f"dbase={c14.dist_base:.6g} ref={c14.ref}")
    for lab, b in (("current", BASE), ("akd", AKD), ("seq", REF)):
        try:
            m, frames, sm, pts = report_run(lab, b, c14)
            d_tdr = m[1] - tdr_f
            d_rnd = m[2] - rnd_f
            print(f"    vs floor  dTDR={d_tdr:.6g}  dROUND={d_rnd:.6g}  "
                  f"{'AT FLOOR' if d_tdr <= 1e-6 and d_rnd <= 1e-6 else 'ABOVE'}")
        except Exception as e:
            print(f"  {lab:<18} FAIL {e}")

    # Grid: is current ever above the floor on single-request L_out=2?
    print("\n  floor grid for current binary:")
    bad = 0
    worst = (0.0, 0.0, "")
    n = 0
    for kind in ("gpu", "edge"):
        for K in (1, 4, 8):
            for S in (2.0, 9.0):
                for lat, bw in ((1.0, 10.0), (20.0, 1.0)):
                    for lin in (16, 256, 4096):
                        for layers in (1, 8):
                            rng = random.Random(1)
                            rows = sim.make_table(kind, rng)
                            c = sim.Case(K, S, lat, bw, 32768, layers, 1.0, 1.0,
                                         rows, [(0.0, lin, 2)], 0.65, 0.35)
                            c.name = f"{kind}-K{K}-S{S}-lat{lat}-lin{lin}-L{layers}"
                            c._a1, c._a2 = 1.5, 1.2
                            tf, rf = floors_one(c)
                            (tp, td, to), _, _ = sim.run(BASE, c)
                            n += 1
                            dt, dr = td - tf, to - rf
                            if dt > 1e-6 or dr > 1e-6:
                                bad += 1
                                if dt + dr > worst[0] + worst[1]:
                                    worst = (dt, dr, c.name)
    print(f"  current above floor on {bad}/{n} shapes; worst {worst[2]} "
          f"dTDR={worst[0]:.6g} dROUND={worst[1]:.6g}")

    print("\n" + "=" * 72)
    print("TARGET B — #10 / #15 mean-completion lower bounds")
    print("=" * 72)
    # Official #10 nc inversion: dist ≈ ex_tdr since tpot leg is tiny.
    ex1 = (OFF10["tdr"] - OFF10["slo1"]) / OFF10["slo1"]
    ex2 = max(0.0, (OFF10["tpot"] - OFF10["slo2"]) / OFF10["slo2"])
    dist = math.hypot(ex1, ex2)
    dbase10 = dist / max(1e-12, 1.0 - OFF10["nc"])
    print(f"  #10 ex1={ex1:.4f} ex2={ex2:.4f} dist={dist:.4f} dbase={dbase10:.2f} "
          f"(TDR leg share {ex1 / dist:.6f})")
    print(f"  #10 ntp remaining {1-OFF10['ntp']:.4f} -> {0.15*(1-OFF10['ntp'])*1000:.1f} tp pts; "
          f"nc remaining {1-OFF10['nc']:.4f} -> {0.85*(1-OFF10['nc'])*1000:.1f} wait pts")

    print("\n  #10 official-constant R=2000 probes (SPT already on at w=.15):")
    for c in official10_cases((1009, 1010)):
        lbs = mean_completion_lbs(c)
        m, frames, sm, pts = report_run("current", BASE, c)
        tdr = m[1]
        print(f"    {c.name}: meanTDR={tdr:.1f}  LB[{lbs['which']}]={lbs['best']:.1f}  "
              f"ratio={tdr / lbs['best']:.4f}  chain={lbs['chain']:.1f}  "
              f"pre+rest={lbs['pre_spt+rest']:.1f} up+rest={lbs['up_spt+rest']:.1f} "
              f"cloud+rest={lbs['cloud_spt+rest']:.1f}")

    print("\n  #15 L_out=1 probes (decode batching irrelevant):")
    print(f"  official tdr={OFF15['tdr']:.2f} tpot=0 ntp={OFF15['ntp']} nc={OFF15['nc']}")
    print(f"  remaining: {0.45*(1-OFF15['ntp'])*1000:.1f} tp pts + "
          f"{0.55*(1-OFF15['nc'])*1000:.1f} wait pts")
    for c in official15_cases((1509, 1510)):
        lbs = mean_completion_lbs(c)
        m, frames, sm, pts = report_run("current", BASE, c)
        tdr = m[1]
        print(f"    {c.name}: meanTDR={tdr:.1f}  LB[{lbs['which']}]={lbs['best']:.1f}  "
              f"ratio={tdr / lbs['best']:.4f}  chain={lbs['chain']:.1f}  "
              f"pre+rest={lbs['pre_spt+rest']:.1f} up+rest={lbs['up_spt+rest']:.1f} "
              f"cloud+rest={lbs['cloud_spt+rest']:.1f}")
        if abs(m[2]) > 1e-9:
            print(f"    WARNING tpot={m[2]} expected 0")


if __name__ == "__main__":
    main()

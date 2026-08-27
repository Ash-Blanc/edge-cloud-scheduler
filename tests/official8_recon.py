#!/usr/bin/env python3
"""Confirm fitted official #8 (WTP=0.25) vs d202b1a and report honest LBs.

Official #8 (16041 vector):
  points=833.386 tp=0.013238 tdr=1087.155 tpot=98.803
  ntp=0.766 nc=0.856 remaining ~167

Usage: python3 tests/official8_recon.py /tmp/d202-sched
"""
from __future__ import annotations

import math
import sys

import sim
from official48_recon import OFF, fitted8, summarize
from tdr_decomp import STAGES, request_parts, request_service


def spt_mean(ps):
    t = acc = 0.0
    for p in sorted(ps):
        t += p
        acc += t
    return acc / len(ps) if ps else 0.0


def xfer(c, n):
    return c.lat + 8.0 * n * c.bpt / (c.bw * 1e6)


def release_spt(jobs):
    """Mean completion on one FIFO with (release, service) under SPT among ready."""
    jobs = sorted(jobs)
    t = acc = 0.0
    ready = []
    i = 0
    n = len(jobs)
    done = 0
    while done < n:
        while i < n and jobs[i][0] <= t + 1e-12:
            ready.append(jobs[i][1])
            i += 1
        if not ready:
            t = jobs[i][0]
            continue
        ready.sort()
        p = ready.pop(0)
        t = max(t, jobs[0][0]) if done == 0 else t
        t += p
        acc += t
        done += 1
    return acc / n if n else 0.0


def floors(case):
    s = sim.Sim(case)
    edge = []
    cloud = []
    up = []
    pe = pc = pu = 0.0
    ppre_jobs = []
    up_jobs = []
    after = []
    t_ppre = 0.0
    for (_t, lin, _l) in case.arrivals:
        e = (case.S + s.ppre.get(lin)) + (case.S + s.ppost.get(lin))
        ppre = case.S + s.ppre.get(lin)
        p = case.S + s.pproc.get(lin)
        u = xfer(case, lin)
        d = xfer(case, lin)
        post = case.S + s.ppost.get(lin)
        edge.append(e)
        cloud.append(p)
        up.append(u)
        pe += e
        pc += p
        pu += u
        ppre_jobs.append(ppre)
        up_jobs.append(u)
        after.append(p + d + post)
    t_edge = t_up = 0.0
    tdrs = []
    for u, ppre, a in sorted(zip(up_jobs, ppre_jobs, after)):
        t_edge += ppre
        t_up = max(t_up, t_edge) + u
        tdrs.append(t_up + a)
    tdr_spt_lb = sum(tdrs) / len(tdrs) if tdrs else 0.0
    tot = sum(l for (_t, _i, l) in case.arrivals)
    best = 0.0
    best_m = 1
    for m in range(1, min(4096, tot) + 1):
        k = min(case.K, m)
        per = math.ceil(m / k)
        rt = (2 * case.S + s.dpre.get(m) + s.dpost.get(m)
              + 2 * (k * case.lat + 8.0 * m * case.bpt / (case.bw * 1e6))
              + case.S + s.dproc.get(per))
        rate = m / max(rt, 1e-12)
        if rate > best:
            best, best_m = rate, m
    fl = {
        "edge_work": pe,
        "cloud_work": pc / case.K,
        "up_work": pu,
        "down_work": pu,
        "dec_work": tot / best if best else 0.0,
        "edge_spt": spt_mean(edge),
        "cloud_spt_serial": spt_mean(cloud),
        "up_spt": spt_mean(up),
        "best_m": best_m,
        "best_rate": best,
        "need": math.ceil(pc / max(pe, pu, 1e-12) * 1.08) if max(pe, pu) else case.K,
        "tdr_spt_lb": tdr_spt_lb,
        "tdr_up_plus_after": spt_mean(up) + (sum(after) / len(after) if after else 0.0),
    }
    fl["prefill_span"] = max(fl["edge_work"], fl["cloud_work"], fl["up_work"], fl["down_work"])
    fl["span_lb"] = max(fl["prefill_span"], fl["dec_work"])
    return fl


def decomp(state):
    rows = [request_parts(r) for r in state.reqs]
    svc = [request_service(r) for r in state.reqs]
    n = len(rows)
    out = []
    for i, name in enumerate(STAGES):
        mean = sum(row[i] for row in rows) / n
        service = sum(row[i] for row in svc) / n
        queue = mean - service
        out.append((name, mean, queue, service, queue / mean if mean else 0.0))
    return out


def main():
    binary = sys.argv[1] if len(sys.argv) > 1 else "/tmp/d202-sched"
    o = OFF[8]
    print(
        f"official #8 tp={o['tp']} tdr={o['tdr']:.3f} tpot={o['tpot']:.3f} "
        f"ntp={o['ntp']:.3f} nc={o['nc']:.3f} pts={o['pts']:.3f}"
    )
    print(
        f"  remaining={1000 - o['pts']:.1f}  "
        f"ntp_left={o['wtp'] * (1 - o['ntp']) * 1000:.1f}  "
        f"nc_left={(1 - o['wtp']) * (1 - o['nc']) * 1000:.1f}"
    )
    worst = 0.0
    for seed in (38, 39, 48, 58, 68):
        case = fitted8(seed=seed)
        err, rel, metrics, pts, ntp, nc, sm = summarize(binary, case, 8)
        emax = max(rel.values())
        worst = max(worst, emax)
        fl = floors(case)
        span = max(r.toks[-1] for r in sm.reqs) - min(r.arr for r in sm.reqs)
        tdr = metrics[1]
        print(
            f"  span={span:.1f} prefill_lb={fl['prefill_span']:.1f} "
            f"span_lb={fl['span_lb']:.1f} x{span / fl['span_lb']:.3f} "
            f"need={fl['need']}/{case.K} "
            f"{'PREFILL-BOUND' if fl['need'] >= case.K else 'LAT-bound-ish'} "
            f"best_m={fl['best_m']} rate={fl['best_rate']:.5f}"
        )
        print(
            f"  work edge={fl['edge_work']:.1f} cloud/K={fl['cloud_work']:.1f} "
            f"up={fl['up_work']:.1f} dec={fl['dec_work']:.1f}"
        )
        print(
            f"  TDR={tdr:.1f} tdr_spt_lb={fl['tdr_spt_lb']:.1f} "
            f"TDR/SPT={tdr / fl['tdr_spt_lb']:.4f} slack="
            f"{100 * (tdr / fl['tdr_spt_lb'] - 1):.2f}% "
            f"up_spt+after={fl['tdr_up_plus_after']:.1f} "
            f"edge_spt={fl['edge_spt']:.1f} cloud_spt={fl['cloud_spt_serial']:.1f}"
        )
        if seed == 38:
            print("  TDR decomposition:")
            for name, mean, queue, service, qfrac in decomp(sm):
                print(
                    f"    {name:<9} mean={mean:10.1f} queue={queue:10.1f} "
                    f"svc={service:8.1f} q%={qfrac:6.1%}"
                )
            dpre = sm.stats["D PRE"]
            print(
                f"  D PRE tasks={dpre[0]} mean_group={dpre[1] / max(1, dpre[0]):.2f} "
                f"busy={dpre[2]:.1f}"
            )
            for k in ("P PRE", "P PROC", "P POST", "D PRE", "D PROC", "D POST"):
                n, g, tsum = sm.stats[k]
                print(f"    {k:<7} n={n:4d} mean_g={g / max(1, n):6.2f} busy={tsum:10.1f}")
        if emax > 0.05:
            print(f"  WARN seed {seed} rel-err {emax:.3f} > 5%")
    print(f"worst rel-err {worst:.4f}")


if __name__ == "__main__":
    main()

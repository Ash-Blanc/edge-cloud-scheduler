#!/usr/bin/env python3
"""A/B decode-fire probes on official-binding #5/#6 reconstructions.

Variants are compile-time AKD56_* flags gated to wEq(.80)||wEq(.90).
Prefill-bound means ceil(cloudW/feedW*1.08) >= K (k-shrink floor holds k=K).

Usage: python3 tests/akd56_stream_probe.py BASE VAR=path [VAR=path ...]
"""
from __future__ import annotations

import copy
import math
import random
import sys

import sim
from ensemble_compare import test17_case, test22_case
from historical22_trace_compare import historical_replay
from trace_compare import traced_run

OFFICIAL = {
    5: dict(wtp=0.80, pts=465.593, tp=1.121008, tdr=1497.256, tpot=60.081,
            ntp=0.3326, nc=0.9977, tp_base=0.022737, tp_ub=3.32417,
            slo1=309.6, slo2=45.8),
    6: dict(wtp=0.90, pts=389.543, tp=0.696236, tdr=3102.232, tpot=57.814,
            ntp=0.3226, nc=0.9921, tp_base=0.021842, tp_ub=2.11234,
            slo1=505.0, slo2=64.4),
}


def decode_table(pproc_k, dproc_k, dpre_k=1.00, dpre_s=0.008, dproc_s=0.04):
    sizes = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]
    return [
        (
            b,
            0.25 + 0.010 * b,
            pproc_k + 0.08 * b,
            0.20 + 0.005 * b,
            dpre_k + dpre_s * b,
            dproc_k + dproc_s * b,
            dpre_k + dpre_s * b,
        )
        for b in sizes
    ]


def make_case(name, wtp, **kw):
    rng = random.Random(kw["seed"])
    lins = kw["lin"]
    louts = kw["lout"]
    if isinstance(louts, int):
        louts = (louts,)
    arrivals = [
        (rng.uniform(0.0, kw["span"]), rng.choice(lins), rng.choice(louts))
        for _ in range(kw["R"])
    ]
    arrivals.sort()
    case = sim.Case(
        kw["K"], kw["S"], kw["lat"], kw["bw"], kw.get("bpt", 32768),
        kw["layers"], kw.get("slo1", 1.0), kw.get("slo2", 1.0),
        decode_table(kw["pproc"], kw["dproc"], kw.get("dpre_k", 1.00),
                     kw.get("dpre_s", 0.008), kw.get("dproc_s", 0.04)),
        arrivals, wtp, 1.0 - wtp,
    )
    case.tp_base = kw.get("tp_base", 0.05)
    case.tp_ub = kw.get("tp_ub", 3.40)
    case.dist_base = kw.get("dist_base", 12.0)
    case.name = name
    return case


def official5(seed=701, **override):
    kw = dict(K=8, R=100, lout=96, lat=5.0, bw=8.0, S=2.0, layers=8,
              span=8.0, lin=(256, 512, 1024), seed=seed, pproc=44, dproc=2.5,
              slo1=1500, slo2=60.2, tp_base=0.05, tp_ub=3.40, dist_base=12.0)
    kw.update(override)
    return make_case(f"official5-s{kw['seed']}", 0.80, **kw)


def official6(seed=802, **override):
    kw = dict(K=8, R=140, lout=46, lat=4.4, bw=8.0, S=2.0, layers=8,
              span=4.0, lin=(512, 1024, 2048), seed=seed, pproc=90, dproc=2.5,
              slo1=3200, slo2=58.0, tp_base=0.03, tp_ub=2.16, dist_base=12.0)
    kw.update(override)
    return make_case(f"official6-s{kw['seed']}", 0.90, **kw)


def pin_official_constants(case, test):
    o = OFFICIAL[test]
    case.wtp = o["wtp"]
    case.wc = 1.0 - o["wtp"]
    case.tp_base = o["tp_base"]
    case.tp_ub = o["tp_ub"]
    case.slo1 = o["slo1"]
    case.slo2 = o["slo2"]
    ex1 = max(0.0, (o["tdr"] - o["slo1"]) / o["slo1"])
    ex2 = max(0.0, (o["tpot"] - o["slo2"]) / o["slo2"])
    dist = math.hypot(ex1, ex2)
    case.dist_base = dist / max(1e-12, 1.0 - o["nc"])
    return case


def prefill_need(case):
    s = sim.Sim(case)
    cloud_w = feed_w = 0.0
    for _t, lin, _lout in case.arrivals:
        cloud_w += case.S + s.pproc.get(lin)
        feed_w += max(2.0 * case.S + s.ppre.get(lin) + s.ppost.get(lin),
                      s.xfer(lin))
    ratio = cloud_w / feed_w if feed_w > 0 else 0.0
    need = max(1, int(math.ceil(ratio * 1.08))) if feed_w > 0 else 1
    return need, ratio


def retarget(case, wtp):
    c = copy.deepcopy(case)
    c.wtp = wtp
    c.wc = 1.0 - wtp
    c.name = f"{case.name}-w{wtp:g}"
    return c


def summarize(label, binary, case, test=None):
    metrics, frames, sm = sim.run(binary, case)
    pts, ntp, nc, dist = sim.score(case, metrics)
    extra = ""
    if test:
        o = OFFICIAL[test]
        rel = {
            "tp": abs(metrics[0] - o["tp"]) / o["tp"],
            "tdr": abs(metrics[1] - o["tdr"]) / o["tdr"],
            "tpot": abs(metrics[2] - o["tpot"]) / max(o["tpot"], 1e-12),
        }
        extra = (f" fit={rel['tp']+rel['tdr']+rel['tpot']:.3f}"
                 f" dtp={100*rel['tp']:+.1f}% dtdr={100*rel['tdr']:+.1f}%"
                 f" dtpot={100*rel['tpot']:+.1f}%")
    dpre = sm.stats["D PRE"]
    print(
        f"  {label:<16} pts={pts:8.2f} ntp={ntp:.3f} nc={nc:.3f} "
        f"tp={metrics[0]:.4f} tdr={metrics[1]:.1f} tpot={metrics[2]:.2f} "
        f"dpre_n={dpre[0]} dpre_g={dpre[1]/max(1,dpre[0]):.1f}{extra}"
    )
    return metrics, pts, ntp, nc, frames


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: akd56_stream_probe.py BASE [name=BIN ...]")
    base = sys.argv[1]
    variants = []
    for arg in sys.argv[2:]:
        if "=" in arg:
            name, path = arg.split("=", 1)
            variants.append((name, path))
        else:
            variants.append((arg.split("/")[-1], arg))

    print("=== reconstruction fit / prefill-need ===")
    recon = []
    shapes = [
        (5, official5(), "lat5-K8 (known LAT-bound)"),
        (5, official5(K=4), "lat5-K4"),
        (6, official6(), "lat4.4-K8"),
        (5, official5(seed=711, R=100, lout=96, pproc=160, span=15.0),
         "FITTED in-box prefill-bound R100 L96 pp160 sp15"),
        (5, official5(seed=711, lout=128, pproc=207.5, span=50.0),
         "pproc207 span50 (tdr +21%, disqualified)"),
        (5, official5(seed=711, lout=128, pproc=400.0, span=40.0, R=80),
         "pproc400 R80"),
        (5, official5(seed=721, lout=96, pproc=300.0, span=30.0, lat=1.0),
         "pproc300 lat1"),
        (6, official6(seed=812, pproc=250.0, span=20.0, lat=1.0),
         "off6 pproc250 lat1"),
        (6, official6(seed=822, pproc=180.0, span=12.0, K=8, R=120),
         "off6 pproc180"),
    ]
    for test, case, note in shapes:
        pin_official_constants(case, test)
        need, ratio = prefill_need(case)
        bound = "PREFILL" if need >= case.K else "not-prefill"
        print(f"\n#{test} {case.name} {note}")
        print(f"  K={case.K} need={need} ratio={ratio:.2f} -> {bound} "
              f"kuse={'K' if need >= case.K else 'maybe-shrink'}")
        summarize("base", base, case, test)
        recon.append((test, case, need >= case.K, note))

    print("\n=== A/B on reconstructions ===")
    for test, case, pbound, note in recon:
        print(f"\n{case.name}  bound={'PREFILL' if pbound else 'LAT/other'}  {note}")
        b_m, b_pts, b_ntp, b_nc, b_fr = summarize("base", base, case, test)
        b_tr = traced_run(base, case)
        for name, path in variants:
            try:
                m, pts, ntp, nc, fr = summarize(name, path, case, test)
            except Exception as e:
                print(f"  {name:<16} FAIL {e}")
                continue
            tr = traced_run(path, case)
            dpts = pts - b_pts
            dtp = m[0] - b_m[0]
            dtpot = m[2] - b_m[2]
            same = tr[1][0] == b_tr[1][0]
            flag = "IDENTICAL" if same else "DIFFERS"
            if nc + 1e-9 < 0.99:
                flag += " NC<0.99"
            print(
                f"           delta pts={dpts:+8.2f} tp={dtp:+.4f} "
                f"({100*dtp/max(b_m[0],1e-12):+.1f}%) tpot={dtpot:+.2f} "
                f"frames {b_fr}->{fr} {flag}"
            )

    print("\n=== multi-seed prefill-bound-ish + official5/6 ===")
    seeds5 = []
    for seed in (701, 702, 711, 721, 731):
        case = official5(seed=seed)
        pin_official_constants(case, 5)
        seeds5.append((5, case))
    for seed in (711, 721, 731, 741, 751):
        case = official5(seed=seed, lout=128, pproc=207.5, span=50.0)
        pin_official_constants(case, 5)
        case.name = f"prefill5-s{seed}"
        seeds5.append((5, case))
    for seed in (802, 803, 812, 822, 832):
        case = official6(seed=seed)
        pin_official_constants(case, 6)
        seeds5.append((6, case))
    for seed in (812, 822, 832, 842, 852):
        case = official6(seed=seed, pproc=250.0, span=20.0, lat=1.0)
        pin_official_constants(case, 6)
        case.name = f"prefill6-s{seed}"
        seeds5.append((6, case))

    by_var = {name: [] for name, _ in variants}
    for test, case in seeds5:
        need, ratio = prefill_need(case)
        print(f"\n{case.name} need={need}/{case.K} ratio={ratio:.2f}")
        b_m, b_pts, b_ntp, b_nc, _ = summarize("base", base, case, test)
        b_tr = traced_run(base, case)
        for name, path in variants:
            try:
                m, pts, ntp, nc, _ = summarize(name, path, case, test)
            except Exception as e:
                print(f"  {name:<16} FAIL {e}")
                continue
            tr = traced_run(path, case)
            dpts = pts - b_pts
            same = tr[1][0] == b_tr[1][0]
            print(f"           delta pts={dpts:+8.2f} tp={m[0]-b_m[0]:+.4f} "
                  f"{'IDENTICAL' if same else 'DIFFERS'} nc={nc:.3f}")
            by_var[name].append((case.name, need >= case.K, dpts, m[0] - b_m[0],
                                 nc, same))

    print("\n=== variant totals ===")
    for name, _ in variants:
        rows = by_var[name]
        if not rows:
            continue
        pref = [r for r in rows if r[1]]
        other = [r for r in rows if not r[1]]
        def fmt(rs, tag):
            if not rs:
                return f"{tag} n=0"
            dpts = sum(x[2] for x in rs)
            dtp = sum(x[3] for x in rs) / len(rs)
            ident = sum(1 for x in rs if x[5])
            ncslip = sum(1 for x in rs if x[4] + 1e-9 < 0.99)
            return (f"{tag} n={len(rs)} sum_dpts={dpts:+.1f} mean_dtp={dtp:+.4f} "
                    f"identical={ident} nc<0.99={ncslip}")
        print(f"  {name:<16} {fmt(pref, 'PREFILL')} | {fmt(other, 'other')}")

    print("\n=== gate proof: non-target weights IDENTICAL ===")
    suite = sim.build_cases()
    guards = []
    sat5 = next(c for c in suite if c.name == "sat5-K8")
    for w in (0.05, 0.15, 0.25, 0.30, 0.75, 0.98, 0.99, 1.0):
        guards.append(retarget(sat5, w))
    lat = next(c for c in suite if c.name == "lat-only-K4")
    guards.append(lat)
    guards.append(test17_case())
    guards.append(test22_case())
    guards.append(historical_replay())
    tp_sat = next(c for c in suite if c.name == "tp-sat-K8")
    guards.append(tp_sat)
    failures = 0
    for case in guards:
        b = traced_run(base, case)
        print(f"  {case.name:<28} wtp={case.wtp:.2f} base={b[1][0][:12]} "
              f"tp={b[0][0]:.4f}")
        for name, path in variants:
            a = traced_run(path, case)
            ok = a[1][0] == b[1][0]
            if not ok:
                failures += 1
            print(f"    {name:<14} {'MATCH' if ok else 'MISMATCH'} "
                  f"{a[1][0][:12]} tp={a[0][0]:.4f}")
    if failures:
        print(f"{failures} gate MISMATCH(es)")
        return 1
    print("all non-target traces IDENTICAL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

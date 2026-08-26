#!/usr/bin/env python3
"""Local interactor + judge for Codeforces 2251A.

Implements the statement's timing model (FIFO uplink/downlink, schedule cost S,
piecewise-linear task-time table) so schedulers can be compared off-judge.

tp_base and dist_base are measured by first running a one-request-at-a-time
reference scheduler on the same workload, mirroring how the real judge defines
them. That makes the reported points directly comparable to the judge's.

Usage:
    python3 tests/sim.py ./sched [./other ...]
"""
from __future__ import annotations

import heapq
import math
import random
import resource
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Req:
    rid: int
    lin: int
    lout: int
    arr: float
    remote: int = -1
    next_ls: int = 0
    tokens: int = 0
    st: str = "new"
    tdr: Optional[float] = None
    toks: List[float] = field(default_factory=list)


class Col:
    def __init__(self, pts):
        self.p = sorted((s, t) for s, t in pts if t >= 0)

    def get(self, m):
        p = self.p
        if not p:
            return 1.0
        if m <= p[0][0]:
            return p[0][1]
        if m >= p[-1][0]:
            return p[-1][1]
        lo, hi = 0, len(p) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if p[mid][0] <= m:
                lo = mid
            else:
                hi = mid
        (x0, y0), (x1, y1) = p[lo], p[hi]
        if x1 == x0:
            return y0
        return y0 + (y1 - y0) * (m - x0) / (x1 - x0)


class Case:
    """A workload plus system parameters (scoring constants filled in later)."""

    def __init__(self, K, S, lat, bw, bpt, layers, slo1, slo2, table, arrivals, wtp, wc):
        self.K, self.S, self.lat, self.bw, self.bpt, self.layers = K, S, lat, bw, bpt, layers
        self.slo1, self.slo2 = slo1, slo2
        self.table = table
        self.arrivals = arrivals
        self.wtp, self.wc = wtp, wc
        self.tp_base = 0.0
        self.tp_ub = 1.0
        self.dist_base = 0.0


class Sim:
    def __init__(self, case: Case):
        c = case
        self.c = c
        self.ppre = Col([(r[0], r[1]) for r in c.table])
        self.pproc = Col([(r[0], r[2]) for r in c.table])
        self.ppost = Col([(r[0], r[3]) for r in c.table])
        self.dpre = Col([(r[0], r[4]) for r in c.table])
        self.dproc = Col([(r[0], r[5]) for r in c.table])
        self.dpost = Col([(r[0], r[6]) for r in c.table])
        self.reqs: List[Req] = []
        self.up_free = 0.0
        self.down_free = 0.0
        self.ev: List[Tuple[float, int, str, dict]] = []
        self.seq = 0
        self.edge_task = None
        self.cloud_task = [None] * c.K
        self.t = 0.0
        self.stats = {k: [0, 0, 0.0] for k in
                      ("P PRE", "P PROC", "P POST", "D PRE", "D PROC", "D POST")}
        self.edge_busy = 0.0
        self.cloud_busy = 0.0
        for (t, lin, lout) in c.arrivals:
            self.push(t, "ARR", {"lin": lin, "lout": lout})

    def push(self, t, kind, p):
        heapq.heappush(self.ev, (t, self.seq, kind, p))
        self.seq += 1

    def xfer(self, ln):
        return self.c.lat + 8.0 * ln * self.c.bpt / (self.c.bw * 1e6)

    def q_up(self, t, ln, kind, rids, rem):
        st = max(t, self.up_free)
        self.up_free = st + self.xfer(ln)
        self.push(self.up_free, "XDN",
                  {"dir": "UP", "rem": rem, "size": int(ln * self.c.bpt), "kind": kind, "rids": rids})

    def q_down(self, t, ln, kind, rids, rem):
        st = max(t, self.down_free)
        self.down_free = st + self.xfer(ln)
        self.push(self.down_free, "XDN",
                  {"dir": "DOWN", "rem": rem, "size": int(ln * self.c.bpt), "kind": kind, "rids": rids})

    def frame(self):
        t, _, kind, p = heapq.heappop(self.ev)
        evs = [(kind, p)]
        while self.ev and abs(self.ev[0][0] - t) < 1e-12:
            _, _, k2, p2 = heapq.heappop(self.ev)
            evs.append((k2, p2))
        return t, evs

    def apply(self, kind, p) -> List[str]:
        out = []
        if kind == "ARR":
            rid = len(self.reqs)
            self.reqs.append(Req(rid, p["lin"], p["lout"], self.t))
            out.append(f"ARR {rid} {p['lin']}")
        elif kind == "TDN":
            server, spec, dur = p["server"], p["spec"], p["dur"]
            if server == "E":
                self.edge_task = None
            else:
                self.cloud_task[int(server[1:])] = None
            f = spec.split()
            phase, ty = f[0], f[1]
            if phase == "P":
                if ty == "PRE":
                    rid = int(f[3])
                    r = self.reqs[rid]
                    self.q_up(self.t, r.lin, "PRE", [rid], r.remote)
                    r.st = "up"
                elif ty == "PROC":
                    le, rid = int(f[3]), int(f[5])
                    r = self.reqs[rid]
                    r.next_ls = le
                    if le >= self.c.layers:
                        r.st = "down"
                        self.q_down(self.t, r.lin, "PRE", [rid], r.remote)
                    else:
                        r.st = "pproc_ready"
                else:
                    rid = int(f[3])
                    r = self.reqs[rid]
                    r.st = "didle"
                    r.tdr = self.t - r.arr
            else:
                m = int(f[3])
                rids = [int(x) for x in f[4:4 + m]]
                if ty == "PRE":
                    by: Dict[int, List[int]] = {}
                    for rid in rids:
                        self.reqs[rid].st = "dup"
                        by.setdefault(self.reqs[rid].remote, []).append(rid)
                    for c in sorted(by):
                        self.q_up(self.t, len(by[c]), "DEC", by[c], c)
                elif ty == "PROC":
                    rem = int(f[2])
                    for rid in rids:
                        self.reqs[rid].st = "ddown"
                    self.q_down(self.t, len(rids), "DEC", rids, rem)
                else:
                    for rid in rids:
                        r = self.reqs[rid]
                        r.tokens += 1
                        r.toks.append(self.t)
                        r.st = "fin" if r.tokens >= r.lout else "didle"
            out.append(f"TDN {server} {spec} {dur:.9f}")
            if phase == "D" and ty == "POST":
                for rid in rids:
                    if self.reqs[rid].st == "fin":
                        out.append(f"FIN {rid}")
        else:  # XDN
            for rid in p["rids"]:
                r = self.reqs[rid]
                if p["kind"] == "PRE":
                    r.st = "pproc_ready" if p["dir"] == "UP" else "ppost_ready"
                else:
                    r.st = "dproc_ready" if p["dir"] == "UP" else "dpost_ready"
            ids = " ".join(str(x) for x in p["rids"])
            out.append(f"XDN {p['dir']} {p['rem']} {p['size']} {p['kind']} {len(p['rids'])} {ids}")
        return out

    def assign(self, cmd: str):
        t = cmd.split()
        srv = t[0]
        spec = " ".join(t[1:])
        S = self.c.S
        if srv == "E":
            if self.edge_task is not None:
                raise RuntimeError("edge busy: " + cmd)
            phase, ty = t[1], t[2]
            if phase == "P" and ty == "PRE":
                rem, rid = int(t[3]), int(t[4])
                r = self.reqs[rid]
                if r.st != "new":
                    raise RuntimeError(f"P PRE on state {r.st}")
                if not (0 <= rem < self.c.K):
                    raise RuntimeError("remote out of range")
                r.remote = rem
                r.st = "ppre"
                dur = self.ppre.get(r.lin)
            elif phase == "P" and ty == "POST":
                rem, rid = int(t[3]), int(t[4])
                r = self.reqs[rid]
                if r.st != "ppost_ready" or r.remote != rem:
                    raise RuntimeError("bad P POST")
                r.st = "ppost"
                dur = self.ppost.get(r.lin)
            elif phase == "D" and ty in ("PRE", "POST"):
                m = int(t[4])
                rids = [int(x) for x in t[5:5 + m]]
                if len(rids) != m or len(set(rids)) != m:
                    raise RuntimeError("bad group")
                need = "didle" if ty == "PRE" else "dpost_ready"
                for rid in rids:
                    if self.reqs[rid].st != need:
                        raise RuntimeError(f"D {ty} member {rid} in state {self.reqs[rid].st}")
                    self.reqs[rid].st = "dpre" if ty == "PRE" else "dpost"
                dur = (self.dpre if ty == "PRE" else self.dpost).get(m)
            else:
                raise RuntimeError("bad edge cmd " + cmd)
            self.edge_task = spec
            key = f"{phase} {ty}"
            grp = len(rids) if phase == "D" else 1
            st = self.stats[key]
            st[0] += 1
            st[1] += grp
            st[2] += S + dur
            self.edge_busy += S + dur
            self.push(self.t + S + dur, "TDN", {"server": "E", "spec": spec, "dur": dur})
        else:
            c = int(srv[1:])
            if self.cloud_task[c] is not None:
                raise RuntimeError("cloud busy: " + cmd)
            phase, ty = t[1], t[2]
            if phase == "P":
                ls, le, rem, rid = int(t[3]), int(t[4]), int(t[5]), int(t[6])
                r = self.reqs[rid]
                if r.st != "pproc_ready" or r.remote != c or rem != c:
                    raise RuntimeError("bad P PROC")
                if ls != r.next_ls or le <= ls or le > self.c.layers:
                    raise RuntimeError(f"bad piece [{ls},{le}) expected ls={r.next_ls}")
                r.st = "pproc"
                dur = (le - ls) / self.c.layers * self.pproc.get(r.lin)
            else:
                rem, m = int(t[3]), int(t[4])
                rids = [int(x) for x in t[5:5 + m]]
                if rem != c or len(rids) != m or len(set(rids)) != m:
                    raise RuntimeError("bad D PROC")
                for rid in rids:
                    r = self.reqs[rid]
                    if r.st != "dproc_ready" or r.remote != c:
                        raise RuntimeError("bad D PROC member")
                    r.st = "dproc"
                dur = self.dproc.get(m)
            self.cloud_task[c] = spec
            key = f"{phase} {ty}"
            grp = len(rids) if phase == "D" else 1
            st = self.stats[key]
            st[0] += 1
            st[1] += grp
            st[2] += S + dur
            self.cloud_busy += S + dur
            self.push(self.t + S + dur, "TDN", {"server": srv, "spec": spec, "dur": dur})

    def metrics(self):
        if not self.reqs or any(r.st != "fin" for r in self.reqs):
            return None
        tot = sum(r.lout for r in self.reqs)
        t0 = min(r.arr for r in self.reqs)
        t1 = max(r.toks[-1] for r in self.reqs)
        tp = tot / max(t1 - t0, 1e-12)
        tdr = sum(r.tdr for r in self.reqs) / len(self.reqs)
        gaps = [b - a for r in self.reqs for a, b in zip(r.toks, r.toks[1:])]
        tpot = sum(gaps) / len(gaps) if gaps else 0.0
        return tp, tdr, tpot


def run(binary: str, case: Case, timeout=120.0):
    sim = Sim(case)
    c = case
    ru0 = resource.getrusage(resource.RUSAGE_CHILDREN)
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

    frames = 0
    while True:
        if not sim.ev:
            if sim.reqs and all(r.st == "fin" for r in sim.reqs):
                proc.stdin.write("END\n")
                proc.stdin.flush()
                proc.stdin.close()
                proc.wait(timeout=10)
                ru1 = resource.getrusage(resource.RUSAGE_CHILDREN)
                sim.cpu = (ru1.ru_utime - ru0.ru_utime) + (ru1.ru_stime - ru0.ru_stime)
                return sim.metrics(), frames, sim
            raise RuntimeError("stuck: no future event with unfinished requests")
        t, evs = sim.frame()
        sim.t = t
        lines = []
        for kind, p in evs:
            lines.extend(sim.apply(kind, p))
        proc.stdin.write(f"{t:.9f}\n{len(lines)}\n" + "\n".join(lines) + "\n")
        proc.stdin.flush()
        head = proc.stdout.readline()
        if not head:
            raise RuntimeError("scheduler closed the stream")
        n = int(head.strip())
        seen = set()
        for _ in range(n):
            cmd = proc.stdout.readline().strip()
            srv = cmd.split()[0]
            if srv in seen:
                raise RuntimeError("two tasks assigned to " + srv)
            seen.add(srv)
            sim.assign(cmd)
        frames += 1
        if frames > 3_000_000:
            raise RuntimeError("frame limit")


def score(case: Case, m):
    tp, tdr, tpot = m
    ntp = 0.0
    if case.tp_ub > case.tp_base:
        ntp = max(0.0, min(1.0, (tp - case.tp_base) / (case.tp_ub - case.tp_base)))
    ex1 = max(0.0, (tdr - case.slo1) / case.slo1)
    ex2 = max(0.0, (tpot - case.slo2) / case.slo2)
    dist = math.hypot(ex1, ex2)
    if case.dist_base > 0:
        nc = max(0.0, 1.0 - dist / case.dist_base)
    else:
        nc = 1.0 if dist <= 1e-12 else 0.0
    return 1000.0 * (case.wtp * ntp + case.wc * nc), ntp, nc, dist


def make_table(kind, rng):
    """Task times. Decode is strongly sublinear in batch size, which is what
    makes batching the dominant lever; prefill scales with input length."""
    rows = []
    sizes = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]
    if kind == "flat":
        # Near-flat decode scaling: batching is almost free, which is what a
        # task-time table listing sizes up to 4096 implies.
        rows2 = []
        for b in sizes:
            rows2.append((b,
                          0.05 + 0.02 * b,
                          0.9 * b * 0.35 + 2.0,
                          0.04 + 0.01 * b,
                          0.40 + 0.0008 * b,
                          2.50 + 0.0040 * b,
                          0.40 + 0.0008 * b))
        return rows2
    if kind == "edge":
        # Edge-bound: the shared edge, not the clouds, is the bottleneck. A
        # one-request-at-a-time reference is then nearly as fast as anything
        # else, so beating it on mean TDR is a question of *ordering* rather
        # than of parallelism -- which is the shape of the judge's hardest
        # waiting-time tests, where mean TDR runs to six and seven figures
        # while throughput sits close to its own upper bound.
        rows2 = []
        for b in sizes:
            rows2.append((b,
                          2.00 + 0.050 * b,   # P PRE   (edge)
                          4.00 + 0.100 * b,   # P PROC  (cloud, and there are K)
                          2.00 + 0.030 * b,   # P POST  (edge)
                          1.00 + 0.020 * b,   # D PRE   (edge)
                          3.00 + 0.020 * b,   # D PROC  (cloud)
                          1.00 + 0.020 * b))  # D POST  (edge)
        return rows2
    if kind == "gpu":
        pp, pr, po = 0.05, 0.9, 0.04
        dp, dr, dq = 0.30, 1.8, 0.30
        dpc, drc, dqc = 0.004, 0.05, 0.004
    else:
        pp, pr, po = 0.20, 2.5, 0.15
        dp, dr, dq = 0.80, 4.0, 0.80
        dpc, drc, dqc = 0.02, 0.30, 0.02
    for b in sizes:
        rows.append((b,
                     pp + pr * 0.02 * b,
                     pr * b * 0.35 + 2.0,
                     po + pr * 0.01 * b,
                     dp + dpc * b,
                     dr + drc * b,
                     dq + dqc * b))
    return rows


def make_case(name, seed, K, R, layers, span, wtp, a1, a2, kind="gpu",
              lat=1.0, bw=10.0, bpt=32768, S=2.0, lin_hi=1024, lout_hi=128,
              lin_lo=16):
    """span is the arrival window in ms; a small span means a saturated backlog,
    which is the regime the judge's hard tests live in."""
    rng = random.Random(seed)
    table = make_table(kind, rng)
    arrivals = []
    for _ in range(R):
        t = rng.uniform(0.0, span)
        lin = rng.choice([x for x in [16, 32, 64, 128, 256, 512, 1024, 2048, 4096]
                          if lin_lo <= x <= lin_hi])
        lout = rng.choice([x for x in [1, 2, 4, 8, 16, 32, 64, 128, 256, 512] if x <= lout_hi])
        arrivals.append((t, lin, lout))
    arrivals.sort(key=lambda x: x[0])
    c = Case(K, S, lat, bw, bpt, layers, 1.0, 1.0, table, arrivals, wtp, 1.0 - wtp)
    c.name = name
    c._a1, c._a2 = a1, a2
    return c


def calibrate(case: Case, ref_bin: str):
    """Mirror the judge: measure the one-request-at-a-time reference, then set
    tp_base / dist_base from it. SLOs are placed as a fraction of the reference's
    own latency so dist_base lands in a range comparable to the real tests."""
    case.slo1, case.slo2 = 1e18, 1e18
    case.tp_base, case.tp_ub, case.dist_base = 0.0, 1.0, 0.0
    (tp, tdr, tpot), _, _ = run(ref_bin, case)
    case.ref = (tp, tdr, tpot)
    case.tp_base = tp
    case.slo1 = max(tdr * case._a1, 1e-3)
    case.slo2 = max(tpot * case._a2, 1e-3) if tpot > 0 else 1e-3
    ex1 = max(0.0, (tdr - case.slo1) / case.slo1)
    ex2 = max(0.0, (tpot - case.slo2) / case.slo2)
    case.dist_base = math.hypot(ex1, ex2)
    sim = Sim(case)
    ideal = 0.0
    for m in [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048]:
        k = min(case.K, m)
        per = math.ceil(m / k)
        edge = 2 * case.S + sim.dpre.get(m) + sim.dpost.get(m)
        link = 2 * (k * case.lat + 8.0 * m * case.bpt / (case.bw * 1e6))
        proc = case.S + sim.dproc.get(per)
        ideal = max(ideal, m / (edge + link + proc))
    case.tp_ub = max(min(ideal, case.tp_base * 25.0), case.tp_base * 2.0 + 1e-12)
    return case


def build_cases():
    c = []
    # Saturated, throughput-dominant (judge tests 19 / 16 / 12 look like this).
    c.append(make_case("tp-sat-K8", 11, 8, 400, 16, 50.0, 1.00, 0.05, 0.05))
    c.append(make_case("tp-sat-K4", 12, 4, 250, 8, 50.0, 0.98, 0.05, 0.05))
    c.append(make_case("tp-burst-K2", 13, 2, 150, 4, 20.0, 0.80, 0.10, 0.10))
    # Latency-dominant with a tight reference (judge test 3).
    c.append(make_case("lat-only-K4", 21, 4, 120, 16, 4000.0, 0.00, 0.60, 0.60))
    c.append(make_case("lat-heavy-K8", 22, 8, 250, 32, 3000.0, 0.05, 0.30, 0.30))
    c.append(make_case("lat-mid-K4", 23, 4, 180, 8, 2000.0, 0.15, 0.20, 0.20))
    # Balanced.
    c.append(make_case("bal-K4", 31, 4, 200, 16, 800.0, 0.50, 0.15, 0.15))
    c.append(make_case("bal-K1", 32, 1, 80, 4, 600.0, 0.50, 0.20, 0.20))
    c.append(make_case("bal-K8-cpu", 33, 8, 250, 64, 900.0, 0.45, 0.15, 0.15, kind="cpu"))
    # Link latency dominates: transfer amortisation is the lever.
    c.append(make_case("hi-lat-K4", 41, 4, 180, 8, 400.0, 0.65, 0.15, 0.15, lat=20.0, bw=2.0))
    c.append(make_case("hi-lat-K8", 42, 8, 220, 16, 300.0, 0.35, 0.15, 0.15, lat=35.0, bw=1.0))
    # Saturated *and* link-latency bound, with throughput the whole score. A
    # round costs one link latency per participating cloud whatever it carries,
    # and a large backlog means the input stage runs dry long before the run
    # ends, so the cohort has nothing to hide behind. This is the shape whose
    # metrics no amount of cohort-sizing or edge-ordering tuning can move.
    c.append(make_case("tp-lat-sat-K16", 43, 16, 700, 32, 100.0, 1.00, 0.05, 0.05,
                       lat=20.0, bw=1.0, lout_hi=64))
    c.append(make_case("tp-lat-sat-K4", 44, 4, 700, 32, 100.0, 0.95, 0.05, 0.05,
                       lat=20.0, bw=1.0, kind="flat", lout_hi=64))
    # Input stage capacity bound: one cloud, maximal inputs, throughput the whole
    # score. Mean TDR runs into the millions purely from queueing, and the
    # makespan equals the unbatchable prefill work, so no schedule can beat it.
    # Present to prove a change does not mistake this for slack.
    c.append(make_case("tp-prefill-K1", 45, 1, 500, 32, 200.0, 1.00, 0.05, 0.05,
                       kind="cpu", lin_lo=4096, lin_hi=4096, lout_hi=64))
    # Large schedule cost: every task pays S, so task count matters most.
    c.append(make_case("bigS-K4", 51, 4, 200, 8, 400.0, 0.60, 0.15, 0.15, S=9.0))
    # Degenerate shapes the statement warns about; these only need to survive.
    c.append(make_case("edge-R1", 81, 1, 1, 1, 1.0, 0.50, 0.5, 0.5, lin_hi=16, lout_hi=1))
    c.append(make_case("edge-K1L1", 82, 1, 25, 1, 100.0, 0.50, 0.5, 0.5, lout_hi=8))
    c.append(make_case("edge-lout1", 83, 4, 40, 8, 100.0, 0.70, 0.5, 0.5, lout_hi=1))
    c.append(make_case("edge-tinySLO", 84, 2, 40, 4, 50.0, 0.20, 0.01, 0.01))
    c.append(make_case("edge-1cloud-big", 85, 1, 40, 64, 300.0, 0.60, 0.3, 0.3, lin_hi=4096))
    # Worst-case size: R and total tokens at the stated limits, to check CPU.
    c.append(make_case("stress-R2000", 99, 8, 2000, 64, 200.0, 0.90, 0.10, 0.10,
                       kind="flat", lout_hi=128))
    # Same size, but weighted so the waiting-time term is what pays. Shrinking
    # the cohort to protect round time multiplies the number of decode rounds,
    # and each round costs the interactor a handful of events, so this is the
    # case that bounds how far that trade may be taken.
    c.append(make_case("stress-lat-R2000", 98, 8, 2000, 64, 200.0, 0.05, 0.10, 0.10,
                       kind="flat", lout_hi=128))
    # Near-flat decode scaling: huge cohorts should pay off enormously.
    c.append(make_case("flat-sat-K8", 91, 8, 800, 16, 100.0, 1.00, 0.05, 0.05, kind="flat"))
    c.append(make_case("flat-sat-K4", 92, 4, 500, 8, 100.0, 0.60, 0.10, 0.10, kind="flat"))
    c.append(make_case("flat-lat-K8", 93, 8, 400, 16, 800.0, 0.20, 0.20, 0.20, kind="flat"))
    # Edge-bound backlogs: everything arrives at once and the edge is the
    # bottleneck, so mean TDR is queueing delay and the only lever on it is the
    # order the edge works in. Judge tests 9 / 10 / 15 / 17 live here.
    # lout=1 throughout the first and third means no request ever produces a
    # second token, so mean TPOT is the mean of an empty set -- exactly zero,
    # as reported for tests 9 and 15 -- and dist is the TDR term alone.
    c.append(make_case("bk-lout1-K8", 101, 8, 600, 8, 5.0, 0.05, 0.05, 0.05,
                       kind="edge", lout_hi=1))
    c.append(make_case("bk-mix-K8", 102, 8, 400, 8, 5.0, 0.15, 0.05, 0.50,
                       kind="edge", lout_hi=32))
    c.append(make_case("bk-big-K4", 103, 4, 800, 16, 5.0, 0.45, 0.05, 0.05,
                       kind="edge", lout_hi=1, lin_hi=4096))
    # Few clouds as well as an edge bottleneck, so the sequential reference is
    # only about twice as slow as we are and the SLOs sit far under both. dist
    # is then the TDR term by two orders of magnitude over a dist_base in the
    # hundreds -- the shape the judge reports for tests 10, 15 and 17, where
    # mean_tdr/SLO1 runs to 178 and above while mean_tpot/SLO2 stays near 1.
    c.append(make_case("bk-tdr-K1", 104, 1, 300, 8, 5.0, 0.15, 0.0026, 0.55,
                       kind="edge", lout_hi=32))
    c.append(make_case("bk-tdr-K2", 105, 2, 500, 8, 5.0, 0.67, 0.0026, 0.10,
                       kind="edge", lout_hi=16))
    # Long outputs, few requests: decode-dominated.
    c.append(make_case("longout-K4", 61, 4, 60, 8, 200.0, 0.55, 0.20, 0.20, lout_hi=512))
    # Wide inputs: prefill-dominated.
    c.append(make_case("bigin-K8", 71, 8, 150, 32, 600.0, 0.40, 0.15, 0.15, lin_hi=4096))
    return c


def main():
    bins = sys.argv[1:] or ["./sched"]
    ref = "/tmp/ref_sequential"
    cases = build_cases()
    print("calibrating tp_base / dist_base against the sequential reference ...")
    for c in cases:
        calibrate(c, ref)

    totals = {b: 0.0 for b in bins}
    fails = {b: 0 for b in bins}
    nw = max(len(c.name) for c in cases) + 1
    names = [b.split("/")[-1] for b in bins]
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
                m, frames, sm = run(b, c)
                if m is None:
                    raise RuntimeError("unfinished")
                pts, ntp, nc, dist = score(c, m)
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
    print(f"{'MEAN/1000':<{nw}} {'':>5} {'':>8}  " +
          "  ".join(f"{totals[b]/len(cases):>10.1f}{'':>22}" for b in bins))
    for b in bins[1:]:
        d = totals[b] - base
        print(f"  delta vs {names[0]}: {d:+.1f} total  ({d/len(cases):+.1f} per case)")


def detail(bins, case_name):
    ref = "/tmp/ref_sequential"
    cases = {c.name: c for c in build_cases()}
    c = cases[case_name]
    calibrate(c, ref)
    for b in bins:
        m, frames, sm = run(b, c)
        pts, ntp, nc, dist = score(c, m)
        tp, tdr, tpot = m
        print(f"\n=== {b.split('/')[-1]} on {case_name}: pts={pts:.1f} "
              f"tp={tp:.4f} tdr={tdr:.1f} tpot={tpot:.2f} frames={frames} "
              f"cpu={getattr(sm, 'cpu', float('nan')):.2f}s")
        span = max(r.toks[-1] for r in sm.reqs) - min(r.arr for r in sm.reqs)
        print(f"    makespan={span:.1f}  edge_busy={sm.edge_busy:.1f} "
              f"({100*sm.edge_busy/span:.1f}%)  cloud_busy={sm.cloud_busy:.1f} "
              f"({100*sm.cloud_busy/(span*c.K):.1f}% of {c.K} clouds)")
        for k, (n, g, tsum) in sm.stats.items():
            if n:
                print(f"    {k:<7} tasks={n:6d} mean_group={g/n:8.2f} busy={tsum:10.1f}")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--detail":
        detail(sys.argv[3:], sys.argv[2])
    else:
        main()

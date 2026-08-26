#!/usr/bin/env python3
"""Lightweight interactor for the Huawei/Codeforces 2251 scheduler.

Deterministic synthetic tests plus the official Example 1 workload.
Used to catch protocol violations (stuck / illegal assignment) locally.
"""
from __future__ import annotations

import heapq
import math
import subprocess
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class Req:
    rid: int
    lin: int
    lout: int
    arr: float
    remote: int = -1
    next_ls: int = 0
    tokens: int = 0
    st: str = "new"  # new, ppre, wait_up, pproc_ready, pproc, wait_down, ppost_ready, ppost, dready, dpre, wait_dup, dproc_ready, dproc, wait_ddown, dpost_ready, dpost, fin
    tdr: Optional[float] = None
    token_times: List[float] = field(default_factory=list)


class Col:
    def __init__(self, pts: List[Tuple[int, float]]):
        self.p = sorted((s, t) for s, t in pts if t >= 0)

    def get(self, m: int) -> float:
        p = self.p
        if not p:
            return 1.0
        if m <= p[0][0]:
            return p[0][1]
        if m >= p[-1][0]:
            return p[-1][1]
        for i in range(len(p) - 1):
            if p[i][0] <= m <= p[i + 1][0]:
                s0, t0 = p[i]
                s1, t1 = p[i + 1]
                if s1 == s0:
                    return t0
                return t0 + (t1 - t0) * (m - s0) / (s1 - s0)
        return p[-1][1]


class Sim:
    def __init__(self, K, S, lat, bw, bpt, layers, slo1, slo2, tpub, tpbase, distbase, wtp, wc,
                 table, arrivals):
        self.K, self.S, self.lat, self.bw, self.bpt, self.layers = K, S, lat, bw, bpt, layers
        self.slo1, self.slo2 = slo1, slo2
        self.tpub, self.tpbase, self.distbase, self.wtp, self.wc = tpub, tpbase, distbase, wtp, wc
        self.ppre = Col([(b, a) for b, a, *_ in table])
        self.pproc = Col([(b, x[1]) for b, *x in table])
        self.ppost = Col([(b, x[2]) for b, *x in table])
        self.dpre = Col([(b, x[3]) for b, *x in table])
        self.dproc = Col([(b, x[4]) for b, *x in table])
        self.dpost = Col([(b, x[5]) for b, *x in table])
        self.arrivals = list(arrivals)  # (t, lin, lout)
        self.reqs: List[Req] = []
        self.edge_busy_until = 0.0
        self.cloud_busy_until = [0.0] * K
        self.up_free = 0.0
        self.down_free = 0.0
        self.events: List[Tuple[float, int, str, dict]] = []
        self.seq = 0
        self.edge_task = None
        self.cloud_task = [None] * K
        self.t = 0.0
        self.arr_i = 0
        for t, lin, lout in self.arrivals:
            self.push(t, "ARR", {"lin": lin, "lout": lout})

    def push(self, t, kind, payload):
        heapq.heappush(self.events, (t, self.seq, kind, payload))
        self.seq += 1

    def xfer(self, length: int) -> float:
        return self.lat + 8.0 * length * self.bpt / (self.bw * 1e6)

    def start_up(self, t, length, typ, rids, remote):
        st = max(t, self.up_free)
        dur = self.xfer(length)
        self.up_free = st + dur
        self.push(st + dur, "XDN", {"dir": "UP", "remote": remote, "size": length * self.bpt, "typ": typ, "rids": rids})

    def start_down(self, t, length, typ, rids, remote):
        st = max(t, self.down_free)
        dur = self.xfer(length)
        self.down_free = st + dur
        self.push(st + dur, "XDN", {"dir": "DOWN", "remote": remote, "size": length * self.bpt, "typ": typ, "rids": rids})

    def collect_frame(self):
        if not self.events:
            return None
        t, _, kind, payload = heapq.heappop(self.events)
        frame = [(kind, payload)]
        while self.events and abs(self.events[0][0] - t) < 1e-12:
            _, _, k2, p2 = heapq.heappop(self.events)
            frame.append((k2, p2))
        return t, frame

    def apply_event(self, kind, p):
        if kind == "ARR":
            rid = len(self.reqs)
            r = Req(rid, p["lin"], p["lout"], self.t)
            self.reqs.append(r)
            return f"ARR {rid} {r.lin}"
        if kind == "TDN":
            server, spec, dur = p["server"], p["spec"], p["dur"]
            if server == "E":
                self.edge_task = None
                self.edge_busy_until = self.t
            else:
                c = int(server[1:])
                self.cloud_task[c] = None
                self.cloud_busy_until[c] = self.t
            parts = spec.split()
            phase, typ = parts[0], parts[1]
            if phase == "P":
                if typ == "PRE":
                    rid = int(parts[3])
                    r = self.reqs[rid]
                    r.st = "wait_up"
                    self.start_up(self.t, r.lin, "PRE", [rid], r.remote)
                elif typ == "PROC":
                    ls, le, remote, rid = int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])
                    r = self.reqs[rid]
                    r.next_ls = le
                    if le >= self.layers:
                        r.st = "wait_down"
                        self.start_down(self.t, r.lin, "PRE", [rid], r.remote)
                    else:
                        r.st = "pproc_ready"
                else:
                    rid = int(parts[3])
                    r = self.reqs[rid]
                    r.st = "dready"
                    r.tdr = self.t - r.arr
            else:
                m = int(parts[3])
                rids = list(map(int, parts[4:4 + m]))
                if typ == "PRE":
                    by = {}
                    for rid in rids:
                        self.reqs[rid].st = "wait_dup"
                        by.setdefault(self.reqs[rid].remote, []).append(rid)
                    for c in sorted(by):
                        self.start_up(self.t, len(by[c]), "DEC", by[c], c)
                elif typ == "PROC":
                    remote = int(parts[2])
                    m = int(parts[3])
                    rids = list(map(int, parts[4:4 + m]))
                    for rid in rids:
                        self.reqs[rid].st = "wait_ddown"
                    self.start_down(self.t, m, "DEC", rids, remote)
                else:
                    for rid in rids:
                        r = self.reqs[rid]
                        r.tokens += 1
                        r.token_times.append(self.t)
                        if r.tokens >= r.lout:
                            r.st = "fin"
                        else:
                            r.st = "dready"
            extra = []
            if phase == "D" and typ == "POST":
                for rid in rids:
                    if self.reqs[rid].st == "fin":
                        extra.append(f"FIN {rid}")
            line = f"TDN {server} {spec} {dur:.9f}"
            return line, extra
        if kind == "XDN":
            for rid in p["rids"]:
                r = self.reqs[rid]
                if p["typ"] == "PRE":
                    r.st = "pproc_ready" if p["dir"] == "UP" else "ppost_ready"
                else:
                    r.st = "dproc_ready" if p["dir"] == "UP" else "dpost_ready"
            ids = " ".join(str(x) for x in p["rids"])
            return f"XDN {p['dir']} {p['remote']} {p['size']} {p['typ']} {len(p['rids'])} {ids}"
        raise RuntimeError(kind)

    def fmt_frame(self, t, evs):
        lines = [f"{t:.9f}", str(len(evs))]
        extras_fin = []
        body = []
        for kind, p in evs:
            out = self.apply_event(kind, p)
            if isinstance(out, tuple):
                body.append(out[0])
                extras_fin.extend(out[1])
            else:
                body.append(out)
        # FIN shares TDN timestamp; already same frame if we added during apply
        if extras_fin:
            # recount: we need FIN in the same frame
            pass
        all_lines = body + extras_fin
        lines = [f"{t:.9f}", str(len(all_lines))] + all_lines
        return "\n".join(lines) + "\n"

    def busy_edge(self):
        return self.edge_task is not None

    def busy_cloud(self, c):
        return self.cloud_task[c] is not None

    def assign(self, cmd: str):
        tok = cmd.split()
        server = tok[0]
        spec = " ".join(tok[1:])
        if server == "E":
            if self.busy_edge():
                raise RuntimeError("edge busy: " + cmd)
            phase, typ = tok[1], tok[2]
            if phase == "P" and typ == "PRE":
                remote, rid = int(tok[3]), int(tok[4])
                r = self.reqs[rid]
                if r.st != "new":
                    raise RuntimeError("bad P PRE state " + r.st)
                if not (0 <= remote < self.K):
                    raise RuntimeError("bad remote")
                r.remote = remote
                r.st = "ppre"
                dur = self.ppre.get(r.lin)
                self.edge_task = spec
                self.push(self.t + self.S + dur, "TDN", {"server": "E", "spec": spec, "dur": dur})
            elif phase == "P" and typ == "POST":
                remote, rid = int(tok[3]), int(tok[4])
                r = self.reqs[rid]
                if r.st != "ppost_ready" or r.remote != remote:
                    raise RuntimeError("bad P POST")
                r.st = "ppost"
                dur = self.ppost.get(r.lin)
                self.edge_task = spec
                self.push(self.t + self.S + dur, "TDN", {"server": "E", "spec": spec, "dur": dur})
            elif phase == "D" and typ == "PRE":
                m = int(tok[4])
                rids = list(map(int, tok[5:5 + m]))
                if m != len(rids) or len(set(rids)) != m:
                    raise RuntimeError("bad D PRE group")
                for rid in rids:
                    if self.reqs[rid].st != "dready":
                        raise RuntimeError("bad D PRE member " + self.reqs[rid].st)
                    self.reqs[rid].st = "dpre"
                dur = self.dpre.get(m)
                self.edge_task = spec
                self.push(self.t + self.S + dur, "TDN", {"server": "E", "spec": spec, "dur": dur})
            elif phase == "D" and typ == "POST":
                m = int(tok[4])
                rids = list(map(int, tok[5:5 + m]))
                if m != len(rids) or len(set(rids)) != m:
                    raise RuntimeError("bad D POST group")
                for rid in rids:
                    if self.reqs[rid].st != "dpost_ready":
                        raise RuntimeError("bad D POST member " + self.reqs[rid].st)
                    self.reqs[rid].st = "dpost"
                dur = self.dpost.get(m)
                self.edge_task = spec
                self.push(self.t + self.S + dur, "TDN", {"server": "E", "spec": spec, "dur": dur})
            else:
                raise RuntimeError("unknown edge " + cmd)
        else:
            c = int(server[1:])
            if self.busy_cloud(c):
                raise RuntimeError("cloud busy " + cmd)
            phase, typ = tok[1], tok[2]
            if phase == "P" and typ == "PROC":
                ls, le, remote, rid = int(tok[3]), int(tok[4]), int(tok[5]), int(tok[6])
                r = self.reqs[rid]
                if r.st != "pproc_ready" or r.remote != c or remote != c:
                    raise RuntimeError("bad P PROC state")
                if ls != r.next_ls or le <= ls or le > self.layers:
                    raise RuntimeError(f"bad piece {ls} {le} next={r.next_ls}")
                r.st = "pproc"
                frac = (le - ls) / self.layers
                dur = frac * self.pproc.get(r.lin)
                self.cloud_task[c] = spec
                self.push(self.t + self.S + dur, "TDN", {"server": server, "spec": spec, "dur": dur})
            elif phase == "D" and typ == "PROC":
                remote = int(tok[3])
                m = int(tok[4])
                rids = list(map(int, tok[5:5 + m]))
                if remote != c or m != len(rids) or len(set(rids)) != m:
                    raise RuntimeError("bad D PROC")
                for rid in rids:
                    r = self.reqs[rid]
                    if r.st != "dproc_ready" or r.remote != c:
                        raise RuntimeError("bad D PROC member")
                    r.st = "dproc"
                dur = self.dproc.get(m)
                self.cloud_task[c] = spec
                self.push(self.t + self.S + dur, "TDN", {"server": server, "spec": spec, "dur": dur})
            else:
                raise RuntimeError("unknown cloud " + cmd)

    def unfinished(self):
        return any(r.st != "fin" for r in self.reqs) or self.arr_i < len(self.arrivals) or self.events

    def score(self):
        if not self.reqs or any(r.st != "fin" for r in self.reqs):
            return 0.0
        tot_tok = sum(r.lout for r in self.reqs)
        t0 = min(r.arr for r in self.reqs)
        t1 = max(r.token_times[-1] for r in self.reqs)
        tp = tot_tok / max(t1 - t0, 1e-12)
        def clamp(x, base, target):
            if target == base:
                return 1.0 if x >= target else 0.0
            return max(0.0, min(1.0, (x - base) / (target - base)))
        tdr = sum(r.tdr for r in self.reqs) / len(self.reqs)
        gaps = []
        for r in self.reqs:
            for a, b in zip(r.token_times, r.token_times[1:]):
                gaps.append(b - a)
        tpot = sum(gaps) / len(gaps) if gaps else 0.0
        ex_tdr = max(0.0, (tdr - self.slo1) / self.slo1)
        ex_tpot = max(0.0, (tpot - self.slo2) / self.slo2)
        dist = math.sqrt(ex_tdr ** 2 + ex_tpot ** 2)
        if self.distbase > 0:
            wait_c = max(0.0, 1.0 - dist / self.distbase)
        else:
            wait_c = 1.0 if dist == 0 else 0.0
        ns = self.wtp * clamp(tp, self.tpbase, self.tpub) + self.wc * wait_c
        return 1000.0 * ns, tp, tdr, tpot, dist


def run(bin_path: str, sim: Sim) -> float:
    proc = subprocess.Popen(
        [bin_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    assert proc.stdin and proc.stdout
    header = (
        f"{sim.K} {sim.S:.9f} {sim.lat:.9f} {sim.bw:.9f} {sim.bpt} {sim.layers}\n"
        f"{sim.slo1:.9f} {sim.slo2:.9f} {sim.tpub:.9f} {sim.tpbase:.9f} {sim.distbase:.9f} {sim.wtp:.9f} {sim.wc:.9f}\n"
    )
    # rebuild table from cols — use original via arrivals only; pass table rows stored on sim
    # We stored table in constructor via Cols only. Re-send a dense table from Cols points.
    rows = {}
    for col_name, col in [("ppre", sim.ppre), ("pproc", sim.pproc), ("ppost", sim.ppost),
                          ("dpre", sim.dpre), ("dproc", sim.dproc), ("dpost", sim.dpost)]:
        for s, t in col.p:
            rows.setdefault(s, [s, -1, -1, -1, -1, -1, -1])
    for s, t in sim.ppre.p:
        rows[s][1] = t
    for s, t in sim.pproc.p:
        rows[s][2] = t
    for s, t in sim.ppost.p:
        rows[s][3] = t
    for s, t in sim.dpre.p:
        rows[s][4] = t
    for s, t in sim.dproc.p:
        rows[s][5] = t
    for s, t in sim.dpost.p:
        rows[s][6] = t
    tbl = sorted(rows.values())
    header += f"{len(tbl)}\n"
    for r in tbl:
        header += f"{r[0]} " + " ".join(f"{x:.9f}" if isinstance(x, float) else str(x) for x in r[1:]) + "\n"
    proc.stdin.write(header)
    proc.stdin.flush()

    steps = 0
    while True:
        if not sim.events:
            # all done?
            if all(r.st == "fin" for r in sim.reqs) and sim.reqs:
                proc.stdin.write("END\n")
                proc.stdin.flush()
                proc.stdin.close()
                proc.wait(timeout=5)
                sc = sim.score()
                return sc[0] if isinstance(sc, tuple) else sc
            raise RuntimeError("stuck: no events, unfinished")
        t, evs = sim.collect_frame()
        sim.t = t
        frame = sim.fmt_frame(t, evs)
        proc.stdin.write(frame)
        proc.stdin.flush()
        nline = proc.stdout.readline()
        if not nline:
            raise RuntimeError("solver exited")
        n = int(nline.strip())
        cmds = []
        for _ in range(n):
            cmds.append(proc.stdout.readline().strip())
        seen_server = set()
        for cmd in cmds:
            srv = cmd.split()[0]
            if srv in seen_server:
                raise RuntimeError("two tasks on " + srv)
            seen_server.add(srv)
            sim.assign(cmd)
        steps += 1
        if steps > 500000:
            raise RuntimeError("too many steps")


def example1():
    table = [
        (1, 3.0, 10.0, 2.0, 1.0, 4.0, 1.0),
        (4, 3.0, 10.0, 2.0, 1.0, 4.0, 1.0),
    ]
    return Sim(1, 1.0, 2.0, 1.0, 125000, 4,
               30.0, 15.0, 0.0625, 0.022222222, 0.0, 0.5, 0.5,
               table, [(0.0, 4, 1)])


def synth(seed: int, K: int, R: int, layers: int):
    import random
    rng = random.Random(seed)
    table = []
    for b in [1, 2, 4, 8, 16, 32, 64, 128]:
        table.append((
            b,
            0.4 + 0.02 * b,          # ppre ~ slow grow with Lin
            2.0 + 0.15 * b,          # pproc
            0.3 + 0.01 * b,          # ppost
            0.2 + 0.03 * math.log2(b + 1),  # dpre
            0.8 + 0.12 * b,          # dproc more linear
            0.2 + 0.02 * math.log2(b + 1),
        ))
    arrivals = []
    t = 0.0
    for i in range(R):
        t += rng.expovariate(1 / 8.0)
        lin = rng.choice([8, 16, 32, 64, 128, 256])
        lout = rng.choice([1, 2, 4, 8, 16, 32])
        arrivals.append((t, lin, lout))
    S = 0.8
    lat = 0.5
    bw = 10.0
    bpt = 4096
    slo1 = 80.0
    slo2 = 12.0
    return Sim(K, S, lat, bw, bpt, layers,
               slo1, slo2, 0.5, 0.02, 1.5, 0.6, 0.4,
               table, arrivals)


def synth_hard(seed: int, K: int, R: int, layers: int):
    import random
    rng = random.Random(seed)
    table = []
    for b in [1, 2, 4, 8, 16, 32, 64, 128, 256, 512]:
        table.append((
            b,
            0.5 + 0.01 * b,
            3.0 + 0.22 * b,
            0.4 + 0.008 * b,
            0.25 + 0.04 * math.log2(b + 1),
            0.5 + 0.08 * b,
            0.25 + 0.03 * math.log2(b + 1),
        ))
    arrivals = []
    t = 0.0
    for i in range(R):
        if rng.random() < 0.15:
            t += rng.uniform(20.0, 40.0)
        else:
            t += rng.expovariate(1 / 2.5)
        lin = rng.choice([16, 32, 64, 128, 256, 512])
        lout = rng.choice([4, 8, 16, 32, 64])
        arrivals.append((t, lin, lout))
    return Sim(K, 1.2, 1.0, 4.0, 8192, layers,
               40.0, 6.0, 1.2, 0.05, 2.0, 0.55, 0.45,
               table, arrivals)


def main():
    bin_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/sched"
    tests = [("example1", example1())]
    for seed, K, R, L in [
        (1, 2, 8, 4),
        (2, 4, 20, 8),
        (3, 8, 40, 16),
        (4, 3, 15, 1),
        (5, 2, 12, 32),
        (6, 4, 60, 8),
        (7, 8, 80, 16),
        (8, 1, 20, 4),
    ]:
        tests.append((f"synth{seed}", synth(seed, K, R, L)))
    for seed, K, R, L in [
        (11, 4, 40, 8),
        (12, 8, 50, 16),
        (13, 2, 30, 32),
    ]:
        tests.append((f"hard{seed}", synth_hard(seed, K, R, L)))
    ok = True
    for name, sim in tests:
        try:
            sc = run(bin_path, sim)
            detail = sim.score()
            extra = ""
            if isinstance(detail, tuple) and len(detail) >= 5:
                extra = f"  tp={detail[1]:.4f} tdr={detail[2]:.2f} tpot={detail[3]:.2f} dist={detail[4]:.3f}"
            print(f"{name:12s}  score={sc:.3f}  R={len(sim.reqs)}{extra}")
        except Exception as e:
            ok = False
            print(f"{name:12s}  FAIL: {e}")
    if not ok:
        sys.exit(1)



if __name__ == "__main__":
    main()

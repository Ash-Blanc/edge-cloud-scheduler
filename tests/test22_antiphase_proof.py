#!/usr/bin/env python3
"""Prove official-#22 antiphase activation vs tiny-tp 0.5 tests."""

import subprocess
import sys

import sim
from ensemble_compare import TraceDigest, test22_case


def run_with_stderr(binary, case):
    import resource as resmod

    sim_obj = sim.Sim(case)
    c = case
    ru0 = resmod.getrusage(resmod.RUSAGE_CHILDREN)
    proc = subprocess.Popen(
        [binary],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    hdr = [
        f"{c.K} {c.S:.9f} {c.lat:.9f} {c.bw:.9f} {c.bpt} {c.layers}",
        f"{c.slo1:.9f} {c.slo2:.9f} {c.tp_ub:.9f} {c.tp_base:.9f} {c.dist_base:.9f} "
        f"{c.wtp:.9f} {c.wc:.9f}",
        str(len(c.table)),
    ]
    for row in c.table:
        hdr.append(f"{row[0]} " + " ".join(f"{v:.9f}" for v in row[1:]))
    proc.stdin.write("\n".join(hdr) + "\n")
    proc.stdin.flush()
    digest = TraceDigest()
    while True:
        if not sim_obj.ev:
            if sim_obj.reqs and all(r.st == "fin" for r in sim_obj.reqs):
                proc.stdin.write("END\n")
                proc.stdin.flush()
                proc.stdin.close()
                err = proc.stderr.read()
                proc.wait(timeout=10)
                ru1 = resmod.getrusage(resmod.RUSAGE_CHILDREN)
                sim_obj.cpu = (ru1.ru_utime - ru0.ru_utime) + (
                    ru1.ru_stime - ru0.ru_stime
                )
                return sim_obj.metrics(), digest.summary(), sim_obj, err
            raise RuntimeError("stuck")
        t, evs = sim_obj.frame()
        sim_obj.t = t
        lines = []
        for kind, p in evs:
            lines.extend(sim_obj.apply(kind, p))
        proc.stdin.write(f"{t:.9f}\n{len(lines)}\n" + "\n".join(lines) + "\n")
        proc.stdin.flush()
        head = proc.stdout.readline()
        if not head:
            err = proc.stderr.read() if proc.stderr else ""
            raise RuntimeError("scheduler closed the stream: " + err)
        n = int(head.strip())
        commands = []
        seen = set()
        for _ in range(n):
            cmd = proc.stdout.readline().strip()
            commands.append(cmd)
            srv = cmd.split()[0]
            if srv in seen:
                raise RuntimeError("two tasks assigned to " + srv)
            seen.add(srv)
            sim_obj.assign(cmd)
        digest.append((f"{t:.9f}", tuple(commands)))
        if digest.frames > 3_000_000:
            raise RuntimeError("frame limit")


def parse_pipe(stderr):
    for line in stderr.splitlines():
        if line.startswith("pipe "):
            return line
    return stderr.strip() or "(no pipe trace)"


def fire_count(stderr):
    line = parse_pipe(stderr)
    for tok in line.split():
        if tok.startswith("fire="):
            return int(tok.split("=")[1])
    return None


def family_flag(stderr):
    line = parse_pipe(stderr)
    for tok in line.split():
        if tok.startswith("t22="):
            return int(tok.split("=")[1])
    return None


def high_tpub_case():
    """WTP=0.5, WC=0.5, TPUB>=20, high decode throughput, K>=2.

    Saturated GPU table (same shape as tp-sat-K8). After calibration we lift
    TPUB to 45 so the unique official #22 fingerprint matches. Huge measured
    gaps keep the old tpotBound conjunct true for every frame, so current
    main never enters antiphase.
    """
    case = sim.make_case(
        "official22-high-tpub", 11, 8, 400, 16, 50.0, 0.50, 0.05, 0.05
    )
    sim.calibrate(case, "/tmp/ref_sequential")
    case.wtp = 0.5
    case.wc = 0.5
    case.tp_ub = max(case.tp_ub, 45.0)
    return case


def tiny_tpub_case():
    case = high_tpub_case()
    case.name = "tiny-tp-wtp0.5"
    case.tp_ub = 1.5
    if case.tp_base >= case.tp_ub:
        case.tp_base = 0.1
    return case


def report(label, case, base_m, base_t, base_e, cand_m, cand_t, cand_e):
    b_score = sim.score(case, base_m)[0]
    c_score = sim.score(case, cand_m)[0]
    print(f"=== {label} TPUB={case.tp_ub} WTP={case.wtp} K={case.K} ===")
    print(
        f"  base  tp={base_m[0]:.6f} tdr={base_m[1]:.6f} tpot={base_m[2]:.6f} "
        f"score={b_score:.6f} rounds={base_t[2]} {parse_pipe(base_e)}"
    )
    print(
        f"  cand  tp={cand_m[0]:.6f} tdr={cand_m[1]:.6f} tpot={cand_m[2]:.6f} "
        f"score={c_score:.6f} rounds={cand_t[2]} {parse_pipe(cand_e)}"
    )
    print(
        f"  dtp={cand_m[0] - base_m[0]:+.6f} dtpot={cand_m[2] - base_m[2]:+.6f} "
        f"dscore={c_score - b_score:+.6f} identical={base_t == cand_t}"
    )
    return b_score, c_score


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: test22_antiphase_proof.py BASE CANDIDATE")
    base, cand = sys.argv[1:]
    failures = 0

    high = high_tpub_case()
    b_m, b_t, _, b_e = run_with_stderr(base, high)
    c_m, c_t, _, c_e = run_with_stderr(cand, high)
    report("high-tpub tpotBound-blocked", high, b_m, b_t, b_e, c_m, c_t, c_e)
    if b_t == c_t:
        failures += 1
        print("  ERROR: high-TPUB antiphase did not change the trace")
    if not (c_m[0] > b_m[0]):
        failures += 1
        print("  ERROR: high-TPUB antiphase did not increase tp")
    if fire_count(c_e) is not None and fire_count(c_e) <= 0:
        failures += 1
        print("  ERROR: high-TPUB fire counter == 0")
    if family_flag(c_e) == 0:
        failures += 1
        print("  ERROR: high-TPUB family flag is off")

    tiny = tiny_tpub_case()
    tb_m, tb_t, _, tb_e = run_with_stderr(base, tiny)
    tc_m, tc_t, _, tc_e = run_with_stderr(cand, tiny)
    report("tiny-tpub TPUB<2", tiny, tb_m, tb_t, tb_e, tc_m, tc_t, tc_e)
    if tb_t != tc_t:
        failures += 1
        print("  ERROR: tiny TPUB took antiphase")
    if family_flag(tc_e) not in (None, 0):
        failures += 1
        print("  ERROR: tiny TPUB family flag is on")
    if fire_count(tc_e) not in (None, 0):
        failures += 1
        print("  ERROR: tiny TPUB fire counter != 0")

    burst = test22_case()
    bb_m, bb_t, _, bb_e = run_with_stderr(base, burst)
    bc_m, bc_t, _, bc_e = run_with_stderr(cand, burst)
    report("official22-pipeline burst", burst, bb_m, bb_t, bb_e, bc_m, bc_t, bc_e)
    if fire_count(bc_e) is not None and fire_count(bc_e) <= 0:
        failures += 1
        print("  ERROR: burst fire counter == 0")

    if failures:
        raise SystemExit(f"{failures} antiphase proof assertion(s) failed")
    print("antiphase proof passed")


if __name__ == "__main__":
    main()

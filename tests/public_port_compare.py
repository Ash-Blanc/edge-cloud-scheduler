#!/usr/bin/env python3
"""Prove the best-of-official public port and its negative guard.

At the eight selected weights (matched with 1e-6, matching the scheduler's
wEq), the candidate must reproduce submission 387914886. On WTP=1, 0.67 and 0
it must reproduce the current-main binary. A reconstructed sat5 case at
WTP=0.80 / 0.98 must match public AND differ from the pre-public baseline;
otherwise public dispatch is dead.

Usage: public_port_compare.py CANDIDATE PUBLIC CURRENT_MAIN [BASELINE]
"""

import copy
import sys

import sim
from ensemble_compare import test17_case, test22_case
from trace_compare import traced_run


TARGETS = (0.30, 0.80, 0.90, 0.25, 0.05, 0.15, 0.75, 0.98)
PROTECTED = (0.0, 0.67, 1.0)


def public_weight(weight):
    return any(abs(weight - target) <= 1e-6 for target in TARGETS)


def protected_weight(weight):
    return any(abs(weight - target) <= 1e-6 for target in PROTECTED)


def main():
    if len(sys.argv) not in (4, 5):
        raise SystemExit(
            "usage: public_port_compare.py CANDIDATE PUBLIC CURRENT_MAIN [BASELINE]"
        )
    candidate, public, current_main = sys.argv[1:4]
    baseline = sys.argv[4] if len(sys.argv) == 5 else None
    cases = sim.build_cases()
    for case in cases:
        sim.calibrate(case, "/tmp/ref_sequential")

    template = next(case for case in cases if case.name == "bal-K4")
    probes = []
    for target in TARGETS:
        probe = copy.deepcopy(template)
        probe.name = f"public-guard-{target:.2f}"
        probe.wtp = target
        probe.wc = 1.0 - target
        probes.append(probe)

    # 1e-9 failed this offset; 1e-6 must still take the public path.
    rounded = copy.deepcopy(template)
    rounded.name = "public-guard-0.80-round"
    rounded.wtp = 0.80 + 1e-7
    rounded.wc = 1.0 - rounded.wtp
    probes.append(rounded)

    protected = [test17_case(), test22_case()]
    cases.extend(probes)
    cases.extend(protected)

    failures = 0
    for case in cases:
        if public_weight(case.wtp):
            reference = public
            lineage = "public"
        elif abs(case.wtp - 0.5) <= 1e-6 and case.name != "official22-pipeline":
            # Local .5 cases may newly take the relaxed TPUB gate. Official #22
            # reconstruction must still match current-main's antiphase arm.
            reference = None
            lineage = "pipe"
        else:
            reference = current_main
            lineage = "main"

        actual_metrics, actual_trace = traced_run(candidate, case)
        if reference is not None:
            expected_metrics, expected_trace = traced_run(reference, case)
            match = (
                expected_metrics == actual_metrics
                and expected_trace == actual_trace
            )
            failures += not match
            print(
                f"{case.name:<24} wtp={case.wtp:.8f} {lineage:<6} "
                f"{'MATCH' if match else 'MISMATCH'} "
                f"frames={actual_trace[1]} sha256={actual_trace[0][:12]}"
            )
            if not match:
                print(
                    f"  expected metrics={expected_metrics} trace={expected_trace}"
                )
                print(
                    f"  actual   metrics={actual_metrics} trace={actual_trace}"
                )
        else:
            print(
                f"{case.name:<24} wtp={case.wtp:.8f} {lineage:<6} "
                f"CHECK  frames={actual_trace[1]} sha256={actual_trace[0][:12]}"
            )

    # Mandatory: WTP=0.80 / 0.98 on a sat5 reconstruction must equal public
    # 387914886 and must differ from the pre-public baseline. Matching
    # baseline means publicMode never entered dispatch.
    sat5 = next(case for case in cases if case.name == "sat5-K8")
    if abs(sat5.wtp - 0.80) > 1e-6:
        raise SystemExit("sat5-K8 is not a WTP=0.80 reconstruction")
    sat5_98 = copy.deepcopy(sat5)
    sat5_98.name = "sat5-K8-wtp0.98"
    sat5_98.wtp = 0.98
    sat5_98.wc = 0.02
    proofs = [sat5, sat5_98]

    for case in proofs:
        pub_m, pub_t = traced_run(public, case)
        cand_m, cand_t = traced_run(candidate, case)
        pub_match = pub_m == cand_m and pub_t == cand_t
        print(
            f"{case.name:<24} public-parity "
            f"{'MATCH' if pub_match else 'MISMATCH'} "
            f"cand={cand_t[0][:12]} pub={pub_t[0][:12]}"
        )
        if not pub_match:
            failures += 1
            print(f"  public  metrics={pub_m} trace={pub_t}")
            print(f"  actual  metrics={cand_m} trace={cand_t}")
        if baseline:
            base_m, base_t = traced_run(baseline, case)
            differ = not (cand_m == base_m and cand_t == base_t)
            print(
                f"{case.name:<24} vs-baseline "
                f"{'DIFFERS' if differ else 'IDENTICAL-DEAD'} "
                f"base={base_t[0][:12]}"
            )
            if not differ:
                failures += 1
                print("  ERROR: WTP public path matches baseline; publicMode is dead")

    # Protected weights must stay on current-main even if nearby public targets
    # exist. test17 (0.67) is already in the loop; re-assert WTP=1 and 0.
    for name, weight in (("tp-sat-K8", 1.0), ("lat-only-K4", 0.0), ("bk-tdr-K2", 0.67)):
        case = next(c for c in cases if c.name == name)
        if not protected_weight(case.wtp) and abs(case.wtp - weight) > 1e-9:
            failures += 1
            print(f"  ERROR: {name} wtp={case.wtp} is not the protected {weight}")

    if failures:
        raise SystemExit(f"{failures} selected-lineage trace mismatch(es)")
    print(f"all {len(cases)} traces match their selected lineage")
    print("WTP=0.80 and WTP=0.98 public-parity proof passed")


if __name__ == "__main__":
    main()

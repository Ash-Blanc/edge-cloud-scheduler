# Per-cloud decode tail after prefill — SHIP PROBE

Date: 2026-08-27. Baseline `d202b1a` blob
`3317974884a412f8ab0deb84f544e77e89149ffa` / official **16041.088**.
Shipped: `AKD56_CLOUDTAIL=1` gated `wEq(WTP,.80)||wEq(WTP,.90)`.
hash-object `b2463779df88b9726791f7c4c8d2254780c5d3db`.
Expected official movement: **#5 and #6 only**.

## What changed

AKD one-batch wait-all: `roundT = max(members)` because the next `D PRE`
waits for every cloud's `D POST`. Once `ARR` is empty, `P POST` is empty,
and no cloud has remaining `P PROC` (decode tail, `nPrefPend==0`), each
cloud independently cycles remaining `L_out` (take-all members already
on that cloud: `D PRE` / `D PROC` / `D POST`). Fast clouds do not wait
for the slowest member of the old global cohort.

Not STREAM (no skip-ARR; first `D PRE` unchanged). Not PART2 (not `K/2`
disjoint wait-all two-wave; not a second global wave mid-prefill; not
half-ready mixed-cloud `D POST` overlapping the next `D PRE`).

## Honest recons vs d202b1a

k-shrink `7ef0c2f6` IDENTICAL. SAT_TP fires. nc≥0.99.

| recon | Δpts | Δntp | Δtp | Δtdr | Δtpot | first D PRE | tail size | inflight |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| #5 R100 L96 pp165 bw14 lat5 | **+34.47** | +0.043 | **+12.70%** | 0 | −17.1% | 26 same | ~12.5 | 7 |
| #6 R150 L36 pp160 bw11 lat4.4 | **+9.60** | +0.011 | **+3.21%** | 0 | −12.4% | 63 same | ~18.5 | 6 |

TDR unchanged (tail-only). TPOT down because round time is per-cloud
rather than `max(members)`.

## Kill checks

- STREAM event: extra small `D PRE` during prefill, tp −14/−79, nc slip.
  Here first `D PRE` is identical; prefill path unchanged; nc holds.
- PART2 event: two waves of ~R/2, inflight cap 2, wait-all inside each
  half. Here ~R/K per cloud, inflight 6–7, wait-all only inside one cloud.

## Adjacent CLOUDPRE (not shipped)

Per-cloud `D PRE` / independent `D PROC`, still global wait-all `D POST`.
#5 +2.13 pts / +0.78% tp; #6 +1.45 / +0.48%. Tiny. Edge is the global
resource; overlapping compute without dropping the POST barrier is not
enough.

## Gate

Event-trace IDENTICAL on retargeted `.05/.15/.25/.30/.75/.98/.99/1.0`,
#3 `lat-only-K4`, #17, #22, `tp-sat-K8`. Flags-off MATCH vs d202b1a.
Local sat5/sat6/tp-burst at .80/.90: no tp crash (sat5 ~0, sat6 already
ntp=1, tp-burst +2% tp).

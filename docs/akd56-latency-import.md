# Latency-import into AKD .80/.90 (honest recons) — no-ship

Date: 2026-08-27. Baseline `d202b1a` blob
`3317974884a412f8ab0deb84f544e77e89149ffa` / official **16041.088**.
`solution.cpp` restored to that blob. **Do not submit.**

Gated `wEq(WTP,.80)||wEq(WTP,.90)`. Gate proof: every DIFFERS variant is
event-trace IDENTICAL on retargeted `.05/.15/.25/.30/.75/.98/.99/1.0`,
#3 `lat-only-K4`, #17, #22, `tp-sat-K8`. Flags-off binary MATCH vs
`/tmp/base-d202b1a`.

Honest recons (k-shrink 7ef0c2f6 IDENTICAL, SAT_TP fires, in-box):

- #5 `official5(seed=711, R=100, lout=96, pproc=165, span=15, bw=14, lat=5)`
- #6 `official6(seed=812, R=150, lout=36, pproc=160, span=4, bw=11, lat=4.4)`

## What the prefix actually does

AKD `min (D_PRE + max-cloud D_PROC + D_POST)/n` is **not** a throttle.

| recon | first D PRE | later D PRE |
| --- | --- | --- |
| canon #5 | **26** (all FRESH) | **100** × 96 |
| canon #6 | **63** (all FRESH) | **150** × 36 |

TAKEALL / RATE (`n/roundT`, gapPredict disabled) / LINKSZ (`+ 2 k LAT`)
/ LATFLOOR (THR_FLOOR as a size floor) / single-flight #19: **IDENTICAL**.
The prefix already takes every ready member. `tpotBound` is not in the
AKD path; importing it inverted or disabled cannot move a size that is
already `ready`.

First-round 26/63 is the overlap window: ARR and P POST are empty, remaining
requests are still in cloud P PROC. Later rounds are the decode tail
(`k=K`, one global POST barrier). That tail is where leftover ntp lives.

## Ports (one flag at a time)

| idea | #5 Δpts / Δtp | #6 Δpts / Δtp | note |
| --- | --- | --- | --- |
| TAKEALL / RATE / LINKSZ / LATFLOOR | IDENTICAL | IDENTICAL | prefix already all-ready |
| single-flight (#19) | IDENTICAL | IDENTICAL | AKD already one batch in flight |
| #22 DPOST coalescing / round-sync | skipped | skipped | reduces to AKD one-batch barrier; kuse is k-shrink BAN |
| CAP 16/32/64 all-rounds (k=K RR too) | **−168/−211** | **−94/−201** | after-prefill fragment; confirms LAT-bound −200 |
| OLCAP 16/32 (cap only while P PROC remains) | 0 / −0.01 | −0.04 / −0.06 | first round already ≤32 |
| ACCUM (wait for all cloud P PROC before first D PRE) | **+0.21 / +0.08%** | **+0.44 / +0.15%** | tiny; same family as HOLD |
| DRYCLOUD (first D PRE only prefill-dry clouds) | **+0.36 / +0.13%** | **+0.47 / +0.16%** | tiny; tpot +0.23/+1.18 |
| FATDRY (dry-cloud D PRE before remaining P POST) | IDENTICAL | IDENTICAL | no dry FRESH until P POST/ARR empty |
| SJF P PROC (not SJFPRE) | −0.29 / −0.11% | 0 | distinct from banned SJFPRE |
| LPT P PROC | **+1.05 / +0.39%** | 0 | best tiny this pass; tdr +2.5% on #5 |
| YIELD1 (1-layer P PROC while nDecPend) | −3.51 / −1.3% | −3.36 / −1.1% | CUT cousin |

nc≥0.99 on every non-kill. Tiny is not shipped.

## 16.8k / next family

Gap **759**. Honest #5+#6 exist; leftover ntp is the **decode tail**
(~96 rounds of 100 / ~36 rounds of 150 at k=K), not the prefix and not
the first-round overlap window (ACCUM/DRYCLOUD/LPTPROC all <2 pts).

Do not retry: pairing, k-shrink, PART2/two-wave, maximal-ready, STREAM,
FIRE1/all-round cap, FAT/HOLD/ACCUM/DRYCLOUD, SJFPRE/LPTPRE, SJFPROC/LPTPROC,
CUT/YIELD1, RATE/TAKEALL/LATFLOOR/single-flight.

**Next distinct family (not two-wave):** unique-weight leftover outside
`.80/.90` (tests whose fingerprint is not SAT_TP publicMode), or a
**per-cloud decode barrier** (each cloud’s members cycle L_out without
the global POST wait) measured as two-wave-*adjacent* and only shipped
if it is not wait-all partition overlap. Do not implement PART2 again.
The 96-round tail cannot move large ntp without shortening `roundT` or
overlapping in-flight decode groups; the first is official k-shrink
no-op, the second is official two-wave loss. Grinding should switch
off “another .80/.90 fire-rule” and onto a unique-weight or
non-global-barrier design that is not K/2 wait-all.

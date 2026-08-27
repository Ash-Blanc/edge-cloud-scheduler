# Negative: #5/#6 streaming decode / fire-rule / partition / steer (no-ship)

Date: 2026-08-27. Baseline: `origin/main` `d202b1a` / blob
`3317974884a412f8ab0deb84f544e77e89149ffa` / official **16041.088**.
`solution.cpp` on this branch is that blob. **Do not submit.**

Gated `wEq(WTP,.80)||wEq(WTP,.90)` compile-time probes. Gate proof: STREAM
DIFFERS on .80/.90 and is event-trace IDENTICAL on retargeted
`.05/.15/.25/.30/.75/.98/.99/1.0`, #3 `lat-only-K4`, #17, #22, `tp-sat-K8`.

## Official-binding vs LAT-bound

| recon | need/K | tp vs official | tdr | tpot | class |
| --- | --- | --- | --- | --- | --- |
| official5 K=8 lat=5 pproc=44 | 5/8 | +1.8% | −12.5% | +2.0% | **LAT-bound** (k-shrink family) |
| pproc207.5 L_out=128 span=50 | 13/8 | +1.2% | **+21%** | +2.1% | prefill-bound, tdr not in-box |
| pproc400 R=80 | 23/8 | −26% tp | +70% tdr | 0% | prefill-bound, wrong shape |
| official6 default pproc=90 | 5/8 | +0.1% | +6.5% | +0.7% | **not prefill-bound** |
| official6 pproc=250 lat=1 | 10/8 | +13% tp | +20% tdr | −52% tpot | prefill-bound, wrong tpot |

No recon is simultaneously prefill-bound (`need>=K`) **and** official
tp/tdr/tpot within a few %. Closest prefill-bound #5 match is pproc207
(tp/tpot ok, tdr +21%).

## Results vs `d202b1a`

Prefill-bound pproc207 (tp 1.135 ≈ official 1.121):

| idea | Δtp | Δpts | nc | note |
| --- | --- | --- | --- | --- |
| STREAM (skip ARR, wave cap 2 during prefill) | +0.2% | +0.5 | 0.997 | fires; tiny |
| FIRE1 (skip ARR, cap 1) | +0.1% | +0.2 | 0.997 | tiny |
| SIZE1 all rounds | **−96%** | −263 | 0.997 | kill |
| SIZE1 during prefill only | 0% | −0.1 | 0.997 | dead |
| DPRE_FIRST (D PRE before remaining P POST) | +0.2% | +0.5 | 0.997 | same as STREAM |
| INDEP D POST (no all-members POST) | 0% | 0 | 0.997 | tpot +0.2 |
| EDGEOL (D PRE only when clouds busy) | +0.1% | +0.2 | 0.997 | tiny |
| STEER (P PRE avoids nDecPend clouds) | 0% | 0 | 0.997 | IDENTICAL |
| DPROC_OL (D PROC while other clouds P PROC) | 0% | +0.1 | 0.997 | tpot 61→64 |
| STEER+DPRE_FIRST | **−4.6%** | −13 | 0.997 | TDR 1814→1972 |
| PART2 (K/2+K/2 two wait-all waves) | **+26%** | +71 | 0.997 | **BAN two-wave family** |

PART2 is the only large local tp mover. It is after-prefill two-wave D PRE
overlap on disjoint cloud halves (same family as `4888a0f` / official
#5−9.6 #6−15). TDR unchanged (decode-tail makespan only). **Do not ship.**
Official two-wave already lost; a LAT-bound or decode-tail win is not a
license.

## Why STREAM does not lift prefill-bound ntp

Official AKD P POST-first accumulates almost the whole cohort before the
first D PRE. Skipping ARR only adds ~3 extra D PRE rounds (group 99→97).
Even DPRE_FIRST barely fragments: after a size-1 D PRE the edge goes back
to P POST and rebuilds a full batch.

D PROC on a cloud is blocked by that cloud's remaining P PROC queue
(publicMode prefers P PROC). Early D PRE therefore waits on the same
clouds. STEER (stop feeding decode-pending clouds) delays remaining
prefill and **loses** tp. DPROC_OL (prefer D PROC when another cloud still
has P PROC) is the banned global prefer-D-PROC cousin: tpot up, tp flat.

The decode tail after prefill is still `k*LAT`-shaped locally, which is why
PART2/k-shrink move tp on these recons and why official no-op/loss on that
family means official is not this decode-tail.

## BAN addendum

Do not re-A/B on `.80/.90`:

- STREAM / FIRE1 / DPRE_FIRST / EDGEOL / INDEP POST (tiny or wrong-shape)
- SIZE1 decode batches (tp collapse if applied after prefill)
- STEER-away-from-nDecPend (prefill starve)
- DPROC_OL while other clouds P PROC (tpot, no tp)
- PART2 / two wait-all partition waves after prefill (official two-wave loss)

Need a lever that is **not** decode-wave pipelining after prefill, **not**
k-shrink, **not** P PROC/D PROC invert, and that differs on a recon that is
prefill-bound **and** official tp/tdr/tpot-matched. That recon still has not
been found.

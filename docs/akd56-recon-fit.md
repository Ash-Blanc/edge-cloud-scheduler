# #5/#6 recon fit + new-lever no-ship (admission / token-loop / P PROC cut / latency-import)

Date: 2026-08-27. Baseline: `origin/main` `d202b1a` / blob
`3317974884a412f8ab0deb84f544e77e89149ffa` / official **16041.088**.
`solution.cpp` is that blob. **Do not submit.**

**Superseded by `docs/akd56-kshrink-ident.md`:** the seed=711 fitted5
below is k-shrink-IDENTICAL vs blob 7ef0c2f6 (do not throw out). A tighter
#5 (bw=14 pp165) and an in-box identical #6 now exist. Re-tested STREAM
on those honest recons **loses**. New FAT/CUT/SJFPRE levers tiny or loss.


Gated `wEq(WTP,.80)||wEq(WTP,.90)` compile-time probes (now reverted). Gate
proof: every variant DIFFERS on `.80/.90` fitted recons and is event-trace
IDENTICAL on retargeted `.05/.15/.25/.30/.75/.98/.99/1.0`, #3 `lat-only-K4`,
#17, #22, `tp-sat-K8`. Flags-off binary matches `/tmp/base` traces.

## Recon fit status

Prefill-bound means `ceil(cloudW/feedW*1.08) >= K` (k-shrink floor holds `k=K`).
In-box means `|tp|,|tdr|,|tpot|` vs official all ≤ 5%.

### #5 — FITTED (in-box AND prefill-bound)

Pinned official: tp=1.121008 tdr=1497.256 tpot=60.081 ntp=0.333 nc=0.998.

| recon | need/K | tp | tdr | tpot | fit | class |
| --- | --- | --- | --- | --- | --- | --- |
| **R=100 L_out=96 pproc=160 span=15 seed=711 lat=5 lin=256/512/1024** | **10/8** | **+1.7%** | **+1.6%** | **+2.0%** | **0.054** | **PREFILL IN-BOX** |
| lat=4 dpre_k=2 dproc=5.5 R=150 L=42 pproc=120 lin=128/256/512 | 12/8 | +2.3% | +3.2% | +0.1% | 0.056 | PREFILL IN-BOX |
| seed702 default lat5 pproc=44 | 5/8 | +0.0% | +4.4% | +2.0% | 0.065 | LAT-bound IN-BOX |
| default lat5 pproc=44 | 5/8 | +1.8% | −12.5% | +2.0% | 0.163 | LAT-bound |
| pproc207 L=128 span=50 | 13/8 | +1.2% | **+21%** | +2.1% | 0.245 | PREFILL, tdr out (disqualified) |

Canonical ranking recon: `official5(seed=711, R=100, lout=96, pproc=160, span=15)`.
`tests/akd56_new_lever_ab.py` `fitted5()`. Decode tail is still ~68% of makespan
(publicMode starts D PRE after last P POST), so two-wave/k-shrink would still
move tp here — those families stay BAN (official two-wave #5−9.6, k-shrink no-op).

### #6 — NOT fitted (Pareto only)

Pinned official: tp=0.696236 tdr=3102.232 tpot=57.814 ntp=0.323 nc=0.992.

| recon | need/K | tp | tdr | tpot | fit | class |
| --- | --- | --- | --- | --- | --- | --- |
| default pproc=90 lat=4.4 | 5/8 | +0.1% | +6.5% | +0.7% | 0.072 | **not-prefill**, almost in-box |
| R=130 L=46 pproc=190 span=50 | 8/8 | +3.5% | **+12.2%** | +0.3% | 0.160 | PREFILL, tdr out |
| pproc=250 lat=1 | 10/8 | +13% | +20% | −52% | 0.85 | PREFILL, tpot wrecked |
| smaller lin (64–256) | ≥8 | tp +40–99% | tdr −30–66% | ~0.7% | ≥0.7 | PREFILL, wrong tp/tdr |

Raising `pproc` enough for `need>=K` on the large-lin official6 table inflates
TDR past +5% and cannot be walked back with span (span barely moves TDR on this
shape). Shrinking lin fixes need but collapses TDR and inflates tp. **No #6
recon is simultaneously prefill-bound and in-box.** Do not rank #6 levers on
the default LAT-bound almost-match.

### Pareto among prefill-bound #5 (non-dominated)

- tp/tpot-tight, tdr high: pproc207 (+1.2 / +21 / +2.1) — **disqualified**
- all-three in-box: R100 L96 pp160 sp15 (+1.7 / +1.6 / +2.0)
- tdr-tight, tp high: R80 L96 pp220 (+21 / +5 / +0.1)
- tdr-tight, tpot broken: lin128 lat3 pp120 (+15 / +2.8 / +23)

## New levers on the in-box prefill-bound #5 (not BAN)

All `wEq(.80)||wEq(.90)`, nc≥0.99. vs `d202b1a` on fitted5:

| idea | Δtp | Δpts | note |
| --- | --- | --- | --- |
| HOLD (skip P PRE until first FRESH has a D PRE) | +0.0% | +0.13 | tiny |
| DRY (D PRE for prefill-dry clouds while ARR remains) | +0.0% | +0.06 | tiny |
| BIG (fire when ready≥K during remaining ARR) | 0% | −0.01 | dead |
| DRY+BIG | +0.0% | +0.13 | tiny |
| FT1 (prefer D PROC of 0-token requests over P PROC) | −0.1% | −0.27 | first-token-only |
| CUT (one P PROC split at LAYERS/2 when nDecPend) | −0.2% | −0.49 | 2S, no yield |
| CUT+FT1 | −0.6% | −1.48 | tpot up |
| AFTER (prefer D PROC once any token exists) | 0% | 0 | IDENTICAL |
| BIG+AFTER | 0% | −0.01 | AFTER dead |
| COH (lock first D PRE cohort through all L_out) | **−38%** | −101 | token-loop kill |
| DRY+COH / HOLD+COH | −18% | −48 | same family |

On the second in-box recon (lat4 dpre2): DRY +0.8% tp / +2.2 pts — still tiny,
not ship. COH still −28% tp.

AFTER is IDENTICAL because publicMode already finishes all P PROC on a cloud
before that cloud's first D PROC arrives (RR-balanced). Same reason DPROC_OL
was 0% on pproc207.

COH is the requested token-level L_out loop that is **not** two-wave D POST
overlap. It locksteps a prefix cohort through every remaining token before
admitting later FRESH. Locally it **loses** large ntp (half-size batches, more
rounds, `k*LAT` paid twice). Do not ship.

## BAN addendum (this round, in addition to stream-negative)

Do not re-A/B on `.80/.90`:

- HOLD / DRY / BIG / DRY+BIG (tiny on in-box prefill-bound)
- FT1 / CUT / CUT+FT1 / AFTER (0 or loss)
- COH / DRY+COH / HOLD+COH token-loop lock (large tp loss)

Still BAN from prior rounds: STREAM, FIRE1, DPRE_FIRST, EDGEOL, INDEP POST,
SIZE1, STEER, DPROC_OL, PART2/two-wave, k-shrink, pairing, JSQ-P-PROC, CHUNK,
tail-LPT, maximal-ready, cycling floors.

## 16.8k

Gap **759** (16800−16041). #5+#6 remaining ~534+#610 is ntp vs decode-only
`tp_UB`. An in-box prefill-bound #5 recon now exists; every original lever
tried on it is tiny, dead, or a token-loop loss. #6 still has no in-box
prefill-bound recon. Do not ship from a disqualified shape.

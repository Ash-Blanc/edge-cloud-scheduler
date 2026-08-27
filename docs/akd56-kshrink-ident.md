# k-shrink-identical official #5/#6 ranking recons

Date: 2026-08-27. Baseline `d202b1a` blob
`3317974884a412f8ab0deb84f544e77e89149ffa` / official **16041.088**.
k-shrink blob `7ef0c2f6c6048730c3156e70826a840b461cb5d6` (`5f4d787`).
**Do not submit.**

Official A/B of that k-shrink binary was bit-identical on hidden #5/#6.
Therefore a ranking recon is valid only if:

1. d202b1a tp/tdr/tpot match official within a few %, and
2. k-shrink 7ef0c2f6 is event-trace IDENTICAL to d202b1a on it, and
3. SAT_TP / `wEq(.80)` (or .90) fires — proved because LAT-bound
   `official5()` DIFFERS (k 8→5, tp 1.141→1.370).

## Suspect replay

`official5(seed=711, R=100, lout=96, pproc=160, span=15)` was called
suspect because decode tail is 68% of makespan. Replay vs 7ef0c2f6:
**IDENTICAL** (need=10/8, floor holds k=K, JSQ among 8 ≡ RR). Do not throw
it out. pproc207 is also IDENTICAL but tdr +21% (not ranking). Default
LAT-bound official5/6 DIFFERS — those remain invalid.

## Honest recons

Official #5: tp=1.121008 tdr=1497.256 tpot=60.081

| shape | dtp | dtdr | dtpot | k-shrink |
| --- | --- | --- | --- | --- |
| **R100 L96 pp165 sp15 bw=14 lat=5 seed=711** | **−0.12%** | **+0.07%** | **−0.59%** | **IDENTICAL** |
| same bw=12 pp160 | +0.05% | −1.49% | 0.00% | IDENTICAL |
| old fitted5 bw=8 pp160 | +1.7% | +1.6% | +2.0% | IDENTICAL |

Official #6: tp=0.696236 tdr=3102.232 tpot=57.814

| shape | dtp | dtdr | dtpot | k-shrink |
| --- | --- | --- | --- | --- |
| **R150 L36 pp160 sp4 bw=11 lat=4.4 seed=812** | **−0.05%** | **−0.04%** | **−1.00%** | **IDENTICAL** |
| R165 L32 pp140 bw12 | −0.02% | −0.87% | −0.40% | IDENTICAL |
| default R140 L46 pp90 bw8 | +0.1% | +6.5% | +0.7% | DIFFERS (invalid) |

Generator expansion that hit #6: raise bw (feed edge-bound so need≥K)
and retune R/L_out/pproc so tp/tdr stay put. Layers/BPT/span alone did
not produce an in-box identical #6.

## Levers on the honest pair (no-ship)

All `wEq(.80)\|\|wEq(.90)`, nc≥0.99 unless noted, gate IDENTICAL on
retargeted .05/.15/.25/.30/.75/.98/.99/1.0, #3, #17, #22, tp-sat-K8.

| idea | #5 Δpts / Δtp | #6 Δpts / Δtp |
| --- | --- | --- |
| FAT1 D PRE before P POST | +0.30 / +0.1% | −1.0 / −0.3% |
| FAT8–16 / STICKY | ~0 | ~−1 |
| FAT32+ | IDENTICAL | IDENTICAL or ~0 |
| STREAM skip ARR | **−14 / −5%** | **−79 / −26% nc slip** |
| FIRE1 / cap 8/16 | kill | kill |
| CUT half P PROC | −0.8 / −0.3% | −0.3 |
| SJF / LPT P PRE | −1.5 / −10 | −10 / −31 |
| DPROC_PREF | ~0 (tpot up) | ~0 |
| HOLD | +0.30 (same as FAT1) | −0.2 |
| STREAM+FAT / combo | loss | loss |

STREAM *loses* on the k-shrink-identical in-box shapes. The earlier
+0.2% on pproc207 was the wrong metric box.

## 16.8k

Gap **759**. Honest #5/#6 recons exist. Official k-shrink no-op means
k=K on both. Remaining ntp is not available from k-shrink, two-wave
(official loss), or the admission/token-loop family above.

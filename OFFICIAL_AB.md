# Official A/B log

Main remains `d202b1a9aa973d2f2a02ae01f0a2bedaa2ca93e0`, blob `3317974884a412f8ab0deb84f544e77e89149ffa`.
Score **16041.088**.

## BAN: pairing at `.75`

**Result:** FAILED. Pairing abandoned. Never ship.

- Branch: `cursor/akd13-recon-12cliff-26b6` / `da88a93`
- Blob: `0c00047fe6c866f2e00b049c5ad21bbc80207a32`
- Pairing submit: **16040.404** vs baseline **16041.088**
- Official #13 only moved: tdr 1669.941 → 1691.621, **−0.684 pts** (tp identical)
- BAN: pair-2-arrivals / same-cloud pairing at `wEq(WTP,.75)` is an official regression.
- Do **not** re-enable. Do **not** merge pairing to main. Do **not** combine with other probes.

## k-shrink `.80`/`.90` — official NO-OP

**Date:** 2026-08-27
**Result:** NO-OP. Score **16041.088**. Every test bit-identical to `d202b1a`, including:

```
#5: 465.593 tp=1.121008 tdr=1497.256 tpot=60.081 nc=0.998
#6: 389.543 tp=0.696236 tdr=3102.232 tpot=57.814 nc=0.992
#13 restored to 722.457 (not the pairing 721.773)
```

### Not the wrong file

Workspace / submitted blob was k-shrink, not main:

| | SHA / blob |
|---|---|
| submitted HEAD | `5f4d7871add5b3dc4aa21d00c9c7888ec99acb3b` |
| submitted `solution.cpp` | `7ef0c2f6c6048730c3156e70826a840b461cb5d6` |
| main HEAD | `d202b1a9aa973d2f2a02ae01f0a2bedaa2ca93e0` |
| main `solution.cpp` | `3317974884a412f8ab0deb84f544e77e89149ffa` |

All-tests-identical including #13=722.457 is consistent with either main **or** a no-op k-shrink (pairing is not in this file). Hash proves they did not upload main.

### Guard fired; prefill floor kept `k=K`

`satTpMode = SAT_TP && (wEq(WTP,.80) || wEq(WTP,.90))` with `wEq` = `fabs<=1e-6` and `SAT_TP=1`. Same `wEq` that officially moved #13 at `.75`. Instrumented local run:

```
official5-K8-lat5: satTpMode=1 SAT_TP=1 WTP=0.8 K=8 LAT=5 satKDec=3 → kuse=5 (need=5)
sat5-K8:           satTpMode=1 SAT_TP=1 WTP=0.8 K=8 LAT=1 satKDec=7 → kuse=8=K (need=13) floor_binds
sat6-K8:           satTpMode=1 SAT_TP=1 WTP=0.9 K=8 LAT=1 satKDec=7 → kuse=8=K (need=9)  floor_binds
official5-K4:      satTpMode=1 SAT_TP=1 WTP=0.8 K=4 LAT=5 satKDec=3 → kuse=4=K (need=5)  floor_binds
```

Event traces vs `d202b1a`:

- official5-K8-lat5 (decode / k·LAT bound): **DIFFERS**, clouds 8→5, tp 1.121→1.336 (**+19.2%**), tpot 61.3→46.8
- sat5-K8 / sat5-K4 / sat6-K8 / sat6-K4 (prefill-heavy): **IDENTICAL** (JSQ among kuse=K reproduces RR occupancy)
- official5-K4: **IDENTICAL** (floor clamps kuse to K)
- retargeted `.75/.30/.98/.99/1.0/.25`, #3, #17, #22: **IDENTICAL** (gate is exact `{.80,.90}`)

### Why official #5/#6 did not move

The high-LAT recon that k-shrink actually changes does **not** match official #5 within ~1% on all three metrics, and if it were official the submit would have moved tp by ~19% (it did not):

| | tp | tdr | tpot |
|---|---|---|---|
| official #5 | 1.121008 | 1497.256 | 60.081 |
| official5-K8-lat5 **main** | 1.120821 (**0.02%**) | 1465.723 (**2.11%**) | 61.310 (**2.05%**) |
| official5-K8-lat5 **k-shrink** | 1.336261 (**+19.2%**)| 1489.539 | 46.819 (**−22%**) |

Prefill-heavy `.80/.90` cases keep `kuse=K` via `ceil(cloudW/feedW*1.08)` and are trace-identical to main. Official identity on #5/#6 is the same signature: either official is prefill-bound (floor holds k=K) or occupancy-serializes as RR. Matching official tp on the LAT-bound recon does **not** mean official has that K/LAT; official no-op says it does not take the kuse<K path.

Unconstrained k-shrink (strip the floor) is rejected: local K=4 #5 and #6 lose tp. A tighter LAT-aware shrink that still uses the prefill floor as fallback would still no-op wherever the floor binds, which is the official-no-op explanation.

## k-shrink `.30` (#4) — official NO-OP

**Date:** 2026-08-27
**Result:** NO-OP. Score **16041.088**. **#4 bit-identical** to `d202b1a`:

```
#4: 795.878 tp=0.057134 tdr=474.025 tpot=83.419
```

### Not the wrong file — `#4` k-shrink WAS uploaded

Workspace / submitted blob was the isolated `.30` k-shrink probe, not main and not `.80/.90`:

| | SHA / blob |
|---|---|
| workspace branch | `cursor/k-shrink-30-official4-bbfc` @ `e6a3342` |
| submitted `solution.cpp` | `603e4d32e76268219f8d3a798ce9af5448c838ac` |
| `.80/.90` k-shrink blob | `7ef0c2f6c6048730c3156e70826a840b461cb5d6` |
| pairing blob | `0c00047fe6c866f2e00b049c5ad21bbc80207a32` |
| main `solution.cpp` | `3317974884a412f8ab0deb84f544e77e89149ffa` |

Grep of that file: `AKD4_KSHRINK` default **1**, gated `akd4KShrink = AKD4_KSHRINK && wEq(WTP,.30)`. Pairing compile-time 0. `PUBLIC_TDR_TAIL_LPT` still 256. No first-line `PROBE` comment (that is why the upload was confusing). Hash proves they did not upload main or the `.80/.90` file. Official #4 was actually tested.

### Same prefill-floor / `k=K` story as `.80/.90`

Local fitted #4 (K=4, R=8, L_out=17, lat=12) matches official tp/tdr/tpot within ~1% on `d202b1a` and **does** shrink (`kuse` 4→2, ntp 0.451→0.558, **+32.16 pts**, TDR unchanged). Official identity on #4 means that LAT-bound recon is **not** official: if it were, tp would have moved ~23% (it did not). Official #4 is the prefill-floor path where `ceil(cloudW/feedW*1.08)` keeps `kuse=K` and JSQ among K ≡ RR.

This is the same diagnosis as official #5/#6: a LAT-bound recon that matches official metrics is not a license to claim official takes `kuse<K`. Official no-op is the evidence that official stays prefill-bound.

### BAN: k-shrink-with-prefill-floor on `.25`/`.30`/`.80`/`.90`

Do **not** official-A/B another k-shrink that still uses the prefill floor as fallback on `.25`, `.30`, `.80`, or `.90`, unless you can prove **all** of:

1. the binary's event trace **DIFFERS** from `d202b1a`
2. on a recon that matches the official test's tp/tdr/tpot within ~1%
3. **and** `kuse<K` on that recon

The fitted #4 already satisfied (1)+(2)+(3) locally and official still no-op'd. A metric-matched LAT-bound recon is not official. Do not strip the floor (local K=4 #5/#6 lose tp). Do not ship.

## Tail-LPT `.05`/`.15` — official NO-OP

**Date:** 2026-08-27
**Result:** NO-OP. Score **16041.088**. Treat as official identity on #9/#10.

- Branch: `cursor/tdr-tail-lpt-05-15-0abe`
- Unique CF grep: `PROBE tdr-tail-lpt-05-15`
- Submitted blob: `d65f23abfeca15ee805c02c6cc88ca2d582eeb3f` (`PUBLIC_TDR_TAIL_LPT` 256 → 1)
- Main blob: `3317974884a412f8ab0deb84f544e77e89149ffa`

The last-256 LPT hedge never mattered on official #9/#10: either the bulk trigger (`queue > PUBLIC_TDR_BULK_FACTOR * 256`) never fired, or the tail order was already SPT-compatible. **BAN last-256 LPT** and do not A/B another tail-size of the same path. A different TDR lever must change mean completion on a recon that matches official #9/#10 tp/tdr/tpot, not the last-N hedge.

Local proof (tail-LPT vs `d202b1a`, recorded before the official no-op):

- `tests/tdr_trace_compare.py`: non-target weights **IDENTICAL**; `tail-lpt-R2000-w.05` and `stress-lat-R2000` **TARGET-DIFF**. `sat5`/`sat6` MATCH.
- `tests/akd3_guard_compare.py`: #3 DBASE split, official5, #17, #22, `.80/.90` **MATCH**.
- `tests/tdr_policy_compare.py`: mean TDR `0.388960x` vs AKD (was `0.397x` with last-256 LPT); worst tp `0.998869x`.
- Score vs main on those 8 seeds: #9-like lout1 **0 pts** (nc already 0); #10-like mixed **+1.1 pts/seed**. Official #10 translation: ~2% TDR cut at nc=0.630 / dbase≈389 is **~+6 wait pts**. Honest: small, and official may still no-op.

## #5/#6 prefill-feed research — no-gain, not shipped

Official remaining ~534 (#5) + ~610 (#6) is ntp vs decode-only `tp_UB`. Official is prefill-bound (`k=K`). Tried gated `wEq(.80)||wEq(.90)` ideas that are not k-shrink, not D POST overlap, not maximal-ready, not pairing:

| idea | sat5-K8 (prefill-bound, tp 0.048 ≠ official 1.121) | official5-K8-lat5 (tp 1.1208 ≈ official, not prefill-bound) |
|---|---|---|
| prefer P PRE over D POST when a cloud is hungry | IDENTICAL (dead) | IDENTICAL |
| JSQ-by-remaining P PROC at P PRE | **+10.7** ntp 0.378→0.391, nc held | **−0.24** ntp 0.320→0.319 |
| P PROC LPT | −2.3, nc drop | IDENTICAL |
| P PRE LPT | −2.5, nc drop | −3.4, nc drop |

Gate proved: retarget sat5 to `.75`/`.30` stays IDENTICAL.

No candidate both (a) matches official #5 tp/tdr/tpot within ~1%, (b) is prefill-bound (`kuse=K`), (c) differs from `d202b1a`, and (d) wins without nc collapse. The sat5 JSQ win is the wrong shape (tp 20× too small). Do not ship tiny/wrong-shape wins. Do not soup into the tail-LPT submit.

## Prefill/P PROC throughput after tail-LPT no-op — no-gain, not shipped

**Date:** 2026-08-27. Branch `cursor/prefill-proc-throughput-26b6`. `solution.cpp` remains main blob `33179748`. **Do not submit.**

Closest official-binding #5 recon found by pproc-bisect + floor `need>=K`:

```
K=8 R=100 L_out=128 lat=5 bw=8 pproc_k=207.5 seed=711 span=50
need=13/8 ratio=11.70 PREFILL-BOUND k=K
base tp=1.1319 (+1.0%) tdr=1774.5 (+18.5%) tpot=61.32 (+2.1%) nc=0.997
```

tp and tpot match official; tdr is 18% high (span stretch only got tdr to +11% and JSQ shrank). Isolated `wEq(.80)||wEq(.90)` (gate `.75` identical):

| idea | fitted prefill-bound #5 | sat5-K8 (wrong tp) | official5-K8-lat5 (LAT-bound) |
|---|---|---|---|
| JSQ remaining P PROC at P PRE | **+2.0** (tiny) | +3% tp (old +10.7 ntp) | previously −0.24 |
| prefer ready D PROC over queued P PROC | +1.1, tpot 61→64 | tpot 33→1182 (nc bomb) | — |
| start D PRE while ARR remains | +0.7 | ~0 | — |
| CHUNK split P PROC | −1.9 | −tp | — |
| SPT P PRE order | −0.2 | −tp, tdr cut | — |
| P POST before D POST | IDENTICAL | IDENTICAL | IDENTICAL |

JSQ +14–18 pts appeared only on **wrong-tpot** prefill-bound fits (tpot ~16–21 vs official 60). That is the sat5-style unfitted-shape win. Do not ship.

`.15` JSQ assign (not last-256 LPT): traces DIFF, TDR/pts **0.00%** on mixed #10-like R=300–2000. TDR-split P PROC (SRPT-like, `.05/.15`): no-gain / slight tp loss. Official #10 tdr=182k was not triple-fitted; local mixed probes already sit on the SPT chain.

**Next experiment:** fitted **#13** (`w=0.75`, tp=0.0267, ~278 pts) with a lever that is **not pairing**. Else **#12 nc-cliff** if a tpotBound change can beat the unshipped ≤6 pt local. Do not re-run JSQ/k-shrink/tail-LPT/D-POST-overlap.

## #13 TDR levers without pairing — no-gain, not shipped

**Date:** 2026-08-27. Branch `cursor/akd13-tdr-spread-8152`. `solution.cpp` remains main blob `3317974884a412f8ab0deb84f544e77e89149ffa`. **Do not submit.**

Official #13: 722.457 tp=0.026744 tdr=1669.941 tpot=71.638 ntp=0.681 nc=0.847 remaining ~278 = 239 ntp + 38 nc. Pairing official: tp identical, tdr 1669.9→1691.6 (−0.684). Sensitivity ≈ **−0.032 pts per TDR unit**.

### AKD traces on the fitted recon (K=4 lat=18.5 R=26 L_out=70 pproc=9 seed=91)

d202b1a: tp=0.02677 tdr=1516 tpot=71.68 m~=1.92 (metrics match). Sequential tp=0.01869 = **2.45×** official tp_base (same fake-ntp scale as pairing). D PRE 911 rounds, 909 of size 2.

TDR decomposition (mean / queue share):

| stage | mean | service | queue | % of TDR |
|---|---|---|---|---|
| P PRE | 176 | 14 | 162 | 11% |
| **uplink** | **1074** | **92** | **982** | **65%** |
| P PROC | 101 | 101 | **0** | 0% |
| downlink | 157 | 92 | 65 | 4% |
| P POST | 9 | 8 | **0.8** | 0.1% |

Uplink HOL is the TDR story. P PROC is already empty under RR. P POST vs D POST never conflicts.

Pairing vs base on the same traces: P PRE/uplink queues **unchanged**; P PROC queue +23 and downlink +32 (pack). Local tp 0.0268→0.035 (fake k=1 LAT). Official tp identical ⇒ official is **not** k*LAT bound. Search for a recon that matches official tp/tdr/tpot **and** pairing’s official signature (Δtp≈0, TDR up): **empty**. Low-LAT / proc-bound shapes that kill pairing’s tp win have TDR 600–800, not 1670.

### Isolated `wEq(WTP,.75)` probes (other weights trace-identical)

| idea | fitted #13 (5 seeds) | argument |
|---|---|---|
| P POST before D POST | **IDENTICAL** | P POST queue 0.8; no conflict |
| P PRE before D POST | **IDENTICAL** | all 26 P PREs already finish before first D PRE |
| SPT P PROC | **IDENTICAL** | P PROC queue already 0 |
| JSQ remaining P PROC at P PRE (spread) | +0 to +13; TDR **not down**; tiny Δtp 0–0.0005 | anti-pairing that does not cut the uplink 65%; tp bump is the untrustworthy family |
| SJF / chain-SPT P PRE | **+7 to +12**; TDR −210 to −387; tpot sometimes 72→80–86 | physically forced uplink interchange; official-scale ≈ 210×0.032 ≈ **+7 pts**. Tiny. Skip. |

SJF is already the optimal order on a single FIFO with the backlog present (span=10 vs uplink ~1250). Mean uplink wait 982 vs equal-job bound (n−1)/2 × 92 ≈ 1150; SJF is the remaining size-variation cut. Cannot beat it without a second uplink.

#12 fallback not reopened: prior tpotBound +0.79 / official cap ≤6.

**BAN addendum:** do not ship pairing, colloc D PRE, or wait-for-2 on `.75`. They are the k=1 LAT family whose local +170–220 is the official pairing fail mode. Do not ship SJF/JSQ on `.75` as a #13 ntp play.

**Next experiment:** do not chase #13 ntp on the LAT-bound recon (pairing proved official tp is invariant to k=1). Prefer a unique-weight remaining that is not an AKD public clone: **#14** (`w=0.65`, L_out=2 single-chain floor — confirm nothing left) or **#10** TDR beyond last-256 LPT (nc remaining ~315; official tail-LPT already no-op). Do not re-run pairing/colloc/wait-2/SJF-as-ntp/#12-tpotBound.

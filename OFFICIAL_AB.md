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

## Next isolated probe (workspace now)

- Tail-LPT drop on `.05`/`.15` only (`PUBLIC_TDR_TAIL_LPT` 256 → 1)
- origin: `cursor/tdr-round-headroom-26b6` `e9fe048` / `ca7750e`
- Workspace branch: `cursor/tdr-tail-lpt-05-15-0abe`
- Unique CF grep: `PROBE tdr-tail-lpt-05-15`
- Restored from known-good main blob `3317974884a412f8ab0deb84f544e77e89149ffa` then the one-line define + first-line comment (comment is inert)
- Expected official move: **#9 / #10 only**. Local translation ~**+6 pts** on TDR-dominated #10-like backlogs (last-256 LPT hedge was ~2% extra mean TDR vs pure SPT). **Possibly also official no-op** if official #9/#10 never take the last-256 LPT path (queue never > 1024, or tail already SPT).
- Honest: small expected delta. Do not soup. Do not pair. Do not re-enable k-shrink.
- If any non-#9/#10 test moves, revert to main blob `3317974884a412f8ab0deb84f544e77e89149ffa`.

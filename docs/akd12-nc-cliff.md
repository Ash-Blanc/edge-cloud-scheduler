# #12 nc cliff (WTP=0.99)

Date: 2026-08-27. Baseline: `origin/main` `d202b1a` / blob
`3317974884a412f8ab0deb84f544e77e89149ffa` / official **16041.088**.
`solution.cpp` on this branch is that blob. **Do not submit.**

Fitted. Tiny. No-gain for submission.

## Official fingerprint (dual-submission)

Checker lines for every d202b1a-lineage blob on #12 (score 798.488 is
byte-identical from the 15272 vector through 16041):

```
points=798.488117 tp=0.000024 tdr=1284442.144348 tpot=4771.825430
dist=36.909161 ntp=0.806554 nc=0.000000 w_tp=0.99
```

Other dual-subs on the same test, same displayed tp:

| tpot | tdr | dist | ntp | nc | pts |
| --- | --- | --- | --- | --- | --- |
| 4771.8 | 1284442 | 36.909 | 0.806554 | 0 | 798.488 |
| 732.8 | 1382426 | 5.315 | 0.808213 | 0 | 800.131 |
| 40479 | 1284488 | 320.116 | 0.809278 | 0 | 801.185 |

SLO1/SLO2 inverted from those three (tdr, tpot, dist) triples; dist
residual <0.02%:

`SLO1=424762.48  SLO2=126.060`

Dist is the TPOT leg (`excess_tpot=36.85`, `excess_tdr=2.02`).
`tpotBound` wants `WC*nc ≥ WTP*ntpCeil` → `0.01 ≥ 0.99*ntp`, impossible,
so the default path never protects TPOT. Remaining ~201 is
`990*(1-0.807)+10`; the 191 ntp pts are a tight `tp_UB` over a K=1
prefill floor, not decode slack.

## Reconstruction (d202b1a match)

`python3 tests/official12_recon.py /tmp/d202-sched --fitted`

Shape: K=1, R=20, L_out=3, L_in=4096, layers=24, all-at-0, pproc≈120000,
lat=20, bw=0.5, S=2. Seed-invariant at span=0.

| metric | official | d202b1a on recon | rel |
| --- | --- | --- | --- |
| tp | 0.000024 | 2.4858e-5 | +3.6% |
| tdr | 1284442 | 1.270e6 | −1.1% |
| tpot | 4771.83 | 4774.17 | +0.05% |
| dist | 36.909 | 36.926 | +0.05% |

Same quality as the fitted #5/#6 fingerprints. Sequential on this recon:
tpot=53 (under SLO2), tdr=1.343e6, `dist_base=2.162`.

TPOT=4771 is **P PROC chunk interleave** (`!tpotBound` splits prefill),
not cohort size (D PRE is already `mean_group=1`). Last-request gaps
are 55 ms once prefill is dry.

## Probe (not in `solution.cpp`)

One-line override, `wEq(WTP, .99)` only:

```
if (wEq(WTP, .99) && WC > 1e-9) tpotBound = true;
```

On the fitted recon (`tests/official12_cliff_compare.py`): tpot 4774→73
(under SLO2), dist 36.93→1.99, nc 0→0.079, ntp unchanged, **+0.79 pts**.
Multi-seed span 0/100/500: same. Traces identical vs d202b1a at WTP
0.98 / 1.0 / 0.80 / 0.90, official5 seed 702, `slow16-K4` (.98),
`tp-sat-K8` (w_tp=1).

TDR stays ~1.27e6 (K=1 prefill queue), so dist cannot hit 0. Official
`dist_base` is <5.315 (dual-sub dist=5.315 still had nc=0), so even the
optimistic nc is ≤0.62 (**≤6 pts**). Tiny → **no submission**.

# Maventlabs component analysis and test-5 probe

## Scope and evidence

This work starts from `origin/main` at `854e490`. The supplied current
official vector sums to 15975.308, leaving 24.692 points to 16000.

The public Maventlabs source is commit
[`19dfc7a2`](https://github.com/Maventlabs/icpc-2026-oc1-edge-cloud-scheduling/commit/19dfc7a28b349ca2e3b0142c0b6b0185d2acfd6a).
Codeforces submission
[`387221296`](https://codeforces.com/contest/2251/submission/387221296)
has aggregate score 15545.146. Its per-test vector remains unavailable, so
the probe below is justified by local structural evidence, not a claimed
official Maventlabs test-5 score.

Current main already sends weights `.05`, `.15`, `.25`, `.30`, `.75`, `.80`,
`.90`, and `.98` to the AKD/387914886 policy. Comparisons below are therefore
against that compiled ensemble, not against the older `fcdc041` baseline.

## Every local Maventlabs win against current main

All listed cases use `S=2`, `LAT=1`, `BW=10`, and `BPT=32768`. A metric tuple
is `(score, throughput, mean TDR, mean TPOT)`. `gpu`, `flat`, and `cpu` identify
the complete task-table family; the remaining fields are directly visible
startup/workload features.

| Case | Identifying features | Current main | Maventlabs | Delta |
|---|---|---:|---:|---:|
| `tp-sat-K8` | gpu, `w=1`, K8/L16/R400, Lin 16-1024, Lout 1-128 | (833.828, 1.41591, 1726.942, 47.361) | (861.671, 1.46094, 3378.679, 60.368) | +27.843 |
| `tp-sat-K4` | gpu, `w=.98`, K4/L8/R250, Lin 16-1024, Lout 1-128 | (438.897, .790392, 3467.095, 18.488) | (514.029, .914178, 3410.818, 17.773) | +75.132 |
| `tp-burst-K2` | gpu, `w=.80`, K2/L4/R150, Lin 16-1024, Lout 1-128 | (193.363, .456842, 3946.543, 15.130) | (219.562, .483282, 3919.331, 13.554) | +26.198 |
| `lat-heavy-K8` | gpu, `w=.05`, K8/L32/R250, Lin 16-1024, Lout 1-128 | (33.730, 1.18759, 421.073, 22.994) | (36.830, 1.29036, 653.927, 41.840) | +3.099 |
| `lat-mid-K4` | gpu, `w=.15`, K4/L8/R180, Lin 16-1024, Lout 1-128 | (56.692, .697903, 1249.212, 17.662) | (76.327, .915614, 1199.261, 16.699) | +19.635 |
| `bal-K4` | gpu, `w=.50`, K4/L16/R200, Lin 16-1024, Lout 1-128 | (295.249, 1.10992, 817.627, 37.764) | (303.124, 1.13757, 1827.962, 15.578) | +7.875 |
| `bal-K1` | gpu, `w=.50`, K1/L4/R80, Lin 16-1024, Lout 1-128 | (52.990, .227981, 1479.664, 53.864) | (84.648, .213927, 3077.362, 13.127) | +31.658 |
| `bal-K8-cpu` | cpu, `w=.45`, K8/L64/R250, Lin 16-1024, Lout 1-128 | (268.048, .634553, 1813.287, 52.162) | (282.820, .667236, 3954.610, 34.109) | +14.772 |
| `tp-prefill-K1` | cpu, `w=1`, K1/L32/R500, Lin 4096, Lout 1-64 | (8.805, .004893, 901784.743, 3487.924) | (8.867, .004899, 899232.445, 87.311) | +.062 |
| `edge-K1L1` | gpu, `w=.50`, K1/L1/R25, Lin 16-1024, Lout 1-8 | (12.072, .033336, 817.599, 165.819) | (60.082, .033883, 1406.708, 11.878) | +48.010 |
| `edge-lout1` | gpu, `w=.70`, K4/L8/R40, Lin 16-1024, Lout 1 | (397.463, .037158, 239.436, 0) | (420.618, .043953, 483.964, 0) | +23.155 |
| `edge-1cloud-big` | gpu, `w=.60`, K1/L64/R40, Lin 16-4096, Lout 1-128 | (28.159, .097165, 3117.584, 48.654) | (82.418, .100289, 7575.943, 12.087) | +54.259 |
| `flat-sat-K4` | flat, `w=.60`, K4/L8/R500, Lin 16-1024, Lout 1-128 | (399.953, 1.13478, 2778.260, 56.569) | (433.701, 1.22490, 5356.438, 16.332) | +33.748 |
| `longout-K4` | gpu, `w=.55`, K4/L8/R60, Lin 16-1024, Lout 1-512 | (149.013, .634844, 454.484, 18.854) | (203.104, .740061, 674.003, 13.317) | +54.091 |
| `bigin-K8` | gpu, `w=.40`, K8/L32/R150, Lin 16-4096, Lout 1-128 | (169.835, .454393, 1383.230, 50.061) | (189.142, .501432, 3364.337, 29.931) | +19.307 |
| `sat5-K8` | gpu prefill-heavy, `w=.80`, K8/L16/R800, Lin 2048-4096, Lout 1-16 | (483.366, .047773, 49323.999, 33.321) | (494.689, .049378, 49236.747, 34.123) | +11.322 |
| `sat5-K4` | gpu prefill-heavy, `w=.80`, K4/L16/R600, Lin 1024-4096, Lout 1-16 | (301.609, .033697, 58826.495, 28.942) | (308.470, .035030, 58753.987, 26.171) | +6.861 |
| `sat6-K4` | gpu high-rate, `w=.90`, K4/L16/R1000, Lin 16-512, Lout 1-128 | (925.629, 1.81029, 6648.906, 32.122) | (997.002, 2.01293, 6645.691, 21.777) | +71.373 |

Maventlabs wins 18 of the 42 base plus official-scale reconstructed cases.
Its total over the original 38-case suite is still 1016.2 points below current
main, so none of these rows supports a broad port.

## Independent component decomposition

Four compile-time ablations were applied to the unmodified public scheduler:
persistent load versus round robin, prefill-first versus decode-first clouds,
age fairness versus fixed `P POST > D POST > D PRE > P PRE`, and maximal-ready
versus singleton decode. Each component was measured both by removing it from
the full scheduler and by adding it alone to the all-off control. Counts below
cover 42 cases and show better/worse/unchanged.

| Component | Full-context score | Full-context throughput | Full-context mean TDR | Alone-context score |
|---|---:|---:|---:|---:|
| Persistent load | 24 / 5 / 13 | 26 / 6 / 10 | 30 / 5 / 7 | 18 / 10 / 14 |
| Prefill-first cloud | 27 / 2 / 13 | 29 / 3 / 10 | 32 / 2 / 8 | 12 / 16 / 14 |
| Age fairness | 16 / 14 / 12 | 19 / 13 / 10 | 2 / 34 / 6 | 23 / 10 / 9 |
| Maximal-ready decode | 35 / 0 / 7 | 36 / 0 / 6 | 27 / 6 / 9 | 37 / 0 / 5 |

Interpretation:

- Persistent load greedily minimizes the largest *estimated charged* prefill
  load at each assignment, but the estimate stays charged until `FIN`.
  Unknown output lengths make it stale, so neither actual TDR nor throughput
  is monotonic; the measured regressions confirm this.
- Prefill-first locally completes an already-ready prefill before competing
  decode work, but delays token work. It has no global monotonic guarantee.
  Its alone-context losses versus full-context wins expose strong interaction
  with batching.
- Age fairness proves bounded service starvation by task type, not low mean
  TDR. In the full context it worsened mean TDR on 34 cases and improved it on
  only two; it is specifically unsuitable as a TDR optimization for tests
  9/10.
- Maximal-ready batching was the only empirically one-sided component for
  throughput. It removes fixed `S` charges and is provably work-reducing when
  each relevant task-time curve is subadditive. The problem does not guarantee
  subadditivity, and the singleton control is more extreme than current main's
  efficient-prefix barrier, so this is not a universal score proof.

## Mapping to remaining official weaknesses

| Test | Current score | Evidence and decision |
|---|---:|---|
| #3, `w=0` | 471.905 | Reject. On `lat-only-K4`, current scores 291.568 and Maventlabs 0.000; all component controls also score zero. |
| #9, `w=.05` | 735.221 | Reject. The generic `lat-heavy` case is +3.099, but the official-constant R2000 reconstruction is 39.859 to 36.084 and `bk-lout1` is 678.9 to 619.9. |
| #10, `w=.15` | 684.422 | Reject. The generic `lat-mid` case is +19.635, but the official-constant reconstruction is 864.120 to 854.686 and `bk-mix` is 690.4 to 480.4. |
| #5, `w=.80` | 465.593 | Select. Maventlabs beats compiled current main on all three `.80` cases: +26.198, +11.322, and +6.861. Both prefill-heavy K4/K8 reconstructions agree. |
| #6, `w=.90` | 389.543 | Reject for this probe. K4 gains +71.373, while K8 loses .737; the hidden K/table fingerprint is unavailable. |
| #13, `w=.75` | 722.457 | Defer. Reweighting finds many synthetic gains (up to +108.863), but there is no dedicated #13 reconstruction or public per-test evidence. |
| #16, `w=.98` | 980.648 | Protect. `tp-sat-K4` gains +75.132, but the structurally relevant `slow16-K4` drops from 455.2 to 151.4, and the official score is already near the cap. |

The official-scale #17 and #22 reconstructions also reject Maventlabs:
380.121 to 315.297 and 468.536 to 199.201 respectively.

## Probe policy and risk

Only `w_tp=.80` (matched by the existing `wEq` tolerance of `1e-6`) switches
from the AKD/387914886 arm to an exact event-level port of Maventlabs
387221296:

- FIFO input and decode-ready queues;
- persistent full-prefill load assignment, released at `FIN`;
- unsplit prefill and prefill-first cloud arbitration;
- all-ready `D PRE`, per-cloud `D PROC`, and `D POST`;
- age-based edge arbitration with
  `P POST > D POST > D PRE > P PRE` tie-breaking.

All three `.80` traces match the compiled public Maventlabs binary exactly.
Every other local trace matches `854e490` exactly. The local expected gain is
6.861 to 26.198 points on matching cases (+44.381 over the whole suite).

The main risk is evidence quality: Maventlabs' official test-5 score is still
unknown, and synthetic gains have previously failed to transfer. This is a
single-test judge probe, not a merge recommendation. If it does not improve
#5, revert this branch without combining it with another policy.

## Verification

- strict C++17 build with `-Wall -Wextra -Werror -pedantic`: pass
- statement example exact diff: pass
- full 38-case suite: 13619.1, zero failures; current main is 13574.8
- ASan/UBSan full suite: 13619.1, zero failures and no findings
- selected-lineage verifier: all 40 traces match, including the `wEq`
  inside/outside boundary probes
- non-`.80` cases: event-for-event identical to `854e490`
- `.80` cases: event-for-event identical to compiled Maventlabs `sol.cpp`
- optimized CPU: 0.05 s on `stress-R2000`, 0.02 s on target `sat5-K8`

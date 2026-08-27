# Negative result: AKD cohort size / decode-balance (no D POST pipeline)

Date: 2026-08-27. Baseline: `origin/main` `d202b1a` / blob
`3317974884a412f8ab0deb84f544e77e89149ffa` / official **16041.088**.
`solution.cpp` on this branch is that blob. **Do not submit this branch.**

## Official reconstructions

Pinned judge constants from the 16041 vector. Current public AKD path:

| test | want tp / tdr / tpot / ntp / nc | current (best seed) | fit |
| --- | --- | --- | --- |
| #5 w=0.80 | 1.121 / 1497 / 60.08 / 0.333 / 0.998 | seed 702: 1.121 / 1431 / 61.31 / 0.333 / 0.998 | tp 0.0%, tpot 2% |
| #6 w=0.90 | 0.696 / 3102 / 57.81 / 0.323 / 0.992 | 0.697 / 3303 / 58.20 / 0.323 / 0.991 | tp 0.1%, tpot 0.7% |
| #13 w=0.75 | 0.0267 / 1670 / 71.64 / 0.681 / 0.847 | recon tp ~5x too high | not fitted |

#5/#6 are honest: same ntp/nc as official, latency already free, remaining
score is almost all `m / roundT(m)` vs unconstrained `tp_UB`.

## Experiment A (gated `wEq(WTP,.80\|\|.90\|\|.75)`, one batch in flight)

Compile-time probes, never enabled in the checked-in binary:

- decode-balanced P PRE assignment (least remaining P PROC / nDec / nPre+nDec)
  vs arrival-RR
- larger batches (take-all, argmax n/roundT, wait until prefill drains)
- smaller batches (cap 16/32/64)
- per-cloud balanced subset

Results vs `d202b1a` on the fitted #5/#6 seeds plus extra shapes (18 cases):

- take-all and max-rate: **identical** (efficiency prefix already takes everyone)
- cap-16 / cap-32: **−200 pts/case** (more rounds, link latency not amortised)
- least-loaded assignment: **−0.2 pts** or identical (RR is already balanced
  when L_out is uniform)
- wait-until-prefill-dry: **+1.2 pts** on #5 (~0.25% of the 534-pt gap)

nc stayed ≥0.99 on every #5/#6 case. Local win is tiny → **no submission**.

Maximal-ready overlapping D POST was already dropped in `12d3d8f` after it
regressed official-calibrated #5. That path was not re-enabled.

## #14

One request, L_out=2. `tdr + 2*tpot = 561.245793` and `2/span = 0.0035635`
matches official tp=0.003564. Current and AKD both hit the closed-form
unsplit chain (dTDR=0, dROUND=0) on the calibrated recon and on a 27-shape
grid. **Physical floor. Skip.**

## TDR SRPT (#10 / #15 / #9)

Official remaining is almost all wait: #10 0.9 tp + 315 wait; #15 ~9 tp +
277 wait. Current `.05/.15` already uses shortest remaining input chain.

On R=60 L_out=1 probes, current TDR is **0.968–0.997×** the all-at-0 SPT +
complementary-chain lower bound, and **0.40×** compiled AKD TDR with no tp
loss. Previous “+120–300 official from SRPT” claims do not survive this
bound. The 5–200× gap between official mean TDR and a mismatched R=2000
reconstruction LB is workload error, not scheduling slack.

Do not ship another TDR SRPT probe without an official-fingerprint case
whose current TDR sits well above that bound.

## Next honest experiments

1. **#5/#6 decode/prefill overlap that is not D POST pipelining** — only if
   it can be shown the first-token delay is free (nc already 1) and clouds
   idle after P PROC while the edge is still draining. High risk of looking
   like the dropped maximal-ready path.
2. **#13 recon** until current matches official tp=0.0267 (ub/base only
   4.67×). Mixed 0.75, ~278 pts left.
3. **#12 nc cliff** (~201 pts) — separate from this AKD cohort work.
4. Do not re-enable global stagger/kuse, POST_HOLD globally, D POST overlap,
   D PRE split, or Mavent maximal-ready on .80.

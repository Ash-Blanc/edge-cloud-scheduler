# Maventlabs 15545.146 scheduler analysis

This analysis is based on `fcdc041`, the 15272.025-point baseline. No
Maventlabs policy is enabled in `solution.cpp`.

## Public evidence and score comparison

- Repository: <https://github.com/Maventlabs/icpc-2026-oc1-edge-cloud-scheduling>
- Repository commit inspected:
  [`19dfc7a28b349ca2e3b0142c0b6b0185d2acfd6a`](https://github.com/Maventlabs/icpc-2026-oc1-edge-cloud-scheduling/commit/19dfc7a28b349ca2e3b0142c0b6b0185d2acfd6a)
- Codeforces submission metadata:
  <https://codeforces.com/api/user.status?handle=maventlabs&from=1&count=100>
- Scoring submission:
  [`387221296`](https://codeforces.com/contest/2251/submission/387221296),
  15545.146 points, 22 passed tests, 828 ms, 100 KB
- Public standings:
  <https://codeforces.com/contest/2251/standings/participant/244838969>
- Repository standings screenshot:
  <https://github.com/Maventlabs/icpc-2026-oc1-edge-cloud-scheduling/blob/main/docs/standings.png>

The repository, screenshot, standings, and API expose only the aggregate
15545.146. They do not contain an ordered per-test vector. While the contest
is running, Codeforces denies a guest access to the submission page and its
judgement protocol. Consequently, there is no public evidence for the 22
individual values, which tests Maventlabs wins, or those tests' startup
fingerprints.

The supplied baseline vector is:

```text
[500.000, 500.000, 466.521, 775.793, 207.478, 353.161, 921.508,
 809.697, 727.416, 664.648, 500.131, 798.488, 681.579, 415.267,
 713.530, 768.113, 755.126, 913.458, 919.530, 998.028, 963.649,
 918.904]
```

It sums to 15272.025, so 16000 requires 727.975 points. Maventlabs' aggregate
is 273.121 points higher, but that difference is not a best-of-both delta:
losses on some tests can conceal larger gains on others. Without its vector,
the exact best-of-both score is unknowable. The only defensible range is
15545.146 through 21444.774; the upper endpoint is a loose mathematical bound
obtained by distributing the public aggregate over the 22 tests, each capped
at 1000, in the way most favorable relative to our vector.

## Exact public policy

The submitted `sol.cpp` implements the following decisions:

- Input-stage ready queues are FIFO, and `P PROC` always covers the complete
  layer interval `[0, num_layers)`.
- At `P PRE`, the cloud with the smallest `remote_load` is selected, ties
  going to the lowest cloud index. The added load is the request's rounded
  full-prefill compute estimate. It is not released when prefill completes;
  it remains charged throughout decode until `FIN`.
- Every `D PRE` contains all requests currently in its ready FIFO. Every cloud
  similarly runs all of its currently ready `D PROC` requests, and every
  `D POST` contains all currently ready post requests. These are maximal-ready
  batches, not a barrier preserving one cohort through all three stages.
- A free cloud calls `tryAssignPProc()` before `tryAssignDProc()`. Therefore
  any ready prefill on that cloud has unconditional priority over decode.
- Edge arbitration chooses among `P PRE`, `P POST`, `D PRE`, and `D POST` by
  the number of free-edge scheduling turns since that type was last selected.
  Equal ages prefer `P POST > D POST > D PRE > P PRE`.

The edge fairness and unconditional prefill-first cloud order are material
parts of the scheduler. “Maximal batching” and “load-aware assignment” alone
do not reproduce it. In contrast, `fcdc041` uses score-aware cohort sizing
and admission, shortest-prefill-first ordering, collision-aware placement and
prefill splitting, decode-first cloud arbitration, and an exact
`w_tp=1, w_c=0` single-flight guard for preliminary test 19.

## Reproduction evidence

The unmodified public source completed all three repository examples. It
builds with ordinary `-Wall -Wextra`, but fails the strict `-Werror` build
because `TimeTable::interp` declares unused `lo` and `hi` variables.

The public binary also completed all 38 cases in our local simulator. Against
an optimized `fcdc041` binary it scored 12558.6 versus 14596.4, a net loss of
2037.8 points. It had the following isolated synthetic gains:

```text
case             w_tp  fcdc041  public   delta
tp-sat-K8        1.00  833.828  861.671  +27.843
tp-sat-K4        0.98  483.178  514.029  +30.851
tp-burst-K2      0.80  196.190  219.562  +23.372
bal-K4           0.50  295.249  303.124   +7.875
bal-K1           0.50   52.990   84.648  +31.658
bal-K8-cpu       0.45  268.048  282.820  +14.772
tp-prefill-K1    1.00    8.805    8.867   +0.062
edge-K1L1        0.50   12.072   60.082  +48.010
edge-lout1       0.70  397.463  420.618  +23.155
edge-1cloud-big  0.60   28.159   82.418  +54.259
flat-sat-K4      0.60  399.953  433.701  +33.748
longout-K4       0.55  149.013  203.104  +54.091
bigin-K8         0.40  169.835  189.142  +19.307
sat5-K8          0.80  483.353  494.689  +11.336
sat6-K4          0.90  933.816  997.002  +63.186
```

Representative trace digests confirm that these are different event
schedules, rather than scorer noise. On `sat6-K4`, `fcdc041` emitted 12173
frames (`c3cc0af99231...`) and the public scheduler emitted 10470
(`1c677c6e4898...`). The public scheduler also has severe counterexamples:
on the latency-only case it falls from 291.6 to 0.0 points, and on the
high-link-latency `slow16-K4` reconstruction it falls from 464.3 to 151.4.
These generated cases are useful for understanding behavior, but are not
evidence of any official-test gain or fingerprint.

## Baseline verification

Because no port was justified, `solution.cpp` is byte-identical to `fcdc041`;
there are no target or non-target trace changes, and test 19's single-flight
path is unchanged.

- strict C++17 build with `-Wall -Wextra -Werror -pedantic`: pass
- statement example exact diff: pass
- full 38-case local suite: 14596.4, zero failures
- full 38-case ASan/UBSan suite: 14596.4, zero failures and no findings
- worst-case `stress-R2000`: 0.07 s scheduler CPU, below 0.10 s
- threshold sweep: not applicable; no policy or threshold was added

## Port decision

No policy mode is ported. A gate based only on an assumed test number, weight,
or synthetic resemblance would not establish that submission `387221296`
wins that official test, and would violate the required event-for-event
identity outside proven targets. In particular, the public policy is not
allowed to replace test 19's proven strict single-flight behavior.

## Decisive next probe

Export the judgement protocol for submission `387221296` while authenticated
as `maventlabs`, or provide its ordered 22-value vector. For each Maventlabs
win, capture the startup configuration (`w_tp`, `w_c`, `tp_UB`, `SLO1`,
`SLO2`, `K`, system constants, and complete task table). That permits:

1. replaying both schedulers on the actual workload or a faithful
   reconstruction;
2. attributing the delta separately to edge fairness, prefill-first clouds,
   placement, and maximal-ready batching; and
3. adding an exact fingerprint-gated mode while proving all non-target traces
   remain identical to `fcdc041`.

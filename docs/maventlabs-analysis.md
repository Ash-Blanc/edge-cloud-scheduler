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

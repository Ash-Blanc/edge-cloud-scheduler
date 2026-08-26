# Maventlabs 15545.146 scheduler analysis

## Public evidence

- Repository: <https://github.com/Maventlabs/icpc-2026-oc1-edge-cloud-scheduling>
- Repository commit inspected: `19dfc7a28b349ca2e3b0142c0b6b0185d2acfd6a`
- Codeforces submission metadata:
  <https://codeforces.com/api/user.status?handle=maventlabs&from=1&count=100>
- Scoring submission: `387221296`, 15545.146 points, 828 ms, 100 KB:
  <https://codeforces.com/contest/2251/submission/387221296>
- Public standings entry:
  <https://codeforces.com/contest/2251/standings/participant/244838969>

The repository contains one aggregate standings screenshot but no per-test
results. While the contest is running, Codeforces does not expose this
submission's protocol to a guest: the submissions page emits an empty
`viewableSubmissionIds` list, `POST /data/judgeProtocol` returns the JSON empty
string, and `POST /data/submitSource` returns HTTP 403. Therefore the complete
22-test vector, winning test numbers, and their startup fingerprints cannot be
verified from public evidence.

## Exact public policy

`sol.cpp` implements:

- FIFO input-stage queues and unsplit `P PROC [0, num_layers)`.
- Cloud placement by the sum of each live request's estimated full prefill
  compute. The estimate remains charged until `FIN`, including the request's
  whole decode lifetime.
- Maximal ready `D PRE`, per-cloud `D PROC`, and `D POST` batches; it never
  deliberately accumulates a larger future cohort.
- Unconditional cloud priority for `P PROC` over `D PROC`.
- Edge arbitration by age since each of `P PRE`, `P POST`, `D PRE`, and
  `D POST` was last selected. Equal ages prefer
  `P POST > D POST > D PRE > P PRE`.

The edge fairness and unconditional prefill priority are the material
differences from `fcdc041`; maximal ready batching and load-based placement
alone do not describe the scheduler.

## Reproduction evidence

The public source completes all three repository examples. It does not pass a
strict warning build because `TimeTable::interp` declares unused `lo` and `hi`
variables.

Against the 38-case local simulator, the unmodified public binary completed
legally but scored 12558.6 versus 14596.8 for `fcdc041` (-2038.2). It had
isolated synthetic gains, but also large losses in latency-heavy and
high-link-latency regimes. These synthetic results are diagnostic only and are
not substitutes for the missing official per-test vector.

## Port decision and next probe

No policy mode was ported. Without an official winning-test list and a unique
startup fingerprint, any gate would be guessed and would violate the
event-for-event identity requirement. In particular, no Mavent behavior is
allowed to replace the proven pure-throughput single-flight policy for test 19.

The next decisive probe is to export the judgement protocol for submission
`387221296` from the submitting Codeforces account (or provide its ordered
22-value vector). For each Mavent win, also capture the startup configuration's
`w_tp`, `w_c`, `tp_UB`, `SLO1`, `SLO2`, `K`, and task table. That makes it
possible to replay the public scheduler, attribute the gain among edge
fairness, prefill-first clouds, placement, and batching, and add an exact
fingerprint-gated mode without affecting other tests.

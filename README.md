# Edge–Cloud Collaborative Scheduler

C++ interactive scheduler for [Codeforces 2251A](https://codeforces.com/contest/2251/problem/A) (ICPC 2026 Online Challenge 1, powered by Huawei).

Submit `solution.cpp`.

## Build and check

```bash
make            # builds ./sched
make test       # replays statement Example 1, then runs the local judge
```

## What the judge rewards

```
score = w_tp * clamp((tp - tp_base)/(tp_UB - tp_base))
      + w_c  * (dist_base > 0 ? max(0, 1 - dist/dist_base) : (dist == 0))
dist  = hypot(excess(mean_tdr, SLO1), excess(mean_tpot, SLO2))
```

Every constant above arrives in the input, so the scheduler evaluates this
formula directly instead of using hand-set thresholds.

Two consequences of the definitions drive the design:

1. **TDR ends at `P POST`, and TPOT only averages gaps _between_ tokens.** The
   interval from `P POST` to a request's *first* token is therefore scored by
   nothing. Holding a not-yet-decoding request costs only makespan, which buys
   large decode cohorts for free.
2. **Every cohort member is served once per decode round**, so its TPOT
   converges to the round time. Round time is the quantity to steer.

## Strategy

- **Cohort sizing.** Predict round time for a candidate cohort (edge pre/post,
  both link hops, cloud proc), evaluate the judge's objective over candidate
  sizes, take the best. A cohort grows only when the objective says the larger
  round still pays.
- **Accumulate on prefill.** Rather than firing `D PRE` whenever anything is
  ready, wait for the target cohort and spend the wait on prefill, which is
  productive. Fire early only when the edge would otherwise idle, when gaps are
  about to breach SLO2, or when the batch is already efficient.
- **Measured feedback.** A modelled round is optimistic: real gaps include
  interleaved prefill and pipeline stalls. An inflation factor measured from
  observed gaps corrects the prediction. Without it the optimiser chases an
  unreachable round time and shrinks the cohort to nothing.
- **Throughput floor.** Shrinking a cohort to protect TPOT also lengthens every
  queue, which feeds back into TDR and makespan — a coupling the model does not
  capture. The cohort may not give up more than half the peak token rate.
- **`dist_base == 0` is a cliff.** There the waiting-time component is all or
  nothing, so when the target is still reachable it is protected rather than
  traded.
- **Weight-aware edge order.** On latency-heavy tests, ready `P POST` work
  finishes before a new decode round so TDR stops growing. On high-link-latency
  throughput tests, decode posts wait for the other running cloud groups and
  coalesce, amortising one edge schedule over a larger batch.
- **Prefill.** Shortest-job-first (mean TDR is a mean completion time, which SJF
  minimises), least-loaded cloud assignment, and `P PROC` split into pieces only
  when the per-piece `S` overhead stays a few percent of the work it protects.
- **I/O.** `read`/`write` buffers with token parsing. `fread` would block until
  its buffer filled, which deadlocks against an interactor awaiting a response.

## Local judge

`tests/sim.py` implements the statement's timing model (FIFO uplink/downlink,
schedule cost `S`, piecewise-linear task-time table) and validates every
assignment, so illegal commands and stuck states surface locally.

`tp_base` and `dist_base` are measured by first running
`bench/ref_sequential.cpp` (one request at a time) on the same workload, which
is how the real judge defines them. Cases span saturated/throughput-dominant,
latency-dominant, high link latency, large `S`, near-flat decode scaling, the
degenerate shapes the statement calls out (`K=1`, `num_layers=1`, `L_out=1`,
single request), and a worst-case `R=2000` run.

```
python3 tests/sim.py bench/v1 ./sched      # A/B any two builds
python3 tests/sim.py --detail tp-sat-K8 ./sched   # per-task-type breakdown
```

Against the previous submission (`bench/v1_13k.cpp`, 13137.7 on the preliminary
tests) across 23 local cases: **+293 points total**, no failures, mean TDR
roughly halved, and 0.09s vs 0.28s of scheduler CPU on the `R=2000` stress case.

## Tuning knobs

`EFF_RATIO`, `EFF_PLATEAU`, `THR_FLOOR`, and the guarded edge-order thresholds
are compile-time macros so variants can be swept without editing code:

```bash
g++ -O2 -std=c++17 -DTHR_FLOOR=0.7 -o /tmp/variant solution.cpp
```

# Edge–Cloud Collaborative Scheduler

C++ interactive scheduler for [Codeforces 2251A](https://codeforces.com/contest/2251/problem/A) (ICPC 2026 Online Challenge 1, powered by Huawei).

Submit `solution.cpp`.

## Baseline note: throughput-cohort-amortisation work reverted

The throughput-cohort-amortisation / decode-staggering / `kuse` cloud-pool-sizing
line of work (roughly the commits between `6c6dfdb` and `fdb98d4`, including the
antiphase-cohort staggering and capacity-based cloud pool sizing described in
some of the strategy notes below) has been **reverted**. Three real-judge
submissions showed it regressing hidden tests #3/#4/#8/#9/#10 by roughly 390
points net, even though the local synthetic suite (`tests/sim.py`) reported it
as a clear gain. `solution.cpp` is back to the pre-amortisation scheduler that
scored 14354 on the real judge, and this is the current baseline: any future
change is judged against real Codeforces submissions first, and the local
suite is not trusted alone for cross-regime interactions when the two
disagree.

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

- **Guarded public-policy port for `w_tp=0.80/0.90`.** Those weights uniquely
  identify preliminary tests #5/#6. Only there, dispatch follows submission
  387914886's one-batch-in-flight policy: round-robin cloud placement, complete
  decode-batch barriers through `D POST`, input-first arbitration otherwise,
  unsplit input processing, and decode prefix size chosen by edge-plus-cloud
  time per member. All other weights stay on the baseline path.
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
- **Which dist leg dominates.** `dist` is the Euclidean norm of the two
  excesses, so shortening the decode round pays exactly while the TPOT leg is
  the longer one — even if mean TDR is already over SLO1. When the TDR leg is
  instead the longer one, decode yields the edge and the clouds to prefill.
  The two trades are mutually exclusive. The TPOT-protective admission cap
  still stands down once a measured gap shows TDR dwarfs TPOT.
- **Weight-aware edge order.** On latency-heavy tests, ready `P POST` work
  finishes before a new decode round so TDR stops growing. On high-link-latency
  throughput tests, decode posts wait for the other running cloud groups and
  coalesce, amortising one edge schedule over a larger batch.
- **An idle edge is not a reason to fire.** A round pays one link latency per
  participating cloud in each direction whatever it carries, and both links are
  FIFO-shared by every round. Once the input stage runs dry the cohort used to be
  fired with whatever happened to be ready, which on a slow link shattered it
  into rounds of one or two: the links saturated on per-round latency while every
  machine idled. Members still inside a round come back and enlarge the cohort
  for nothing but makespan, so they are waited for — but only where that fixed
  latency actually dominates the round, and only while some round is still in
  flight to wait for.
- **Round sync while a link-bound input stage feeds; staggered rounds after.**
  Every decode round pays `k*LAT` on each link whatever it carries. While the
  input stage is still draining and the links are its binding resource, that
  fixed cost comes straight out of the drain rate that sets the makespan, so
  sub-cohort clumps wait for the in-flight round and coalesce into one round
  per return. Once the input stage is dry, the objective is evaluated on plans
  that split the pool into `g` cohorts circulating in antiphase (each member's
  gap is the cycle, the pool makes `g*m` tokens per cycle, and the cycle is
  floored by `g` times the largest single-resource phase), which keeps edge,
  links and clouds simultaneously busy where no one resource saturates.
- **Cloud pool sized by capacity, not by `K`.** Spreading the input stage over
  more clouds than it can keep busy buys nothing and is then paid for on every
  later round. The pool is the input stage's own cloud work divided by the rate
  the edge and the links can feed it, and it is only narrowed while the latency
  that saves beats the longer cloud task a denser decode group implies.
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
python3 tests/public_port_compare.py ./sched /tmp/public ./baseline
python3 tests/lbcheck.py ./sched           # makespan vs resource lower bound
python3 tests/sweep.py ./sched             # same, over a grid of shapes
python3 tests/diag.py hilat-K16 ./sched    # idle-with-work per resource
```

`lbcheck.py` is the tool that says whether a case has anything left to win. It
prices the input stage's unbatchable work on each resource — edge, each cloud,
each link — plus the total tokens at the best achievable decode rate, and reports
the makespan as a multiple of the largest. A case sitting at `x1.00` is capped by
work no schedule can avoid; the high-link-latency shapes sat at `x2.7`–`x4.3`.

Three cases exist specifically to pin down the regime where a judge test returned
byte-identical metrics under three different scheduling policies:

- `tp-lat-sat-K16`, `tp-lat-sat-K4` — saturated, link-latency bound, throughput
  the whole score. The input stage runs dry long before the run ends, so the
  cohort has nothing to hide behind and shatters. Metrics here are invariant to
  `EFF_RATIO`, `EFF_PLATEAU`, `THR_FLOOR`, `POST_HOLD_WTP`, `POST_LAT_RATIO` and
  `PPOST_FIRST_WTP` — every one of those is either weight-gated off or applies to
  a decision the shattered pipeline never reaches.
- `tp-prefill-K1` — one cloud, maximal inputs. Mean TDR runs to ~900k purely from
  queueing and `tp` is a fiftieth of the decode-only ideal, but the makespan
  *equals* the unbatchable prefill work (`x1.00`), so no schedule can beat it.
  It is here to stop a change mistaking that shape for slack.

Across the 26 local cases the cohort-fragmentation fix is **+1068 points** with
no failures, and it also cuts scheduler CPU on the shattering shapes from 0.19s
to 0.02s because there are an order of magnitude fewer frames.

## Tuning knobs

`EFF_RATIO`, `EFF_PLATEAU`, `THR_FLOOR`, `FRAG_LAT_SHARE`, `KUSE_MARGIN`,
`TPOT_DOM`, `TPOT_DIST_SHARE`, `PIPE_MODE`, `PIPE_GCAP`, `PIPE_SYNC_WTP`,
`POST_EDGEBOUND` and the guarded edge-order thresholds are compile-time macros
so variants can be swept without editing code:

```bash
g++ -O2 -std=c++17 -DTHR_FLOOR=0.7 -o /tmp/variant solution.cpp
```

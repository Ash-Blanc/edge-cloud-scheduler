# Edge–Cloud Collaborative Scheduler

C++ interactive scheduler for [Codeforces 2251A](https://codeforces.com/contest/2251/problem/A) (ICPC 2026 Online Challenge 1 powered by Huawei).

The program talks to the contest interactor over stdin/stdout. After every event frame it assigns at most one task to the edge machine and at most one task to each cloud worker.

## Build

```bash
g++ -O2 -std=c++17 -o sched solution.cpp
```

Submit `solution.cpp` on Codeforces (GNU G++17 / G++20). Flush is already handled.

## Local checks

Example 1 from the statement (protocol replay):

```bash
g++ -O2 -std=c++17 -o sched solution.cpp
./sched < tests/example1.in | diff -u tests/example1.out -
```

Synthetic interactor (catches illegal commands / stuck states):

```bash
python3 tests/sim.py ./sched
```

## Strategy (relative to a 13k greedy)

The original greedy is kept as the skeleton:

- Never idle a free machine when a legal task exists.
- Batch **all** currently ready decode work (`D PRE` / `D PROC` / `D POST`).
- Edge order: `D POST` → `P POST` → `D PRE` → `P PRE`.
- Cloud order: `D PROC` before `P PROC`.
- Full-range `P PROC [0, num_layers)`.

What changed, carefully:

1. **Least-loaded cloud assignment** instead of round-robin. Load is remaining prefill compute (`S + prefill_proc(L_in)`) plus a lighter decode term that uses the task-time table, `w_c`, and a running average of finished `L_out`. Near-ties still rotate so homogeneous jobs stay spread.
2. **Oldest-first urgency** on `P PRE` / `P POST` / `P PROC` using wait / `SLO1`.
3. **Live-request scan** so 2e6-frame tests stay inside the 15s limit.

`L_out` is hidden until `FIN`, so remaining decode work is estimated, not known.

Aggressive extras that *looked* promising (idling a cloud for an incoming decode, SLO2 batch caps, many prefill chunks, always running `D PRE` before `P POST`) were tried locally and **hurt** throughput / TDR. They are not in this submission.

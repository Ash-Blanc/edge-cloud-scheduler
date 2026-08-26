# TDR scheduling policy

## Scope

The policy is gated to the exact official TDR weights:

- `w_tp=.05/.15`: retain AKD submission 387914886's one-batch decode barrier,
  unsplit P PROC, and prefill-first cloud arbitration, but replace FIFO input
  order with shortest known remaining input chain.
- `w_tp=.45`: when the measured objective is TDR-only and there are no token-gap
  observations, do not split P PROC.
- Every other weight, including protected `.00` (#7) and `.58` (#18), is
  event-for-event identical to `origin/main`.

## Scheduling invariant

For two adjacent jobs of lengths `a>b` on one non-preemptive resource, their
contribution to sum completion time is `2a+b` in order `(a,b)` and `2b+a` in
order `(b,a)`.  Swapping the inversion reduces the sum by `a-b`.  Repeating
this exchange proves SPT minimizes sum completion time when the jobs are
available together.

P PRE determines both edge order and admission order to the FIFO uplink, so
the key is the known remaining input chain

```
P_PRE(Lin) + 2*xfer(Lin) + P_PROC(Lin) + P_POST(Lin).
```

This is an exact interchange invariant for the serial-chain surrogate, not a
claim that a general four-resource flow shop is globally solved by SPT.  The
extreme-backlog guard is important: SPT is used only after a queue actually
forms.  For the last 256 requests, longest chains are dispatched first so the
shortest chain drains last; this protects makespan while confining the
sum-completion trade to the tail.

Cloud assignment follows what is knowable.  On `.05`/Lout=1, persistent queued
P PROC work is the full known cloud workload, so placement minimizes predicted
input completion.  On `.15`, Lout is hidden and mixed: round-robin keeps cloud
request counts within one, which minimizes worst-case decode imbalance and
preserves AKD's saturated throughput.

## Queue evidence

`tests/tdr_decomp.py` now separates service from queue time at P PRE, uplink,
P PROC, downlink, and P POST, and reports those queues by Lin bucket.  On the
R=2000 probes, AKD spends 99.9% of the dominant stage in queues:

- #9-like: mean TDR `265421 -> 105374`; the FIFO-uplink queue is the dominant
  reduction.
- #10-like: mean TDR `79542 -> 31904`; the edge P PRE queue is the dominant
  reduction.

Across eight seeds in `tests/tdr_policy_compare.py`, the worst throughput ratio
versus compiled AKD is `1.000019`, while mean TDR is `0.397119x`.

## Rejected experiments

- Pure SPT through the final request cut TDR slightly further (`0.388960x`) but
  lost up to `0.12%` throughput on mixed-output seeds.
- Persistent-workload placement on `.15` can balance known prefill work while
  unbalancing hidden decode work; it was rejected there.
- Mavent's FIFO/fair-age scheduler regressed the reconstructed #9/#10 TDR
  probes and was not competitive with either AKD or the candidate.
- Dedicated short/long clouds reduce head-of-line blocking but permanently
  remove capacity from one class and cannot be justified before Lout is known.
- `.00` changes were rejected because #3 and protected #7 share the exact
  weight and no safe static discriminator is known.
- `.58` changes were rejected because #18 has only about 87 points left; the
  risk/reward is poor without an exact workload.

Local aggregate score is deliberately not used as proof.  The acceptance test
is structural: lower mean TDR on each representative backlog, no throughput
loss, and trace identity outside target modes.

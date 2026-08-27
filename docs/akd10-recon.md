# #10 recon (WTP=0.15) — edge SPT floor

Date: 2026-08-27. Baseline: `origin/main` `d202b1a` / blob
`3317974884a412f8ab0deb84f544e77e89149ffa` / official **16041.088**.
`solution.cpp` on this branch is that blob. **Do not submit.**

Fitted. Isolated non-LPT levers no-gain. Official tail-LPT no-op explained.
No-ship.

## Official fingerprints

```
#10 points=684.426 tp=0.007628 tdr=182521.13 tpot=86.987
    dist=143.983 ntp=0.9943 nc=0.6298 w_tp=0.15
    SLO1=1258.9 SLO2=64.85 tp_base=0.0028312 tp_UB=0.0076595
    dist_base=389.0
```

Remaining ~316 is almost all wait (`0.85*(1-0.630)*1000 ≈ 315`). Dual-sub
ntp already 0.994. Last-256 LPT official no-op ⇒ not a long heterogeneous
LPT tail.

## Reconstruction (`d202b1a` match)

`python3 tests/official10_recon.py /tmp/d202-sched`

Homogeneous `Lin=128`, mixed `L_out∈{1,2}`, `K=2`, `R=2000`, `lat=1`,
`bw=10`, `S=2`, P PRE pinned to 180 at the used size, decode scaled so
TPOT≈87:

| metric | official | d202b1a seed 1009 | rel |
| --- | --- | --- | --- |
| tp | 0.007628 | 0.007862 | +3.1% |
| tdr | 182521 | 189554 | +3.9% |
| tpot | 86.987 | 85.737 | −1.4% |

Seeds 1009/1010/1011 stay inside 4% on all three. Prefill-first + one-batch
decode: last TDR ≈ makespan, so ntp is prefill-taxed on the recon (clamps to
1.0 vs official 0.994). Shape still matches the dual-sub “wait, not tp”
signature.

Earlier R=2000 mixed-length probes (TDR ~32k, tp ~0.13) were the wrong
shape. They are why tail-LPT looked like a +6pt idea and then official
no-op’d.

## Honest mean-completion floor

TDR decomposition on the fitted recon: **99.9% P PRE queue**. Uplink / P PROC
/ downlink queues are 0. P POST queue is ~168 of 189k.

Single-resource bound: the edge exclusively runs P PRE and P POST, so SPT
mean of `(S+P_PRE)+(S+P_POST)` is a hard floor.

| recon | TDR | edge_spt | TDR/LB | slack |
| --- | --- | --- | --- | --- |
| fitted identical-Lin | 189554 | 189375 | **1.0009** | **0.09%** |
| mixed Lin 256/512 | 179663 | 179474 | **1.0011** | **0.11%** |

0.09% of 182k TDR is ~170 units. Sensitivity `d(pts)/d(TDR) ≈
1000*0.85/(389*1258.9) ≈ −0.00173` ⇒ **<0.3 pts** even if the slack were
real. SPT is already optimal on that one machine. Cannot beat it without a
second edge.

## Why official last-256 LPT was a no-op

SPT drains shorts first. The last 256 are a homogeneous long tail
(identical Lin, or the long half of a two-point mix). LPT among equals does
not change TDR. Confirmed: `PUBLIC_TDR_TAIL_LPT=1` vs 256 is TDR-identical
on both fitted shapes. BAN last-N LPT stands.

## Isolated `wEq(WTP,.15)` levers (not last-N LPT)

| idea | fitted identical-Lin | mixed 256/512 | other weights |
| --- | --- | --- | --- |
| JSQ remaining P PROC (enable .15) | IDENTICAL | IDENTICAL | `.75/.80/.90/.30/.98/.99/1/#3/#17/#22` IDENTICAL |
| chain key = P PRE+P POST (drop xfer+P PROC) | IDENTICAL | IDENTICAL | — |
| tail-LPT off | TDR identical (tiny tpot from rid order) | TDR identical | — |

JSQ cannot help: P PROC queue is already 0. Reweighting the chain key cannot
help: every component is monotone in Lin, so the order is the same.

**No submission.** Next leftover that is not this floor: **#8** (`w=0.25`,
remaining ~167, already fitted; k-shrink banned). Do **not** chase **#9**
(`w=0.05`): same `publicTdrMode`, same single-resource SPT floor (edge or
uplink). Closed: #4/#5/#6/#12/#13-ntp/#14/#15/#17/#18 and this #10.

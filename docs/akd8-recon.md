# #8 recon (WTP=0.25) — uplink SPT floor

Date: 2026-08-27. Baseline: `origin/main` `d202b1a` / blob
`3317974884a412f8ab0deb84f544e77e89149ffa` / official **16041.088**.
`solution.cpp` on this branch is that blob. **Do not submit.**

Fitted. Isolated non-banned `.25` levers no-gain or tiny. TDR is an
uplink-SPT floor (P PROC queue already 0). No-ship.

## Official fingerprints

```
#8 points=833.386 tp=0.013238 tdr=1087.155 tpot=98.803
    dist=1.568 ntp=0.766 nc=0.856 w_tp=0.25
    SLO1=423.3 SLO2=97.5 tp_base=0.002987 tp_UB=0.016373
    dist_base=10.885
```

Remaining ~167 = 59 ntp + 108 nc. Dist is the TDR excess
(`(1087-423.3)/423.3 ≈ 1.568`); TPOT sits on SLO2.

## Reconstruction (`d202b1a` match)

`python3 tests/official8_recon.py /tmp/d202-sched`

From `tests/official48_recon.py` `fitted8`: K=4, R=18 all-at-0, `L_out=2`,
lat=14, bw=1.5, dproc=9, pproc=15, `Lin∈{256,512,1024}`:

| metric | official | d202b1a seed 38 | rel |
| --- | --- | --- | --- |
| tp | 0.013238 | 0.013186 | −0.4% |
| tdr | 1087.155 | 1092.4 | +0.5% |
| tpot | 98.803 | 97.70 | −1.1% |

Sum relative error 2.0%. Seeds 39/48/58/68 move Lin mix and leave the
1% box; the floor (TDR/SPT) stays 1.0007 on every seed.

## Honest TDR floor

Decomposition on seed 38:

| stage | mean | queue | q% |
| --- | --- | --- | --- |
| P PRE | 64.8 | 56.2 | 87% |
| **uplink** | **831.1** | **707.8** | **85% of stage, 76% of TDR** |
| P PROC | 67.1 | **0.0** | 0% |
| downlink | 124.2 | 0.8 | 1% |
| P POST | 5.3 | 0.0 | 0% |

P PROC is already empty under RR. The TDR story is a single FIFO uplink
with P PRE releasing jobs into it. SPT on that chain (P PRE then uplink
in increasing xfer order, then unqueued P PROC+down+P POST):

```
TDR / uplink-SPT = 1.0007   (0.07% slack)
```

0.07% of 1087 TDR is <1 unit. Sensitivity
`d(pts)/d(TDR) ≈ 750/(10.885*423.3) ≈ −0.163` ⇒ **<0.2 pts**.
Cannot beat a single uplink without a second link. Previous SJF/JSQ=0
is this floor, not a missed order bug.

Makespan 2730 vs uplink-prefill work 2220 (`x1.23`). The extra is
decode after input (4× D PRE mean-9). `need=1/4`: LAT-bound decode tail,
same family as official-no-op k-shrink.

## Isolated `wEq(WTP,.25)` levers (not k-shrink / pair-2 / SJF / JSQ)

Gate proved: retarget `.05/.15/.30/.75/.80/.90/.98/.99/1` plus
official5 / sat5 / sat6 / #3 / #17 / #22 / historical22 **IDENTICAL**.
Default flags-off binary is trace-identical to `d202b1a`.

| idea | fitted #8 (seed 38) | other seeds / shapes |
| --- | --- | --- |
| P PROC SPT | IDENTICAL | IDENTICAL |
| full ready D PRE (no efficiency prefix) | IDENTICAL | IDENTICAL |
| D PRE while ARR remains (interleave) | IDENTICAL | IDENTICAL or +0.00 |
| throughput-max prefix | **−25** tdr held | −14 to −35 |
| wait-all-prefill before first D PRE | **+2.2** tiny; tpot 97.7→91.5 | +1.7 to +3.5 |

Wait-all is tiny and **worsens** the official tpot match (98.8). It is
the LAT-bound decode-after-input family whose k-shrink +5 was already
not shipped and whose `.30/.80/.90` cousins official-no-op'd. Do not
ship. Do not official-A/B.

**No submission.** #8 TDR is a floor; ntp remaining ~59 is the banned
k-shrink/decode-tail family. 16.5k is not reachable from #8.

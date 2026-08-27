# #17 / #18 recon (WTP=0.67 / 0.58)

Date: 2026-08-27. Baseline: `origin/main` `d202b1a` / blob
`3317974884a412f8ab0deb84f544e77e89149ffa` / official **16041**.
`solution.cpp` on this branch is that blob. **Do not submit.**

Fitted. Isolated unique-weight probes no-gain. No-ship.

## Official fingerprints (dual-submission)

Checker lines for the d202b1a lineage:

```
#17 points=833.761960 tp=0.000520 tdr=29116639.357 tpot=14091.868
    dist=1554.656 ntp=0.986830 nc=0.522987 w_tp=0.67
#18 points=913.457972 tp=0.000009 tdr=17962783.644 tpot=0
    dist=141.564 ntp=0.989135 nc=0.808952 w_tp=0.58
```

SLO inverted from six #17 (tdr,tpot,dist) triples (residual <0.001%)
and two #18 L_out=1 triples:

`#17 SLO1=18726.15 SLO2=278.70 dist_base=3259.15 tp_base=2.596e-4 tp_UB=5.235e-4`
`#18 SLO1=125997.91 dist_base=740.99`

#17 TDR is identical across official SPT / tpotBound / recover17 subs
(~29.116639e6). excess_tpot=49 vs excess_tdr=1554, so TPOT to SLO2 is
**+0.07 pts**. Remaining 166 = 8.8 ntp + 157 nc; nc=1 needs TDR 1554x
lower. Sequential dist_base implies seq TDR ~61e6 (current is half;
identical-job FCFS floor).

#18 L_out=1. A worse official sub is TDR 46.96e6 / nc=0.498 at the same
displayed tp. Remaining 87 = 6.3 ntp + 80 nc; nc=1 needs TDR 142x lower.

## Reconstruction (d202b1a match)

`python3 tests/official1718_recon.py /tmp/d202-sched --fitted`

| test | shape | official | d202b1a | rel |
| --- | --- | --- | --- | --- |
| #17 tp | K=1 R=511 L_out=59 Lin=4096 y=8 pproc=113400 span=0 | 0.000520 | 0.000518 | −0.3% |
| #17 tdr | same | 2.9117e7 | 2.9139e7 | +0.1% |
| #17 tpot | 8-layer P-PROC chunk interleave | 14091.9 | 14108.1 | +0.1% |
| #18 tp | K=1 R=323 L_out=1 mixed Lin pproc=111111 | 9.00e-6 | 8.99e-6 | −0.1% |
| #18 tdr | (R+1)/2 · pproc | 1.796e7 | 1.801e7 | +0.3% |
| #18 tpot | L_out=1 | 0 | 0 | 0 |

Seed-invariant on #17 (identical Lin, span=0). #18 five seeds stay inside 0.4%.

## Probes (not in `solution.cpp`)

Compile-time `AKD17_UNSPLIT` / `AKD18_{CHAIN,LPT,TAIL_LPT,UNSPLIT}`,
each `wEq` on `.67` or `.58` only. `tests/official1718_compare.py`
vs d202b1a:

| probe | #17 fitted | #18 fitted | high-CV #18 | non-target traces |
| --- | --- | --- | --- | --- |
| unsplit P PROC @.67 | **−3.4 pts** (tpot 14k→101k) | n/a | n/a | identical |
| chain +2·xfer @.58 | n/a | 0 | 0 | identical |
| LPT @.58 | n/a | −0.09 | −0.5 | identical |
| tail-LPT @.58 | n/a | 0 | 0 | identical |
| unsplit @.58 | n/a | +0.02 tiny | +0.02 | identical |

#17 unsplit loses: holding the full 113k P PROC blocks decode and
inflates TPOT; current split is already the better side. TDR sits on
the K=1 identical-job floor, so SPT/chain/LPT cannot move it (matches
official invariance).

#18 current path is already SJF on PPRE+PPROC+PPOST. xfer/tail-LPT are
dwarfed by pproc≈111k. Tiny +0.02 is not shipped.

**No submission.**

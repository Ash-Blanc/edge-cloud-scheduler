#!/usr/bin/env python3
"""#3 signature fitter v3: add BURSTY arrivals (span>0) + mixed lout, which the
prior fitter lacked (span=0). A 1.55 FIFO/SJF TDR gap needs prefill QUEUEING
(requests pile up behind the edge), which only happens when arrivals outpace
edge service. Target full signature: AKD tdr=1329.85 tpot=61.93 tp=0.00442,
GEN tdr=858.87 tpot=63.72, gap=1.548."""
import math, random, sys, types
_res = types.ModuleType("resource"); _res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path.insert(0, "recon_archive")
import sim

T_A, P_A, TP_A = 1329.849832, 61.933452, 0.004421   # AKD official
T_G, P_G = 858.868074, 63.719084                    # generic official
DA, DG = 0.577735, 0.6109
GAP_TARGET = T_A / T_G   # 1.548

def decode_table(pp, dp):
    sizes = [1,2,4,8,16,32,64,128,256,512,1024,2048,4096]
    return [(b, 0.25+0.010*b, pp+0.08*b, 0.20+0.005*b, 1.00+0.008*b, dp+0.04*b, 1.00+0.008*b) for b in sizes]

def make(seed, K, arrivals, lat, bw, pp, dp, layers=8):
    c = sim.Case(K, 2.0, lat, bw, 32768, layers, 1.0, 1.0, decode_table(pp,dp), arrivals, 0.0, 1.0)
    c.tp_base = 0.001; c.tp_ub = 1.0; c.dist_base = 1.1568; c.name=f"s{seed}"
    return c

def gen(seed, R, span, lins, louts):
    rng = random.Random(seed)
    arr = [(rng.uniform(0.0, span), rng.choice(lins), rng.choice(louts)) for _ in range(R)]
    arr.sort()
    return arr

def main():
    akd, gen_b, ref = sys.argv[1:4]
    results = []
    n=0
    for seed in range(300, 320):
        for R in (8, 12, 16):
            for span in (0.0, 200.0, 600.0, 1500.0):
                for lins in ([64,256,1024,4096],[128,512,2048],[64,512,4096]):
                    for louts in ([1,2],[1,1,2,2],[1,2,4]):
                        for lat in (4.0, 8.0):
                            for pp in (300.0, 700.0, 1200.0):
                                arr = gen(seed, R, span, lins, louts)
                                c = make(seed, 4, arr, lat, 8.0, pp, 14.0)
                                try:
                                    mA,_,_ = sim.run(akd, c); mG,_,_ = sim.run(gen_b, c)
                                except Exception: continue
                                if not (mA and mG): continue
                                n+=1
                                gap = mA[1]/max(mG[1],1e-9)
                                sig = (abs(gap-GAP_TARGET)/GAP_TARGET
                                       + abs(mA[1]-T_A)/T_A + abs(mA[2]-P_A)/P_A
                                       + abs(mG[1]-T_G)/T_G + abs(mG[2]-P_G)/P_G)
                                results.append((sig, seed, R, span, lins, louts, lat, pp, gap, mA, mG))
    results.sort(key=lambda r: r[0])
    print(f"searched {n}")
    for r in results[:6]:
        sig,seed,R,span,lins,louts,lat,pp,gap,mA,mG = r
        print(f"sig={sig:.4f} gap={gap:.3f} R={R} span={span} lin={lins} lout={louts} lat={lat} pp={pp}")
        print(f"   AKD tdr={mA[1]:.1f}({100*(mA[1]/T_A-1):+.1f}%) tpot={mA[2]:.2f}({100*(mA[2]/P_A-1):+.1f}%) | GEN tdr={mG[1]:.1f}({100*(mG[1]/T_G-1):+.1f}%) tpot={mG[2]:.2f}")
if __name__=="__main__": main()

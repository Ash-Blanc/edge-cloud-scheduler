import sys, types
_res = types.ModuleType("resource"); _res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path[:0] = ["tests", "tests/recon_archive"]
import sim
from akd56_16063_ab import honest5, honest6, pin_official_constants
bins = [
    ("base", r"C:\Users\hp\AppData\Local\Temp\ecs-bin\sol16125.exe"),
    ("wave2", r"C:\Users\hp\AppData\Local\Temp\ecs-bin\push168k.exe"),
    ("early", r"C:\Users\hp\AppData\Local\Temp\ecs-bin\pipe_early.exe"),
]
for label, case in [("#5", pin_official_constants(honest5(), 5)),
                    ("#6", pin_official_constants(honest6(), 6))]:
    print("===", label, "===")
    for name, b in bins:
        m, _, _ = sim.run(b, case)
        pts, ntp, nc, _ = sim.score(case, m)
        print(f"  {name:<6} pts={pts:7.2f} tp={m[0]:.5f} tdr={m[1]:.1f} tpot={m[2]:.3f} ntp={ntp:.4f} nc={nc:.4f}")

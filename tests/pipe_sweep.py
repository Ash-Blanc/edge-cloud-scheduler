#!/usr/bin/env python3
import os, sys, types, subprocess
_res = types.ModuleType("resource")
_res.RUSAGE_CHILDREN = 0
_res.getrusage = lambda who: types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0)
sys.modules["resource"] = _res
sys.path[:0] = ["tests", "tests/recon_archive"]
import sim
from akd56_16063_ab import honest5, honest6, pin_official_constants, retarget

OFFICIAL = 16125.629
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\solution.cpp"
BIN = r"C:\Users\hp\AppData\Local\Temp\ecs-bin"
BASE = os.path.join(BIN, "sol16125.exe")
WIN = os.path.join(BIN, "push168k.exe")

VARIANTS = [
    ("def", []),
    ("cap4", ["PIPE_CAP=4"]),
    ("post3", ["POST_DEN=3"]),
    ("post1", ["POST_DEN=1"]),
    ("mr80", ["MAXREADY_80=1"]),
    ("nocap", ["DROP_CAP80=1"]),
    ("cap4mr80", ["PIPE_CAP=4", "MAXREADY_80=1"]),
    ("allin", ["PIPE_CAP=4", "POST_DEN=3", "MAXREADY_80=1", "DROP_CAP80=1"]),
    ("post1cap4", ["PIPE_CAP=4", "POST_DEN=1", "MAXREADY_80=1"]),
]

def build(name, defs):
    out = os.path.join(BIN, f"sw_{name}.exe")
    cmd = ["g++", "-O2", "-std=c++17", "-o", out, SRC] + [f"-D{d}" for d in defs]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(name, "FAIL", r.stderr[-300:])
        return None
    return out

def ev(b, c):
    m, _, _ = sim.run(b, c)
    pts, ntp, nc, _ = sim.score(c, m)
    return pts, ntp, nc, m

def main():
    h5 = pin_official_constants(honest5(), 5)
    h6 = pin_official_constants(honest6(), 6)
    anchors = [("16125", BASE), ("pipe2", WIN)]
    print(f"{'var':<12} {'#5':>8} {'d5':>7} {'#6':>8} {'d6':>7} {'vs16125':>9} {'vsPipe':>8}")
    ref = {}
    for name, path in anchors:
        p5, _, _, m5 = ev(path, h5)
        p6, _, _, m6 = ev(path, h6)
        ref[name] = (p5, p6)
        exp = OFFICIAL + (p5 - ref.get("16125", (p5, p6))[0]) + (p6 - ref.get("16125", (p5, p6))[1]) if name != "16125" else OFFICIAL
        if name == "16125":
            print(f"{name:<12} {p5:8.2f} {0:7.2f} {p6:8.2f} {0:7.2f} {OFFICIAL:9.1f} {'':>8}")
        else:
            d5 = p5 - ref["16125"][0]
            d6 = p6 - ref["16125"][1]
            print(f"{name:<12} {p5:8.2f} {d5:+7.2f} {p6:8.2f} {d6:+7.2f} {OFFICIAL+d5+d6:9.1f} {'':>8}")
    r5, r6 = ref["16125"]
    p5w, p6w = ref["pipe2"]
    best_exp, best_name = OFFICIAL, "16125"
    for name, defs in VARIANTS:
        path = build(name, defs)
        if not path:
            continue
        p5, _, _, m5 = ev(path, h5)
        p6, _, _, m6 = ev(path, h6)
        d5, d6 = p5 - r5, p6 - r6
        exp = OFFICIAL + d5 + d6
        vs = (p5 - p5w) + (p6 - p6w)
        print(f"{name:<12} {p5:8.2f} {d5:+7.2f} {p6:8.2f} {d6:+7.2f} {exp:9.1f} {vs:+8.2f}  tp6={m6[0]:.4f} tpot6={m6[2]:.2f}")
        if exp > best_exp:
            best_exp, best_name = exp, name
        # cheap collateral on .00/.75
        for w in (0.0, 0.75):
            c = retarget(h5, w)
            pb, _, _, _ = ev(BASE, c)
            pc, _, _, _ = ev(path, c)
            if abs(pc - pb) > 0.2:
                print(f"   COLLATERAL {name} w={w} d={pc-pb:+.2f}")
    print(f"\nBEST expected {best_name} {best_exp:.1f}")

if __name__ == "__main__":
    main()

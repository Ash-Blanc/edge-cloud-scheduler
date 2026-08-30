#!/usr/bin/env python3
import re, subprocess, os, hashlib
SRC = r"C:\Users\hp\src\edge-cloud-scheduler\candidate_max.cpp"
OUT = r"C:\Users\hp\src\edge-cloud-scheduler"
BIN = os.path.expandvars(r"%LOCALAPPDATA%\Temp\ecs-bin")
src = open(SRC, encoding="utf-8").read()
# Replace the exact line with a safe insertion
pat = re.compile(r'const bool publicTdrMode = wEq\(WTP, \.05\) \|\| wEq\(WTP, \.15\) \|\| wEq\(WTP, \.25\) \|\| wEq\(WTP, \.30\) \|\| wEq\(WTP, \.45\);')
new_line = "    const bool publicTdrMode = wEq(WTP, .05) || wEq(WTP, .15) || wEq(WTP, .25) || wEq(WTP, .30) || wEq(WTP, .45) || wEq(WTP, 0.0);"
src2 = pat.sub(new_line, src, count=1)
p = os.path.join(OUT, "v3_edgebatch.cpp")
open(p, "w", encoding="utf-8").write(src2)
exe = os.path.join(BIN, "v3_edgebatch.exe")
r = subprocess.run(["g++","-O2","-std=c++17","-o",exe,p], capture_output=True, text=True)
print("build:", "OK" if r.returncode==0 else f"FAIL {r.stderr[-400:]}", "hash", hashlib.sha256(src2.encode()).hexdigest()[:12])

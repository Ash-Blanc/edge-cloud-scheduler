***
# Codeforces Contest 2251 — Problem A: Interactive Scheduling
**Topic:** Interactive · Scheduling · Pipeline Optimization  
**Time Limit:** 3.0s | **Memory Limit:** 256 MB

## 1. The Problem in One Minute
This is an **interactive scheduling problem**. You control one local computer (`E`) and $K$ identical remote computers (`C0` to `C_{K-1}`). Requests arrive over time. Each request must go through an **Input Stage** (once) and then repeat an **Output Stage** $L_{out}[i]$ times to produce tokens. 

You must assign legal tasks to free machines as events happen. Your score rewards high output rate (throughput) and low waiting times (latency).

---

## 2. The Pipeline Model
Every request follows a strict `local → remote → local` trip for both stages.

### The Input Stage (Prefill - Happens ONCE per request)
1. **`P PRE`** (Local `E`): Packs data, assigns a remote computer.
2. **`↑ UP Transfer`**: Sends data to the remote.
3. **`P PROC`** (Remote `Cx`): Processes the input layers. (Can be split into chunks).
4. **`↓ DOWN Transfer`**: Sends result back to local.
5. **`P POST`** (Local `E`): Unpacks. The request is now **Decode Ready**.

### The Output Stage (Decode - Repeats $L_{out}[i]$ times)
1. **`D PRE`** (Local `E`): Packs data for the next token. (Can be batched across multiple requests and remotes!)
2. **`↑ UP Transfer`**: Sends data to remotes.
3. **`D PROC`** (Remote `Cx`): Generates the token.
4. **`↓ DOWN Transfer`**: Sends result back to local.
5. **`D POST`** (Local `E`): Unpacks. **Emits 1 token per request in the batch.**

---

## 3. System Model & Constraints
- **Machines:** 1 Local (`E`), $K$ Remotes (`C0`...`C7`). $1 \le K \le 8$.
- **Requests:** $R$ total requests ($R \le 2000$, but $R$ is **hidden**).
- **Sizes:** $L_{in}[i] \le 4096$ (Input tokens). $L_{out}[i] \le 512$ (Output tokens, **hidden** until `FIN`).
- **Schedule Cost ($S$):** Every task started on a machine incurs a fixed overhead $S$ ($1 \le S \le 10$ ms). A task with duration $dur$ occupies the machine for $[t, t + S + dur]$. **Transfers do not pay $S$.**
- **Concurrency:** A machine executes at most one task at a time. Transfers happen automatically in the background and do not occupy machines.
- **Batches:** Output tasks (`D PRE`, `D PROC`, `D POST`) can group multiple requests. `D PRE`/`D POST` run on `E` and can mix remotes. `D PROC` runs on `Cx` and must only contain requests assigned to `Cx`.

---

## 4. The Protocol (Input & Output)

### Phase 1: Startup Configuration (Read-only)
The judge sends two lines of parameters, then $N$ rows for the Task-Time Table.
```text
K S latency_in_ms bandwidth_gbps bytes_per_token num_layers
SLO1 SLO2 tp_UB tp_base dist_base w_tp w_c
N
batch_size prefill_pre prefill_proc prefill_post decode_pre decode_proc decode_post
... (N rows)
```
*Note: The Task-Time Table gives execution durations (excluding $S$). If a batch size is not listed, linearly interpolate between the nearest listed sizes.*

### Phase 2: The Interactive Loop
The judge sends **Frames**. A frame contains a timestamp, an event count, and the events. You must reply with tasks to start.
```text
[Judge sends timestamp, e.g., 14.500000000]
[Judge sends event count, e.g., 2]
[Judge sends Event 1]
[Judge sends Event 2]

[You reply with number of tasks to start, e.g., 1]
[You reply with Task 1, e.g., E D PRE -1 2 0 1]
[You MUST flush stdout]
```

#### Events you will receive:
- `ARR <rid> <Lin>`: Request `rid` arrives.
- `TDN <server> <task_spec> <dur>`: Task finished. Machine is now free.
- `XDN <UP|DOWN> <remote> <size> <PRE|DEC> <m> <rids...>`: Transfer finished.
- `FIN <rid>`: Request finished all output steps.
- `END`: All requests finished. Exit your program.

#### Legal Commands you can output:
| Command | Server | Description |
| :--- | :--- | :--- |
| `P PRE <remote> <rid>` | E | Start input stage, lock to `<remote>` (0-indexed). |
| `P PROC <ls> <le> <remote> <rid>` | Cx | Process layers `[ls, le)` on remote. |
| `P POST <remote> <rid>` | E | Finish input stage. |
| `D PRE -1 <m> <rids...>` | E | Batch `m` requests for output step. |
| `D PROC <remote> <m> <rids...>` | Cx | Batch `m` requests on specific remote. |
| `D POST -1 <m> <rids...>` | E | Finish output step, emit tokens. |

---

## 5. The Scoring Mathematics
The score is in $[0, 1000]$, calculated from two components based on your run statistics.

**1. Output Rate Component (Throughput):**
$$tp = \frac{\sum L_{out}[i]}{\text{latest final token time} - \text{earliest arrival time}} \quad \text{[tokens/ms]}$$
$$\text{Rate Score} = \text{clamp}(tp; \ tp_{base}, \ tp_{UB})$$

**2. Waiting Time Component (Latency):**
- **TDR (Time to Decode Ready):** Mean time from arrival to `P POST` completion.
- **TPOT (Time Per Output Token):** Mean gap between consecutive tokens for the same request.
$$excess_{tdr} = \max(0, \text{TDR} - \text{SLO1})$$
$$excess_{tpot} = \max(0, \text{TPOT} - \text{SLO2})$$
$$dist = \sqrt{excess_{tdr}^2 + excess_{tpot}^2}$$
$$\text{Wait Score} = \text{clamp}(dist; \ dist_{base}, \ 0)$$

**Final Score:**
$$\text{Score} = 1000 \times \Big( w_{tp} \times \text{Rate Score} + w_{c} \times \text{Wait Score} \Big)$$
*(Where $\text{clamp}(x; \text{base}, \text{target}) = \max(0, \min(1, \frac{x - \text{base}}{\text{target} - \text{base}}))$)*

**Transfer Time Formula:**
$$\text{Transfer Time} = \text{latency} + \frac{8 \times \text{len} \times \text{bytes\_per\_token}}{\text{bandwidth\_gbps} \times 10^6} \quad \text{[ms]}$$

---

## 6. Sample Test Cases

### Example 1: Single Request Lifecycle (K=1)
**Parameters:** $S=1$, Latency=$2$, Bandwidth=$1$ Gbps, Bytes/Token=$125,000$.
**Input Timeline:**
```text
0.000  ARR 0 4           -> You reply: E P PRE 0 0
4.000  TDN E P PRE ...   -> (Wait for UP transfer: 2 + 4 = 6ms)
10.000 XDN UP 0 ...      -> You reply: C0 P PROC 0 4 0 0
21.000 TDN C0 P PROC ... -> (Wait for DOWN transfer: 6ms)
27.000 XDN DOWN 0 ...    -> You reply: E P POST 0 0
30.000 TDN E P POST ...  -> You reply: E D PRE -1 1 0
32.000 TDN E D PRE ...   -> (Wait for UP: 2 + 1 = 3ms)
35.000 XDN UP 0 ...      -> You reply: C0 D PROC 0 1 0
40.000 TDN C0 D PROC ... -> (Wait for DOWN: 3ms)
43.000 XDN DOWN 0 ...    -> You reply: E D POST -1 1 0
45.000 TDN E D POST + FIN 0 -> Token produced! Request done.
```

### Example 2: Batching Across Remotes
Requests `0` (on `C0`) and `1` (on `C1`) are both Decode Ready.
Instead of doing them separately, you batch them on the Local machine:
```text
You reply: E D PRE -1 2 0 1
```
This triggers **two separate UP transfers** (one to C0, one to C1, in index order). Later, you can batch them again on the local machine for `D POST`:
```text
You reply: E D POST -1 2 0 1
```
*Result: You paid the $S$ overhead only once, and saved local machine compute time, while still correctly routing data to their respective remotes.*

---
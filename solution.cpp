// Edge-Cloud Collaborative Scheduling -- Codeforces 2251A (ICPC 2026 / Huawei).
//
// Scoring drives every decision here, so the shape of the objective matters:
//   score = w_tp * clamp((tp - tp_base)/(tp_UB - tp_base))
//         + w_c  * (dist_base > 0 ? max(0, 1 - dist/dist_base) : (dist == 0))
//   dist  = hypot(excess(mean_tdr, SLO1), excess(mean_tpot, SLO2))
//
// Two facts follow from the definitions and shape the whole scheduler:
//
//   * TDR ends at P POST and TPOT only averages gaps *between* tokens, so the
//     interval from P POST to a request's first token is scored by nothing.
//     Holding a not-yet-decoding request costs only makespan, which lets us
//     assemble large decode cohorts for free.
//   * Every request in a cohort is served once per decode round, so its TPOT is
//     the round time. Round time is what we steer: pick the cohort size whose
//     predicted round maximizes the real objective above.
//
// Everything else (SJF prefill, prefill chunking, edge arbitration) follows from
// pushing on whichever of the two excesses currently dominates dist.

#include <bits/stdc++.h>
#include <unistd.h>
using namespace std;

// ---------------------------------------------------------------- fast io
// read()/write() directly: fread would block until the buffer fills, which
// deadlocks against an interactor waiting on our response.
namespace io {
static char ib[1 << 16];
static int ip = 0, il = 0;
static inline int gc() {
    if (ip == il) {
        il = (int)::read(0, ib, sizeof(ib));
        ip = 0;
        if (il <= 0) return -1;
    }
    return (unsigned char)ib[ip++];
}
static char tok[64];
static inline int rtok() {
    int c = gc();
    while (c == ' ' || c == '\n' || c == '\r' || c == '\t') c = gc();
    if (c < 0) return 0;
    int n = 0;
    while (c > ' ') {
        if (n < 63) tok[n++] = (char)c;
        c = gc();
    }
    tok[n] = 0;
    return n;
}
static inline bool rint(long long& v) {
    if (!rtok()) return false;
    v = strtoll(tok, nullptr, 10);
    return true;
}
static inline bool rdbl(double& v) {
    if (!rtok()) return false;
    v = strtod(tok, nullptr);
    return true;
}
static char ob[1 << 16];
static int op = 0;
static inline void oflush() {
    if (op) {
        ssize_t r = ::write(1, ob, op);
        (void)r;
        op = 0;
    }
}
static inline void oc(char c) {
    if (op == (int)sizeof(ob)) oflush();
    ob[op++] = c;
}
static inline void os(const char* s) {
    while (*s) oc(*s++);
}
static inline void osn(const char* p, size_t n) {
    for (size_t i = 0; i < n; ++i) oc(p[i]);
}
static inline void oi(long long v) {
    char t[24];
    int n = 0;
    if (v < 0) {
        oc('-');
        v = -v;
    }
    do {
        t[n++] = (char)('0' + (int)(v % 10));
        v /= 10;
    } while (v);
    while (n) oc(t[--n]);
}
}  // namespace io

// Assignments are buffered because the response must lead with its count.
static string ANS;
static inline void as(const char* s) { ANS += s; }
static inline void ai(long long v) {
    char t[24];
    int n = 0;
    if (v < 0) {
        ANS += '-';
        v = -v;
    }
    do {
        t[n++] = (char)('0' + (int)(v % 10));
        v /= 10;
    } while (v);
    while (n) ANS += t[--n];
}
static inline void ac(char c) { ANS += c; }

// Piecewise-linear task-time column, clamped outside the listed sizes.
struct Tab {
    vector<int> xs;
    vector<double> ys;
    void add(int x, double y) {
        if (y >= 0) {
            xs.push_back(x);
            ys.push_back(y);
        }
    }
    void build() {
        vector<int> id(xs.size());
        iota(id.begin(), id.end(), 0);
        sort(id.begin(), id.end(), [&](int a, int b) { return xs[a] < xs[b]; });
        vector<int> nx;
        vector<double> ny;
        for (int i : id) {
            if (!nx.empty() && nx.back() == xs[i]) continue;
            nx.push_back(xs[i]);
            ny.push_back(ys[i]);
        }
        xs.swap(nx);
        ys.swap(ny);
    }
    double get(double m) const {
        if (xs.empty()) return 1.0;
        if (m <= xs.front()) return ys.front();
        if (m >= xs.back()) return ys.back();
        int lo = 0, hi = (int)xs.size() - 1;
        while (hi - lo > 1) {
            int mid = (lo + hi) >> 1;
            if (xs[mid] <= m) lo = mid;
            else hi = mid;
        }
        double x0 = xs[lo], x1 = xs[hi];
        if (x1 == x0) return ys[lo];
        return ys[lo] + (ys[hi] - ys[lo]) * (m - x0) / (x1 - x0);
    }
};

enum : int {
    ST_ARR = 0,
    ST_PPRE_RUN,
    ST_PPROC_READY,
    ST_PPROC_RUN,
    ST_PDOWN_WAIT,
    ST_PPOST_READY,
    ST_PPOST_RUN,
    ST_DIDLE,
    ST_DPRE_RUN,
    ST_DUP_WAIT,
    ST_DPROC_READY,
    ST_DPROC_RUN,
    ST_DDOWN_WAIT,
    ST_DPOST_READY,
    ST_DPOST_RUN,
    ST_FIN
};

#ifndef EFF_RATIO
#define EFF_RATIO 1.1
#endif
#ifndef EFF_PLATEAU
#define EFF_PLATEAU 0.97
#endif
// Shrinking the cohort to protect TPOT also lengthens every queue, which feeds
// back into TDR and makespan. The model does not capture that coupling, so keep
// a floor on the fraction of peak token rate the cohort may give up.
#ifndef THR_FLOOR
#define THR_FLOOR 0.5
#endif
#ifndef POST_HOLD_WTP
#define POST_HOLD_WTP 0.3
#endif
#ifndef POST_LAT_RATIO
#define POST_LAT_RATIO 2.0
#endif
#ifndef PPOST_FIRST_WTP
#define PPOST_FIRST_WTP 0.4
#endif
#ifndef CHUNK_OVERHEAD
#define CHUNK_OVERHEAD 0.05
#endif
#ifndef CHUNK_S_FACTOR
#define CHUNK_S_FACTOR 20.0
#endif
// Fraction of a decode round that has to be fixed link latency before the
// cohort is worth protecting from fragmentation.
#ifndef FRAG_LAT_SHARE
#define FRAG_LAT_SHARE 0.5
#endif
// Slack kept on the number of clouds used, above the number the input stage can
// actually keep busy.
#ifndef KUSE_MARGIN
#define KUSE_MARGIN 1.5
#endif
static int K, LAYERS;
static double S, LAT, BW, BPT;
static double SLO1, SLO2, TPUB, TPBASE, DBASE, WTP, WC;
static Tab tPpre, tPproc, tPpost, tDpre, tDproc, tDpost;

static inline double xfer(double len) { return LAT + 8.0 * len * BPT / (BW * 1e6); }

// One decode round for a cohort of m: edge pre/post, both link hops, cloud proc.
// This is the value a member's TPOT converges to, so it is also what we tune.
static double round_time(int m) {
    if (m < 1) m = 1;
    int k = min(K, m);
    double per = ceil((double)m / k);
    double edge = 2.0 * S + tDpre.get(m) + tDpost.get(m);
    double link = 2.0 * (k * LAT + 8.0 * (double)m * BPT / (BW * 1e6));
    double proc = S + tDproc.get(per);
    return edge + link + proc;
}

static vector<double> roundCache;
static inline double roundT(int m) {
    if (m >= 1 && m < (int)roundCache.size()) return roundCache[m];
    return round_time(m);
}

// Fraction of a round of m that is fixed link latency. A round pays LAT once
// per participating cloud in each direction whatever it carries, so this is the
// part of the round that a larger cohort amortises and a smaller one repeats.
static inline double latShare(int m) {
    if (m < 1) m = 1;
    return 2.0 * min(K, m) * LAT / max(roundT(m), 1e-12);
}

static inline double clamp01(double x) { return x < 0 ? 0 : (x > 1 ? 1 : x); }

// The judge's own formula, evaluated on the cohort we are considering.
static double objective(int m, double ex_tdr, double infl) {
    double rt = roundT(m);
    double ntp = 0.0;
    if (TPUB > TPBASE) ntp = clamp01(((double)m / rt - TPBASE) / (TPUB - TPBASE));
    double ex_tpot = max(0.0, (rt * infl - SLO2) / SLO2);
    double dist = sqrt(ex_tdr * ex_tdr + ex_tpot * ex_tpot);
    double nc;
    if (DBASE > 0) nc = max(0.0, 1.0 - dist / DBASE);
    else nc = (dist <= 1e-12) ? 1.0 : 0.0;
    return WTP * ntp + WC * nc;
}

struct Req {
    int lin = 1;
    int cloud = -1;
    int next_ls = 0;
    int tokens = 0;
    double arr = 0;
    double last_tok = 0;
    int st = ST_ARR;
};

static vector<Req> R;
static vector<int> bid, bpos;
static vector<vector<int>> BK;

static inline void ensureReq(int rid) {
    if ((int)R.size() <= rid) {
        R.resize(rid + 1);
        bid.resize(rid + 1, -1);
        bpos.resize(rid + 1, -1);
    }
}

static inline void bmove(int rid, int nb) {
    int ob = bid[rid];
    if (ob == nb) return;
    if (ob >= 0) {
        vector<int>& v = BK[ob];
        int p = bpos[rid];
        v[p] = v.back();
        bpos[v[p]] = p;
        v.pop_back();
    }
    bid[rid] = nb;
    if (nb >= 0) {
        bpos[rid] = (int)BK[nb].size();
        BK[nb].push_back(rid);
    }
}

int main() {
    long long k_ = 1, bpt_ = 1, nl_ = 1, n_ = 0;
    double s_ = 1, lat_ = 1, bw_ = 1;
    if (!io::rint(k_)) return 0;
    io::rdbl(s_);
    io::rdbl(lat_);
    io::rdbl(bw_);
    io::rint(bpt_);
    io::rint(nl_);
    K = (int)k_;
    S = s_;
    LAT = lat_;
    BW = bw_;
    BPT = (double)bpt_;
    LAYERS = (int)nl_;

    io::rdbl(SLO1);
    io::rdbl(SLO2);
    io::rdbl(TPUB);
    io::rdbl(TPBASE);
    io::rdbl(DBASE);
    io::rdbl(WTP);
    io::rdbl(WC);

    io::rint(n_);
    for (long long i = 0; i < n_; ++i) {
        long long b = 1;
        double a = -1, c = -1, d = -1, e = -1, f = -1, g = -1;
        io::rint(b);
        io::rdbl(a);
        io::rdbl(c);
        io::rdbl(d);
        io::rdbl(e);
        io::rdbl(f);
        io::rdbl(g);
        int bs = (int)b;
        tPpre.add(bs, a);
        tPproc.add(bs, c);
        tPpost.add(bs, d);
        tDpre.add(bs, e);
        tDproc.add(bs, f);
        tDpost.add(bs, g);
    }
    tPpre.build();
    tPproc.build();
    tPpost.build();
    tDpre.build();
    tDproc.build();
    tDpost.build();

    const int MAXM = 4097;
    roundCache.resize(MAXM);
    for (int m = 1; m < MAXM; ++m) roundCache[m] = round_time(m);

    // Cohort size past which extra members stop paying for themselves.
    int M_EFF = 1, M_FLOOR = 1;
    {
        double peak = 0;
        for (int m = 1; m <= 4096; ++m) peak = max(peak, m / roundT(m));
        for (int m = 1; m <= 4096; ++m) {
            if (m / roundT(m) >= THR_FLOOR * peak) {
                M_FLOOR = m;
                break;
            }
        }
        double best = 0;
        for (int m = 1; m <= 2048; ++m) {
            double e = m / roundT(m);
            if (e > best) {
                best = e;
                M_EFF = m;
            }
        }
        for (int m = 1; m <= M_EFF; ++m) {
            if (m / roundT(m) >= EFF_PLATEAU * best) {
                M_EFF = m;
                break;
            }
        }
    }

    // buckets: 0 arrived, 1 ppost-ready, 2 dpost-ready, 3 fresh, 4 active,
    // 5+c pproc-ready, 5+K+c dproc-ready
    const int B_ARR = 0, B_PPOST = 1, B_DPOST = 2, B_FRESH = 3, B_ACT = 4, B_PPROC = 5;
    const int B_DPROC = 5 + K;
    BK.assign(5 + 2 * K, {});

    R.reserve(2048);
    bid.reserve(2048);
    bpos.reserve(2048);

    bool edgeFree = true;
    vector<char> cloudFree(K, 1);
    vector<int> nPre(K, 0), nDec(K, 0);

    // Lazy heaps give shortest-job-first prefill order without rescanning.
    typedef pair<double, int> PDI;
    priority_queue<PDI, vector<PDI>, greater<PDI>> qArr;
    vector<priority_queue<PDI, vector<PDI>, greater<PDI>>> qProc(K);

    long long running = 0, xfers = 0, decDown = 0, decProcRun = 0;
    int nLive = 0, nActive = 0, nPrefPend = 0, nDecFlight = 0;
    double sumLastTok = 0, sumArrPend = 0;
    double sumTdr = 0;
    long long nTdr = 0;
    double sumGap = 0;
    long long nGap = 0;
    double cloudW = 0, feedW = 0;

    vector<int> finBuf, ridBuf, batch;

    auto setSt = [&](int rid, int st) { R[rid].st = st; };

    for (;;) {
        if (!io::rtok()) {
            io::oflush();
            return 0;
        }
        if (io::tok[0] == 'E' && io::tok[1] == 'N') {
            io::oflush();
            return 0;
        }
        double now = strtod(io::tok, nullptr);
        long long ecnt;
        if (!io::rint(ecnt)) {
            io::oflush();
            return 0;
        }

        finBuf.clear();
        for (long long ev = 0; ev < ecnt; ++ev) {
            if (!io::rtok()) {
                io::oflush();
                return 0;
            }
            char e0 = io::tok[0], e1 = io::tok[1];
            if (e0 == 'A') {  // ARR rid lin
                long long rid = 0, lin = 0;
                io::rint(rid);
                io::rint(lin);
                ensureReq((int)rid);
                Req& r = R[rid];
                r.lin = (int)lin;
                r.arr = now;
                r.last_tok = now;
                r.next_ls = 0;
                r.tokens = 0;
                r.cloud = -1;
                r.st = ST_ARR;
                bid[rid] = -1;
                bmove((int)rid, B_ARR);
                nLive++;
                nPrefPend++;
                sumArrPend += now;
                double w = tPpre.get(r.lin) + tPproc.get(r.lin) + tPpost.get(r.lin);
                qArr.push(PDI(w, (int)rid));
                // Capacity of the input stage, used to size the cloud pool.
                cloudW += S + tPproc.get(r.lin);
                feedW += max(2.0 * S + tPpre.get(r.lin) + tPpost.get(r.lin),
                             xfer(r.lin));
            } else if (e0 == 'F') {  // FIN rid
                long long rid = 0;
                io::rint(rid);
                finBuf.push_back((int)rid);
            } else if (e0 == 'T') {  // TDN <server> <phase> <type> ... <dur>
                io::rtok();
                bool isEdge = (io::tok[0] == 'E');
                int cl = isEdge ? -1 : atoi(io::tok + 1);
                io::rtok();
                char ph = io::tok[0];
                io::rtok();
                char ty = io::tok[0];        // P / R / O  (PRE / PROC / POST)
                bool isPre = (io::tok[1] == 'R' && io::tok[2] == 'E');
                bool isProc = (io::tok[1] == 'R' && io::tok[2] == 'O');
                (void)ty;
                running--;
                if (isEdge) edgeFree = true;
                else if (cl >= 0 && cl < K) cloudFree[cl] = 1;

                double dur = 0;
                if (ph == 'P') {
                    long long a = 0, b = 0, c = 0, d = 0;
                    if (isProc) {
                        io::rint(a);
                        io::rint(b);
                        io::rint(c);
                        io::rint(d);
                        io::rdbl(dur);
                        int rid = (int)d;
                        Req& r = R[rid];
                        if (r.next_ls >= LAYERS) {
                            setSt(rid, ST_PDOWN_WAIT);
                            xfers++;  // last piece queues the input-stage DOWN
                        } else {
                            setSt(rid, ST_PPROC_READY);
                            bmove(rid, B_PPROC + r.cloud);
                            qProc[r.cloud].push(PDI(tPproc.get(r.lin) *
                                                        (double)(LAYERS - r.next_ls) / LAYERS,
                                                    rid));
                        }
                    } else {
                        io::rint(a);
                        io::rint(b);
                        io::rdbl(dur);
                        int rid = (int)b;
                        if (isPre) {
                            setSt(rid, ST_PPROC_READY);  // waits on the UP XDN
                            xfers++;
                        } else {  // P POST: this is where TDR stops
                            Req& r = R[rid];
                            setSt(rid, ST_DIDLE);
                            bmove(rid, B_FRESH);
                            sumTdr += now - r.arr;
                            nTdr++;
                            nPrefPend--;
                            sumArrPend -= r.arr;
                            r.last_tok = now;
                        }
                    }
                } else {
                    long long a = 0, m = 0;
                    io::rint(a);
                    io::rint(m);
                    ridBuf.clear();
                    for (long long j = 0; j < m; ++j) {
                        long long x = 0;
                        io::rint(x);
                        ridBuf.push_back((int)x);
                    }
                    io::rdbl(dur);
                    if (isPre) {  // D PRE -> one UP per distinct cloud
                        static vector<char> seen;
                        seen.assign(K, 0);
                        for (int rid : ridBuf) {
                            setSt(rid, ST_DUP_WAIT);
                            if (R[rid].cloud >= 0) seen[R[rid].cloud] = 1;
                        }
                        for (int c = 0; c < K; ++c)
                            if (seen[c]) xfers++;
                    } else if (isProc) {
                        decProcRun--;
                        for (int rid : ridBuf) setSt(rid, ST_DDOWN_WAIT);
                        xfers++;
                        decDown++;
                    } else {  // D POST: one token per member
                        nDecFlight -= (int)ridBuf.size();
                        for (int rid : ridBuf) {
                            Req& r = R[rid];
                            if (r.tokens >= 1) {
                                sumGap += now - r.last_tok;
                                nGap++;
                                sumLastTok -= r.last_tok;
                            } else {
                                nActive++;  // gap clock starts at the first token
                            }
                            r.tokens++;
                            r.last_tok = now;
                            sumLastTok += now;
                            setSt(rid, ST_DIDLE);
                            bmove(rid, B_ACT);
                        }
                    }
                }
            } else if (e0 == 'X') {  // XDN <dir> <remote> <size> <kind> <m> <rid...>
                io::rtok();
                bool up = (io::tok[0] == 'U');
                long long rem = 0, sz = 0, m = 0;
                io::rint(rem);
                io::rint(sz);
                io::rtok();
                bool kindPre = (io::tok[0] == 'P');
                io::rint(m);
                xfers--;
                for (long long j = 0; j < m; ++j) {
                    long long x = 0;
                    io::rint(x);
                    int rid = (int)x;
                    Req& r = R[rid];
                    if (kindPre) {
                        if (up) {
                            setSt(rid, ST_PPROC_READY);
                            bmove(rid, B_PPROC + r.cloud);
                            qProc[r.cloud].push(
                                PDI(tPproc.get(r.lin) * (double)(LAYERS - r.next_ls) / LAYERS, rid));
                        } else {
                            setSt(rid, ST_PPOST_READY);
                            bmove(rid, B_PPOST);
                        }
                    } else {
                        if (!up) decDown--;
                        if (up) {
                            setSt(rid, ST_DPROC_READY);
                            bmove(rid, B_DPROC + r.cloud);
                        } else {
                            setSt(rid, ST_DPOST_READY);
                            bmove(rid, B_DPOST);
                        }
                    }
                }
                (void)e1;
                (void)rem;
                (void)sz;
            }
        }
        for (int rid : finBuf) {
            Req& r = R[rid];
            if (r.st == ST_FIN) continue;
            if (r.tokens >= 1) {
                nActive--;
                sumLastTok -= r.last_tok;
            }
            r.st = ST_FIN;
            bmove(rid, -1);
            if (r.cloud >= 0) nDec[r.cloud]--;
            nLive--;
        }

        // Estimated means, including work still in flight, so the two excesses
        // can be compared while there is still time to act on them.
        double estTdr, estTpot;
        {
            double pend = (double)nPrefPend * now - sumArrPend;
            estTdr = (sumTdr + max(0.0, pend)) / max(1.0, (double)(nTdr + nPrefPend));
            double open = (double)nActive * now - sumLastTok;
            estTpot = (sumGap + max(0.0, open)) / max(1.0, (double)(nGap + nActive));
        }
        double exTdr = max(0.0, (estTdr - SLO1) / SLO1);
        double exTpot = max(0.0, (estTpot - SLO2) / SLO2);
        double meanOpenGap =
            nActive > 0 ? ((double)nActive * now - sumLastTok) / nActive : 0.0;

        int nAssigned = 0;
        ANS.clear();

        // ---- edge ----
        bool edgeBusyNow = !edgeFree;
        bool holdDpost = edgeFree && !BK[B_DPOST].empty() && (decDown > 0 || decProcRun > 0) &&
                         WTP >= POST_HOLD_WTP && LAT > POST_LAT_RATIO * (S + tDpost.get(1)) &&
                         !(DBASE <= 0 && WC > 1e-9);
        if (edgeFree && !BK[B_DPOST].empty() && !holdDpost) {
            batch = BK[B_DPOST];
            sort(batch.begin(), batch.end());
            as("E D POST -1 ");
            ai((long long)batch.size());
            for (int rid : batch) {
                ac(' ');
                ai(rid);
                setSt(rid, ST_DPOST_RUN);
                bmove(rid, -1);
            }
            ac('\n');
            edgeFree = false;
            running++;
            nAssigned++;
        }

        if (edgeFree && WTP <= PPOST_FIRST_WTP && !BK[B_PPOST].empty()) {
            int best = BK[B_PPOST][0];
            double bw = 1e300;
            for (int rid : BK[B_PPOST]) {
                double w = tPpost.get(R[rid].lin);
                if (w < bw) { bw = w; best = rid; }
            }
            as("E P POST "); ai(R[best].cloud); ac(' '); ai(best); ac('\n');
            setSt(best, ST_PPOST_RUN);
            bmove(best, -1);
            edgeFree = false;
            running++;
            nAssigned++;
        }

        // Decode cohort. mDesign is the size the system *wants* to run at; we
        // let requests accumulate towards it and spend the wait on prefill,
        // which is productive work rather than an idle edge.
        // The model assumes a request's gap equals one clean round. Reality adds
        // interleaved prefill and pipeline stalls, so calibrate against measured
        // gaps -- without this the optimiser chases a round time it cannot reach
        // and shrinks the cohort to nothing.
        double infl = 1.0;
        if (nGap >= 8 && nActive > 0) {
            double model = roundT(max(1, nActive));
            if (model > 1e-9) infl = min(20.0, max(1.0, (sumGap / (double)nGap) / model));
        }
        int mDesign = 1;
        {
            double best = -1;
            int hi = min(4096, max(1, M_EFF));
            for (int m = 1;;) {
                double v = objective(m, exTdr, infl);
                if (v >= best - 1e-12) {
                    best = max(best, v);
                    mDesign = m;
                }
                if (m >= hi) break;
                m = min(hi, m + max(1, m / 8));
            }
            // dist_base == 0 makes the waiting-time component all-or-nothing:
            // any excess at all forfeits the whole w_c share. When the target is
            // still reachable, protect it rather than trusting the tdr estimate.
            if (WTP > 1e-9) mDesign = max(mDesign, min(hi, M_FLOOR));
            if (DBASE <= 0 && WC > 1e-9 && roundT(1) * infl <= SLO2) {
                int cap = 1;
                for (int m = 1; m <= hi; ++m) {
                    if (roundT(m) * infl <= SLO2) cap = m;
                    else break;
                }
                mDesign = min(mDesign, cap);
            }
        }

        if (edgeFree) {
            bool haveAct = !BK[B_ACT].empty();
            bool haveFresh = !BK[B_FRESH].empty();
            bool havePrefill = !BK[B_PPOST].empty() || !BK[B_ARR].empty();
            int ready = (int)BK[B_ACT].size() + (int)BK[B_FRESH].size();

            bool fire = false;
            if (haveAct || haveFresh) {
                if (ready >= mDesign) {
                    fire = true;  // cohort is as large as it is worth waiting for
                } else if (!havePrefill) {
                    // An idle edge is not on its own a reason to fire. Where a
                    // round is mostly fixed link latency, splitting the cohort
                    // multiplies the dominant term by the number of pieces, and
                    // both links are FIFO-shared by every round, so short rounds
                    // saturate the links while every machine idles. Members still
                    // inside a round return and enlarge this cohort for nothing
                    // but makespan, so wait for them -- but only in that regime,
                    // and only while there is something left to wait for.
                    fire = (nDecFlight == 0) || latShare(ready) < FRAG_LAT_SHARE;
                } else if (haveAct && WC > 1e-9) {
                    // Serving gaps early is only worth it if the batch is not so
                    // small that its per-token edge cost starves everything else.
                    double ptcNow =
                        (2.0 * S + tDpre.get(ready) + tDpost.get(ready)) / max(1, ready);
                    double ptcBest =
                        (2.0 * S + tDpre.get(mDesign) + tDpost.get(mDesign)) / max(1, mDesign);
                    bool efficient = ptcNow <= EFF_RATIO * ptcBest;
                    double pred = meanOpenGap + roundT(max(1, nActive));
                    if (efficient && pred >= SLO2 * 0.85) {
                        if (pred <= SLO2 * 2.0) fire = true;
                        else {
                            double dT = max(1.0, (double)(nTdr + nPrefPend));
                            double dG = max(1.0, (double)(nGap + nActive));
                            double rP = nPrefPend * exTdr / (SLO1 * dT);
                            double rD = nActive * exTpot / (SLO2 * dG);
                            fire = (rD >= rP);
                        }
                    }
                }
                // Starvation escape: waiting for a bigger cohort is only free
                // while nothing is being scored, so it can never outlast the
                // gap budget of a request that already has a token.
                if (!fire && WC > 1e-9 && meanOpenGap > 8.0 * SLO2) fire = true;
            }

            if (fire) {
                batch.clear();
                for (int rid : BK[B_ACT]) batch.push_back(rid);
                int room = mDesign - nActive;
                for (int i = (int)BK[B_FRESH].size() - 1; i >= 0 && room > 0; --i, --room)
                    batch.push_back(BK[B_FRESH][i]);
                if (!batch.empty()) {
                    sort(batch.begin(), batch.end());
                    as("E D PRE -1 ");
                    ai((long long)batch.size());
                    for (int rid : batch) {
                        ac(' ');
                        ai(rid);
                        setSt(rid, ST_DPRE_RUN);
                        bmove(rid, -1);
                    }
                    ac('\n');
                    nDecFlight += (int)batch.size();
                    edgeFree = false;
                    running++;
                    nAssigned++;
                }
            }
        }

        if (edgeFree && !BK[B_PPOST].empty()) {
            int best = BK[B_PPOST][0];
            double bw = 1e300;
            for (int rid : BK[B_PPOST]) {
                double w = tPpost.get(R[rid].lin);
                if (w < bw) {
                    bw = w;
                    best = rid;
                }
            }
            as("E P POST ");
            ai(R[best].cloud);
            ac(' ');
            ai(best);
            ac('\n');
            setSt(best, ST_PPOST_RUN);
            bmove(best, -1);
            edgeFree = false;
            running++;
            nAssigned++;
        }

        if (edgeFree && !BK[B_ARR].empty()) {
            int best = -1;
            while (!qArr.empty()) {
                int rid = qArr.top().second;
                if (bid[rid] != B_ARR) {
                    qArr.pop();
                    continue;
                }
                best = rid;
                qArr.pop();
                break;
            }
            if (best < 0) best = BK[B_ARR].back();
            // Every distinct cloud in a decode group costs one link latency in
            // each direction, every round. Spreading the input stage over more
            // clouds than it can keep busy therefore buys nothing and is paid
            // for on every later round, so use only as many clouds as the input
            // stage's own arrival rate needs -- and only while the latency that
            // saves outweighs the longer cloud task a denser group implies.
            int kuse = K;
            if (K > 1 && feedW > 0) {
                int need = (int)ceil(cloudW / feedW * (double)KUSE_MARGIN);
                if (need < 1) need = 1;
                if (need < K) {
                    double saved = 2.0 * (double)(K - need) * LAT;
                    double added = tDproc.get(ceil((double)M_EFF / need)) -
                                   tDproc.get(ceil((double)M_EFF / K));
                    if (saved > added) kuse = need;
                }
            }
            int c = 0;
            double bl = 1e300;
            for (int i = 0; i < kuse; ++i) {
                double load = nPre[i] * (S + tPproc.get(R[best].lin)) +
                              nDec[i] * (S + tDproc.get(max(1, nDec[i])));
                if (load < bl) {
                    bl = load;
                    c = i;
                }
            }
            as("E P PRE ");
            ai(c);
            ac(' ');
            ai(best);
            ac('\n');
            R[best].cloud = c;
            nPre[c]++;
            setSt(best, ST_PPRE_RUN);
            bmove(best, -1);
            edgeFree = false;
            running++;
            nAssigned++;
        }

        // ---- clouds ----
        for (int c = 0; c < K; ++c) {
            if (!cloudFree[c]) continue;
            if (!BK[B_DPROC + c].empty()) {
                batch = BK[B_DPROC + c];
                sort(batch.begin(), batch.end());
                as("C");
                ai(c);
                as(" D PROC ");
                ai(c);
                ac(' ');
                ai((long long)batch.size());
                for (int rid : batch) {
                    ac(' ');
                    ai(rid);
                    setSt(rid, ST_DPROC_RUN);
                    bmove(rid, -1);
                }
                ac('\n');
                cloudFree[c] = 0;
                running++;
                decProcRun++;
                nAssigned++;
                continue;
            }
            if (BK[B_PPROC + c].empty()) continue;
            int best = -1;
            while (!qProc[c].empty()) {
                int rid = qProc[c].top().second;
                if (bid[rid] != B_PPROC + c) {
                    qProc[c].pop();
                    continue;
                }
                best = rid;
                qProc[c].pop();
                break;
            }
            if (best < 0) best = BK[B_PPROC + c].back();

            Req& r = R[best];
            int ls = r.next_ls, remain = LAYERS - ls, take = remain;
            // Split only when a long prefill would otherwise pin this cloud and
            // stall decode rounds that are being measured.
            if (WC > 1e-9 && remain > 1 && nDec[c] > 0) {
                double full = tPproc.get(r.lin) * (double)remain / LAYERS;
                double perLayer = tPproc.get(r.lin) / LAYERS;
                // Every piece pays S again, so only split when that overhead
                // stays under a few percent of the prefill it protects.
                int maxPieces = (int)floor(CHUNK_OVERHEAD * full / S);
                if (maxPieces >= 2) {
                    double budget = max(CHUNK_S_FACTOR * S, SLO2);
                    int byBudget = (int)floor(budget / max(perLayer, 1e-9));
                    int byOverhead = (remain + maxPieces - 1) / maxPieces;
                    take = max(1, max(byBudget, byOverhead));
                    take = min(take, remain);
                }
            }
            int le = ls + take;
            as("C");
            ai(c);
            as(" P PROC ");
            ai(ls);
            ac(' ');
            ai(le);
            ac(' ');
            ai(c);
            ac(' ');
            ai(best);
            ac('\n');
            r.next_ls = le;
            if (le >= LAYERS) {
                nPre[c]--;
                nDec[c]++;
            }
            setSt(best, ST_PPROC_RUN);
            bmove(best, -1);
            cloudFree[c] = 0;
            running++;
            nAssigned++;
        }

        // Safety net: holding work is only legal while some event is still
        // guaranteed to arrive. Otherwise the run is declared stuck and scores 0.
        if (nAssigned == 0 && running == 0 && xfers == 0 && nLive > 0 && !edgeBusyNow) {
            if (edgeFree && (!BK[B_ACT].empty() || !BK[B_FRESH].empty())) {
                batch.clear();
                for (int rid : BK[B_ACT]) batch.push_back(rid);
                for (int rid : BK[B_FRESH]) batch.push_back(rid);
                sort(batch.begin(), batch.end());
                as("E D PRE -1 ");
                ai((long long)batch.size());
                for (int rid : batch) {
                    ac(' ');
                    ai(rid);
                    setSt(rid, ST_DPRE_RUN);
                    bmove(rid, -1);
                }
                ac('\n');
                nDecFlight += (int)batch.size();
                edgeFree = false;
                running++;
                nAssigned++;
            }
        }

        io::oi(nAssigned);
        io::oc('\n');
        io::osn(ANS.data(), ANS.size());
        io::oflush();
    }
}

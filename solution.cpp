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
// The cloud pool is sized from a capacity ratio, so it needs the headroom any
// shared resource needs: a pool loaded to exactly 100% queues without bound.
// This is the reciprocal of the utilisation it is sized for.
#ifndef KUSE_MARGIN
#define KUSE_MARGIN 1.08
#endif
// Fraction of a decode round's free window on a cloud that a prefill piece may
// occupy, in the regime where the waiting-time term is what is being scored.
#ifndef TPOT_CHUNK_SLACK
#define TPOT_CHUNK_SLACK 1.0
#endif
// Steering round time spends TDR headroom, and the TDR consequence of the trade
// shows up well after the decision, so require mean TDR to be comfortably
// inside SLO1 rather than merely inside it.
#ifndef TPOT_TDR_ROOM
#define TPOT_TDR_ROOM 0.5
#endif
// dist = hypot(eT, eG), so the marginal value of shaving the TPOT leg scales
// with eG/dist. Once the TDR leg dwarfs it, no TPOT reduction can move dist,
// and any throughput spent on one is pure loss -- the shape of judge test 17,
// where mean_tdr/SLO1 ran to ~1554 while the TPOT leg contributed ~25, and
// capping the cohort cut mean TPOT five-fold for nothing while tp fell 6%.
// Below this fraction the TPOT-protective policies stand down.
#ifndef TPOT_DIST_SHARE
#define TPOT_DIST_SHARE 0.3
#endif
// Decode round pipelining: a round is edge -> uplink -> cloud -> downlink, four
// distinct resources, so g cohorts in antiphase multiply the token rate until
// one resource saturates (cycle >= g * its phase). 0 disables, 1 engages only
// while no prefill wants the edge, so the extra D PRE / D POST edge cost can
// never starve the input stage (per-cloud decode rounds measured -997 when it
// did).
#ifndef PIPE_MODE
#define PIPE_MODE 1
#endif
#ifndef PIPE_GCAP
#define PIPE_GCAP 8
#endif
// While the input stage still has requests in flight anywhere (nPrefPend > 0)
// and the *links* are its binding resource, every decode round bills its fixed
// k*LAT to the very resource whose drain rate sets the makespan. Rounds are
// then synchronized: wait for the in-flight round to land and fire one
// coalesced round instead of trickling. Where the input stage is edge- or
// cloud-bound the wait would only idle the edge, and once the input stage is
// drained the trickle is organic pipelining, so the sync stays off there.
#ifndef PIPE_SYNC_WTP
#define PIPE_SYNC_WTP 0.3
#endif
// Coalesce D POST while cloud groups are still returning also when the edge is
// the input stage's binding resource: every merged post refunds one S to the
// resource that sets the makespan.
#ifndef POST_EDGEBOUND
#define POST_EDGEBOUND 1
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

// Largest single-resource phase of a round of m: the spacing at which staggered
// cohorts can follow each other before that resource saturates.
static double phase_max(int m) {
    if (m < 1) m = 1;
    int k = min(K, m);
    double per = ceil((double)m / k);
    double edge = 2.0 * S + tDpre.get(m) + tDpost.get(m);
    double link = k * LAT + 8.0 * (double)m * BPT / (BW * 1e6);
    double proc = S + tDproc.get(per);
    return max(edge, max(link, proc));
}

static vector<double> phaseCache;
static inline double phaseT(int m) {
    if (m >= 1 && m < (int)phaseCache.size()) return phaseCache[m];
    return phase_max(m);
}

// Fraction of a round of m that is fixed link latency. A round pays LAT once
// per participating cloud in each direction whatever it carries, so this is the
// part of the round that a larger cohort amortises and a smaller one repeats.
static inline double latShare(int m) {
    if (m < 1) m = 1;
    return 2.0 * min(K, m) * LAT / max(roundT(m), 1e-12);
}

// Observed gaps, bucketed by the size of the round that produced them.
//
// round_time(m) is a hard lower bound on a member's gap at size m: it is the
// serial dependency chain of one round (edge D PRE, uplink, cloud D PROC,
// downlink, edge D POST, plus one S per task), so no schedule beats it. A
// single measured inflation factor cannot respect that -- it is measured at
// whatever size we happen to be running, and scaling a large round's overrun
// onto a small round's bound is what buries the small cohort, which then keeps
// the overrun large. Both a member's gap and the size of the round that
// produced it are observable, so keep the statistic per size: measured where
// there is evidence, at the lower bound where there is none. The search then
// tries a smaller cohort once and afterwards commits to whatever the
// measurement at that size supports, rather than either chasing a round time
// it can never reach or never testing one.
#ifndef GAP_MINSAMP
#define GAP_MINSAMP 6
#endif
#ifndef GAP_WINDOW
#define GAP_WINDOW 64
#endif
static const int GAP_BUCKETS = 14;
static double gapEw[GAP_BUCKETS];
static double gapLo[GAP_BUCKETS];  // prefix max of the measured means
static int gapN[GAP_BUCKETS];
static inline int gapBucket(int m) {
    int b = 0;
    while (b < GAP_BUCKETS - 1 && (2 << b) <= m) ++b;
    return b;
}
static inline void gapObserve(int m, double g) {
    int b = gapBucket(m);
    if (!gapN[b]) gapEw[b] = g;
    else gapEw[b] += (g - gapEw[b]) / (double)min(gapN[b] + 1, (int)GAP_WINDOW);
    ++gapN[b];
    // A bigger cohort cannot round-trip faster than a smaller one did under the
    // same interference, so evidence at one size floors every larger size.
    // Without that, a size nobody has tried yet always looks better than the
    // one just measured, and the search walks the cohort upwards for ever.
    double run = 0;
    for (int i = 0; i < GAP_BUCKETS; ++i) {
        if (gapN[i] >= GAP_MINSAMP && gapEw[i] > run) run = gapEw[i];
        gapLo[i] = run;
    }
}
static inline double gapPredict(int m) {
    int b = gapBucket(m);
    double v = max(roundT(m), gapLo[b]);
    if (gapN[b] >= GAP_MINSAMP) v = max(v, gapEw[b]);
    return v;
}

static inline double clamp01(double x) { return x < 0 ? 0 : (x > 1 ? 1 : x); }

// The judge's own formula, evaluated on the plan being considered: the decode
// pool split into g cohorts of m circulating in antiphase. Each member is
// served once per cycle, so its gap is the cycle, and the pool produces g*m
// tokens per cycle. g == 1 is exactly the old single-cohort model.
//
// `soft` is the same expression with the clamps removed. Both clamps saturate:
// once a target is out of reach the real score is flat zero for *every* cohort
// size, so it cannot say which size comes closest, and a search that maximises
// it keeps whichever candidate it happened to visit last. The unclamped copy
// still ranks those tied sizes, so it is used only to break ties.
static double objective(int m, double ex_tdr, int pool, int gAllow,
                        double* rateOut = nullptr, double* soft = nullptr) {
    int g = 1;
    if (gAllow > 1 && m < pool) {
        g = pool / m;
        if (g > gAllow) g = gAllow;
        if (g < 1) g = 1;
    }
    double cyc = roundT(m);
    if (g > 1) cyc = max(cyc, (double)g * phaseT(m));
    double toks = (double)m * g;
    double raw_tp = 0.0;
    if (TPUB > TPBASE) raw_tp = (toks / cyc - TPBASE) / (TPUB - TPBASE);
    // A member's gap is one full cycle. gapPredict carries the measured
    // per-size evidence; a staggered plan's cycle is a hard lower bound the
    // single-size statistic cannot see, so floor the prediction with it.
    double ex_tpot = max(0.0, (max(gapPredict(m), cyc) - SLO2) / SLO2);
    double dist = sqrt(ex_tdr * ex_tdr + ex_tpot * ex_tpot);
    double raw_c = (DBASE > 0) ? (1.0 - dist / DBASE) : -dist;
    if (soft) *soft = WTP * raw_tp + WC * raw_c;
    double nc;
    if (DBASE > 0) nc = max(0.0, raw_c);
    else nc = (dist <= 1e-12) ? 1.0 : 0.0;
    if (rateOut) *rateOut = toks / cyc;
    return WTP * clamp01(raw_tp) + WC * nc;
}

struct Req {
    int lin = 1;
    int cloud = -1;
    int next_ls = 0;
    int tokens = 0;
    double arr = 0;
    double last_tok = 0;
    int st = ST_ARR;
    char joined = 0;  // has been admitted to a decode round at least once
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
    phaseCache.resize(MAXM);
    for (int m = 1; m < MAXM; ++m) {
        roundCache[m] = round_time(m);
        phaseCache[m] = phase_max(m);
    }

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
    // Members of a decode round already in flight that still owe this cloud a
    // D PROC. While that is nonzero the cloud looks idle but is about to be
    // needed, and any prefill started now lands in a member's gap.
    vector<int> nDecPend(K, 0);
    // Cohort members assigned to each cloud, for as long as they are decoding.
    vector<int> nJoinC(K, 0);

    // Lazy heaps give shortest-job-first prefill order without rescanning.
    typedef pair<double, int> PDI;
    priority_queue<PDI, vector<PDI>, greater<PDI>> qArr;
    vector<priority_queue<PDI, vector<PDI>, greater<PDI>>> qProc(K);

    long long running = 0, xfers = 0, decDown = 0, decProcRun = 0;
    int nLive = 0, nActive = 0, nPrefPend = 0, nDecFlight = 0, nCohort = 0;
    double sumLastTok = 0, sumArrPend = 0;
    double sumTdr = 0;
    long long nTdr = 0;
    double sumGap = 0;
    long long nGap = 0;
    double cloudW = 0, feedW = 0, edgeW = 0, linkW = 0;

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
                r.joined = 0;
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
                edgeW += 2.0 * S + tPpre.get(r.lin) + tPpost.get(r.lin);
                linkW += xfer(r.lin);
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
                        int grp = (int)ridBuf.size();
                        for (int rid : ridBuf) {
                            Req& r = R[rid];
                            if (r.tokens >= 1) {
                                sumGap += now - r.last_tok;
                                nGap++;
                                sumLastTok -= r.last_tok;
                                gapObserve(grp, now - r.last_tok);
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
            if (r.joined) {
                nCohort--;
                if (r.cloud >= 0) nJoinC[r.cloud]--;
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
        // Measured legs of dist. When the TDR leg dominates, policies that
        // spend throughput to shorten decode rounds are gated off: they cannot
        // move dist, only the tp term (see TPOT_DIST_SHARE).
        bool tdrDominated = exTpot < TPOT_DIST_SHARE * exTdr;
        double meanOpenGap =
            nActive > 0 ? ((double)nActive * now - sumLastTok) / nActive : 0.0;

        int nAssigned = 0;
        ANS.clear();

        // ---- edge ----
        bool edgeBusyNow = !edgeFree;
        bool prefWork = !BK[B_PPOST].empty() || !BK[B_ARR].empty();
        // Pipelining engages only while no prefill wants the edge: firing more
        // rounds then converts an idle edge into token rate, and can never
        // starve the input stage. dist_base == 0 keeps the single-cohort model
        // because its SLO2 cap is stated in single-round terms.
        int poolD = (int)BK[B_ACT].size() + (int)BK[B_FRESH].size() + nDecFlight;
        int gAllow = 1;
        if (PIPE_MODE >= 1 && WTP > 1e-9 && !prefWork && !(DBASE <= 0 && WC > 1e-9))
            gAllow = PIPE_GCAP;
        // Which resource the input stage saturates first, from the same request
        // sums the cloud-pool sizing uses. When it is the edge, every merged
        // D POST refunds one S to the resource that sets the makespan -- but
        // only while the edge has prefill to run instead, so holding never
        // trades an idle edge for the refund. Holding is off entirely while
        // rounds are deliberately staggered: merging their posts would collapse
        // the stagger back into one synchronized cohort.
        bool edgeBoundIn = edgeW * (double)K >= cloudW && edgeW >= linkW;
        bool holdDpost = edgeFree && !BK[B_DPOST].empty() && (decDown > 0 || decProcRun > 0) &&
                         gAllow <= 1 && WTP >= POST_HOLD_WTP &&
                         (LAT > POST_LAT_RATIO * (S + tDpost.get(1)) ||
                          (POST_EDGEBOUND && edgeBoundIn && prefWork)) &&
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
        // which is productive work rather than an idle edge. A modelled round
        // is optimistic -- real gaps include interleaved prefill and pipeline
        // stalls -- so the objective scores each candidate against the gaps
        // measured at that candidate's own size (see gapPredict).
        int mDesign = 1;
        // Set when the score is dominated by the waiting-time term, the TPOT
        // half of it is the part still missing, and TDR has room to spare. That
        // is the regime where trading prefill throughput for shorter decode
        // rounds is the profitable direction; everywhere else it is not, so the
        // policies gated on it stay off.
        //
        // The test is whether the cohort size we have actually settled on is one
        // whose value comes from the w_c term. Before anything is measured that
        // is the small cohort the term rewards, so the trade is made and the
        // trial runs with these policies in force -- a fair test. If the trial
        // fails, the search moves to the throughput plateau, the w_c term at
        // that size is zero, and the trade stops being made.
        bool tpotBound = false;
        {
            double best = -1, bestSoft = -1e300;
            int mSoft = 1;
            double ntpCeil = 0;
            int hi = min(4096, max(1, M_EFF));
            if (gAllow > 1) {
                // The fixed M_FLOOR is a single-cohort notion; under pipelining
                // the same protection is a floor on the pooled token rate.
                double bestRate = 0;
                for (int m = 1;;) {
                    double r;
                    objective(m, exTdr, poolD, gAllow, &r);
                    bestRate = max(bestRate, r);
                    if (m >= hi) break;
                    m = min(hi, m + max(1, m / 8));
                }
                for (int m = 1;;) {
                    double r, soft = 0;
                    double v = objective(m, exTdr, poolD, gAllow, &r, &soft);
                    if (r + 1e-12 >= THR_FLOOR * bestRate) {
                        if (v >= best - 1e-12) {
                            best = max(best, v);
                            mDesign = m;
                        }
                        if (soft > bestSoft) {
                            bestSoft = soft;
                            mSoft = m;
                        }
                    }
                    if (m >= hi) break;
                    m = min(hi, m + max(1, m / 8));
                }
                if (best <= 1e-12) mDesign = mSoft;
                // tpotBound stays false here: the stagger regime only engages
                // while no prefill wants the edge, which is when the policies
                // tpotBound gates (prefill placement, chunking, hold-start)
                // have nothing left to act on.
            } else {
                for (int m = 1;;) {
                    double soft = 0;
                    double v = objective(m, exTdr, poolD, 1, nullptr, &soft);
                    if (v >= best - 1e-12) {
                        best = max(best, v);
                        mDesign = m;
                    }
                    if (soft > bestSoft) {
                        bestSoft = soft;
                        mSoft = m;
                    }
                    if (TPUB > TPBASE)
                        ntpCeil =
                            max(ntpCeil, clamp01(((double)m / roundT(m) - TPBASE) /
                                                 (TPUB - TPBASE)));
                    if (m >= hi) break;
                    m = min(hi, m + max(1, m / 8));
                }
                // Every candidate scores exactly zero: the objective has no
                // gradient at all here, so the loop above just kept the last
                // size it looked at -- the largest, which is the worst possible
                // round time. Fall back to the unclamped score, which still
                // points at the size that comes closest to scoring.
                if (best <= 1e-12) mDesign = mSoft;

                double exAt = max(0.0, (gapPredict(mDesign) - SLO2) / SLO2);
                double dAt = sqrt(exTdr * exTdr + exAt * exAt);
                double ncAt =
                    (DBASE > 0) ? max(0.0, 1.0 - dAt / DBASE) : (dAt <= 1e-12 ? 1.0 : 0.0);
                // exAt, not the measured excess: before the first token there
                // are no gaps to measure, and a test that waits for one can
                // never fire in time to choose the cohort that would have
                // avoided it. Whether round time is worth steering is a
                // question about the size we are about to run, which is what
                // exAt answers. Affordability, by contrast, is a measured
                // question -- hence estTdr.
                tpotBound = WC > 1e-9 && exAt > 0.0 && estTdr <= TPOT_TDR_ROOM * SLO1 &&
                            WC * ncAt >= WTP * ntpCeil && !tdrDominated;

                // The throughput floor is here because starving the cohort also
                // lengthens every queue, which feeds back into TDR and makespan
                // -- a coupling round_time does not model. That feedback only
                // threatens a score when TDR has somewhere bad to go, and the
                // test above already establishes that it does not: TDR is
                // inside its SLO and the term being scored is the waiting-time
                // one. Applying the floor anyway overrides the objective before
                // it can even try the small cohort, which is the only size that
                // term ever rewards.
                if (WTP > 1e-9 && !tpotBound) mDesign = max(mDesign, min(hi, M_FLOOR));
                if (DBASE <= 0 && WC > 1e-9 && gapPredict(1) <= SLO2) {
                    int cap = 1;
                    for (int m = 1; m <= hi; ++m) {
                        if (gapPredict(m) <= SLO2) cap = m;
                        else break;
                    }
                    mDesign = min(mDesign, cap);
                }
            }
        }

        if (edgeFree) {
            bool haveAct = !BK[B_ACT].empty();
            bool haveFresh = !BK[B_FRESH].empty();
            bool havePrefill = prefWork;
            int ready = (int)BK[B_ACT].size() + (int)BK[B_FRESH].size();

            // TDR stops at P POST and TPOT only averages gaps *between* tokens,
            // so the wait from P POST to a request's first token is scored by
            // nothing. Where the waiting-time term is what pays, that makes it
            // free to leave the whole cohort idle until prefill has drained,
            // and it keeps every prefill task -- which would otherwise sit on a
            // cloud a round needs, or on the edge between D PRE and D POST --
            // out of every gap that does get measured. Only the *start* of
            // decoding waits: a cohort already running is never held, since
            // that would stretch the very gaps this is protecting.
            bool holdStart = tpotBound && nPrefPend > 0 && nActive == 0 && !haveAct;

            bool fire = false;
            if ((haveAct || haveFresh) && !holdStart) {
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
                    // and only while there is something left to wait for. While
                    // a link-bound input stage is still feeding, the same holds
                    // at any latency share: every extra round bills its fixed
                    // k*LAT to the links whose drain rate sets the makespan, so
                    // clumps wait and coalesce into one round per return.
                    bool linkBoundIn = linkW >= edgeW && linkW * (double)K >= cloudW;
                    bool sync = latShare(ready) >= FRAG_LAT_SHARE ||
                                (nPrefPend > 0 && linkBoundIn &&
                                 WTP >= PIPE_SYNC_WTP && !(DBASE <= 0 && WC > 1e-9));
                    fire = (nDecFlight == 0) || !sync;
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
                if (gAllow > 1) {
                    // One round of the plan, not the whole pool: members left
                    // behind form the next round in antiphase. Longest open gap
                    // rides first so the stagger stays fair per request.
                    int seats = mDesign;
                    if ((int)BK[B_ACT].size() > seats) {
                        batch = BK[B_ACT];
                        nth_element(batch.begin(), batch.begin() + seats, batch.end(),
                                    [&](int a, int b) {
                                        return R[a].last_tok < R[b].last_tok;
                                    });
                        batch.resize(seats);
                    } else {
                        batch = BK[B_ACT];
                    }
                    int room = seats - (int)batch.size();
                    for (int i = (int)BK[B_FRESH].size() - 1; i >= 0 && room > 0;
                         --i, --room)
                        batch.push_back(BK[B_FRESH][i]);
                } else {
                    for (int rid : BK[B_ACT]) batch.push_back(rid);
                    // Admitting a request commits it to every later round, so
                    // the budget has to be spent against everyone already
                    // admitted -- not against nActive, which ignores members
                    // whose first token has not landed yet and so lets a whole
                    // burst of admissions through in the window before it does.
                    // That strict cap is a TPOT protection bought with
                    // throughput, so it only applies while the TPOT leg of dist
                    // is worth buying; where the TDR leg dominates,
                    // over-admission is free score.
                    int room = mDesign - (tdrDominated ? nActive : nCohort);
                    for (int i = (int)BK[B_FRESH].size() - 1; i >= 0 && room > 0;
                         --i, --room)
                        batch.push_back(BK[B_FRESH][i]);
                }
                if (!batch.empty()) {
                    sort(batch.begin(), batch.end());
                    as("E D PRE -1 ");
                    ai((long long)batch.size());
                    for (int rid : batch) {
                        ac(' ');
                        ai(rid);
                        if (!R[rid].joined) {
                            R[rid].joined = 1;
                            nCohort++;
                            if (R[rid].cloud >= 0) nJoinC[R[rid].cloud]++;
                        }
                        if (R[rid].cloud >= 0) nDecPend[R[rid].cloud]++;
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
            // Prefill cannot be preempted, so a piece running on a cloud that a
            // decode round needs delays that round by the rest of the piece --
            // and the piece cannot always be cut small, since a layer is
            // indivisible. Keeping new prefill off the clouds that are decoding
            // avoids the collision outright, and costs nothing while the other
            // clouds have room.
            bool avoidDec = tpotBound;
            if (avoidDec) {
                bool any = false;
                for (int i = 0; i < kuse; ++i)
                    if (!nJoinC[i]) any = true;
                avoidDec = any;
            }
            for (int i = 0; i < kuse; ++i) {
                if (avoidDec && nJoinC[i]) continue;
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
                    if (nDecPend[c] > 0) nDecPend[c]--;
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
            // This cloud is about to be asked for a D PROC by a round already
            // in flight. Its D PROC has priority above, but during the uplink
            // the cloud merely looks idle, and a prefill piece started here
            // delays the round by its whole duration.
            if (tpotBound && nDecPend[c] > 0) continue;
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
                // A decode round needs this cloud once per round and leaves the
                // rest of the round free here. Prefill longer than that free
                // window lands straight in a member's gap, so cut the piece to
                // the window. The extra S per piece is a throughput cost, which
                // is the term this regime is not being scored on.
                if (tpotBound) {
                    int per = max(1, (mDesign + K - 1) / K);
                    double slack =
                        TPOT_CHUNK_SLACK * (roundT(mDesign) - (S + tDproc.get(per)));
                    take = max(1, (int)floor(max(slack, perLayer) / max(perLayer, 1e-9)));
                    take = min(take, remain);
                }
                // Every piece pays S again, so only split when that overhead
                // stays under a few percent of the prefill it protects.
                int maxPieces = (int)floor(CHUNK_OVERHEAD * full / S);
                if (!tpotBound && maxPieces >= 2) {
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
                    if (!R[rid].joined) {
                        R[rid].joined = 1;
                        nCohort++;
                        if (R[rid].cloud >= 0) nJoinC[R[rid].cloud]++;
                    }
                    if (R[rid].cloud >= 0) nDecPend[R[rid].cloud]++;
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

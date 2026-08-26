#include <bits/stdc++.h>
using namespace std;

// Interactive scheduler for CF 2251A (Huawei ICPC 2026).
// Greedy decode-first + full decode batches, with least-loaded cloud pick.

enum State : int {
    NEW_REQ = 0,
    P_PRE_RUNNING,
    WAIT_PRE_UP,
    P_PROC_READY,
    P_PROC_RUNNING,
    WAIT_PRE_DOWN,
    PRE_DOWN_DONE,
    P_POST_RUNNING,
    DECODE_READY,
    D_PRE_RUNNING,
    WAIT_DEC_UP,
    DEC_UP_DONE,
    D_PROC_RUNNING,
    WAIT_DEC_DOWN,
    DEC_DOWN_DONE,
    D_POST_RUNNING,
    FINISHED
};

struct Request {
    int remote = -1;
    int lin = 1;
    int next_ls = 0;
    int tokens = 0;
    double arr_time = 0.0;
    double last_tok = 0.0;
    State st = State::NEW_REQ;
};

struct Col {
    vector<pair<int, double>> p;
    void add(int sz, double t) {
        if (t >= 0) p.push_back({sz, t});
    }
    void freeze() {
        sort(p.begin(), p.end());
        p.erase(unique(p.begin(), p.end(),
                       [](auto& a, auto& b) { return a.first == b.first; }),
                p.end());
    }
    double get(int m) const {
        if (p.empty()) return 1.0;
        if (m <= p.front().first) return p.front().second;
        if (m >= p.back().first) return p.back().second;
        int lo = 0, hi = (int)p.size() - 1;
        while (hi - lo > 1) {
            int mid = (lo + hi) >> 1;
            if (p[mid].first <= m) lo = mid;
            else hi = mid;
        }
        int s0 = p[lo].first, s1 = p[hi].first;
        double t0 = p[lo].second, t1 = p[hi].second;
        if (s1 == s0) return t0;
        return t0 + (t1 - t0) * (double)(m - s0) / (double)(s1 - s0);
    }
};

static vector<string> split_ws(const string& s) {
    vector<string> out;
    string x;
    stringstream ss(s);
    while (ss >> x) out.push_back(x);
    return out;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int K, bytesPerToken, numLayers;
    double S, latency, bandwidth;
    if (!(cin >> K >> S >> latency >> bandwidth >> bytesPerToken >> numLayers)) return 0;

    double SLO1, SLO2, tpUB, tpBase, distBase, wtp, wc;
    cin >> SLO1 >> SLO2 >> tpUB >> tpBase >> distBase >> wtp >> wc;

    Col ppre, pproc, ppost, dpre, dproc, dpost;
    int Ntbl;
    cin >> Ntbl;
    for (int i = 0; i < Ntbl; ++i) {
        int bsz;
        double a, b, c, d, e, f;
        cin >> bsz >> a >> b >> c >> d >> e >> f;
        ppre.add(bsz, a);
        pproc.add(bsz, b);
        ppost.add(bsz, c);
        dpre.add(bsz, d);
        dproc.add(bsz, e);
        dpost.add(bsz, f);
    }
    ppre.freeze();
    pproc.freeze();
    ppost.freeze();
    dpre.freeze();
    dproc.freeze();
    dpost.freeze();

    vector<Request> req;
    req.reserve(2048);
    vector<int> live;
    live.reserve(2048);
    bool edgeFree = true;
    vector<char> cloudFree(K, 1);
    vector<int> n_pre(K, 0), n_dec(K, 0);
    vector<double> lin_pre(K, 0.0);
    double avg_lout = 16.0;
    int fin_cnt = 0;
    double sum_lout = 0.0;

    auto ensure = [&](int rid) {
        if ((int)req.size() <= rid) req.resize(rid + 1);
    };

    auto go = [&](int rid, State ns) {
        State os = req[rid].st;
        int c = req[rid].remote;
        auto in_pre = [&](State s) {
            return s == State::NEW_REQ || s == State::P_PRE_RUNNING || s == State::WAIT_PRE_UP ||
                   s == State::P_PROC_READY || s == State::P_PROC_RUNNING ||
                   s == State::WAIT_PRE_DOWN || s == State::PRE_DOWN_DONE ||
                   s == State::P_POST_RUNNING;
        };
        if (c >= 0 && c < K) {
            if (in_pre(os) && !in_pre(ns)) {
                n_pre[c]--;
                lin_pre[c] -= req[rid].lin;
                n_dec[c]++;
            }
            if (os != State::FINISHED && ns == State::FINISHED && !in_pre(os)) n_dec[c]--;
        }
        req[rid].st = ns;
    };

    auto tdr_urg = [&](int i, double now) -> double {
        return (now - req[i].arr_time) / SLO1;
    };

    auto cloud_load = [&](int c) -> double {
        double avg_lin = n_pre[c] ? lin_pre[c] / n_pre[c] : 1.0;
        double pre = n_pre[c] * (S + pproc.get(max(1, (int)(avg_lin + 0.5))));
        double dec = n_dec[c] * (S + dproc.get(max(1, n_dec[c]))) *
                     (0.20 + 0.50 * wc) * max(0.5, avg_lout * 0.08);
        return pre + dec + (cloudFree[c] ? 0.0 : 0.05 * S);
    };

    int rr = 0;
    auto pick_cloud = [&]() -> int {
        int best = rr;
        double bl = cloud_load(rr);
        for (int i = 1; i < K; ++i) {
            int c = (rr + i) % K;
            double L = cloud_load(c);
            if (L + 1e-12 < bl) {
                bl = L;
                best = c;
            }
        }
        rr = (best + 1) % K;
        return best;
    };

    auto on_tdn = [&](const vector<string>& tok, double now) {
        string server = tok[1];
        string phase = tok[2];
        string type = tok[3];
        if (server == "E") edgeFree = true;
        else {
            int c = stoi(server.substr(1));
            if (0 <= c && c < K) cloudFree[c] = 1;
        }
        if (phase == "P") {
            int rid = -1;
            if (type == "PRE" || type == "POST") rid = stoi(tok[5]);
            else if (type == "PROC") rid = stoi(tok[7]);
            if (rid < 0) return;
            ensure(rid);
            if (type == "PRE") go(rid, State::WAIT_PRE_UP);
            else if (type == "PROC") {
                if (req[rid].next_ls >= numLayers) go(rid, State::WAIT_PRE_DOWN);
                else go(rid, State::P_PROC_READY);
            } else if (type == "POST") {
                req[rid].last_tok = now;
                go(rid, State::DECODE_READY);
            }
            return;
        }
        int m = stoi(tok[5]);
        for (int j = 0; j < m; ++j) {
            int rid = stoi(tok[6 + j]);
            ensure(rid);
            if (type == "PRE") go(rid, State::WAIT_DEC_UP);
            else if (type == "PROC") go(rid, State::WAIT_DEC_DOWN);
            else if (type == "POST") {
                req[rid].tokens++;
                req[rid].last_tok = now;
                go(rid, State::DECODE_READY);
            }
        }
    };

    auto on_xdn = [&](const vector<string>& tok) {
        string dir = tok[1];
        string type = tok[4];
        int m = stoi(tok[5]);
        for (int j = 0; j < m; ++j) {
            int rid = stoi(tok[6 + j]);
            ensure(rid);
            if (type == "PRE") {
                if (dir == "UP") go(rid, State::P_PROC_READY);
                else go(rid, State::PRE_DOWN_DONE);
            } else {
                if (dir == "UP") go(rid, State::DEC_UP_DONE);
                else go(rid, State::DEC_DOWN_DONE);
            }
        }
    };

    while (true) {
        string first;
        if (!(cin >> first)) return 0;
        if (first == "END") return 0;
        double now = stod(first);
        int eventCount;
        cin >> eventCount;
        string dummy;
        getline(cin, dummy);

        for (int ev = 0; ev < eventCount; ++ev) {
            string line;
            getline(cin, line);
            auto tok = split_ws(line);
            if (tok.empty()) continue;
            if (tok[0] == "ARR") {
                int rid = stoi(tok[1]);
                int lin = stoi(tok[2]);
                ensure(rid);
                req[rid].lin = lin;
                req[rid].arr_time = now;
                req[rid].last_tok = now;
                req[rid].next_ls = 0;
                req[rid].tokens = 0;
                req[rid].remote = -1;
                req[rid].st = State::NEW_REQ;
                live.push_back(rid);
            } else if (tok[0] == "TDN") {
                on_tdn(tok, now);
            } else if (tok[0] == "XDN") {
                on_xdn(tok);
            } else if (tok[0] == "FIN") {
                int rid = stoi(tok[1]);
                ensure(rid);
                sum_lout += req[rid].tokens;
                fin_cnt++;
                avg_lout = sum_lout / max(1, fin_cnt);
                go(rid, State::FINISHED);
            }
        }

        vector<string> ans;

        vector<int> v_dpost, v_dpre, v_ppost, v_ppre;
        v_dpost.reserve(64);
        v_dpre.reserve(64);
        v_ppost.reserve(16);
        v_ppre.reserve(16);
        vector<vector<int>> v_dproc(K), v_pproc(K);
        size_t wlive = 0;
        for (size_t k = 0; k < live.size(); ++k) {
            int i = live[k];
            if (req[i].st == State::FINISHED) continue;
            live[wlive++] = i;
            switch (req[i].st) {
                case State::DEC_DOWN_DONE: v_dpost.push_back(i); break;
                case State::DECODE_READY: v_dpre.push_back(i); break;
                case State::PRE_DOWN_DONE: v_ppost.push_back(i); break;
                case State::NEW_REQ: v_ppre.push_back(i); break;
                case State::DEC_UP_DONE:
                    if (req[i].remote >= 0) v_dproc[req[i].remote].push_back(i);
                    break;
                case State::P_PROC_READY:
                    if (req[i].remote >= 0) v_pproc[req[i].remote].push_back(i);
                    break;
                default: break;
            }
        }
        live.resize(wlive);

        int best_ppost = -1;
        double best_ppost_u = -1.0;
        for (int rid : v_ppost) {
            double u = tdr_urg(rid, now);
            if (u > best_ppost_u) {
                best_ppost_u = u;
                best_ppost = rid;
            }
        }

        if (edgeFree && !v_dpost.empty()) {
            for (int rid : v_dpost) go(rid, State::D_POST_RUNNING);
            string cmd = "E D POST -1 " + to_string(v_dpost.size());
            for (int rid : v_dpost) cmd += " " + to_string(rid);
            ans.push_back(cmd);
            edgeFree = false;
        }

        if (edgeFree && best_ppost != -1) {
            edgeFree = false;
            go(best_ppost, State::P_POST_RUNNING);
            ans.push_back("E P POST " + to_string(req[best_ppost].remote) + " " +
                          to_string(best_ppost));
        }

        if (edgeFree && !v_dpre.empty()) {
            for (int rid : v_dpre) go(rid, State::D_PRE_RUNNING);
            string cmd = "E D PRE -1 " + to_string(v_dpre.size());
            for (int rid : v_dpre) cmd += " " + to_string(rid);
            ans.push_back(cmd);
            edgeFree = false;
        }

        if (edgeFree && !v_ppre.empty()) {
            int best = -1;
            double bu = -1e100;
            for (int rid : v_ppre) {
                double u = tdr_urg(rid, now);
                if (u > bu) {
                    bu = u;
                    best = rid;
                }
            }
            if (best != -1) {
                int c = pick_cloud();
                edgeFree = false;
                req[best].remote = c;
                n_pre[c]++;
                lin_pre[c] += req[best].lin;
                go(best, State::P_PRE_RUNNING);
                ans.push_back("E P PRE " + to_string(c) + " " + to_string(best));
            }
        }

        for (int c = 0; c < K; ++c) {
            if (!cloudFree[c]) continue;
            if (!v_dproc[c].empty()) {
                cloudFree[c] = 0;
                for (int rid : v_dproc[c]) go(rid, State::D_PROC_RUNNING);
                string cmd = "C" + to_string(c) + " D PROC " + to_string(c) + " " +
                             to_string(v_dproc[c].size());
                for (int rid : v_dproc[c]) cmd += " " + to_string(rid);
                ans.push_back(cmd);
                continue;
            }
            if (v_pproc[c].empty()) continue;
            int best = -1;
            double bu = -1e100;
            for (int rid : v_pproc[c]) {
                double u = tdr_urg(rid, now);
                if (u > bu) {
                    bu = u;
                    best = rid;
                }
            }
            if (best == -1) continue;
            int ls = req[best].next_ls;
            int nly = numLayers - ls;
            int le = ls + nly;
            cloudFree[c] = 0;
            req[best].next_ls = le;
            go(best, State::P_PROC_RUNNING);
            ans.push_back("C" + to_string(c) + " P PROC " + to_string(ls) + " " + to_string(le) +
                          " " + to_string(c) + " " + to_string(best));
        }

        cout << ans.size() << '\n';
        for (const string& s : ans) cout << s << '\n';
        cout.flush();
    }
}

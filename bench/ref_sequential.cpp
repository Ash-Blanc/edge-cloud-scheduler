// One-request-at-a-time reference schedule, matching the description of how the
// judge derives tp_base and dist_base. Used only by tests/sim.py to calibrate.
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int K, bpt, layers;
    double S, lat, bw;
    if (!(cin >> K >> S >> lat >> bw >> bpt >> layers)) return 0;
    double a, b, c, d, e, f, g;
    cin >> a >> b >> c >> d >> e >> f >> g;
    int N;
    cin >> N;
    for (int i = 0; i < N; ++i) {
        int bs;
        double v[6];
        cin >> bs >> v[0] >> v[1] >> v[2] >> v[3] >> v[4] >> v[5];
    }

    enum { ARR, PPRE, PPROC_R, PPROC, PDOWN, PPOST_R, PPOST, DIDLE, DPRE, DUP, DPROC_R, DPROC, DDOWN, DPOST_R, DPOST, FIN };
    vector<int> st;
    vector<int> cl;
    auto ensure = [&](int rid) {
        if ((int)st.size() <= rid) {
            st.resize(rid + 1, ARR);
            cl.resize(rid + 1, -1);
        }
    };
    int cur = -1;  // the single request being driven
    vector<int> pending;

    auto split = [](const string& s) {
        vector<string> o;
        string x;
        stringstream ss(s);
        while (ss >> x) o.push_back(x);
        return o;
    };

    while (true) {
        string first;
        if (!(cin >> first)) return 0;
        if (first == "END") return 0;
        int ec;
        cin >> ec;
        string dummy;
        getline(cin, dummy);
        for (int i = 0; i < ec; ++i) {
            string line;
            getline(cin, line);
            auto t = split(line);
            if (t.empty()) continue;
            if (t[0] == "ARR") {
                int rid = stoi(t[1]);
                ensure(rid);
                st[rid] = ARR;
                pending.push_back(rid);
            } else if (t[0] == "FIN") {
                int rid = stoi(t[1]);
                ensure(rid);
                st[rid] = FIN;
                if (cur == rid) cur = -1;
            } else if (t[0] == "TDN") {
                string ph = t[2], ty = t[3];
                if (ph == "P") {
                    int rid = (ty == "PROC") ? stoi(t[7]) : stoi(t[5]);
                    ensure(rid);
                    if (ty == "PRE") st[rid] = DUP;          // waiting on UP xfer
                    else if (ty == "PROC") st[rid] = PDOWN;  // waiting on DOWN xfer
                    else st[rid] = DIDLE;
                } else {
                    int m = stoi(t[5]);
                    for (int j = 0; j < m; ++j) {
                        int rid = stoi(t[6 + j]);
                        ensure(rid);
                        if (ty == "PRE") st[rid] = DUP;
                        else if (ty == "PROC") st[rid] = DDOWN;
                        else st[rid] = DIDLE;
                    }
                }
            } else if (t[0] == "XDN") {
                bool up = (t[1] == "UP");
                bool pre = (t[4] == "PRE");
                int m = stoi(t[5]);
                for (int j = 0; j < m; ++j) {
                    int rid = stoi(t[6 + j]);
                    ensure(rid);
                    if (pre) st[rid] = up ? PPROC_R : PPOST_R;
                    else st[rid] = up ? DPROC_R : DPOST_R;
                }
            }
        }

        if (cur == -1) {
            for (size_t i = 0; i < pending.size(); ++i) {
                int rid = pending[i];
                if (st[rid] != FIN) {
                    cur = rid;
                    pending.erase(pending.begin() + i);
                    break;
                }
            }
        }

        vector<string> ans;
        if (cur != -1) {
            int rid = cur;
            switch (st[rid]) {
                case ARR:
                    cl[rid] = 0;
                    st[rid] = PPRE;
                    ans.push_back("E P PRE 0 " + to_string(rid));
                    break;
                case PPROC_R:
                    st[rid] = PPROC;
                    ans.push_back("C0 P PROC 0 " + to_string(layers) + " 0 " + to_string(rid));
                    break;
                case PPOST_R:
                    st[rid] = PPOST;
                    ans.push_back("E P POST 0 " + to_string(rid));
                    break;
                case DIDLE:
                    st[rid] = DPRE;
                    ans.push_back("E D PRE -1 1 " + to_string(rid));
                    break;
                case DPROC_R:
                    st[rid] = DPROC;
                    ans.push_back("C0 D PROC 0 1 " + to_string(rid));
                    break;
                case DPOST_R:
                    st[rid] = DPOST;
                    ans.push_back("E D POST -1 1 " + to_string(rid));
                    break;
                default: break;
            }
        }
        cout << ans.size() << '\n';
        for (auto& s : ans) cout << s << '\n';
        cout.flush();
    }
}

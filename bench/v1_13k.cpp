#include <bits/stdc++.h>
using namespace std;

enum class State {
    NEW_REQ,
    P_PRE_RUNNING,
    WAIT_PRE_UP,
    PRE_UP_DONE,
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
    int lin = 0;
    double arr_time = 0.0;
    State st = State::NEW_REQ;
};

static vector<string> split_ws(const string& s) {
    stringstream ss(s);
    vector<string> out;
    string x;
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
    int N;
    cin >> N;
    for (int i = 0; i < N; ++i) {
        int batchSize;
        double a, b, c, d, e, f;
        cin >> batchSize >> a >> b >> c >> d >> e >> f;
    }

    vector<Request> req;
    bool edgeFree = true;
    vector<bool> cloudFree(K, true);
    int nextRemote = 0;

    auto ensure_req = [&](int rid) {
        if ((int)req.size() <= rid) req.resize(rid + 1);
    };

    auto on_tdn = [&](const vector<string>& tok) {
        string server = tok[1];
        string phase = tok[2];
        string type = tok[3];
        if (server == "E") edgeFree = true;
        else {
            int c = stoi(server.substr(1));
            if (0 <= c && c < K) cloudFree[c] = true;
        }
        if (phase == "P") {
            int rid = -1;
            if (type == "PRE" || type == "POST") rid = stoi(tok[5]);
            else if (type == "PROC") rid = stoi(tok[7]);
            if (rid >= 0) {
                ensure_req(rid);
                if (type == "PRE") req[rid].st = State::WAIT_PRE_UP;
                else if (type == "PROC") req[rid].st = State::WAIT_PRE_DOWN;
                else if (type == "POST") req[rid].st = State::DECODE_READY;
            }
            return;
        }
        int m = stoi(tok[5]);
        for (int j = 0; j < m; ++j) {
            int rid = stoi(tok[6 + j]);
            ensure_req(rid);
            if (type == "PRE") req[rid].st = State::WAIT_DEC_UP;
            else if (type == "PROC") req[rid].st = State::WAIT_DEC_DOWN;
            else if (type == "POST") req[rid].st = State::DECODE_READY;
        }
    };

    auto on_xdn = [&](const vector<string>& tok) {
        string dir = tok[1];
        string type = tok[4];
        int m = stoi(tok[5]);
        for (int j = 0; j < m; ++j) {
            int rid = stoi(tok[6 + j]);
            ensure_req(rid);
            if (type == "PRE") {
                if (dir == "UP") req[rid].st = State::PRE_UP_DONE;
                else req[rid].st = State::PRE_DOWN_DONE;
            } else {
                if (dir == "UP") req[rid].st = State::DEC_UP_DONE;
                else req[rid].st = State::DEC_DOWN_DONE;
            }
        }
    };

    while (true) {
        string first;
        if (!(cin >> first)) return 0;
        if (first == "END") return 0;
        double current_time = stod(first);
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
                ensure_req(rid);
                req[rid].lin = lin;
                req[rid].arr_time = current_time;
                req[rid].st = State::NEW_REQ;
            } else if (tok[0] == "TDN") on_tdn(tok);
            else if (tok[0] == "XDN") on_xdn(tok);
            else if (tok[0] == "FIN") {
                int rid = stoi(tok[1]);
                ensure_req(rid);
                req[rid].st = State::FINISHED;
            }
        }
        vector<string> ans;
        if (edgeFree) {
            vector<int> batch;
            for (int i = 0; i < (int)req.size(); ++i)
                if (req[i].st == State::DEC_DOWN_DONE) batch.push_back(i);
            if (!batch.empty()) {
                edgeFree = false;
                for (int rid : batch) req[rid].st = State::D_POST_RUNNING;
                string cmd = "E D POST -1 " + to_string(batch.size());
                for (int rid : batch) cmd += " " + to_string(rid);
                ans.push_back(cmd);
            }
        }
        if (edgeFree) {
            int best_rid = -1;
            double best_urg = -1.0;
            for (int i = 0; i < (int)req.size(); ++i) {
                if (req[i].st == State::PRE_DOWN_DONE) {
                    double u = (current_time - req[i].arr_time) / SLO1;
                    if (u > best_urg) { best_urg = u; best_rid = i; }
                }
            }
            if (best_rid != -1) {
                edgeFree = false;
                req[best_rid].st = State::P_POST_RUNNING;
                ans.push_back("E P POST " + to_string(req[best_rid].remote) + " " + to_string(best_rid));
            }
        }
        if (edgeFree) {
            vector<int> batch;
            for (int i = 0; i < (int)req.size(); ++i)
                if (req[i].st == State::DECODE_READY) batch.push_back(i);
            if (!batch.empty()) {
                edgeFree = false;
                for (int rid : batch) req[rid].st = State::D_PRE_RUNNING;
                string cmd = "E D PRE -1 " + to_string(batch.size());
                for (int rid : batch) cmd += " " + to_string(rid);
                ans.push_back(cmd);
            }
        }
        if (edgeFree) {
            int best_rid = -1;
            double best_urg = -1.0;
            for (int i = 0; i < (int)req.size(); ++i) {
                if (req[i].st == State::NEW_REQ) {
                    double u = (current_time - req[i].arr_time) / SLO1;
                    if (u > best_urg) { best_urg = u; best_rid = i; }
                }
            }
            if (best_rid != -1) {
                int c = nextRemote;
                nextRemote = (nextRemote + 1) % K;
                edgeFree = false;
                req[best_rid].remote = c;
                req[best_rid].st = State::P_PRE_RUNNING;
                ans.push_back("E P PRE " + to_string(c) + " " + to_string(best_rid));
            }
        }
        for (int c = 0; c < K; ++c) {
            if (cloudFree[c]) {
                vector<int> batch;
                for (int i = 0; i < (int)req.size(); ++i)
                    if (req[i].remote == c && req[i].st == State::DEC_UP_DONE) batch.push_back(i);
                if (!batch.empty()) {
                    cloudFree[c] = false;
                    for (int rid : batch) req[rid].st = State::D_PROC_RUNNING;
                    string cmd = "C" + to_string(c) + " D PROC " + to_string(c) + " " + to_string(batch.size());
                    for (int rid : batch) cmd += " " + to_string(rid);
                    ans.push_back(cmd);
                }
            }
            if (cloudFree[c]) {
                int best_rid = -1;
                double best_urg = -1.0;
                for (int i = 0; i < (int)req.size(); ++i) {
                    if (req[i].remote == c && req[i].st == State::PRE_UP_DONE) {
                        double u = (current_time - req[i].arr_time) / SLO1;
                        if (u > best_urg) { best_urg = u; best_rid = i; }
                    }
                }
                if (best_rid != -1) {
                    cloudFree[c] = false;
                    req[best_rid].st = State::P_PROC_RUNNING;
                    ans.push_back("C" + to_string(c) + " P PROC 0 " + to_string(numLayers) + " " + to_string(c) + " " + to_string(best_rid));
                }
            }
        }
        cout << ans.size() << '\n';
        for (const string& s : ans) cout << s << '\n';
        cout.flush();
    }
}

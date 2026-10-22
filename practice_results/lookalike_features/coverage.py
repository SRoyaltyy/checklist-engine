"""Coverage ledger: union of six_bucket_map_v5_1 (13,169) + master.csv (819, dedupe by id) + path bank v2 (5,716) + chart-picture v2 -> TESTED / NOT_READY with reason."""
import sys, os, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from build import TMP, SQ, HARD
CB = "/workspace/checklist_brainstorm"; OUT = os.path.dirname(os.path.abspath(__file__))
cells = pd.read_parquet(f"{TMP}/cells.parquet", columns=["ticker"]); ans = {}
for k in ["JG", "NB", "TR", "SHARED", "PB2", "MPV"]:
    z = np.load(f"{TMP}/A_{k}.npz", allow_pickle=True); nz = (z["A"] > 0).sum(0)
    for i, n in zip(z["ids"], nz): b = str(i).split("|")[0]; ans[b] = max(ans.get(b, 0), int(n))
S = pd.read_csv(f"{CB}/map_v5/six_bucket_map_v5_1.csv", dtype=str); M = pd.read_csv(f"{CB}/master.csv", dtype=str)
PB = pd.read_csv(f"{CB}/path_bank_v2/PATH_BANK_V2.csv", dtype=str)
PV = {"Candlestick", "Moving averages", "Overbought/oversold", "Volume", "Relative strength", "52w hi/lo", "Price return", "Bollinger/volatility", "Money flow", "Gap", "Prior-day structure", "Own history", "Sector relative strength", "Industry group"}
rows = []
MPV_NR = {"SEC-JA-031": "needs after-hours prints of industry peers", "STR-NB-005": "needs intraday last-hour bars", "STR-NB-006": "needs intraday VWAP",
          "STR-NB-007": "needs earnings dates (AVWAP anchor) not on box point-in-time", "STR-NB-011": "needs LULD halt records",
          "HST-NB-004": "needs 10 years of same-month history; price file starts 2020-01-02"}
def st(i, n_ans, why_missing):
    if i in ans: return ("TESTED", f"answered on {ans[i]:,} setup cells") if ans[i] > 0 else ("NOT_READY", "engine row present but NR on every 2020-24 setup cell (source has no 2020-24 history)")
    return ("NOT_READY", why_missing)
for r in S.itertuples():
    s, why = st(r.row_id.split("|")[0], None, f"no 2020-24 answer: {r.in_engine_counts}" if r.in_engine_counts != "yes" else "listed in engine but no reader output in universe chunks")
    rows.append(("six_bucket_map_v5_1", r.row_id, r.indicator, s, why))
for r in M[~M.id.isin(S.row_id)].itertuples():
    kbo = str(getattr(r, "_10"))
    if r.id in ans and ans[r.id] > 0: rows.append(("master.csv", r.id, f"{r.data_type}: {r.variant}", "TESTED", f"ported formula (master_pv.py), answered on {ans[r.id]:,} setup cells")); continue
    if r.id in MPV_NR: why = MPV_NR[r.id]
    elif not kbo.startswith("Yes"): why = f"not known before 09:25 ET on D ({kbo})"
    elif r.data_type in PV: why = "price/volume computable, but master free-text definition not yet ported to a deterministic formula; covered in spirit by path bank v2 / sheet rows of the same family (not counted as tested)"
    else: why = f"needs {r.data_type} data not on box point-in-time for 2020-24"
    rows.append(("master.csv", r.id, f"{r.data_type}: {r.variant}", "NOT_READY", why))
for r in PB.itertuples():
    if r.kind == "label": rows.append(("path_bank_v2", r.id, r.rule, "NOT_READY", "multi-class label (not YES/NO); its yes/no cuts are tested"))
    else: s, why = st(r.id, None, "not computed"); rows.append(("path_bank_v2", r.id, r.rule, s, why))
for q in SQ: rows.append(("chart_picture_v2", q, "story question", "TESTED", "all setup cells"))
for q in HARD: rows.append(("chart_picture_v2", q, "chart-pass check", "SETUP", "defines the setup (criteria), not a difference candidate"))
C = pd.DataFrame(rows, columns=["list", "id", "label", "status", "reason"]); C.to_csv(f"{OUT}/coverage_ledger.csv.gz", index=False)
T = C.groupby(["list", "status"]).size().unstack(fill_value=0); print(T); print(C[C.status == "NOT_READY"].groupby(["list", "reason"]).size().sort_values(ascending=False).head(15))
L = ["", "## Coverage ledger (every row of six_bucket_map_v5_1 ∪ master.csv ∪ path bank v2 ∪ chart-picture v2) — `coverage_ledger.csv.gz`", "", "| list | " + " | ".join(T.columns) + " |", "|---" * (len(T.columns) + 1) + "|"]
L += [f"| {i} | " + " | ".join(f"{v:,}" for v in r) + " |" for i, r in T.iterrows()]
L += ["", "NOT_READY reasons:", ""] + [f"- {a}: {b} — {n:,}" for (a, b), n in C[C.status == "NOT_READY"].groupby(["list", "reason"]).size().sort_values(ascending=False).items()]
open(f"{TMP}/coverage.md", "w").write("\n".join(L) + "\n")

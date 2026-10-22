#!/usr/bin/env python3
"""Cheap post-pass: per stock-morning YES counts per (meaning x lens) from stored 2-bit chunks + any tag files in engine/out/tags/*_tags.csv
(question_id, meaning, lens). Re-run any time tags change; no rebuild. Stock columns = all ids (ticker-dep + shared broadcast + TR);
mkt_* columns = ticker-free (shared) ids only. TR multi-horizon rows count once per horizon N that is YES. Also n_ready per cell."""
import sys, glob, re, numpy as np, pandas as pd
sys.path.insert(0, '.'); from engine_year import unpack, CHUNKS
y = int(sys.argv[1]); ROOT = CHUNKS.parent.parent.parent
# tags are (re)read at count time: James polarity, New Bot, Grok, Theme Radar (when present). Lens = sheet column verbatim.
SH = pd.read_csv(ROOT / "merged_draft_v8.2.csv", dtype=str).set_index("id").lens.fillna("none")
NORM = {"bearish": "loud_bearish", "warning": "quiet_warning", "loud_bearish": "loud_bearish", "quiet_warning": "quiet_warning",
        "bullish": "bullish", "asterisk": "asterisk", "neutral": "neutral"}
src = []
jp = ROOT / "v8src/James-v5.5f-polarity.csv"
if jp.exists():
    j = pd.read_csv(jp, dtype=str); mc0 = "meaning" if "meaning" in j else ("polarity" if "polarity" in j else None)
    if mc0: src.append(pd.DataFrame({"row_id": j.row_id, "meaning": j[mc0]}))
for f in sorted(glob.glob(str(ROOT / "engine/out/tags/*_tags.csv"))):
    t = pd.read_csv(f, dtype=str); rid = "row_id" if "row_id" in t else "question_id"; mc = "meaning" if "meaning" in t else "polarity"
    t = t.drop_duplicates(rid)
    src.append(pd.DataFrame({"row_id": t[rid], "meaning": t[mc]}))
TAGS = [str(jp)] + sorted(glob.glob(str(ROOT / "engine/out/tags/*_tags.csv")))
T = pd.concat(src).drop_duplicates("row_id", keep="last"); T["meaning"] = T.meaning.str.strip().str.lower().map(NORM).fillna("neutral")
T["lens"] = T.row_id.map(SH).fillna("none"); T = T.rename(columns={"row_id": "question_id"})
LENS = [l for l in (sys.argv[2].split(";") if len(sys.argv) > 2 else []) if l]   # optional: meaning x lens columns on demand
T["cat"] = T.meaning
if LENS:
    X = T[T.lens.isin(LENS)].copy(); X["cat"] = X.meaning + "__" + X.lens; T = pd.concat([T, X])
cats = sorted(T.cat.unique()); ci = {c: i for i, c in enumerate(cats)}
def onehot(ids):
    ids = [i.split("|")[0] for i in ids]; M = np.zeros((len(ids), len(cats)), np.int16); tg = T.groupby("question_id").cat.apply(list)
    for j, q in enumerate(ids):
        for c in tg.get(q, []): M[j, ci[c]] = 1
    return M, int(sum(q in tg.index for q in ids))
sh = np.load(CHUNKS / f"{y}__SHARED.npz"); S = unpack(sh["packed"], len(sh["ids"])); MS, cov_s = onehot(list(sh["ids"]))
mkt = (S == 2).astype(np.int16) @ MS; sdates = list(sh["dates"]); sdi = {d: i for i, d in enumerate(sdates)}
out = []
for f in sorted(glob.glob(str(CHUNKS / f"{y}__*.npz"))):
    if "SHARED" in f or "__TR__" in f: continue
    z = np.load(f); ids = list(z["ids"]); M, cov_d = onehot(ids); tk = z["tickers"]; ds = z["dates"]; nd = len(ds)
    P = z["packed"]; cnt = np.concatenate([(unpack(P[i:i+100000], len(ids)) == 2).astype(np.int16) @ M for i in range(0, len(P), 100000)])
    di = np.tile(np.arange(nd), len(tk)); cnt = cnt + mkt[[sdi[d] for d in ds]][di]
    df = pd.DataFrame(cnt, columns=cats); df.insert(0, "ticker", np.repeat(tk, nd)); df.insert(1, "date", np.tile(ds, len(tk)))
    out.append(df)
D = pd.concat(out, ignore_index=True)
# TR chunks (if present): add per-key YES counts
for f in sorted(glob.glob(str(CHUNKS / f"{y}__TR__*.npz"))):
    z = np.load(f); keys = list(z["keys"]); M, _ = onehot(keys); P = z["packed"]; cnt = np.concatenate([(unpack(P[i:i+50000], len(keys)) == 2).astype(np.int16) @ M for i in range(0, len(P), 50000)])
    t = pd.DataFrame(cnt, columns=cats); t["ticker"] = z["ticker"]; t["date"] = z["answer_date"]
    D = D.set_index(["ticker", "date"]).add(t.groupby(["ticker", "date"]).sum(), fill_value=0).reset_index()
mk = pd.DataFrame(mkt, columns=["mkt__" + c for c in cats]); mk["date"] = sdates
D = D.merge(mk, on="date", how="left")
D[[c for c in D.columns if c not in ("ticker","date")]] = D[[c for c in D.columns if c not in ("ticker","date")]].astype("int16")
D.to_parquet(CHUNKS / (f"{y}__COUNTS.parquet" if not LENS else f"{y}__COUNTS_bylens.parquet"), index=False)
print(f"counts {y} rows={len(D)} cats={len(cats)} tag_files={[f.split('/')[-1] for f in TAGS]} tagged_shared_ids={cov_s} tagged_dep_ids={cov_d}")

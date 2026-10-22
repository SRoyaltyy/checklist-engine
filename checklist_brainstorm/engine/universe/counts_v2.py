#!/usr/bin/env python3
"""Counts v2 (room spec 2026-10-22 ~11:57 HKT). Cheap post-pass over stored 2-bit chunks; tags re-read at run time.
Tags: james_tags.csv, theme-radar_tags.csv, new-bot_tags.csv, grok_tags.csv (sha256 checked). asterisk -> context.
Groups = scope (mkt = ticker-free ids, stk = ticker-dependent ids) x source x lens (source's own tag lens) x meaning.
Per group: yes, ready (YES or NO), frac = yes/ready. Context rows are caveats, not votes:
 lean_bull_share = bull_yes / (bull_yes + loud_bearish_yes + quiet_warning_yes) over all scopes/sources that morning;
 ctx_opp_{source}|{lens} = YES context rows whose own lean is opposite the morning lean (share>=0.5 -> count bear-lean context).
Context lean: New Bot context_lean; others from sheet yes_means. Excludes new-bot_excluded_inference.csv rows.
Outputs: chunks/{y}__COUNTS2_MKT.parquet (date x mkt groups) and chunks/{y}__COUNTS2_STK__{sector}.parquet (ticker,date x stk groups + lean + ctx_opp)."""
import pyarrow as pa, pyarrow.parquet as pq
import sys, glob, hashlib, re, numpy as np, pandas as pd
sys.path.insert(0, '.'); from engine_year import unpack, CHUNKS
y = int(sys.argv[1]); TD = CHUNKS.parent.parent / "out/tags"; ROOT = CHUNKS.parent.parent.parent
FP = {"james_tags.csv": "11a45eb7", "theme-radar_tags.csv": "ac295dcf", "new-bot_tags.csv": "1849cb7c"}
for f, p in FP.items():
    h = hashlib.sha256(open(TD / f, "rb").read()).hexdigest(); assert h.startswith(p), f"fingerprint mismatch {f} {h}"
SRC = {"james_tags.csv": "james", "theme-radar_tags.csv": "theme-radar", "new-bot_tags.csv": "new-bot", "grok_tags.csv": "grok"}
sheet = pd.read_csv(ROOT / "merged_draft_v8.2.csv", dtype=str).set_index("id")["yes_means (bullish/bearish)"].str.lower().fillna("")
excl = set(pd.read_csv(TD / "new-bot_excluded_inference.csv", dtype=str).row_id)
T = []
for f, s in SRC.items():
    t = pd.read_csv(TD / f, dtype=str); t["source"] = s
    t["key"] = t.row_id + ("|" + t.N.fillna("0") if "N" in t else "")
    if "context_lean" not in t: t["context_lean"] = t.row_id.map(lambda r: "bullish" if sheet.get(r, "").startswith("bull") else ("bearish" if sheet.get(r, "").startswith("bear") else "none"))
    T.append(t[["row_id", "key", "source", "meaning", "lens", "context_lean"]])
T = pd.concat(T); T = T[~T.row_id.isin(excl)]; T["meaning"] = T.meaning.replace({"asterisk": "context"}); T["lens"] = T.lens.fillna("none")
byrow = T.drop_duplicates("row_id").set_index("row_id"); bykey = T.set_index("key")
VOTE = ["bullish", "loud_bearish", "quiet_warning"]

def groups(ids, scope):
    """ids may be 'row' or 'row|N'. Returns vote onehot (ids x G), names, ctx bull/bear onehots (ids x H), ctx names, meaning arrays."""
    rec = []
    for q in ids:
        r = bykey.loc[q] if q in bykey.index else (byrow.loc[q.split("|")[0]] if q.split("|")[0] in byrow.index else None)
        if isinstance(r, pd.DataFrame): r = r.iloc[0]
        rec.append(None if r is None else (r.source, r.lens, r.meaning, r.context_lean))
    gv = sorted({f"{scope}|{a}|{b}|{c}" for x in rec if x for a, b, c, _ in [x] if c in VOTE + ["neutral"]})
    gc = sorted({f"{a}|{b}" for x in rec if x for a, b, c, _ in [x] if c == "context"})
    Gv = np.zeros((len(ids), len(gv)), np.float32); Gb = np.zeros((len(ids), len(gc)), np.float32); Gr = np.zeros_like(Gb)
    gvi = {g: i for i, g in enumerate(gv)}; gci = {g: i for i, g in enumerate(gc)}
    mean = np.array([x[2] if x else "" for x in rec])
    for j, x in enumerate(rec):
        if not x: continue
        a, b, c, l = x
        if c == "context":
            if l == "bullish": Gb[j, gci[f"{a}|{b}"]] = 1
            elif l == "bearish": Gr[j, gci[f"{a}|{b}"]] = 1
        else: Gv[j, gvi[f"{scope}|{a}|{b}|{c}"]] = 1
    return Gv, gv, Gb, Gr, gc, mean

def tally(codes, Gv, Gb, Gr, mean):
    yes = (codes == 2).astype(np.float32); rdy = (codes > 0).astype(np.float32)
    vb = yes @ (mean == "bullish").astype(np.float32); vr = yes @ np.isin(mean, ["loud_bearish", "quiet_warning"]).astype(np.float32)
    return yes @ Gv, rdy @ Gv, yes @ Gb, yes @ Gr, vb, vr

# market-wide (per date)
sh = np.load(CHUNKS / f"{y}__SHARED.npz"); sids = list(sh["ids"]); sdates = list(sh["dates"]); S = unpack(sh["packed"], len(sids))
Gv, gv, Gb, Gr, gc_m, mm = groups(sids, "mkt"); my, mr, mcb, mcr, mvb, mvr = tally(S, Gv, Gb, Gr, mm)
M = pd.DataFrame({"date": sdates})
for i, g in enumerate(gv): M[g + "|yes"] = my[:, i].astype(np.int16); M[g + "|ready"] = mr[:, i].astype(np.int16); M[g + "|frac"] = np.where(mr[:, i] > 0, my[:, i] / np.maximum(mr[:, i], 1), np.nan).astype(np.float32)
M.to_parquet(CHUNKS / f"{y}__COUNTS2_MKT.parquet", index=False)
sdi = {d: i for i, d in enumerate(sdates)}; nst = 0
for f in sorted(glob.glob(str(CHUNKS / f"{y}__*.npz"))):
    if "SHARED" in f or "__TR__" in f: continue
    z = np.load(f); ids = list(z["ids"]); tk = z["tickers"]; ds = z["dates"]; nd = len(ds); P = z["packed"]
    Gv, gv, Gb, Gr, gc, ms = groups(ids, "stk"); W = None; nrow = 0; sec = f.split("__")[-1][:-4]
    for i in range(0, len(P), 25000):
        C = unpack(P[i:i + 25000], len(ids)); sy, sr, scb, scr, svb, svr = tally(C, Gv, Gb, Gr, ms)
        di = np.array([sdi[d] for d in ds])[np.arange(i, i + len(C)) % nd]
        vb = svb + mvb[di]; vr = svr + mvr[di]; share = np.where(vb + vr > 0, vb / np.maximum(vb + vr, 1), np.nan)
        bull = np.nan_to_num(share, nan=0.5) >= 0.5
        d = {"ticker": np.repeat(tk, nd)[i:i + len(C)], "date": np.tile(ds, len(tk))[i:i + len(C)], "lean_bull_share": share.astype(np.float32),
             "votes_bull_yes": vb.astype(np.int16), "votes_bear_yes": vr.astype(np.int16)}
        for k, g in enumerate(gv):
            d[g + "|yes"] = sy[:, k].astype(np.int16); d[g + "|ready"] = sr[:, k].astype(np.int16)
            d[g + "|frac"] = np.where(sr[:, k] > 0, sy[:, k] / np.maximum(sr[:, k], 1), np.nan).astype(np.float32)
        allc = sorted(set(gc) | set(gc_m))
        for g in allc:
            sb = scb[:, gc.index(g)] if g in gc else 0; sR = scr[:, gc.index(g)] if g in gc else 0
            mb = mcb[di, gc_m.index(g)] if g in gc_m else 0; mR = mcr[di, gc_m.index(g)] if g in gc_m else 0
            d["ctx_opp|stk|" + g] = np.where(bull, sR, sb).astype(np.int16); d["ctx_opp|mkt|" + g] = np.where(bull, mR, mb).astype(np.int16)
        tb = pa.Table.from_pandas(pd.DataFrame(d), preserve_index=False)
        if W is None: W = pq.ParquetWriter(CHUNKS / f"{y}__COUNTS2_STK__{sec}.parquet", tb.schema, compression="zstd")
        W.write_table(tb); nrow += len(C); del C, tb, d
    W.close(); nst += nrow
    print(f"stk {sec} rows={nrow}", flush=True)
print(f"COUNTS2 {y} mkt_dates={len(M)} mkt_groups={len(gv)} stk_rows={nst}")

# ---- Theme Radar chunks (if assembled): stock-specific groups keyed row|N; lean recomputed with JG+TR votes ----
for f in sorted(glob.glob(str(CHUNKS / f"{y}__TR__*.npz"))):
    sec = f.split("__TR__")[-1][:-4]; base_sec = re.sub(r"_part\d+$", "", sec)
    V = pd.concat([pd.read_parquet(p, columns=["ticker", "date", "votes_bull_yes", "votes_bear_yes"]) for p in glob.glob(str(CHUNKS / f"{y}__COUNTS2_STK__{base_sec}*.parquet"))]).set_index(["ticker", "date"])
    if base_sec != sec: V = V[V.index.get_level_values(0).isin(set(np.load(f)["ticker"]))]
    z = np.load(f); keys = list(z["keys"]); P = z["packed"]; tk = z["ticker"]; ad = z["answer_date"]
    Gv, gv, Gb, Gr, gc, ms = groups(keys, "stk"); W = None; nrow = 0
    for i in range(0, len(P), 20000):
        C = unpack(P[i:i + 20000], len(keys)); sy, sr, scb, scr, svb, svr = tally(C, Gv, Gb, Gr, ms)
        t_, a_ = tk[i:i + len(C)], ad[i:i + len(C)]
        jv = V.reindex(pd.MultiIndex.from_arrays([t_, a_])); jb = jv.votes_bull_yes.fillna(0).values; jr = jv.votes_bear_yes.fillna(0).values
        vb = svb + jb; vr = svr + jr; share = np.where(vb + vr > 0, vb / np.maximum(vb + vr, 1), np.nan); bull = np.nan_to_num(share, nan=0.5) >= 0.5
        d = {"ticker": t_, "date": a_, "lean_bull_share_all": share.astype(np.float32), "tr_votes_bull_yes": svb.astype(np.int16), "tr_votes_bear_yes": svr.astype(np.int16)}
        for k, g in enumerate(gv):
            d[g + "|yes"] = sy[:, k].astype(np.int16); d[g + "|ready"] = sr[:, k].astype(np.int16)
            d[g + "|frac"] = np.where(sr[:, k] > 0, sy[:, k] / np.maximum(sr[:, k], 1), np.nan).astype(np.float32)
        for k, g in enumerate(gc): d["ctx_opp|stk|" + g] = np.where(bull, scr[:, k], scb[:, k]).astype(np.int16)
        tb = pa.Table.from_pandas(pd.DataFrame(d), preserve_index=False)
        if W is None: W = pq.ParquetWriter(CHUNKS / f"{y}__COUNTS2_TR__{sec}.parquet", tb.schema, compression="zstd")
        W.write_table(tb); nrow += len(C)
    W.close(); print(f"tr {sec} rows={nrow} groups={len(gv)}", flush=True)

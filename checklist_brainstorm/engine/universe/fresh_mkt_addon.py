#!/usr/bin/env python3
"""ADD-ON (Grok Bot, 2026-10-22): FRESH for MARKET-WIDE quiet_warning ids.
fresh.py reads only per-stock STK chunks ({y}__<sector>.npz, 1,478 ticker-dependent ids). Ticker-free ids (incl. James's
market-wide Outlier gap / Outlier follow-up rows) live in shared/{y}.parquet tier=='ind' and were never read, so those groups
showed 0 YES. This script builds the same features from the shared tier, one row per date (identical for every stock that day;
broadcast by joining on date). Same definitions as fresh.py: fresh = YES today & NO previous session; jump_z vs prior 20 sessions,
min 10, NaN if std==0. Does not touch existing chunks/COUNTS/FRESH files.
Output: chunks/{y}__FRESH_MKT_ADDON.parquet  cols: date, <source>|<lens>|qw_{fresh,yes,ready,frac,jump_z}"""
import sys, hashlib, numpy as np, pandas as pd
from pathlib import Path
H = Path(__file__).resolve().parent; TD = H.parent / "out/tags"; y = int(sys.argv[1])
assert hashlib.sha256(open(TD/"grok_tags.csv","rb").read()).hexdigest() == "505f452c65cdabda1576f978ad9a76be5acc546b4b41d0268caeb05d14f58ad7"
excl = set(pd.read_csv(TD/"new-bot_excluded_inference.csv", dtype=str).row_id)
T = []
for f, s in {"james_tags.csv": "james", "grok_tags.csv": "grok"}.items():
    t = pd.read_csv(TD/f, dtype=str); t["source"] = s; T.append(t[["row_id","source","meaning","lens"]])
T = pd.concat(T); T = T[~T.row_id.isin(excl)].drop_duplicates("row_id"); T["lens"] = T.lens.fillna("none")
qw = T[T.meaning == "quiet_warning"].set_index("row_id")
sh = pd.read_parquet(H/"shared"/f"{y}.parquet"); sh = sh[(sh.tier == "ind") & sh.row_id.isin(qw.index)]
C = sh.pivot(index="date", columns="row_id", values="code").sort_index().fillna(0).astype(np.uint8)
P = C.shift(1).fillna(0).astype(np.uint8)
d = {"date": pd.to_datetime(C.index.astype(str))}
for (src, lens), g in qw.loc[C.columns].groupby(["source","lens"]):
    c = C[g.index].values; p = P[g.index].values; k = f"{src}|{lens}"
    yes = (c == 2).sum(1); rdy = (c > 0).sum(1); fr = pd.Series(np.where(rdy > 0, yes/np.maximum(rdy,1), np.nan))
    sh1 = fr.shift(1); m = sh1.rolling(20, min_periods=10).mean(); sd = sh1.rolling(20, min_periods=10).std()
    d[f"{k}|qw_fresh"] = ((c == 2) & (p == 1)).sum(1).astype(np.int16); d[f"{k}|qw_yes"] = yes.astype(np.int16)
    d[f"{k}|qw_ready"] = rdy.astype(np.int16); d[f"{k}|qw_frac"] = fr.values.astype(np.float32)
    d[f"{k}|qw_jump_z"] = ((fr - m)/sd.where(sd > 0)).values.astype(np.float32)
D = pd.DataFrame(d); out = H/"chunks"/f"{y}__FRESH_MKT_ADDON.parquet"; D.to_parquet(out, index=False)
print(f"FRESH_MKT_ADDON {y} dates={len(D)} ids={C.shape[1]} groups={(D.shape[1]-1)//5} -> {out.name}")

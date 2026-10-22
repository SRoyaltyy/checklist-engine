#!/usr/bin/env python3
"""COUNTS2 for EARN add-on: only New Bot nbx-EARN-* rows from new-bot_earn_tags.csv."""
import sys, json, glob, re, os
from pathlib import Path
import numpy as np, pandas as pd, pyarrow as pa, pyarrow.parquet as pq
HERE = Path(__file__).resolve().parent; ENG = HERE.parent; CH = HERE / "chunks"
sys.path.insert(0, str(HERE)); from nb_year import unpack
T = pd.read_csv(ENG / "out/tags/new-bot_earn_tags.csv").set_index("row_id")
def scope(rid): return "stk"
def run(year):
    for fn in sorted(glob.glob(str(CH / f"{year}__EARN__*.parquet"))):
        o = fn.replace("__EARN__", "__COUNTS2_EARN__")
        meta = json.load(open(fn.replace(".parquet", ".json"))); ids = meta["ids"]
        DF = pd.read_parquet(fn); W = None
        for a in range(0, len(DF), 40000):
            df = DF.iloc[a:a + 40000]
            C = unpack(np.stack([np.frombuffer(b, np.uint8) for b in df.packed]), len(ids))
            tg = T.reindex(ids); mean = tg.meaning.values; lens = tg.lens.fillna("none").values
            sc = np.array([scope(r) for r in ids])
            Y = C == 2; R = C > 0
            bull = Y[:, mean == "bullish"].sum(1); bear = Y[:, np.isin(mean, ["loud_bearish", "quiet_warning"])].sum(1)
            share = np.where(bull + bear > 0, bull / np.maximum(bull + bear, 1), np.nan)
            out = {"ticker": df.ticker.values, "date": df.date.values, "lean_bull_share": share.astype(np.float32),
                   "votes_bull_yes": bull.astype(np.int16), "votes_bear_yes": bear.astype(np.int16)}
            keys = sorted({(s, l, m) for s, l, m in zip(sc, lens, mean) if isinstance(m, str) and m != "context"})
            for s, l, m in keys:
                j = (sc == s) & (lens == l) & (mean == m); g = f"{s}|new-bot|{l}|{m}"
                y = Y[:, j].sum(1); r = R[:, j].sum(1)
                out[g + "|yes"] = y.astype(np.int16); out[g + "|ready"] = r.astype(np.int16)
                out[g + "|frac"] = np.where(r > 0, y / np.maximum(r, 1), np.nan).astype(np.float32)
            cl = tg.context_lean.fillna("none").values; isbull = share >= 0.5
            for s, l in sorted({(s, l) for s, l, m in zip(sc, lens, mean) if m == "context"}):
                jb = (sc == s) & (lens == l) & (mean == "context") & (cl == "bullish")
                jr = (sc == s) & (lens == l) & (mean == "context") & (cl == "bearish")
                out[f"ctx_opp|{s}|new-bot|{l}"] = np.where(isbull, Y[:, jr].sum(1), Y[:, jb].sum(1)).astype(np.int16)
            t = pa.table(out)
            W = W or pq.ParquetWriter(o + ".tmp", t.schema); W.write_table(t)
        W.close(); os.replace(o + ".tmp", o); print(o, flush=True)
if __name__ == "__main__":
    run(int(sys.argv[1]))

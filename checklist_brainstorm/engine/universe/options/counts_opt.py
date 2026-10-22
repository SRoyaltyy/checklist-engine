#!/usr/bin/env python3
"""COUNTS2 for options rows: chunks/{y}__OPT__{sec}.parquet -> chunks/{y}__COUNTS2_OPT__{sec}.parquet.
Groups stk|grok-options|lens|meaning with yes/ready/frac (all rows) and yes_fresh/ready_fresh/frac_fresh (stale=0 only),
so spike / z-score work can exclude carried-forward (stale) readings. stale & lag passed through."""
import sys, json, glob, os
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; U = HERE.parent; CH = U / "chunks"
sys.path.insert(0, str(U)); from nb_year import unpack
T = pd.read_csv(U.parent / "out/tags/options_tags.csv").set_index("row_id")
def run(y):
    for fn in sorted(glob.glob(str(CH / f"{y}__OPT__*.parquet"))):
        ids = json.load(open(fn.replace(".parquet", ".json")))["ids"]; df = pd.read_parquet(fn)
        C = unpack(np.stack([np.frombuffer(b, np.uint8) for b in df.packed]), len(ids)); tg = T.reindex(ids)
        fr = (df.stale.values == 0)[:, None]; Y = C == 2; R = C > 0
        out = {"ticker": df.ticker.values, "date": df.date.values, "stale": df.stale.values, "lag": df.lag.values}
        for (l, m), g in tg.groupby(["lens", "meaning"]):
            j = np.isin(ids, g.index); k = f"stk|grok-options|{l}|{m}"
            for suf, msk in (("", True), ("_fresh", fr)):
                yy = (Y[:, j] & msk).sum(1); rr = (R[:, j] & msk).sum(1)
                out[k + "|yes" + suf] = yy.astype(np.int16); out[k + "|ready" + suf] = rr.astype(np.int16)
                out[k + "|frac" + suf] = np.where(rr > 0, yy / np.maximum(rr, 1), np.nan).astype(np.float32)
        pd.DataFrame(out).to_parquet(fn.replace("__OPT__", "__COUNTS2_OPT__"), index=False); print(fn, flush=True)
if __name__ == "__main__": run(int(sys.argv[1]))

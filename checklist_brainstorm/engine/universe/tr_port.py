#!/usr/bin/env python3
"""Theme Radar 528 OHLCV rows on the universe. Formulas = engine/out/tr_rebuildable/ohlcv_formulas.py, UNCHANGED;
only its emit() is redirected from long DataFrames to 2-bit codes. Non-rank rows: per ticker block (whole history).
'rank vs SPY/market' rows: per date over the WHOLE universe (slim frame of the needed columns), never per chunk.
Prices: universe_2020_survivors.parquet (split-only); SPY from etf_2015.parquet (longer history). Key (ticker, answer_date, row_id, N)."""
import sys, re, json, time, inspect, textwrap, argparse
from pathlib import Path
import numpy as np, pandas as pd, pyarrow.parquet as pq
HERE = Path(__file__).resolve().parent; TR = HERE.parent / "out/tr_rebuildable"
sys.path.insert(0, str(TR)); import ohlcv_formulas as of
sys.path.insert(0, str(HERE)); from engine_year import pack
PX = "/workspace/pricehist/universe_2020_survivors.parquet"; ETF = "/workspace/pricehist/etf_2015.parquet"
OUT = HERE / "tr"; OUT.mkdir(exist_ok=True)
src = textwrap.dedent(inspect.getsource(of.answer_rows))
new_emit = '''    def emit(rid, N, yes, ready, reason):
        yes = pd.Series(yes, index=F.index); ready = pd.Series(ready, index=F.index).fillna(False).astype(bool)
        code = np.where(~ready.to_numpy(), 0, np.where(yes.fillna(False).astype(bool).to_numpy(), 2, 1)).astype(np.uint8)
        out.append(((rid, N if N else 0), code[keep.to_numpy()]))
'''
src = re.sub(r"    def emit\(rid, N, yes, ready, reason\):\n(?:        .*\n)+?(?=\n    def anchor)", new_emit, src)
src = src.replace("return pd.concat(out, ignore_index=True) if out else pd.DataFrame()", "return out")
ns = dict(vars(of)); exec(src, ns); answer_codes = ns["answer_rows"]

def rows_all():
    st = pd.read_csv(TR / "row_status.csv"); ok = set(st[st.cat == "ohlcv_ok"].id)
    s = pd.read_csv(HERE.parent.parent / "merged_draft_v8.2.csv", dtype=str)
    return s[s.id.isin(ok)][["id", "variant", "lens", "timeframe", "strict_definition"]].reset_index(drop=True)

def spy():
    e = pd.read_parquet(ETF); e["ticker"] = e.ticker.astype(str); return e[e.ticker == "SPY"][["date", "close"]]

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--block", type=int, default=60); ap.add_argument("--only"); ap.add_argument("--tag", default="all"); a = ap.parse_args()
    R = rows_all(); rank = R[R.lens == "rank vs SPY/market"]; nonr = R[R.lens != "rank vs SPY/market"]
    sp = spy(); cal = of._calendar(pd.read_parquet(PX, columns=["ticker", "date"], filters=[("ticker", "in", ["SPY", "AAPL", "MSFT"])]))
    floor = pd.Timestamp("2020-01-02")
    tick = sorted(a.only.split(",")) if a.only else sorted(pq.read_table(PX, columns=["ticker"]).column(0).unique().to_pylist())
    t0 = time.time(); slim_cols = None; nb = 0
    for i in range(0, len(tick), a.block):
        bt = tick[i:i + a.block]; fn = OUT / f"{a.tag}_b{i:05d}.npz"
        if fn.exists(): continue
        df = pd.read_parquet(PX, columns=["ticker", "date", "open", "high", "low", "close", "volume"], filters=[("ticker", "in", bt)])
        df["ticker"] = df.ticker.astype(str)
        F = of.base_features(df, spy=sp, calendar=cal, history_floor=floor); F = F[F.ticker.isin(bt)].reset_index(drop=True)
        res = answer_codes(F, nonr, dates=None)
        keys = [k for k, _ in res]; codes = np.stack([c for _, c in res], 1)
        np.savez_compressed(fn, packed=pack(codes), ticker=F.ticker.to_numpy().astype(str), answer_date=F.answer_date.to_numpy().astype("datetime64[D]").astype(str),
                            keys=np.array([f"{r}|{n}" for r, n in keys]))
        # slim frame for universe-wide rank rows
        if slim_cols is None:
            used = set(re.findall(r'F\["(\w+)"\]', src)) | set(re.findall(r"F\['(\w+)'\]", src))
            slim_cols = [c for c in F.columns if c in ("ticker", "date", "answer_date") or F[c].dtype != object]
        F[slim_cols].astype({c: "float32" for c in slim_cols if F[c].dtype == "float64"}).to_parquet(OUT / f"{a.tag}_slim_b{i:05d}.parquet", index=False)
        nb += 1; print(f"block {i} tickers={len(bt)} rows={len(F)} keys={len(keys)} t={time.time()-t0:.0f}s", flush=True)
    print("NONRANK DONE", time.time() - t0, flush=True)

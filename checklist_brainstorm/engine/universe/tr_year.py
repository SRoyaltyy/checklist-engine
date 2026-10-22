#!/usr/bin/env python3
"""TR per-year: (1) rank-vs-SPY/market rows over the WHOLE universe for that year (needs same-date cross-section only),
(2) assemble nonrank block codes + rank codes into year x sector chunks (2-bit packed), keyed (ticker, answer_date, row_id|N)."""
import sys, glob, re, json, time, numpy as np, pandas as pd
sys.path.insert(0, '.'); import tr_port as T; from engine_year import pack, unpack, SECT, CHUNKS
y = int(sys.argv[1]); t0 = time.time()
R = T.rows_all(); rank = R[R.lens == "rank vs SPY/market"]
lo, hi = pd.Timestamp(f"{y}-01-01"), pd.Timestamp(f"{y}-12-31")
parts = [pd.read_parquet(f, filters=[("answer_date", ">=", lo), ("answer_date", "<=", hi)]) for f in sorted(glob.glob(str(T.OUT / "all_slim_b*.parquet")))]
F = pd.concat(parts, ignore_index=True); del parts
res = T.answer_codes(F, rank, dates=None)
rk = [f"{r}|{n}" for (r, n), _ in res]; RC = np.stack([c for _, c in res], 1)
rank_idx = pd.MultiIndex.from_arrays([F.ticker.astype(str).values, F.answer_date.values.astype("datetime64[D]").astype(str)])
rpos = pd.Series(np.arange(len(F)), index=rank_idx); del F
print(f"rank {y} rows={len(rpos)} keys={len(rk)} t={time.time()-t0:.0f}s", flush=True)
sect = pd.read_csv(SECT, usecols=["Ticker", "Sector"]).set_index("Ticker").Sector
acc = {}
for f in sorted(glob.glob(str(T.OUT / "all_b*.npz"))):
    z = np.load(f); keys = list(z["keys"]); ad = z["answer_date"]; m = (ad >= f"{y}-01-01") & (ad <= f"{y}-12-31")
    if not m.any(): continue
    C = unpack(z["packed"][m], len(keys)); tk = z["ticker"][m]; ad = ad[m]
    ri = rpos.reindex(pd.MultiIndex.from_arrays([tk, ad])).values
    RCb = np.where(np.isnan(ri)[:, None], 0, RC[np.nan_to_num(ri).astype(int)]).astype(np.uint8)
    full = np.concatenate([C, RCb], 1); sec = pd.Series(tk).map(sect).fillna("Unknown").values
    for s in np.unique(sec):
        k = sec == s; acc.setdefault(s, []).append((tk[k], ad[k], pack(full[k])))
allkeys = keys + rk; tot = 0
for s, L0 in acc.items():
  groups_, cur, n = [], [], 0
  for it in L0:
      cur.append(it); n += len(it[0])
      if n >= 400000: groups_.append(cur); cur, n = [], 0
  if cur: groups_.append(cur)
  for pi, L in enumerate(groups_):
    nm = re.sub(r'[^A-Za-z0-9]', '_', s) + (f"_part{pi}" if len(groups_) > 1 else "")
    fn = CHUNKS / f"{y}__TR__{nm}.npz"
    tk = np.concatenate([a for a, _, _ in L]); ad = np.concatenate([b for _, b, _ in L]); P = np.concatenate([c for _, _, c in L])
    np.savez_compressed(fn, packed=P, ticker=tk, answer_date=ad, keys=np.array(allkeys)); del P
    json.dump(dict(year=y, sector=s, part=pi, owner="theme-radar", n_rows=int(len(tk)), n_tickers=int(len(set(tk))), n_keys=len(allkeys),
                   key="(ticker, answer_date, row_id|N)", codes="0=NR 1=NO 2=YES 2-bit packed", survivor_only=True, sector_map="current_backfilled",
                   price_source=T.PX, spy_source=T.ETF, price_adjust="split_only", rank_rows="computed per date over whole universe",
                   formulas="engine/out/tr_rebuildable/ohlcv_formulas.py (unchanged)"), open(str(fn).replace(".npz", ".json"), "w"), indent=1)
    tot += fn.stat().st_size
print(f"TR YEAR {y} sectors={len(acc)} bytes={tot} t={time.time()-t0:.0f}s", flush=True)

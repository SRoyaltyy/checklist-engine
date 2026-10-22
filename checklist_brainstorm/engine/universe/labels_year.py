"""Universe labels per year. ret_open_next_open = (open_{D+1} + div_{D+1}) / open_D - 1, where div_{D+1} is a dividend whose
ex-date is the next bar (holder at D's open owns it through D+1's ex-open). ret_open_close: open->close on D, no dividend
can go ex inside that interval (ex-dates take effect at the open). Dividends > 20% of open_D are capped at 20% and flagged.
Prices: universe_2020_survivors.parquet (split-only); dividends_2020.parquet (split-adjusted amounts)."""
import sys, numpy as np, pandas as pd
y = int(sys.argv[1]); PX = "/workspace/pricehist/universe_2020_survivors.parquet"
p = pd.read_parquet(PX, columns=["ticker", "date", "open", "close"], filters=[("date", ">=", pd.Timestamp(f"{y}-01-01")), ("date", "<=", pd.Timestamp(f"{y+1}-01-15"))])
p["ticker"] = p.ticker.astype(str); p = p.sort_values(["ticker", "date"]).reset_index(drop=True)
d = pd.read_parquet("/workspace/pricehist/dividends_2020.parquet"); d["ticker"] = d.ticker.astype(str)
d = d.groupby(["ticker", "ex_date"]).amount.sum().rename("div").reset_index().rename(columns={"ex_date": "date"})
p = p.merge(d, on=["ticker", "date"], how="left")
g = p.groupby("ticker", sort=False)
p["open_next"] = g.open.shift(-1); p["div_next"] = g["div"].shift(-1).fillna(0.0); p["date_next"] = g.date.shift(-1)
o = p.open.astype("float64")
cap = 0.2 * o; p["div_capped"] = p.div_next > cap; p["div_next"] = np.minimum(p.div_next, cap)
p["ret_open_next_open"] = (p.open_next + p.div_next) / o - 1
p["ret_open_close"] = p.close.astype("float64") / o - 1
p = p[(p.date.dt.year == y) & (o > 0)]
out = p[["ticker", "date", "ret_open_next_open", "ret_open_close", "div_next", "div_capped"]].astype({"ret_open_next_open": "float32", "ret_open_close": "float32", "div_next": "float32"})
out["ticker"] = out.ticker.astype("category")
out.attrs = {}
out.to_parquet(f"chunks/{y}__LABELS.parquet", index=False)
print(y, len(out), "with_div", int((out.div_next > 0).sum()), "capped", int(out.div_capped.sum()), "nan_next", int(out.ret_open_next_open.isna().sum()))

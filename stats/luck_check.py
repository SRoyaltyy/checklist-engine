"""Luck check for checklist answers (James).

Input: one row per trade with columns
  ticker, date (entry day D), ret (exit-rule-v1 return after 30bp/side fees),
  bench (same-day equal-weight filtered-universe return, same exit rule).
Output per answer: n, win%, avg win, avg loss, expected profit (ep),
excess = mean(ret - bench), and its standard error three ways:
  naive (iid), two-way clustered by ticker and date (Cameron-Gelbach-Miller),
  and a date-block bootstrap. z uses the LARGEST of the three, so trades on the
  same stock or the same day can't pass as independent tries.
Single-trade influence is capped by clipping excess at the 0.5/99.5 pct.
"""
import numpy as np, pandas as pd

def _cluster_var(e, g):
    s = pd.Series(e).groupby(np.asarray(g)).sum().values
    return (s**2).sum() / len(e)**2

def twoway_se(e, tick, date):
    e = e - e.mean()
    both = pd.Series(tick).astype(str).values + "|" + pd.Series(date).astype(str).values
    vt, vd = _cluster_var(e, tick), _cluster_var(e, date)
    v = vt + vd - _cluster_var(e, both)
    return float(np.sqrt(max(v, vt, vd)))

def block_bootstrap_se(e, date, block_days=20, reps=500, seed=0):
    rng = np.random.default_rng(seed)
    d = pd.to_datetime(pd.Series(date)).values.astype("datetime64[D]")
    days = np.unique(d)
    blocks = [days[i:i+block_days] for i in range(0, len(days), block_days)]
    idx = [np.flatnonzero(np.isin(d, b)) for b in blocks]
    means = []
    for _ in range(reps):
        ix = np.concatenate([idx[p] for p in rng.integers(0, len(blocks), len(blocks))])
        if len(ix): means.append(e[ix].mean())
    return float(np.std(means, ddof=1))

def score(trades, bar=5.4, min_win=0.40, cap_pct=(0.5, 99.5)):
    r = trades["ret"].to_numpy(float); b = trades["bench"].to_numpy(float)
    win = r > 0; n = len(r); w = win.mean()
    ex = np.clip(r - b, *np.percentile(r - b, cap_pct))
    aw = r[win].mean() if win.any() else 0.0
    al = -r[~win].mean() if (~win).any() else 0.0
    se_naive = ex.std(ddof=1) / np.sqrt(n)
    se_2w = twoway_se(ex, trades["ticker"].values, trades["date"].values)
    se_bs = block_bootstrap_se(ex, trades["date"].values)
    se = max(se_naive, se_2w, se_bs); z = ex.mean() / se if se > 0 else 0.0
    top = np.sort(r)[::-1][:max(1, n // 20)].sum(); tot = r.sum()
    return dict(n=n, win=w, avg_win=aw, avg_loss=al, ep=w*aw - (1-w)*al,
                excess=ex.mean(), se_naive=se_naive, se_twoway=se_2w, se_block=se_bs,
                z=z, top5_share=(top/tot if tot else np.nan),
                passes=bool(z >= bar and w >= min_win))

if __name__ == "__main__":
    # Self-test: pure same-day shocks, no real edge. Clustered SE must be far above naive.
    rng = np.random.default_rng(1); D = pd.bdate_range("2020-01-01", "2022-12-31")
    rows = [(t, d) for t in range(200) for d in D[rng.integers(0, len(D), 30)]]
    df = pd.DataFrame(rows, columns=["ticker", "date"])
    shock = pd.Series(rng.normal(0, .03, len(D)), index=D)
    df["bench"] = 0.0
    df["ret"] = shock.reindex(df.date).values + rng.normal(0, .05, len(df))
    out = score(df)
    print({k: (round(v, 5) if isinstance(v, float) else v) for k, v in out.items()})
    assert out["se_twoway"] > out["se_naive"] and not out["passes"]
    print("SELFTEST OK")

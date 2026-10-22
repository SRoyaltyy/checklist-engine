#!/usr/bin/env python3
"""Fresh Clean Rally screen. 2020-24 ONLY. No 2025-26 read."""
import pandas as pd, numpy as np, pyarrow.parquet as pq, gc
from scipy.stats import norm
from pathlib import Path

FEE = 0.006  # 30bp/side round trip
OUT = Path(__file__).resolve().parent
YR = ['2020', '2021', '2022', '2023', '2024']

# --- load feat (returns + buckets + OB gauges); assert sealed ---
need = ['ticker','date','close','r5','r20','r1','rsi14','mfi','ext20','year','b_atr','b_px','b_r1']
A = pd.read_parquet(OUT.parent / 'ohlcv' / 'feat.parquet', columns=need)
assert A.date.max() < '2025-01-01', A.date.max()
print('feat', A.shape, A.date.min(), A.date.max(), flush=True)

# --- open/high/low from local pricehist (no download); 2019 warmup + 2020-24 ---
px = pq.read_table(
    '/workspace/pricehist/universe_2020_survivors.parquet',
    columns=['ticker','date','open','high','low','close'],
    filters=[('date','>=',pd.Timestamp('2019-01-01')),('date','<',pd.Timestamp('2025-01-01'))],
).to_pandas()
assert px.date.max() < pd.Timestamp('2025-01-01')
px['ticker'] = px.ticker.astype(str)
px['date'] = px.date.dt.strftime('%Y-%m-%d')
px = px.drop_duplicates(['ticker','date']).sort_values(['ticker','date'])
# keep OHLC; drop pricehist close after merge (feat close is dividend-aware path already used for r*)
px = px.rename(columns={'close':'px_close'})
A = A.merge(px[['ticker','date','open','high','low']], on=['ticker','date'], how='inner')
del px; gc.collect()
assert A.date.max() < '2025-01-01'
print('merged', A.shape, flush=True)

A = A.sort_values(['ticker','date']).reset_index(drop=True)
T = A.ticker
g = A.groupby('ticker', sort=False)

def sh(s, k=1):
    return s.groupby(T, sort=False).shift(k)

C, O, H, L = A.close, A.open, A.high, A.low
# body green (close > open) — matches build.py g10 definition
grn = (C > O).astype(float)
A['grn'] = grn
# close-to-close return already in r1; use for magnitude dominance
up = A.r1.clip(lower=0)
dn = (-A.r1).clip(lower=0)

# trailing green streak (vectorized, group-aware)
is_g = grn.fillna(0).to_numpy(dtype=np.int8)
same = T.eq(T.shift()).fillna(False).to_numpy()
# new run whenever ticker changes OR green/red flips
prev_g = np.roll(is_g, 1); prev_g[0] = 0
flip = (is_g != prev_g) | (~same)
run_id = np.cumsum(flip.astype(np.int32))
pos = pd.Series(1, index=A.index).groupby(run_id).cumsum().to_numpy()
streak = np.where(is_g == 1, pos, 0).astype(np.int32)
A['gstreak'] = streak

# Prior quiet/down: 5d return before the streak started <= 0
# prior window ends at D - gstreak (day before streak start)
# ret from close[D-gstreak-5] to close[D-gstreak]
# Approximate: close / close.shift(gstreak) is end of streak / start-1 day before? 
# streak of k means days D-k+1..D are green. Day before streak = D-k.
# prior5 = close[D-k] / close[D-k-5] - 1
# Use shift by streak: for each row, look at close.shift(gstreak) / close.shift(gstreak+5) - 1
# Can't vectorize easily with varying shift; compute for max relevant streak 2..5
pc = {}
for k in range(0, 11):
    pc[k] = sh(C, k)
A['prior5_before_streak'] = np.nan
for k in (2, 3, 4, 5):
    # close at day before streak start = sh(C,k); 5 days before that = sh(C,k+5)
    base = pc[k]
    older = pc[k+5]
    val = base / older - 1
    A.loc[A.gstreak == k, 'prior5_before_streak'] = val[A.gstreak == k]

# For each N, rolling green ratio, up/dn sum, run, max single-day drop, max DD from local high
def roll_sum(s, n):
    return s.groupby(T, sort=False).transform(lambda x: x.rolling(n, min_periods=n).sum())

def roll_min(s, n):
    return s.groupby(T, sort=False).transform(lambda x: x.rolling(n, min_periods=n).min())

def roll_max(s, n):
    return s.groupby(T, sort=False).transform(lambda x: x.rolling(n, min_periods=n).max())

for N in (3, 5, 8):
    A[f'gsum{N}'] = roll_sum(grn, N)
    A[f'gratio{N}'] = A[f'gsum{N}'] / N
    A[f'upsum{N}'] = roll_sum(up, N)
    A[f'dnsum{N}'] = roll_sum(dn, N)
    # run over N sessions (close vs close N ago)
    A[f'run{N}'] = C / sh(C, N) - 1
    # max single-day down (most negative r1) in window
    A[f'maxdn{N}'] = roll_min(A.r1, N)  # most negative
    # max drawdown from local high within window using closes
    # rolling max of close, then (close/rollmax - 1) min over window ≈ worst DD to date within window end
    # Better: for each day in window, peak so far in window; DD = min(close/peak-1)
    # Approximate with close / roll_max(close,N) - 1 at end (only end-of-window DD, not intra)
    # True max DD: roll of (close / expanding max within window)
    # Use high for peak: min(L / roll_max(H,N) - 1) approx via close path
    peak = roll_max(C, N)
    A[f'dd_end{N}'] = C / peak - 1  # how far below window peak at D (0 if at peak)
    # worst intra-window close DD: min over window of (close_t / max_{window start..t} close - 1)
    # approximate: min(close)/max(close)-1 over window (path-independent lower bound of severity)
    A[f'dd_span{N}'] = roll_min(C, N) / peak - 1

print('features built', flush=True)

# Universe filter
A = A[(A.close >= 2) & A.b_atr.notna() & A.b_px.notna() & A.b_r1.notna()].copy()
A = A.reset_index(drop=True)
print('universe', A.shape, A.ticker.nunique(), flush=True)

cell = A.groupby(['date','b_px','b_atr','b_r1']).ngroup().values
nc = int(cell.max()) + 1
dt = A.date.values
yr = A.year.values

def piece_green(N, ratio=0.7, mag=2.0):
    """Good green:red: ratio >= 0.7 AND upsum >= mag * dnsum AND run > 0."""
    return (A[f'gratio{N}'] >= ratio) & (A[f'upsum{N}'] >= mag * A[f'dnsum{N}'].clip(lower=1e-9)) & (A[f'run{N}'] > 0)

def piece_pushback(N, frac=1/3):
    """Little pushback: no day down more than frac of the run; end DD small vs run."""
    run = A[f'run{N}']
    ok_run = run > 0.005  # need a real run to measure pushback against
    # max single-day drop magnitude <= frac * run
    day_ok = (-A[f'maxdn{N}']) <= (frac * run)
    # span DD magnitude <= frac * run
    dd_ok = (-A[f'dd_span{N}']) <= (frac * run)
    return ok_run & day_ok & dd_ok

def piece_not_ob():
    return (A.rsi14 <= 70) & (A.mfi <= 80) & (A.ext20 <= 0.10)

def piece_fresh(lo=2, hi=5):
    return (A.gstreak >= lo) & (A.gstreak <= hi)

def piece_prior_quiet():
    return A.prior5_before_streak.notna() & (A.prior5_before_streak <= 0)

rows = {}
# Full combo for each N, with/without prior quiet
for N in (3, 5, 8):
    g_ = piece_green(N)
    p_ = piece_pushback(N)
    o_ = piece_not_ob()
    f_ = piece_fresh(2, 5)
    q_ = piece_prior_quiet()
    rows[f'FULL-N{N}'] = g_ & p_ & o_ & f_
    rows[f'FULL-N{N}+priorQuiet'] = g_ & p_ & o_ & f_ & q_
    # Ablations of FULL-N5 as primary (drop one piece each)
    if N == 5:
        rows['ABL-dropGreen-N5'] = p_ & o_ & f_           # no green:red
        rows['ABL-dropPush-N5'] = g_ & o_ & f_             # no pushback
        rows['ABL-dropNotOB-N5'] = g_ & p_ & f_            # allow overbought
        rows['ABL-dropFresh-N5'] = g_ & p_ & o_            # any aged streak
        rows['ABL-onlyGreen-N5'] = g_
        rows['ABL-onlyPush-N5'] = p_
        rows['ABL-onlyNotOB'] = o_
        rows['ABL-onlyFresh'] = f_
        rows['ABL-Green+Fresh-N5'] = g_ & f_
        rows['ABL-Green+NotOB-N5'] = g_ & o_
        rows['ABL-Green+Push-N5'] = g_ & p_
        rows['ABL-NotOB+Fresh'] = o_ & f_
        # Freshness window variants on full
        rows['FULL-N5-fresh2to3'] = g_ & p_ & o_ & piece_fresh(2, 3)
        rows['FULL-N5-fresh4to5'] = g_ & p_ & o_ & piece_fresh(4, 5)
        rows['FULL-N5-fresh2to8'] = g_ & p_ & o_ & piece_fresh(2, 8)  # allow slightly older
        # Stricter green
        rows['FULL-N5-gratio0.8'] = piece_green(5, 0.8, 2.0) & p_ & o_ & f_
        rows['FULL-N5-mag3x'] = piece_green(5, 0.7, 3.0) & p_ & o_ & f_
        # Looser pushback (half of run)
        rows['FULL-N5-pushHalf'] = g_ & piece_pushback(5, 0.5) & o_ & f_

print('rows', len(rows), {k: int(v.sum()) for k,v in list(rows.items())[:6]}, flush=True)

out = []
for name, s in rows.items():
    y = s.fillna(False).values.astype(bool)
    for h in (5, 20):
        r = A[f'r{h}'].values
        ok = ~np.isnan(r)
        no = ok & ~y
        sm = np.bincount(cell[no], r[no], nc)
        n = np.bincount(cell[no], minlength=nc)
        i = np.where(y & ok & (n[cell] > 0))[0]
        if len(i) < 50 or len(np.unique(dt[i])) < 30:
            out.append(dict(row=name, h=h, n_obs=len(i), n_dates=len(np.unique(dt[i])) if len(i) else 0,
                            status='n<30 dates', side='long', resid=np.nan, boot_lo=np.nan, boot_hi=np.nan,
                            p=np.nan, raw_mean_after_fee=np.nan, win_after_fee=np.nan, win_vs_match=np.nan,
                            signs='.....', yes_rate=float(y.mean())))
            continue
        e = r[i] - sm[cell[i]] / n[cell[i]]
        raw = r[i]
        m = e.mean()
        dd = pd.Series(e - m).groupby(dt[i]).sum()
        se = np.sqrt((dd ** 2).sum()) / len(e)
        # date-clustered bootstrap
        gser = pd.Series(e).groupby(dt[i]).agg(['sum', 'count'])
        rng = np.random.default_rng(0)
        k = len(gser)
        b = [(lambda j: gser['sum'].values[j].sum() / gser['count'].values[j].sum())(rng.integers(0, k, k)) for _ in range(1000)]
        sg = 1 if m > 0 else -1
        ys = pd.Series(e).groupby(yr[i]).mean()
        yw = pd.Series((sg * raw - FEE) > 0).groupby(yr[i]).mean()
        out.append(dict(
            row=name, h=h, n_obs=len(i), n_dates=k, status='tested',
            side='long' if sg > 0 else 'short',
            resid=m, boot_lo=np.percentile(b, 2.5), boot_hi=np.percentile(b, 97.5),
            p=2 * norm.sf(abs(m / se)) if se > 0 else 1.0,
            raw_mean_after_fee=(sg * raw).mean() - FEE,
            win_after_fee=((sg * raw - FEE) > 0).mean(),
            win_vs_match=(sg * e > 0).mean(),
            signs=''.join('+' if ys.get(Y, 0) > 0 else '-' for Y in YR),
            yes_rate=float(y.mean()),
            **{f'y{Y}': ys.get(Y) for Y in YR},
            **{f'w{Y}': yw.get(Y) for Y in YR},
        ))

T = pd.DataFrame(out)
tested = T.status == 'tested'
ps = T.loc[tested, 'p'].values
o_ = np.argsort(ps)
n = len(ps)
bh = np.zeros(len(T), bool)
if n:
    th = ps[o_] <= 0.05 * np.arange(1, n + 1) / n
    if th.any():
        idxs = T.index[tested].values
        bh[idxs[o_[:np.where(th)[0].max() + 1]]] = True
T['bh'] = bh
T['nsame'] = [sum((c == '+') == (sd == 'long') for c in s) if isinstance(s, str) else 0
              for s, sd in zip(T.signs, T.side)]
T['ci_clear'] = np.where(T.side == 'long', T.boot_lo > 0, T.boot_hi < 0)
T['pass'] = tested & T.bh & T.ci_clear & (T.win_after_fee > 0.5) & (T.raw_mean_after_fee > 0) & (T.nsame >= 4)

T.to_csv(OUT / '2020_24_fresh_rally_score.csv', index=False, float_format='%.5f')
print('trials', tested.sum(), 'bh', T.bh.sum(), 'pass', T['pass'].sum(), flush=True)
pd.set_option('display.width', 220)
pd.set_option('display.max_rows', 100)
cols = ['row','h','n_obs','n_dates','side','resid','boot_lo','boot_hi','win_after_fee','raw_mean_after_fee','signs','bh','pass','yes_rate','status']
print(T[cols].to_string())

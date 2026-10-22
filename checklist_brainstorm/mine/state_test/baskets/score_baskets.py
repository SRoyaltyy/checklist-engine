#!/usr/bin/env python3
"""Same-day basket vs one-at-a-time. 2020-24 ONLY. No 2025-26 read."""
import pandas as pd, numpy as np, pyarrow.parquet as pq, glob, json, ast, gc, hashlib
from pathlib import Path
from scipy.stats import norm

ROOT = Path('/workspace/checklist_brainstorm/mine/state_test')
OUT = ROOT / 'baskets'
FEE = 0.006  # 30bp/side
YR = ['2020','2021','2022','2023','2024']
LEAN_CUT = 0.6205
assert True

# ---- load feat (needed cols only) ----
cols = ['ticker','date','close','r5','r20','r1','rvol','rv','gap','mfi','ext20','rsi14',
        'fade1','up5','b_atr','b_px','b_r1','year',
        'stoch','wr','cci','bbp','rsi2','upvs','g10','cmf']
A = pd.read_parquet(ROOT/'ohlcv'/'feat.parquet', columns=cols)
assert A.date.max() < '2025-01-01', A.date.max()
nb = pd.read_parquet(ROOT/'ohlcv'/'nb.parquet',
    columns=['ticker','date','nb4-HIS-NB-029-P5-POSQ','nb4-REL-NB-026-T1-THR',
             'nb4-PDS-NB-036-T20-RXS','nb4-PDS-NB-015-T1-EXT'])
A = A.merge(nb, on=['ticker','date'], how='left'); del nb
A = A.dropna(subset=['b_atr','b_px','b_r1']).reset_index(drop=True)
A = A[A.close >= 2].reset_index(drop=True)

# ---- OHLCV6 warnings (full-pass shorts; Manager-final 6) ----
A['sig_VOLJUMP'] = (A.rv > 2)
A['sig_RVOL5'] = (A.rvol >= 5)
A['sig_UP10'] = (A.r1 >= 0.10)
A['sig_NB029'] = (A['nb4-HIS-NB-029-P5-POSQ'] == 2)
A['sig_GAPDN'] = (A.gap <= -0.05)
A['sig_MFI80'] = (A.mfi > 80)
# OHLCV long candidates (BH+CI clear on at least one hold in 2020_24_ohlcv_score; win often <50%)
A['sig_OS_EXT'] = (A.ext20 < -0.10)
A['sig_OS_RSI'] = (A.rsi14 < 30)
A['sig_OS_MFI'] = (A.mfi < 20)
A['sig_LOW_UPVS'] = (A.upvs < 0.3)
A['sig_FEW_GREEN'] = (A.g10 <= 2)

ohlcv6 = ['sig_VOLJUMP','sig_RVOL5','sig_UP10','sig_NB029','sig_GAPDN','sig_MFI80']
long_cand = ['sig_OS_EXT','sig_OS_RSI','sig_OS_MFI','sig_LOW_UPVS','sig_FEW_GREEN']

# ---- warnspike from v5 states ----
ws = []
for y in range(2020, 2025):
    p = ROOT / f'states_{y}_v5.parquet'
    d = pd.read_parquet(p, columns=['ticker','date','lean','jumpz'])
    assert str(d.date.max())[:10] < '2025-01-01' or str(d.date.max())[:4] == str(y)
    d['date'] = d.date.astype(str).str[:10]
    d['sig_WARNSPIKE'] = (d.lean >= LEAN_CUT) & (d.jumpz >= 1.5)
    ws.append(d[['ticker','date','sig_WARNSPIKE','lean','jumpz']])
WS = pd.concat(ws, ignore_index=True); del ws
A = A.merge(WS, on=['ticker','date'], how='left')
A['sig_WARNSPIKE'] = A['sig_WARNSPIKE'].fillna(False).astype(bool)
del WS; gc.collect()

# ---- 00051-C from F4TR chunks 2020-24 only ----
Cdir = '/workspace/checklist_brainstorm/engine/universe/chunks/'
W = 'OWN-TR-00051-C'
def unpack(b, k):
    return np.stack([(b >> s) & 3 for s in (0, 2, 4, 6)], -1).reshape(b.shape[0], -1)[:, :k]
X = []
for y in range(2020, 2025):
    for f in sorted(glob.glob(Cdir + f'{y}__F4TR__*.parquet')):
        j = json.load(open(f[:-8] + '.json'))
        fid = j['ids'] if isinstance(j['ids'], list) else ast.literal_eval(j['ids'])
        if W not in fid: continue
        ix = fid.index(W)
        D = pd.read_parquet(f)
        D['date'] = D.date.astype(str).str[:10]
        assert D.date.max() < '2025-01-01'
        cc = unpack(np.stack([np.frombuffer(x, np.uint8) for x in D.packed]), len(fid))[:, ix]
        X.append(pd.DataFrame({'ticker': D.ticker.astype(str).values,
                               'date': D.date.values,
                               'o51': cc.astype('int8')}))
O51 = pd.concat(X, ignore_index=True); del X
A = A.merge(O51, on=['ticker','date'], how='left')
A['sig_O51'] = (A.o51 == 2)
A['o51_ready'] = A.o51.isin([1, 2])
del O51; gc.collect()

# event-start for O51 (first YES after non-YES)
A = A.sort_values(['ticker','date']).reset_index(drop=True)
y51 = A.sig_O51.fillna(False)
A['sig_O51_START'] = y51 & ~y51.groupby(A.ticker).shift(1, fill_value=False)

# ---- signal families ----
FAM = {
  'MIX_ANY': ohlcv6 + long_cand + ['sig_WARNSPIKE','sig_O51'],
  'LONG_ONLY': long_cand + ['sig_O51'],
  'SHORT_PKG': ohlcv6 + ['sig_WARNSPIKE'],  # trade SHORT
  'O51_ONLY': ['sig_O51'],
  'OHLCV6_ONLY': ohlcv6,
  'WARN_ONLY': ['sig_WARNSPIKE'],
}
# strength: count of lit signals in MIX_ANY + |r1| tiebreak
mix_cols = FAM['MIX_ANY']
for c in mix_cols:
    A[c] = A[c].fillna(False).astype(bool)
A['n_sig'] = A[mix_cols].sum(axis=1).astype('int16')
A['strength'] = A.n_sig.astype(float) + A.r1.abs().fillna(0).clip(0, 2) * 0.01

# matched-control cell id (all rows with bins; control = not in the day's selected set)
cell = A.groupby(['date','b_px','b_atr','b_r1']).ngroup().values
nc = int(cell.max()) + 1
dt = A.date.values; yr = A.year.values; tk = A.ticker.values
r5 = A.r5.values; r20 = A.r20.values

def stock_resid(mask, h):
    """mask: bool array of signal stock-days. Control = ~mask in same cell (all ready with return)."""
    r = r5 if h == 5 else r20
    ok = ~np.isnan(r)
    no = ok & ~mask
    s = np.bincount(cell[no], r[no], nc)
    n = np.bincount(cell[no], minlength=nc)
    ys = mask & ok & (n[cell] > 0)
    i = np.where(ys)[0]
    e = r[i] - s[cell[i]] / n[cell[i]]
    return i, e, r[i]

def date_cluster_stats(i, e, raw, side='long'):
    """side long: edge = +resid; short: edge = -resid for win."""
    if len(i) < 10:
        return None
    m = e.mean()
    dd = pd.Series(e - m).groupby(dt[i]).sum()
    se = np.sqrt((dd ** 2).sum()) / len(e)
    sgn = 1 if side == 'long' else -1
    # date-level basket later; stock-level win:
    win = ((sgn * raw - FEE) > 0).mean()
    ys = pd.Series(e).groupby(yr[i]).mean()
    signs = ''.join(('+' if ys.get(Y, 0) > 0 else '-') if Y in ys.index else '.' for Y in YR)
    return dict(n_obs=len(i), n_dates=int(pd.Series(dt[i]).nunique()), n_tickers=int(pd.Series(tk[i]).nunique()),
                resid=m, lo95=m - 1.96*se, hi95=m + 1.96*se, p=float(2*norm.sf(abs(m/max(se,1e-12)))),
                win_after_fee=float(win), signs=signs,
                **{f'y{Y}': float(ys.get(Y, np.nan)) for Y in YR})

def basket_from_mask(mask, h, side='long', min_n=1, top_n=None):
    """Build date-level equal-weight baskets from stock residuals.
    Matched control at stock level, then average into basket.
    top_n: keep top-N by strength within date.
    min_n: only dates with >= min_n names after top_n cut.
    """
    i, e, raw = stock_resid(mask, h)
    if len(i) == 0:
        return None, None
    df = pd.DataFrame({
        'date': dt[i], 'year': yr[i], 'ticker': tk[i],
        'resid': e, 'raw': raw, 'strength': A.strength.values[i],
        'idx': i
    })
    if top_n is not None:
        df = df.sort_values(['date','strength'], ascending=[True, False]).groupby('date', sort=False).head(top_n)
    # basket = equal weight of members that day
    g = df.groupby('date', sort=False)
    b = g.agg(resid=('resid','mean'), raw=('raw','mean'), n=('ticker','count'),
              year=('year','first')).reset_index()
    b = b[b.n >= min_n]
    if len(b) < 30:
        return b, None
    m = b.resid.mean()
    # date-clustered CI: each date is one obs; SE of mean
    se = b.resid.std(ddof=1) / np.sqrt(len(b))
    # also cluster-robust via sum-of-demeaned (same when 1 obs/date)
    sgn = 1 if side == 'long' else -1
    win = ((sgn * b.raw - FEE) > 0).mean()
    ys = b.groupby('year').resid.mean()
    signs = ''.join(('+' if ys.get(Y, 0) > 0 else '-') if Y in ys.index else '.' for Y in YR)
    # single-stock on the SAME names as in baskets
    kept = df[df.date.isin(b.date)]
    sm = kept.resid.mean()
    sdd = pd.Series(kept.resid - sm).groupby(kept.date).sum()
    sse = np.sqrt((sdd ** 2).sum()) / len(kept)
    swin = ((sgn * kept.raw - FEE) > 0).mean()
    sys = kept.groupby('year').resid.mean()
    ssigns = ''.join(('+' if sys.get(Y, 0) > 0 else '-') if Y in sys.index else '.' for Y in YR)
    basket_stat = dict(
        n_baskets=len(b), n_stock_obs=len(kept), n_tickers=kept.ticker.nunique(),
        mean_names=float(b.n.mean()), median_names=float(b.n.median()),
        resid=m, lo95=m-1.96*se, hi95=m+1.96*se, p=float(2*norm.sf(abs(m/max(se,1e-12)))),
        win_after_fee=float(win), raw_mean_after_fee=float(sgn*b.raw.mean()-FEE),
        signs=signs, **{f'y{Y}': float(ys.get(Y, np.nan)) for Y in YR}
    )
    single_stat = dict(
        n_obs=len(kept), n_dates=kept.date.nunique(), n_tickers=kept.ticker.nunique(),
        resid=sm, lo95=sm-1.96*sse, hi95=sm+1.96*sse, p=float(2*norm.sf(abs(sm/max(sse,1e-12)))),
        win_after_fee=float(swin), raw_mean_after_fee=float(sgn*kept.raw.mean()-FEE),
        signs=ssigns, **{f'y{Y}': float(sys.get(Y, np.nan)) for Y in YR}
    )
    # package minus single (same names): basket resid - single resid (should be ~0 if equal weight mean)
    # More meaningful: date-win of basket vs mean of stock wins; and variance reduction
    basket_stat['vs_single_resid_diff'] = m - sm  # ~0 by construction for equal-weight mean of same set
    # Better compare: basket date-level win vs single stock-level win; and basket CI width vs single
    basket_stat['single_win'] = float(swin)
    basket_stat['single_resid'] = sm
    basket_stat['single_lo95'] = sm-1.96*sse
    basket_stat['single_hi95'] = sm+1.96*sse
    basket_stat['beat_single_win'] = float(win) - float(swin)
    basket_stat['beat_single_raw'] = float(sgn*b.raw.mean()-FEE) - float(sgn*kept.raw.mean()-FEE)
    # diversification: std of date-basket raw vs std of stock raw
    basket_stat['basket_raw_std'] = float(b.raw.std())
    basket_stat['single_raw_std'] = float(kept.raw.std())
    return b, dict(basket=basket_stat, single=single_stat)

# ---- run trials ----
trials = []
# variants
variants = []
for fam, cols in FAM.items():
    side = 'short' if fam in ('SHORT_PKG','OHLCV6_ONLY','WARN_ONLY') else 'long'
    # SHORT_PKG / OHLCV6 / WARN are avoid flags → score as SHORT
    # MIX_ANY and LONG_ONLY as BUY (even though MIX includes shorts — Cyrus asked to mix)
    if fam == 'MIX_ANY':
        side = 'long'  # buy the mix as requested
    mask0 = np.zeros(len(A), dtype=bool)
    for c in cols:
        mask0 |= A[c].values
    for h in (5, 20):
        for min_n, top_n, tag in [
            (1, None, 'all'),
            (3, None, 'min3'),
            (5, None, 'min5'),
            (1, 5, 'top5'),
            (1, 10, 'top10'),
            (3, 5, 'min3_top5'),
        ]:
            variants.append((fam, side, h, mask0, min_n, top_n, tag))

print(f'universe {len(A)} rows, {A.ticker.nunique()} tickers, dates {A.date.nunique()}')
print(f'trials planned {len(variants)}')

rows = []
for fam, side, h, mask0, min_n, top_n, tag in variants:
    b, st = basket_from_mask(mask0, h, side=side, min_n=min_n, top_n=top_n)
    if st is None:
        rows.append(dict(family=fam, side=side, h=h, variant=tag, min_n=min_n,
                         top_n=top_n if top_n else 0, status='n<30 dates'))
        continue
    B, S = st['basket'], st['single']
    rows.append(dict(
        family=fam, side=side, h=h, variant=tag, min_n=min_n, top_n=top_n if top_n else 0,
        status='tested',
        n_baskets=B['n_baskets'], mean_names=B['mean_names'], median_names=B['median_names'],
        basket_resid=B['resid'], basket_lo=B['lo95'], basket_hi=B['hi95'], basket_p=B['p'],
        basket_win=B['win_after_fee'], basket_raw_af=B['raw_mean_after_fee'], basket_signs=B['signs'],
        single_n=S['n_obs'], single_resid=S['resid'], single_lo=S['lo95'], single_hi=S['hi95'],
        single_win=S['win_after_fee'], single_raw_af=S['raw_mean_after_fee'], single_signs=S['signs'],
        beat_win=B['beat_single_win'], beat_raw=B['beat_single_raw'],
        basket_raw_std=B['basket_raw_std'], single_raw_std=B['single_raw_std'],
        vol_ratio=B['basket_raw_std']/B['single_raw_std'] if B['single_raw_std'] else np.nan,
        **{f'b_y{Y}': B[f'y{Y}'] for Y in YR},
        **{f's_y{Y}': S[f'y{Y}'] for Y in YR},
    ))
    print(f'{fam} {side} h{h} {tag}: baskets={B["n_baskets"]} meanN={B["mean_names"]:.1f} '
          f'b_resid={B["resid"]*100:.2f}% win={B["win_after_fee"]*100:.1f}% | '
          f'single_resid={S["resid"]*100:.2f}% win={S["win_after_fee"]*100:.1f}%')

T = pd.DataFrame(rows)
tested = T[T.status=='tested'].copy()
# BH across tested basket_p
if len(tested):
    ps = tested.basket_p.values
    o_ = np.argsort(ps); n = len(ps); bh = np.zeros(n, bool)
    th = ps[o_] <= 0.05 * np.arange(1, n+1) / n
    if th.any():
        bh[o_[:np.where(th)[0].max()+1]] = True
    tested['bh'] = bh
    tested['ci_clear'] = np.where(tested.side=='long', tested.basket_lo>0, tested.basket_hi<0)
    tested['nsame'] = [sum((c=='+')==(sd=='long') for c in s if c!='.') for s,sd in zip(tested.basket_signs, tested.side)]
    tested['pass'] = tested.bh & tested.ci_clear & (tested.basket_win>0.5) & (tested.nsame>=4) & (tested.basket_raw_af>0)
    # does package beat single on win or raw after fee?
    tested['pkg_beats_single'] = (tested.beat_win > 0) | (tested.beat_raw > 0)
else:
    tested['bh'] = False; tested['pass'] = False

out = pd.concat([tested, T[T.status!='tested']], ignore_index=True)
out.to_csv(OUT/'2020_24_basket_score.csv', index=False, float_format='%.5f')

# per-date detail for main MIX_ANY h=5 all
b_main, st_main = basket_from_mask(
    np.logical_or.reduce([A[c].values for c in FAM['MIX_ANY']]), 5, side='long', min_n=1)
if b_main is not None:
    b_main.to_csv(OUT/'2020_24_basket_dates_MIX_h5.csv', index=False, float_format='%.5f')

# signal coverage
cov = {c: int(A[c].sum()) for c in mix_cols}
pd.Series(cov).to_csv(OUT/'signal_coverage.csv', header=['n_stock_days'])

print('DONE trials', len(tested), 'bh', int(tested['bh'].sum()) if len(tested) else 0,
      'pass', int(tested['pass'].sum()) if len(tested) else 0)
print('coverage', cov)

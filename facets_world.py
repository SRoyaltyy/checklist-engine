"""World snapshot builder (METHODOLOGY 0b 2026-10-25 12:30 HKT, world-snapshot order).

Builds a point-in-time per-ticker per-day column store: `world-2020-26-v1`.
Discipline: every column at day D uses only data with available_from_date < D.
Prices/indicators go up to the D-1 close (shift-by-one convention, same as the
engine: questions for day D read snapshot row D, which contains nothing from D).

Block A: full TA-Lib function set + all 61 candle patterns (auto-discovered from
the installed TA-Lib, OHLCV-fed only; anything needing other inputs is skipped and
listed in the coverage table).
Block K: market breadth (NH-NL / advance-decline / %%>200d) from breadth_2020_24.
Block F: FINRA twice-monthly short interest (I188) + daily short volume (I189),
release data-ext-2020-26-v1. SI keyed on publication_date < D (never settlement);
daily short volume published after 18:00 ET on date X -> usable next session
(strict date < D).
Block G: Nasdaq trading halts (I191) + Reg SHO threshold list (I190), same release.
Halts: only events with halt_date < D; the resume gap is used only when the
resume date is also < D (ongoing halts give halt_days/counts, gap stays blank).
Reg SHO: file for date d is published after the close of d -> usable next session
(strict date < D); membership is sticky, so regsho_on looks back 7 calendar days.
Block J: dividend/split EVENT dates (I196) from fetch_divsplits.py; bars are
already split-adjusted, events power 'in last N days' questions (strict < D).

Output: shard parquets world_shard_NNN.parquet keyed by (ticker, date), float32
for indicators, int8 for candle patterns (-100/0/100). A JSON sidecar per shard
lists the columns and provenance. Not a question module: groups 034+ read these
columns into yes/no / fixed buckets later.

Usage:
  python3 facets_world.py build --shard 0 --shards 8 --out world_out
  python3 facets_world.py coverage            # print TA-Lib coverage table
"""
import os, sys, json, argparse, warnings; warnings.filterwarnings('ignore')
os.environ.setdefault('GRID_FILE', '/nonexistent')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import talib
from talib import abstract
from datapaths import D

END = os.environ.get('WORLD_END', '2026-12-31')   # bars file decides the real end

# ---------------- TA-Lib auto-discovery (Block A) ----------------
def _feed(name):
    """Flatten the real abstract API's grouped input values, not group labels."""
    f = abstract.Function(name)
    spec = f.input_names
    if isinstance(spec, dict):
        names = []
        for value in spec.values():
            names.extend(value if isinstance(value, (list, tuple)) else [value])
    else:
        names = [spec] if isinstance(spec, str) else list(spec)
    names = list(dict.fromkeys(str(x).lower() for x in names))
    unknown = set(names) - {'open', 'high', 'low', 'close', 'volume', 'price'}
    if unknown:
        return None, 'needs ' + ','.join(sorted(unknown))
    return {name: None for name in names}, None


DISCOVERY_EXCLUSIONS = {}


def discover():
    """Discover every OHLCV-fed function, including all 61 candle patterns."""
    patterns = set(talib.get_function_groups().get('Pattern Recognition', []))
    out = {}
    for name in talib.get_functions():
        feed, reason = _feed(name)
        if feed is None:
            DISCOVERY_EXCLUSIONS[name] = reason
            continue
        out[name] = ('pattern' if name in patterns else 'indicator', list(feed))
    return out


COVERAGE_NOTE = None


def compute_talib(o, h, l, c, v, funcs):
    """Unshifted values; ticker_frame applies the one-bar availability shift.

    Never suppress a failed function. Multiple outputs from the real API are
    a list, unlike the tuple used by the old stub regression test.
    """
    feed = {'open': o, 'high': h, 'low': l, 'close': c, 'price': c, 'volume': v}
    out = {}
    for name, (kind, need) in funcs.items():
        try:
            f = abstract.Function(name)
            result = f(feed)
            arrays = result if isinstance(result, (list, tuple)) else [result]
            outputs = list(f.output_names)
            if len(arrays) != len(outputs):
                raise ValueError('output arity mismatch')
            for label, values in zip(outputs, arrays):
                col = f'{name}_{label}' if len(outputs) > 1 else name
                values = np.asarray(values, dtype=np.float64)
                if values.shape != np.asarray(c).shape:
                    raise ValueError(f'bad output shape {values.shape}')
                if kind == 'pattern':
                    values = values / 100.0
                out[col] = values.astype(np.float32)
        except Exception as exc:
            raise RuntimeError(f'TA-Lib {name} failed; refusing partial snapshot') from exc
    return out

# ---------------- Block A2: TradingView computed extras (OHLCV-derived M-items) ----------------
def _ema_np(x, n):
    """TA-Lib-style EMA: alpha = 2/(n+1), seeded with the first value (pandas
    ewm(span=n, adjust=False) matches TA-Lib after the seed burn-in)."""
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy(dtype=np.float64)

def _spearman_rank_last(y):
    """Spearman rank correlation of y (price) vs time index, TV-RCI convention:
    price ranked DESCENDING (highest price = rank 1), time ascending.
    RCI = (1 - 6*sum(d^2) / (n^3 - n)) * 100, over the last n=len(y) bars."""
    n = len(y)
    if n < 3:
        return np.nan
    price_rank = np.empty(n, dtype=np.float64)
    price_rank[np.argsort(-y)] = np.arange(1, n + 1, dtype=np.float64)  # descending
    time_rank = (n - np.arange(n)).astype(np.float64)   # newest bar = rank 1 (TV convention)
    d2 = ((price_rank - time_rank) ** 2).sum()
    return (1.0 - 6.0 * d2 / (n ** 3 - n)) * 100.0

def compute_tv_extra(o, h, l, c, v, dates=None):
    """TradingView master items marked missing-fetchable that are pure OHLCV math.
    Returns dict column -> array, all aligned to the bars (caller shifts by one).
    Deterministic, no external data. M-item ids in comments.
    `dates` (datetime64, same length) enables calendar aggregations (M119)."""
    out = {}
    # M133 PMO: double-smoothed ROC(1). roc1% -> EMA35 -> EMA20 -> EMA10 = PMO line;
    # signal = EMA10(PMO). (Scaling conventions differ across vendors; what matters
    # for the questions is the line/signal crossover and direction.)
    roc1 = np.zeros(len(c), dtype=np.float64)
    roc1[1:] = 100.0 * (c[1:] - c[:-1]) / np.where(c[:-1] == 0, np.nan, c[:-1])
    pmo = _ema_np(_ema_np(_ema_np(roc1, 35), 20), 10)
    pmo_sig = _ema_np(pmo, 10)
    out['tv_pmo'] = pmo.astype(np.float32)
    out['tv_pmo_sig'] = pmo_sig.astype(np.float32)
    out['tv_pmo_x'] = (pmo > pmo_sig).astype(np.float32)          # bull crossover state
    # M137 / M139 RCI + RCI ribbon: Spearman(close, time) over 9 / 26 / 52 bars.
    for w in (9, 26, 52):
        rci = np.full(len(c), np.nan, dtype=np.float64)
        for t in range(w - 1, len(c)):
            rci[t] = _spearman_rank_last(c[t - w + 1:t + 1])
        out[f'tv_rci{w}'] = rci.astype(np.float32)
    out['tv_rci_ribbon_up'] = ((out['tv_rci9'] > out['tv_rci26']) &
                               (out['tv_rci26'] > out['tv_rci52'])).astype(np.float32)
    # M009 Advance/Decline Ratio (Bars): own-bar advancers vs decliners over 14 bars.
    up = (c[1:] > c[:-1]).astype(np.float64); dn = (c[1:] < c[:-1]).astype(np.float64)
    up_s = pd.Series(np.r_[0.0, up]).rolling(14, min_periods=14).sum().to_numpy()
    dn_s = pd.Series(np.r_[0.0, dn]).rolling(14, min_periods=14).sum().to_numpy()
    with np.errstate(divide='ignore', invalid='ignore'):
        ratio = np.where((up_s + dn_s) > 0, up_s / np.where(dn_s == 0, np.nan, dn_s), np.nan)
    out['tv_adbars_up14'] = up_s.astype(np.float32)
    out['tv_adbars_dn14'] = dn_s.astype(np.float32)
    out['tv_adbars_ratio14'] = ratio.astype(np.float32)
    # M265 Tweezer Bottom / M266 Tweezer Top: 2-bar matching lows/highs (tolerance
    # 0.1% of the level) with a direction confirmation bar.
    tol_l = l * 1e-3; tol_h = h * 1e-3
    out['tv_tweezer_bottom'] = np.r_[0.0, ((np.abs(l[1:] - l[:-1]) <= tol_l[1:]) &
                                           (c[1:] > c[:-1])).astype(np.float32)]
    out['tv_tweezer_top'] = np.r_[0.0, ((np.abs(h[1:] - h[:-1]) <= tol_h[1:]) &
                                        (c[1:] < c[:-1])).astype(np.float32)]
    # M237 Falling Window (bearish gap between bars): today's high below yesterday's low.
    out['tv_falling_window'] = np.r_[0.0, (h[1:] < l[:-1]).astype(np.float32)]
    # M039 Chop Zone (approximation): EMA34 slope in bp/day; 'chop' when |slope| < 5bp.
    ema34 = _ema_np(c, 34)
    slope_bp = np.full(len(c), np.nan, dtype=np.float64)
    slope_bp[1:] = (ema34[1:] / np.where(ema34[:-1] == 0, np.nan, ema34[:-1]) - 1.0) * 1e4
    out['tv_chop_slope_bp'] = slope_bp.astype(np.float32)
    out['tv_chop_on'] = (np.abs(slope_bp) < 5.0).astype(np.float32)
    # M026 BBTrend: (Bollinger width on SMA20 − width on EMA20) / close.
    cs = pd.Series(c)
    sma20 = cs.rolling(20, min_periods=20).mean()
    std20 = cs.rolling(20, min_periods=20).std(ddof=0)
    estd20 = (cs - pd.Series(_ema_np(c, 20))).rolling(20, min_periods=20).std(ddof=0)
    out['tv_bbtrend'] = ((4 * (std20 - estd20)) / cs).to_numpy(np.float32)
    # M057 Envelope (2.5%): close position inside the band, 0..1.
    env_lo = sma20 * 0.975; env_hi = sma20 * 1.025
    out['tv_env_pos'] = ((cs - env_lo) / (env_hi - env_lo)).to_numpy(np.float32)
    # M196 Visible Average Price: mean close over 20 bars.
    out['tv_vavg20'] = sma20.to_numpy(np.float32)
    # M222 Volume candles (chart type; proxy): volume relative to its 20-bar mean.
    vma20 = pd.Series(v).rolling(20, min_periods=20).mean()
    out['tv_volr'] = (pd.Series(v) / vma20).to_numpy(np.float32)
    # M186 Trend Strength Index: rolling-20 squared Pearson corr(close, bar index).
    w = 20
    ts = np.full(len(c), np.nan, dtype=np.float64)
    tidx = np.arange(w, dtype=np.float64); tidx_c = tidx - tidx.mean()
    for t in range(w - 1, len(c)):
        y = c[t - w + 1:t + 1]
        if np.isnan(y).any():
            continue
        yc = y - y.mean()
        denom = np.sqrt((yc ** 2).sum() * (tidx_c ** 2).sum())
        ts[t] = (yc * tidx_c).sum() / denom if denom > 0 else np.nan
    out['tv_ts_r2_20'] = (ts ** 2).astype(np.float32)
    if dates is not None:
        # M119 Multi-Time Period Charts: prior completed ISO week (Mon-Fri) H/L/C.
        wkey = (pd.to_datetime(dates).isocalendar()['year'].astype(np.int64) * 100
                + pd.to_datetime(dates).isocalendar()['week'].astype(np.int64)).to_numpy()
        gdf = pd.DataFrame({'k': wkey, 'h': h, 'l': l, 'c': c, 'i': np.arange(len(c))})
        wh = gdf.groupby('k')['h'].max(); wl = gdf.groupby('k')['l'].min()
        wlast = gdf.groupby('k')['i'].max()
        ukeys = wh.index.to_numpy()
        wclose = c[wlast.to_numpy()]
        kidx = np.searchsorted(ukeys, wkey)     # wkey values are all group keys
        has_prior = kidx > 0
        p = np.clip(kidx - 1, 0, len(ukeys) - 1)
        pw_high = np.where(has_prior, wh.to_numpy()[p], np.nan)
        pw_low = np.where(has_prior, wl.to_numpy()[p], np.nan)
        rng = np.where(pw_high > pw_low, pw_high - pw_low, np.nan)
        out['tv_pw_high'] = pw_high.astype(np.float32)
        out['tv_pw_low'] = pw_low.astype(np.float32)
        out['tv_pw_close'] = np.where(has_prior, wclose.astype(np.float32)[p], np.nan)
        out['tv_pw_pos'] = ((c - pw_low) / rng).astype(np.float32)
    # M146 Rob Booker ADX Breakout: ADX>25 and high exceeds the prior 20-bar high.
    adx14 = talib.ADX(h, l, c, timeperiod=14)
    hh20 = pd.Series(h).rolling(20, min_periods=20).max().shift(1).to_numpy()  # excl today
    adxbo = (h > hh20) & (adx14 > 25.0)
    out['tv_adxbo'] = np.where(np.isnan(adx14) | np.isnan(hh20), np.nan,
                               adxbo.astype(np.float64)).astype(np.float32)
    # M150 Rob Booker Reversal: MACD histogram side + stochastic cross at extremes.
    _, _, mhist = talib.MACD(c, fastperiod=12, slowperiod=26, signalperiod=9)
    sk, sd = talib.STOCH(h, l, c, fastk_period=14, slowk_period=3, slowd_period=3)
    kx_up = (sk[1:] > sd[1:]) & (sk[:-1] <= sd[:-1])
    kx_dn = (sk[1:] < sd[1:]) & (sk[:-1] >= sd[:-1])
    rev = np.zeros(len(c), dtype=np.float64)
    rev[1:] = np.where(kx_up & (mhist[1:] > 0) & (sk[1:] < 20), 1.0,
                       np.where(kx_dn & (mhist[1:] < 0) & (sk[1:] > 80), -1.0, 0.0))
    rev[np.isnan(mhist) | np.isnan(sk) | np.isnan(sd)] = 0.0
    out['tv_rb_rev'] = rev.astype(np.float32)
    # M208 Woodies CCI: turbo CCI(6) + CCI(14) zero-line cross direction.
    cci14 = talib.CCI(h, l, c, timeperiod=14)
    out['tv_cci6'] = talib.CCI(h, l, c, timeperiod=6).astype(np.float32)
    zx = np.zeros(len(c), dtype=np.float64)
    zx[1:] = np.where(np.isnan(cci14[1:]) | np.isnan(cci14[:-1]), 0.0,
                      np.where((cci14[1:] > 0) & (cci14[:-1] <= 0), 1.0,
                               np.where((cci14[1:] < 0) & (cci14[:-1] >= 0), -1.0, 0.0)))
    out['tv_cci_zx'] = zx.astype(np.float32)
    # M032 Bollinger Bars (%B): close position inside the 20,2 band, may exceed 0..1.
    bb_up, bb_mid2, bb_lo2 = talib.BBANDS(c, timeperiod=20, nbdevup=2.0, nbdevdn=2.0)
    bbw = np.where(bb_up > bb_lo2, bb_up - bb_lo2, np.nan)
    out['tv_bb_pos'] = ((c - bb_lo2) / bbw).astype(np.float32)
    # M136 Pring's Special K (approximation): sum of SMA10-smoothed ROCs over spans
    # {10,15,20,30,40,65}. TV's exact weight table is proprietary; flagged.
    spec_k = np.zeros(len(c), dtype=np.float64)
    for span in (10, 15, 20, 30, 40, 65):
        roc = np.zeros(len(c), dtype=np.float64)
        roc[span:] = 100.0 * (c[span:] - c[:-span]) / np.where(c[:-span] == 0, np.nan, c[:-span])
        spec_k += pd.Series(roc).rolling(10, min_periods=10).mean().fillna(0.0).to_numpy()
    out['tv_spec_k'] = spec_k.astype(np.float32)
    # M168 Technical Ratings (approximation of TV's published composite): MA half =
    # mean sign(close-MA) over SMA10/20 + EMA10/20/30/50/100/200; oscillator half =
    # RSI14 vs 50, CCI14 vs 0, MACD hist sign, STOCH k>d, ADX>25 ? sign(+DI-DI) : 0,
    # WILLR14 vs -50. tv_tr_total in [-1,1].
    mas = [pd.Series(c).rolling(nn, min_periods=nn).mean().to_numpy() for nn in (10, 20)] + \
          [_ema_np(c, nn) for nn in (10, 20, 30, 50, 100, 200)]
    cn = np.broadcast_to(c, (8, len(c)))
    ma_score = np.nanmean(np.sign(cn - np.vstack(mas)), axis=0)
    rsi14 = talib.RSI(c, timeperiod=14)
    pdi = talib.PLUS_DI(h, l, c, timeperiod=14)
    mdi = talib.MINUS_DI(h, l, c, timeperiod=14)
    wr14 = talib.WILLR(h, l, c, timeperiod=14)
    osc = np.vstack([np.sign(rsi14 - 50.0), np.sign(cci14), np.sign(mhist),
                     np.sign(sk - sd), np.where(adx14 > 25.0, np.sign(pdi - mdi), 0.0),
                     np.sign(wr14 + 50.0)])
    osc_score = np.nanmean(osc, axis=0)
    out['tv_tr_ma'] = ma_score.astype(np.float32)
    out['tv_tr_osc'] = osc_score.astype(np.float32)
    out['tv_tr_total'] = (np.nan_to_num(ma_score) * 0.5 + np.nan_to_num(osc_score) * 0.5).astype(np.float32)
    if dates is not None:
        # M154/M082 Seasonality: expanding PIT historical up-day frequency for the
        # same calendar month / day-of-week (only bars strictly before t count).
        dt = pd.to_datetime(dates)
        upf = np.r_[np.nan, (np.diff(c) > 0).astype(np.float64)]
        nn_f = ~np.isnan(upf)
        u0 = np.nan_to_num(upf)
        for key, colname in ((dt.month.to_numpy(), 'tv_seas_mo_up'),
                             (dt.dayofweek.to_numpy(), 'tv_seas_dow_up')):
            ks = pd.Series(key)
            g_nn = nn_f.astype(np.float64); g_nn = pd.Series(g_nn).groupby(ks).cumsum().to_numpy()  # incl current
            g_u = pd.Series(u0).groupby(ks).cumsum().to_numpy()
            prior_n = g_nn - nn_f.astype(np.float64)
            prior_sum = g_u - u0
            seas = np.where(prior_n > 0, prior_sum / np.where(prior_n > 0, prior_n, np.nan), np.nan)
            out[colname] = seas.astype(np.float32)
    # M218 3-Line Break direction (approximation: close vs the 3 prior closes).
    lb_dir = np.zeros(len(c), dtype=np.float64)
    cur = 0.0
    for t in range(3, len(c)):
        if c[t] > max(c[t - 3:t]):
            cur = 1.0
        elif c[t] < min(c[t - 3:t]):
            cur = -1.0
        lb_dir[t] = cur
    out['tv_lb_dir'] = lb_dir.astype(np.float32)
    # M219 Kagi direction: 4% reversal from the running extreme (close-only).
    kg_dir = np.zeros(len(c), dtype=np.float64)
    cur = 1.0 if len(c) > 1 and c[1] >= c[0] else -1.0
    ext = c[0]
    kg_dir[0] = cur
    for t in range(1, len(c)):
        if cur > 0:
            ext = max(ext, c[t])
            if c[t] < ext * 0.96:
                cur = -1.0; ext = c[t]
        else:
            ext = min(ext, c[t])
            if c[t] > ext * 1.04:
                cur = 1.0; ext = c[t]
        kg_dir[t] = cur
    out['tv_kagi_dir'] = kg_dir.astype(np.float32)
    # M217 Renko: ATR(14) bricks; direction state + bricks since last direction flip.
    atr14 = talib.ATR(h, l, c, timeperiod=14)
    rk_dir = np.zeros(len(c), dtype=np.float64)
    rk_n = np.zeros(len(c), dtype=np.float64)
    state = 0.0; last_brick = c[0]; nbf = 0.0
    for t in range(1, len(c)):
        box = atr14[t] if not np.isnan(atr14[t]) and atr14[t] > 0 else 0.0
        if box > 0:
            while c[t] >= last_brick + box:
                last_brick += box
                if state < 0:
                    nbf = 0.0
                state = 1.0; nbf += 1.0
            while c[t] <= last_brick - box:
                last_brick -= box
                if state > 0:
                    nbf = 0.0
                state = -1.0; nbf += 1.0
        rk_dir[t] = state; rk_n[t] = nbf
    out['tv_renko_dir'] = rk_dir.astype(np.float32)
    out['tv_renko_n'] = rk_n.astype(np.float32)
    # M220 Point & Figure: 1% boxes, 3-box reversal, close-only (approximation).
    pf_dir = np.zeros(len(c), dtype=np.float64)
    state = 0.0; ext = c[0]
    for t in range(1, len(c)):
        box = 0.01 * c[t]
        if state >= 0 and c[t] >= ext + box:
            ext = c[t]; state = 1.0
        elif state <= 0 and c[t] <= ext - box:
            ext = c[t]; state = -1.0
        if state > 0 and c[t] <= ext - 3.0 * box:
            state = -1.0; ext = c[t]
        elif state < 0 and c[t] >= ext + 3.0 * box:
            state = 1.0; ext = c[t]
        pf_dir[t] = state
    out['tv_pnf_dir'] = pf_dir.astype(np.float32)
    # ---- M014/M017/M018/M149/M151/M269: strict swing pivots (left=right=2,
    # dictionary swing rule; a pivot at bar j is knowable once bar j+2 has closed,
    # which the caller's shift-by-one makes strictly leak-safe). ----
    P = 2
    nn = len(c)
    piv_h_idx = []   # confirmed pivot-high bar indices (ascending)
    piv_l_idx = []
    for t in range(P, nn - P):
        if h[t] > max(h[t - P:t]) and h[t] > max(h[t + 1:t + P + 1]):
            piv_h_idx.append(t)
        if l[t] < min(l[t - P:t]) and l[t] < min(l[t + 1:t + P + 1]):
            piv_l_idx.append(t)
    # M018 Auto trendlines: slope (pct/bar) and close distance to the line through
    # the last two confirmed same-kind pivots, extended to t.
    tl_hs = np.full(nn, np.nan); tl_hdist = np.full(nn, np.nan)
    tl_ls = np.full(nn, np.nan); tl_ldist = np.full(nn, np.nan)
    for arr_idx, pivs, price, slope_col, dist_col in (
            (0, piv_h_idx, h, tl_hs, tl_hdist), (1, piv_l_idx, l, tl_ls, tl_ldist)):
        for k in range(1, len(pivs)):
            j1, j2 = pivs[k - 1], pivs[k]
            for t in range(j2 + P, nn if k == len(pivs) - 1 else pivs[k + 1] + P):
                slope = (price[j2] - price[j1]) / (j2 - j1) / price[j1]
                line = price[j2] + slope * price[j1] * (t - j2)
                slope_col[t] = slope * 100.0
                dist_col[t] = (c[t] - line) / c[t]
    out['tv_tl_hslope'] = tl_hs.astype(np.float32)
    out['tv_tl_hdist'] = tl_hdist.astype(np.float32)
    out['tv_tl_lslope'] = tl_ls.astype(np.float32)
    out['tv_tl_ldist'] = tl_ldist.astype(np.float32)
    # M014 Auto fib extension: position in units of the last confirmed swing range,
    # 0 = at the swing high, −1 = at the swing low, >0 = extension beyond the high.
    fibx = np.full(nn, np.nan)
    hi_i = lo_i = None
    hi_v = lo_v = np.nan
    # walk pivots in time order
    events = sorted([(i, 1, h[i]) for i in piv_h_idx] + [(i, -1, l[i]) for i in piv_l_idx])
    ei = 0
    for t in range(nn):
        while ei < len(events) and events[ei][0] + P <= t:
            _, kind, val = events[ei]
            if kind == 1:
                hi_i, hi_v = events[ei][0], val
            else:
                lo_i, lo_v = events[ei][0], val
            ei += 1
        if hi_i is not None and lo_i is not None and hi_v > lo_v:
            fibx[t] = (c[t] - hi_v) / (hi_v - lo_v)
    out['tv_fibx'] = fibx.astype(np.float32)
    # M017 Auto Pitchfork (approximation): midline through the midpoints of the last
    # two confirmed pivot pairs; tv_pf_pos = close distance to the midline.
    pf_slope = np.full(nn, np.nan); pf_pos = np.full(nn, np.nan)
    mids = []   # (bar, midpoint price) alternating from confirmed pivots, time order
    ei = 0
    for t in range(nn):
        while ei < len(events) and events[ei][0] + P <= t:
            _, kind, val = events[ei]
            mids.append((events[ei][0], val))
            ei += 1
        if len(mids) >= 4:
            (a1, v1), (a2, v2), (a3, v3), (a4, v4) = mids[-4:]
            m1 = (v1 + v2) / 2.0; m2 = (v3 + v4) / 2.0
            if a4 > a2:
                slope = (m2 - m1) / (a4 - a2) / m1
                line = m2 + slope * m1 * (t - a4)
                pf_slope[t] = slope * 100.0
                pf_pos[t] = (c[t] - line) / c[t]
    out['tv_pf_slope'] = pf_slope.astype(np.float32)
    out['tv_pf_pos'] = pf_pos.astype(np.float32)
    # M149 Missed Pivot Points: distance to the classic prior-bar floor pivot
    # pp = (H+L+C)/3 of the previous bar.
    pp_prev = (h[:-1] + l[:-1] + c[:-1]) / 3.0
    out['tv_mpp_dist'] = np.r_[np.nan, ((c[1:] - pp_prev) / c[1:])].astype(np.float32)
    # M151 Ziv Ghost Pivots: the most recent confirmed pivot whose level was later
    # exceeded (a 'failed' pivot). Distance to that ghost level.
    ghost = np.full(nn, np.nan)
    ghost_list = []  # (bar, level, kind)
    gi = 0
    cur_ghost = np.nan
    for t in range(nn):
        while gi < len(events) and events[gi][0] + P <= t:
            ghost_list.append(events[gi])
            gi += 1
        # a pivot is a ghost once any later bar's range exceeds its level
        for (j, kind, val) in ghost_list[-6:]:
            if kind == 1 and h[t] > val:
                cur_ghost = val
            elif kind == -1 and l[t] < val:
                cur_ghost = val
        if not np.isnan(cur_ghost):
            ghost[t] = (c[t] - cur_ghost) / c[t]
    out['tv_ghost_dist'] = ghost.astype(np.float32)
    # M269 Elliott Waves (approximation): direction of the last-5-pivot net move and
    # total confirmed pivot count.
    ew_dir = np.zeros(nn); ew_npiv = np.zeros(nn)
    ei = 0
    seq = []
    for t in range(nn):
        while ei < len(events) and events[ei][0] + P <= t:
            seq.append(events[ei])
            ei += 1
        ew_npiv[t] = float(len(seq))
        if len(seq) >= 5:
            ew_dir[t] = float(np.sign(seq[-1][2] - seq[-5][2]))
    out['tv_ew_dir'] = ew_dir.astype(np.float32)
    out['tv_ew_npiv'] = ew_npiv.astype(np.float32)
    # M271 Periodic Volume Profile POC (rolling 20 bars, typical price, 20 bins):
    # distance of close to the point of control.
    tp = (h + l + c) / 3.0
    poc_dist = np.full(nn, np.nan)
    for t in range(19, nn):
        seg = tp[t - 19:t + 1]; vol = v[t - 19:t + 1]
        lo_, hi_ = seg.min(), seg.max()
        if hi_ <= lo_:
            poc = seg[vol.argmax()]
        else:
            bins = np.clip(((seg - lo_) / (hi_ - lo_) * 19.0).astype(int), 0, 19)
            volsum = np.bincount(bins, weights=vol, minlength=20)
            poc = lo_ + (volsum.argmax() + 0.5) * (hi_ - lo_) / 20.0
        poc_dist[t] = (c[t] - poc) / c[t]
    out['tv_poc_dist'] = poc_dist.astype(np.float32)
    # M274 Anchored Volume Profile POC: anchored at the highest-high bar of the
    # 60-bar window ending 5 bars back, so the anchored profile always has >=6 bars
    # and the anchor itself is unambiguously in the past.
    avp_dist = np.full(nn, np.nan)
    for t in range(65, nn):
        anchor = t - 64 + int(np.argmax(h[t - 64:t - 4]))
        seg = tp[anchor:t + 1]; vol = v[anchor:t + 1]
        lo_, hi_ = seg.min(), seg.max()
        if hi_ <= lo_:
            poc = seg[vol.argmax()]
        else:
            bins = np.clip(((seg - lo_) / (hi_ - lo_) * 19.0).astype(int), 0, 19)
            volsum = np.bincount(bins, weights=vol, minlength=20)
            poc = lo_ + (volsum.argmax() + 0.5) * (hi_ - lo_) / 20.0
        avp_dist[t] = (c[t] - poc) / c[t]
    out['tv_avp_dist'] = avp_dist.astype(np.float32)
    # M147 Knoxville Divergence: new 20-day high with RSI lower than at the previous
    # 20-day high (bearish, −1); mirror for lows (bullish, +1). Event column.
    knox = np.zeros(nn)
    prev_hi_i = prev_lo_i = None
    hh = pd.Series(h).rolling(20, min_periods=20).max().to_numpy()
    ll = pd.Series(l).rolling(20, min_periods=20).min().to_numpy()
    for t in range(20, nn):
        if h[t] >= hh[t]:                       # new 20d high
            if prev_hi_i is not None and not np.isnan(rsi14[t]) and not np.isnan(rsi14[prev_hi_i]):
                if rsi14[t] < rsi14[prev_hi_i] - 5.0:
                    knox[t] = -1.0
            prev_hi_i = t
        if l[t] <= ll[t]:                       # new 20d low
            if prev_lo_i is not None and not np.isnan(rsi14[t]) and not np.isnan(rsi14[prev_lo_i]):
                if rsi14[t] > rsi14[prev_lo_i] + 5.0:
                    knox[t] = 1.0
            prev_lo_i = t
    out['tv_knox'] = knox.astype(np.float32)
    # M268 classic chart patterns (approximation): pattern-state flags from the
    # last confirmed pivots. Heuristic rules, deterministic and PIT via shift.
    EPS_S = 0.0003         # ~0.03%/bar slope threshold
    pat_cols = {k: np.zeros(nn, dtype=np.float64) for k in
                ('dbltop', 'dblbot', 'tri', 'rect', 'flag', 'wedge', 'hs')}
    hs_i = []; ls_i = []
    ei = 0
    for t in range(nn):
        while ei < len(events) and events[ei][0] + P <= t:
            _, kind, val = events[ei]
            (hs_i if kind == 1 else ls_i).append((events[ei][0], val))
            ei += 1
        hslope = lslope = None
        if len(hs_i) >= 2 and t - hs_i[-1][0] <= 60:
            (a1, v1), (a2, v2) = hs_i[-2], hs_i[-1]
            hslope = (v2 - v1) / max(a2 - a1, 1) / v1
        if len(ls_i) >= 2 and t - ls_i[-1][0] <= 60:
            (b1, w1), (b2, w2) = ls_i[-2], ls_i[-1]
            lslope = (w2 - w1) / max(b2 - b1, 1) / w1
        if len(hs_i) >= 2:
            (a1, v1), (a2, v2) = hs_i[-2], hs_i[-1]
            if abs(v2 - v1) <= 0.015 * max(v1, v2) and t - a2 <= 30:
                pat_cols['dbltop'][t] = 1.0
        if len(ls_i) >= 2:
            (b1, w1), (b2, w2) = ls_i[-2], ls_i[-1]
            if abs(w2 - w1) <= 0.015 * max(w1, w2) and t - b2 <= 30:
                pat_cols['dblbot'][t] = 1.0
        if hslope is not None and lslope is not None:
            if hslope < -EPS_S and lslope > EPS_S:
                pat_cols['tri'][t] = 1.0        # converging: descending tops, ascending bottoms
            if abs(hslope) < EPS_S and abs(lslope) < EPS_S:
                pat_cols['rect'][t] = 1.0
            if hslope > EPS_S and lslope > EPS_S and hslope < lslope:
                pat_cols['wedge'][t] = 1.0      # rising wedge (bearish)
            if hslope < -EPS_S and lslope < -EPS_S and hslope > lslope:
                pat_cols['wedge'][t] = 1.0      # falling wedge (bullish)
        if len(hs_i) >= 3 and t - hs_i[-1][0] <= 40:
            (_, v1), (_, v2), (_, v3) = hs_i[-3], hs_i[-2], hs_i[-1]
            if v2 > v1 * 1.02 and v2 > v3 * 1.02 and abs(v1 - v3) <= 0.03 * v2:
                pat_cols['hs'][t] = 1.0
        if t >= 15:
            seg15 = c[max(0, t - 15):t]
            mom_rng = seg15.max() / seg15.min() - 1.0
            tight = (c[t - 5:t].max() - c[t - 5:t].min()) / c[t]
            if mom_rng > 0.08 and tight < 0.03:
                pat_cols['flag'][t] = 1.0
    for k, arr in pat_cols.items():
        out[f'tv_pat_{k}'] = arr.astype(np.float32)
    return out

def moon_age(dates):
    """M113 Moon Phases: pure calendar. Days since the 2000-01-06 18:14 UTC new moon,
    mod the synodic month (29.530588853 d). Computed from the row date itself, so no
    shift-by-one is applied by the caller (calendar facts are knowable at open)."""
    days = (pd.to_datetime(dates) - pd.Timestamp('2000-01-06 18:14:00')).total_seconds() / 86400.0
    return (days % 29.530588853).astype(np.float32)

# ---------------- Block B: sector/style ETF overlays ----------------
def etf_wide():
    """All 14 ETFs (SPY, QQQ, IWM, 11 SPDRs) as wide daily columns.
    Every column is shifted by one ETF bar: value labelled D uses the ETF close
    of its last trading day <= D-1, then joins by merge_asof backward, so a
    stock-day D never sees ETF data from D itself. Survivor/label bias: the
    11 SPDR set uses today's sector definitions (flagged in METHODOLOGY)."""
    p = D('/workspace/etf/etf_2015.parquet')
    if not os.path.exists(p):
        return None
    e = pd.read_parquet(p)
    e['date'] = pd.to_datetime(e['date'])
    parts = {}
    for tk, d in e.groupby('ticker'):
        d = d.sort_values('date')
        c = d.close.to_numpy(float)
        s = pd.Series(c)
        cols = {
            f'etf_{tk}_c': c,
            f'etf_{tk}_r1': s.pct_change(1).to_numpy(),
            f'etf_{tk}_r5': s.pct_change(5).to_numpy(),
            f'etf_{tk}_r20': s.pct_change(20).to_numpy(),
            f'etf_{tk}_d50': (s / s.rolling(50).mean() - 1).to_numpy(),
            f'etf_{tk}_d200': (s / s.rolling(200).mean() - 1).to_numpy(),
        }
        dd = pd.DataFrame(cols)
        dd['date'] = d.date.to_numpy()
        parts[tk] = dd
    wide = None
    for tk, dd in parts.items():
        wide = dd if wide is None else pd.merge(wide, dd, on='date', how='outer')
    wide = wide.sort_values('date').reset_index(drop=True)
    val_cols = [c for c in wide.columns if c != 'date']
    wide[val_cols] = wide[val_cols].shift(1)          # D sees the prior ETF bar
    return wide.dropna(subset=val_cols[:1]).sort_values('date')

# ---------------- Block E: Form 4 insider filing-date counts (I187 date-count lens) ----------------
def load_form4(tickers):
    """Per-ticker Form 4 filing events from fetch/fetch_form4.py (release
    data-ext-2020-26-v1 asset form4_counts_2020_26.parquet): ticker, date
    (filingDate), n (filings that day). A filing is public on its filingDate and
    usable next session; joins in ticker_frame are strict < D. Value lens
    (shares, role) is a later refinement; date counts only."""
    p = os.path.join(os.environ.get('CHECKLIST_DATA_DIR', '.'), 'data-ext', 'form4_counts_2020_26.parquet')
    if not os.path.exists(p):
        return None
    df = pd.read_parquet(p)
    if df.empty or 'ticker' not in df: return None
    df = df[df.ticker.isin(tickers)]
    df['date'] = pd.to_datetime(df['date'])
    return df.sort_values('date').reset_index(drop=True)

# ---------------- Block L: analyst action columns (I197) ----------------
def analyst_columns(dates, af):
    """Days-since-last-action + trailing-window counts from a ticker's analyst
    action frame (ticker, date, n_up, n_down, n_init, n_oth). All windows are
    strict < D, same convention as event_columns."""
    d = pd.to_datetime(pd.Series(dates)).reset_index(drop=True)
    n = len(d)
    nan = np.full(n, np.nan, dtype=np.float32)
    out = {k: nan.copy() for k in ('an_days', 'an_n20', 'an_up20', 'an_dn20',
                                   'an_up60', 'an_dn60', 'an_dir')}
    if af is None or not len(af):
        return out
    af = af.sort_values('date')
    ed = af.date.to_numpy(dtype='datetime64[ns]')
    dd = d.to_numpy(dtype='datetime64[ns]')
    one = np.timedelta64(1, 'D')
    pos = np.searchsorted(ed, dd, side='left')        # events with date < D
    has = pos > 0
    idx = np.clip(pos - 1, 0, len(ed) - 1)
    out['an_days'] = np.where(has, (dd - ed[idx]) / one, np.nan).astype(np.float32)
    tot = (af.n_up + af.n_down + af.n_init + af.n_oth).to_numpy(dtype=np.float32)
    up = af.n_up.to_numpy(dtype=np.float32); dn = af.n_down.to_numpy(dtype=np.float32)
    for w, tag in ((20, '20'), (60, '60')):
        lo = np.searchsorted(ed, dd - np.timedelta64(w, 'D'), side='left')
        cs = np.cumsum(tot); cup = np.cumsum(up); cdn = np.cumsum(dn)
        s = lambda cs_: np.where(has, (cs_[np.clip(pos - 1, 0, len(ed) - 1)]
                                       - np.where(lo > 0, cs_[lo - 1], 0)).astype(np.float32), np.nan)
        out[f'an_n{tag}'] = s(cs); out[f'an_up{tag}'] = s(cup); out[f'an_dn{tag}'] = s(cdn)
    # an_dir: direction of the most recent day with a directional move
    # (up != down); NaN before the first such day. ffill over the event timeline.
    dir_ev = np.where(up != dn, np.sign(up - dn), np.nan).astype(np.float32)
    dir_ff = pd.Series(dir_ev).ffill().to_numpy()
    out['an_dir'] = np.where(has, dir_ff[idx], np.nan).astype(np.float32)
    return out

# ---------------- Block I loader: FRED/ALFRED vintages (I195; BLOCKED_SECRET) ----------------
def load_fred(tickers=None):
    """ALFRED vintage long frame from fetch/fetch_fred.py (release data-ext-2020-26-v1
    asset fred_wide_2020_26.parquet): series, obs_date, vintage_date, value. Only
    loaded when the asset exists (i.e. after FRED_API_KEY arrives)."""
    p = os.path.join(os.environ.get('CHECKLIST_DATA_DIR', '.'), 'data-ext', 'fred_wide_2020_26.parquet')
    if not os.path.exists(p):
        return None
    df = pd.read_parquet(p)
    df['vintage_date'] = pd.to_datetime(df['vintage_date'])
    df['obs_date'] = pd.to_datetime(df['obs_date'])
    return df.sort_values('vintage_date').reset_index(drop=True)


def fred_columns(dates, fr):
    """Latest observed period as known at D; revisions of older periods do not
    replace a newer observation. Same-day vintages remain invisible."""
    q = pd.DataFrame({'date': pd.to_datetime(dates).astype('datetime64[ns]')})
    out = {}
    if fr is None or not len(fr): return out
    for sid,group in fr.groupby('series'):
        known = {}; timeline = []
        for vintage,changes in group.sort_values(['vintage_date','obs_date']).groupby('vintage_date',sort=True):
            for row in changes.itertuples():
                observation = pd.Timestamp(row.obs_date)
                if observation <= pd.Timestamp(vintage):
                    known[observation] = row.value
            if known:
                observation = max(known)
                timeline.append((vintage,observation,known[observation]))
        prefix = f'fred_{sid.lower()}'
        if not timeline:
            out[prefix] = np.full(len(q),np.nan,np.float32)
            out[prefix+'_odays'] = np.full(len(q),np.nan,np.float32)
            continue
        right = pd.DataFrame(timeline,columns=['vintage_date','obs_date','value'])
        right['vintage_date'] = pd.to_datetime(right.vintage_date).astype('datetime64[ns]')
        joined = pd.merge_asof(q,right,left_on='date',right_on='vintage_date',direction='backward',allow_exact_matches=False)
        out[prefix] = joined.value.to_numpy(np.float32)
        out[prefix+'_odays'] = (joined.date-joined.obs_date).dt.days.to_numpy(np.float32)
    return out


# ---------------- Block M: 13F holdings columns (I199) ----------------
def f13_columns(dates, hits):
    """Point-in-time institutional-holding recency from raw EDGAR FTS hits
    (cik, adsh, period_ending, file_date). f13_days = days since the latest
    13F-HR(/A) filing mentioning the ticker (filed < D); f13_qdays = days since
    the most recent reported quarter-end; f13_n = distinct filers in that
    quarter (page-cap saturation makes this a lower bound for mega caps);
    f13_q4 = how many of the last ~4 reported quarters have >=1 filer."""
    d = pd.to_datetime(pd.Series(dates)).reset_index(drop=True)
    n = len(d)
    keys = ('f13_days', 'f13_qdays', 'f13_n', 'f13_q4')
    out = {k: np.full(n, np.nan, dtype=np.float32) for k in keys}
    if hits is None or not len(hits):
        return out
    fd = pd.to_datetime(hits.file_date).to_numpy(dtype='datetime64[ns]')
    pe = pd.to_datetime(hits.period_ending).to_numpy(dtype='datetime64[ns]')
    dd = d.to_numpy(dtype='datetime64[ns]')
    one = np.timedelta64(1, 'D')
    pos_all = np.searchsorted(np.sort(fd), dd, side='left')   # hits with file_date < D
    has_any = pos_all > 0
    out['f13_days'] = np.where(has_any, (dd - np.sort(fd)[np.clip(pos_all - 1, 0, len(fd) - 1)]) / one,
                               np.nan).astype(np.float32)
    pes = np.unique(pe)
    Q = len(pes)
    hasq = np.zeros((Q, n), dtype=bool)
    cntq = np.zeros((Q, n), dtype=np.float32)
    for qi, q in enumerate(pes):
        f = np.sort(fd[pe == q])
        pos = np.searchsorted(f, dd, side='left')
        hasq[qi] = pos > 0
        cntq[qi] = pos.astype(np.float32)
    anyq = hasq.any(axis=0)
    # latest reported quarter index per day (NaN if none)
    idx = np.where(hasq, np.arange(Q)[:, None], -1)
    latest = idx.max(axis=0)
    lk = np.clip(latest, 0, Q - 1)
    out['f13_qdays'] = np.where(anyq, (dd - pes[lk]) / one, np.nan).astype(np.float32)
    out['f13_n'] = np.where(anyq, np.take_along_axis(cntq, lk[None, :], axis=0)[0], np.nan).astype(np.float32)
    # q4: distinct quarters reported within ~370 days of the latest quarter
    window = pes[lk][None, :] - np.timedelta64(370, 'D')     # (1, n) lower bound per day
    q4 = (hasq & (pes[:, None] >= window)).sum(axis=0)
    out['f13_q4'] = np.where(anyq, q4, np.nan).astype(np.float32)
    return out


# ---------------- Block O: GDELT mention columns (I200) ----------------
def gd_columns(dates, gdf):
    """Trailing mention windows from a ticker's GDELT daily counts (date, n).
    gd_n7/gd_n30 sum counts over [D-w, D); gd_spike = n7 / (90d baseline daily
    mean, excluding the last 7d); gd_days = days since last mentioned day.
    A true 0 means 'covered by GDELT but silent'; NaN means 'no GDELT data yet'."""
    d = pd.to_datetime(pd.Series(dates)).reset_index(drop=True)
    n = len(d)
    out = {k: np.full(n, np.nan, dtype=np.float32)
           for k in ('gd_days', 'gd_n7', 'gd_n30', 'gd_spike')}
    if gdf is None or not len(gdf):
        return out
    gdf = gdf.sort_values('date')
    ed = gdf.date.to_numpy(dtype='datetime64[ns]')
    dd = d.to_numpy(dtype='datetime64[ns]')
    nv = gdf.n.to_numpy(dtype=np.float32)
    cs = np.cumsum(nv)
    one = np.timedelta64(1, 'D')

    def winsum(w, lag=0):
        hi = np.searchsorted(ed, dd - np.timedelta64(lag, 'D'), side='left') - 1
        lo = np.searchsorted(ed, dd - np.timedelta64(w + lag, 'D'), side='left') - 1
        s = np.where(hi >= 0,
                     cs[np.clip(hi, 0, len(ed) - 1)]
                     - np.where(lo >= 0, cs[np.clip(lo, 0, len(ed) - 1)], 0), np.nan)
        return s.astype(np.float32)

    out['gd_n7'] = winsum(7)
    out['gd_n30'] = winsum(30)
    base = winsum(90, lag=7) / 90.0
    out['gd_spike'] = np.where(base > 0, out['gd_n7'] / (base + 1.0), np.nan).astype(np.float32)
    nz = np.nonzero(nv > 0)[0]
    pos = np.searchsorted(ed, dd, side='left')          # events < D
    li = np.searchsorted(nz, pos, side='left') - 1
    has = li >= 0
    if not len(nz):
        return out
    idx = nz[np.clip(li, 0, len(nz) - 1)]
    out['gd_days'] = np.where(has, (dd - ed[idx]) / one, np.nan).astype(np.float32)
    return out


# ---------------- Block H: XBRL fundamentals columns (I192) ----------------
def xbrl_columns(dates, xb):
    """Latest-filed fundamentals per metric, strict filed < D, from the ticker's
    long frame (metric, period_end, filed, val, yoy). Restatement-safe: a revised
    value arrives with a new filed date; before that date the old value stands."""
    out = {}
    if xb is None or not len(xb):
        return out
    allf = pd.DataFrame({'filed': pd.Series(sorted(set(xb.filed))), 'val': 0.0})
    out.update(_asof_strict(dates, allf, [], 'filed', prefix_days='xb_days'))
    for m, tag in (('Revenues', 'rev'), ('NetIncomeLoss', 'ni'), ('Assets', 'assets'),
                   ('Liabilities', 'debt'), ('CommonStockSharesOutstanding', 'shares')):
        sub = xb[xb.metric == m][['filed', 'val']].sort_values('filed')
        if not len(sub):
            continue
        r = _asof_strict(dates, sub, ['val'], 'filed', prefix_days=f'xb_{tag}_days')
        out[f'xb_{tag}'] = r['val']
        out[f'xb_{tag}_days'] = r[f'xb_{tag}_days']
        if m in ('Revenues', 'NetIncomeLoss'):
            g = xb[xb.metric == m][['filed', 'yoy']].dropna(subset=['yoy']).sort_values('filed')
            g = g.rename(columns={'yoy': 'val'})
            if len(g):
                rg = _asof_strict(dates, g, ['val'], 'filed')
                out[f'xb_{tag}_g'] = rg['val']
    return out


# ---------------- Block H loader: XBRL fundamentals (I192) ----------------
def load_xbrl(tickers):
    """Read filing-version-preserving companyfacts shards, never latest-only frames."""
    from pathlib import Path
    files = sorted(Path(_data_ext_dir()).glob('xbrl_shard_*.parquet'))
    if not files: return None
    frame = pd.concat([pd.read_parquet(p) for p in files],ignore_index=True)
    if frame.empty: return None
    frame = frame[frame.ticker.isin(tickers)].copy()
    frame['filed'] = pd.to_datetime(frame.filed)
    return frame.sort_values(['filed','period_end','accn']).reset_index(drop=True)


# ---------------- Block M loader: 13F hits (I199) ----------------
def load_f13(tickers):
    """Per-ticker raw 13F-HR(/A) FTS hits from fetch/fetch_13f.py (release
    data-ext-2020-26-v1 asset f13_hits_2020_26.parquet): ticker, cik, adsh,
    period_ending, file_date. Point-in-time keyed on file_date."""
    p = os.path.join(os.environ.get('CHECKLIST_DATA_DIR', '.'), 'data-ext', 'f13_hits_2020_26.parquet')
    if not os.path.exists(p):
        return None
    df = pd.read_parquet(p)
    if df.empty or 'ticker' not in df: return None
    df = df[df.ticker.isin(tickers)]
    return df.reset_index(drop=True)


# ---------------- Block O loader: GDELT mention counts (I200) ----------------
def load_gdelt(tickers):
    """Per-ticker GDELT daily mention counts from fetch/fetch_gdelt.py (release
    data-ext-2020-26-v1 asset gdelt_counts_2020_26.parquet): ticker, date, n.
    Query = exact ticker symbol; short-symbol noise bias is uniform and noted
    in the meta."""
    p = os.path.join(os.environ.get('CHECKLIST_DATA_DIR', '.'), 'data-ext', 'gdelt_counts_2020_26.parquet')
    if not os.path.exists(p):
        return None
    df = pd.read_parquet(p)
    if df.empty or 'ticker' not in df: return None
    df = df[df.ticker.isin(tickers)]
    df['date'] = pd.to_datetime(df['date'])
    return df.sort_values('date').reset_index(drop=True)


# ---------------- Block L loader: analyst actions (I197) ----------------
def load_analyst(tickers):
    """Per-ticker analyst action day counts from fetch/fetch_analyst.py (release
    data-ext-2020-26-v1 asset analyst_actions_2020_26.parquet): ticker, date,
    n_up / n_down / n_init / n_oth. Actions are public on their date; joins in
    ticker_frame are strict < D."""
    p = os.path.join(os.environ.get('CHECKLIST_DATA_DIR', '.'), 'data-ext', 'analyst_actions_2020_26.parquet')
    if not os.path.exists(p):
        return None
    df = pd.read_parquet(p)
    if df.empty or 'ticker' not in df: return None
    df = df[df.ticker.isin(tickers)]
    df['date'] = pd.to_datetime(df['date'])
    return df.sort_values('date').reset_index(drop=True)

# ---------------- Market-wide daily series (I178 VIX, block I market columns) ----------------
def load_mkt():
    """Market-wide daily frame from fetch/fetch_mkt.py (release data-ext-2020-26-v1
    asset mkt_wide_2020_26.parquet): date, vix, vix_r5, vix_d20. VIX is a market
    index and is never revised, so current-values data + the strict < D join in
    ticker_frame is point-in-time safe. Returns None when the asset is absent."""
    p = os.path.join(os.environ.get('CHECKLIST_DATA_DIR', '.'), 'data-ext', 'mkt_wide_2020_26.parquet')
    if not os.path.exists(p):
        return None
    df = pd.read_parquet(p)
    df['date'] = pd.to_datetime(df['date'])
    return df.sort_values('date').reset_index(drop=True)

# ---------------- Block D: earnings calendar ----------------
def load_earnings(tickers):
    """Nasdaq earnings calendars 2020-24 (release nasdaq_earn_2020-24.tar ->
    data/earnings/nasdaq_calendar_*.parquet). Point-in-time: only rows with
    report_date < D are used (strict; an AMC report on D-1 is in, a BMO report
    on D itself is out, keeping one convention for every name)."""
    base = os.path.join(os.environ.get('CHECKLIST_DATA_DIR', '.'), 'data', 'earnings')
    if not os.path.isdir(base):
        return None
    fs = [os.path.join(base, f) for f in sorted(os.listdir(base)) if f.startswith('nasdaq_calendar_') and f.endswith('.parquet')]
    if not fs:
        return None
    df = pd.concat([pd.read_parquet(f, columns=['symbol', 'report_date', 'time_label',
                                                'surprise_pct_fill', 'eps_delta']) for f in fs], ignore_index=True)
    df = df[df.symbol.isin(tickers)]
    df['report_date'] = pd.to_datetime(df['report_date'])
    df = df.sort_values('report_date').reset_index(drop=True)
    df['amc'] = df.time_label.astype(str).str.upper().str.contains('AMC').astype(np.float32)
    return df

def earn_for(dates, edf):
    """Earnings columns for one ticker's sorted dates (as strings). Uses only
    reports strictly before each date."""
    if edf is None or len(edf) == 0:
        return None
    q = pd.DataFrame({'date': pd.to_datetime(dates)})
    m = pd.merge_asof(q, edf[['report_date', 'amc', 'surprise_pct_fill', 'eps_delta']],
                      left_on='date', right_on='report_date', direction='backward')
    m = m.where(m.report_date < m.date)               # strict: nothing from D onward
    days = (m.date - m.report_date).dt.days.to_numpy(dtype=np.float32)
    return pd.DataFrame({'earn_days': days,
                         'earn_amc': m.amc.to_numpy(dtype=np.float32),
                         'earn_surp': m.surprise_pct_fill.to_numpy(dtype=np.float32),
                         'earn_deps': m.eps_delta.to_numpy(dtype=np.float32)})

# ---------------- Block C: theme peers (correlation clusters) ----------------
class Peers:
    """Frozen theme-peer clusters. Membership comes from ONE formation year (the
    first full calendar year in the bars file), so cluster assignment at any day D
    uses no data after the formation year (fixed-taxonomy label bias, flagged in
    meta - same spirit as the SPDR sector note). Holds the per-cluster equal-weight
    mean daily-return series (unshifted; consumers shift by one bar)."""
    def __init__(self, tk_cluster, cluster_ret, meta):
        self.tk_cluster = tk_cluster      # ticker -> cluster id (int) or -1
        self.cluster_ret = cluster_ret    # DataFrame date x cret_{id}
        self.cluster_n = meta['cluster_n']
        self.formation_year = meta['formation_year']
        self.corr_thresh = meta['corr_thresh']
        self.usable_from = meta['usable_from']   # peer columns NaN before this date

def _union_find_clusters(corr, thresh):
    """Connected components of the graph with an edge where corr >= thresh
    (upper triangle via numpy; union-find over edge list only)."""
    n = corr.shape[0]
    parent = np.arange(n)
    def find(x):
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root
    edges = np.argwhere(np.triu(corr >= thresh, k=1))
    for i, j in edges:
        pi, pj = find(i), find(j)
        if pi != pj:
            parent[pi] = pj
    comps = {}
    for i in range(n):
        comps.setdefault(find(i), []).append(i)
    return list(comps.values())

def build_peers(bars_all, corr_thresh=0.5, min_days=120, min_members=20):
    """Form theme-peer clusters from the first full calendar year of daily returns
    and build the equal-weight cluster return series for ALL days in bars_all.
    `bars_all` is the full-universe bar frame (ticker, date, close)."""
    p = bars_all[['ticker', 'date', 'close']].dropna()
    p['date'] = pd.to_datetime(p['date'])
    wide = p.pivot_table(index='date', columns='ticker', values='close').sort_index()
    ret = wide.pct_change(fill_method=None)
    years = ret.index.year
    uy = sorted(set(years))
    form_year = None
    for y in uy:
        if (years == y).sum() >= min_days:
            form_year = y
            break
    if form_year is None:
        return None
    X = ret[years == form_year]
    good = X.columns[X.notna().sum() >= min_days]
    X = X[good].dropna()
    if len(X) < min_days or X.shape[1] < min_members:
        return None
    C = np.corrcoef(X.to_numpy(dtype=np.float32).T)
    comps = _union_find_clusters(np.nan_to_num(C, nan=0.0), corr_thresh)
    clusters = [sorted(c) for c in comps if len(c) >= 2]
    if not clusters:
        return None
    tk_cluster = {tk: -1 for tk in wide.columns}
    for cid, comp in enumerate(clusters):
        for idx in comp:
            tk_cluster[X.columns[idx]] = cid
    # equal-weight cluster mean daily return over ALL days (members' returns only;
    # consumed shifted-by-one, so a stock-day D only sees cluster returns <= D-1)
    cret = {}
    for cid, comp in enumerate(clusters):
        members = [X.columns[idx] for idx in comp]
        cret[f'peer_cret_{cid}'] = ret[members].mean(axis=1)
    cret = pd.DataFrame(cret)
    cret.index.name = 'date'
    usable_from = pd.Timestamp(f'{form_year}-12-31') + pd.Timedelta(days=1)
    return Peers(tk_cluster, cret.reset_index(),
                 {'cluster_n': {str(cid): len(comp) for cid, comp in enumerate(clusters)},
                  'formation_year': form_year, 'corr_thresh': corr_thresh,
                  'usable_from': str(usable_from.date())})

def peer_columns(dates, bars_tk, peers, cid):
    """Theme-peer columns for one ticker. Cluster returns are shifted one bar
    (D sees cluster returns <= D-1); vs_peer subtracts the shifted cluster
    return from the stock's own shifted return; peer_corr60 is the trailing 60d
    correlation of stock vs cluster daily returns, min 30 paired days, shifted.
    All NaN before peers.usable_from (formation-year warmup)."""
    d = pd.to_datetime(pd.Series(dates)).reset_index(drop=True)
    n = len(d)
    nan = np.full(n, np.nan, dtype=np.float32)
    out = {'peer_id': nan.copy(), 'peer_n': nan.copy(),
           'peer_r1': nan.copy(), 'peer_r5': nan.copy(), 'peer_r20': nan.copy(),
           'vs_peer_r1': nan.copy(), 'vs_peer_r5': nan.copy(), 'vs_peer_r20': nan.copy(),
           'peer_corr60': nan.copy()}
    if peers is None or cid < 0:
        return out
    cr = peers.cluster_ret[['date', f'peer_cret_{cid}']].rename(columns={f'peer_cret_{cid}': 'cret'})
    cr['date'] = pd.to_datetime(cr['date']).astype('datetime64[ns]')
    q = pd.DataFrame({'date': d.astype('datetime64[ns]')})
    m = pd.merge_asof(q, cr, on='date', direction='backward', allow_exact_matches=True)
    cret = m.cret.astype(np.float32).to_numpy()               # cluster ret, strict < D
    def roll_prod(a, w, mp):
        return pd.Series(a).rolling(w, min_periods=mp).apply(lambda s: (1 + s).prod() - 1, raw=True).to_numpy(dtype=np.float32)
    c5 = roll_prod(cret, 5, 3)
    c20 = roll_prod(cret, 20, 10)
    cl = bars_tk.close.to_numpy(float)
    sret = np.r_[np.nan, pd.Series(cl).pct_change(fill_method=None).to_numpy()[1:]]
    s5 = roll_prod(sret, 5, 3)
    s20 = roll_prod(sret, 20, 10)
    sh = lambda a: np.r_[np.nan, a[:-1]]                      # shift one bar: D sees <= D-1
    c1, c5, c20 = sh(cret), sh(c5), sh(c20)
    s1, s5, s20 = sh(sret), sh(s5), sh(s20)
    out['peer_id'] = np.full(n, cid, dtype=np.float32)
    out['peer_n'] = np.full(n, peers.cluster_n.get(str(cid), np.nan), dtype=np.float32)
    out['peer_r1'], out['peer_r5'], out['peer_r20'] = c1, c5, c20
    out['vs_peer_r1'] = (s1 - c1).astype(np.float32)
    out['vs_peer_r5'] = (s5 - c5).astype(np.float32)
    out['vs_peer_r20'] = (s20 - c20).astype(np.float32)
    pr = pd.DataFrame({'s': sret, 'c': cret})
    corr = pr['s'].rolling(60, min_periods=30).corr(pr['c']).to_numpy(dtype=np.float32)
    out['peer_corr60'] = sh(corr)
    mask = (d < pd.Timestamp(peers.usable_from)).to_numpy()
    for k in out:
        out[k] = np.where(mask, np.nan, out[k]).astype(np.float32)
    return out

# ---------------- Block F: FINRA short interest + daily short volume ----------------
def _data_ext_dir():
    return os.path.join(os.environ.get('CHECKLIST_DATA_DIR', '.'), 'data-ext')

def load_si(tickers):
    """FINRA twice-monthly short interest (dictionary I188). Point-in-time: keyed
    on publication_date, never settlement_date. Columns: si_qty (current short
    position), si_dtc (days to cover), si_chg (qty vs previous settlement as
    published)."""
    base = _data_ext_dir()
    if not os.path.isdir(base):
        return None
    fs = [os.path.join(base, f) for f in sorted(os.listdir(base))
          if f.startswith('finra_si_') and f.endswith('.parquet')]
    if not fs:
        return None
    cols = ['symbol', 'publication_date', 'current_short_qty', 'previous_short_qty', 'days_to_cover']
    df = pd.concat([pd.read_parquet(f, columns=cols) for f in fs], ignore_index=True)
    df = df[df.symbol.isin(tickers)]
    if not len(df):
        return None
    df['publication_date'] = pd.to_datetime(df['publication_date'])
    prev = df.previous_short_qty.to_numpy(float)
    cur = df.current_short_qty.to_numpy(float)
    df['si_chg'] = np.where(prev > 0, cur / prev - 1, np.nan)
    df = df.rename(columns={'current_short_qty': 'si_qty', 'days_to_cover': 'si_dtc'})
    return df[['symbol', 'publication_date', 'si_qty', 'si_dtc', 'si_chg']].sort_values('publication_date')

def load_shvol(tickers):
    """FINRA daily short volume ratio (dictionary I189): published after 18:00 ET
    on date X -> usable from the next session. Adds 5- and 20-day rolling means
    of the ratio per ticker."""
    base = _data_ext_dir()
    if not os.path.isdir(base):
        return None
    fs = [os.path.join(base, f) for f in sorted(os.listdir(base))
          if f.startswith('finra_shvol_') and f.endswith('.parquet')]
    if not fs:
        return None
    df = pd.concat([pd.read_parquet(f, columns=['date', 'symbol', 'short_ratio']) for f in fs],
                   ignore_index=True)
    df = df[df.symbol.isin(tickers)]
    if not len(df):
        return None
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date'])
    g = df.groupby('symbol')['short_ratio']
    df['shv_r5'] = g.transform(lambda s: s.rolling(5, min_periods=3).mean())
    df['shv_r20'] = g.transform(lambda s: s.rolling(20, min_periods=10).mean())
    return df.rename(columns={'short_ratio': 'shv_ratio'})

# ---------------- Block G: halts + Reg SHO threshold ----------------
def load_halts(tickers):
    """Nasdaq trading halts 2020-2026 (dictionary I191). An event is knowable on
    day D only if halt_date < D (strict; the dictionary's pre-open timestamp rule
    is approximated conservatively by date). The resume gap is reported only when
    resume_date is also < D, so no future resume info leaks through ongoing halts.
    reason is factorized to a small int code (fixed set)."""
    base = _data_ext_dir()
    p = os.path.join(base, 'nasdaq_halts_2020_2026.parquet')
    if not os.path.exists(p):
        return None
    df = pd.read_parquet(p, columns=['halt_date', 'symbol', 'reason', 'resume_date'])
    df = df[df.symbol.isin(tickers)]
    if not len(df):
        return None
    hd = pd.to_datetime(df.halt_date, format='%m/%d/%Y', errors='coerce')
    rd = pd.to_datetime(df.resume_date, format='%m/%d/%Y', errors='coerce')
    df = df.assign(halt_d=hd, resume_d=rd).dropna(subset=['halt_d'])
    # Fixed categorical codes; labels cannot change with other tickers/future rows.
    reasons = {'T1':1,'T2':2,'T3':3,'T12':12,'H4':14,'H9':19,'H10':20,'H11':21,'LUDP':30,'LUDS':31,'MWC1':40,'MWC2':41,'MWC3':42}
    df['halt_rsn'] = df.reason.fillna('').str.strip().map(reasons).fillna(99).astype(np.float32)
    return df[['symbol', 'halt_d', 'resume_d', 'halt_rsn']].sort_values('halt_d')

def load_regsho(tickers):
    """NYSE/Nasdaq Reg SHO threshold list (dictionary I190): the file for date d
    is published after the close of d -> usable next session (strict date < D)."""
    base = _data_ext_dir()
    p = os.path.join(base, 'nasdaq_regsho_threshold_2020_2026.parquet')
    if not os.path.exists(p):
        return None
    df = pd.read_parquet(p, columns=['date', 'symbol'])
    df = df[df.symbol.isin(tickers)]
    if not len(df):
        return None
    df['date'] = pd.to_datetime(df['date'])
    return df[['symbol', 'date']].sort_values('date')

def load_box_ext(tickers):
    """Load every available box-only block at once. Returns a dict of per-ticker
    dicts: {'si': {tk: frame}, 'shvol': {tk: frame}, 'halts': {tk: frame},
    'regsho': {tk: frame}}; missing blocks are absent (or None if no files)."""
    out = {}
    si = load_si(tickers)
    out['si'] = dict(tuple(si.groupby('symbol'))) if si is not None else None
    shv = load_shvol(tickers)
    out['shvol'] = dict(tuple(shv.groupby('symbol'))) if shv is not None else None
    ha = load_halts(tickers)
    out['halts'] = dict(tuple(ha.groupby('symbol'))) if ha is not None else None
    rg = load_regsho(tickers)
    out['regsho'] = dict(tuple(rg.groupby('symbol'))) if rg is not None else None
    dv = load_divsplits(tickers)
    if dv is not None:
        out['divs'] = {tk: g[g.kind == 'div'][['date', 'value']] for tk, g in dv.groupby('ticker') if (g.kind == 'div').any()}
        out['splits'] = {tk: g[g.kind == 'split'][['date', 'value']] for tk, g in dv.groupby('ticker') if (g.kind == 'split').any()}
    f4 = load_form4(tickers)
    if f4 is not None:
        out['f4'] = {tk: g[['date', 'n']].rename(columns={'n': 'value'})
                     for tk, g in f4.groupby('ticker')}
    return {k: v for k, v in out.items() if v}

def _asof_strict(dates, right, cols, date_col, prefix_days=None):
    """Backward asof join of per-ticker `right` frame onto sorted `dates`, keeping
    only rows strictly before each date. Returns {col: np.array} plus
    {prefix_days: days-since-last-record} when prefix_days is given."""
    if right is None or not len(right):
        return {}
    q = pd.DataFrame({'date': pd.to_datetime(dates).astype('datetime64[ns]')})
    r = right.rename(columns={date_col: '_evt'}).sort_values('_evt')
    r['_evt'] = pd.to_datetime(r['_evt']).astype('datetime64[ns]')
    m = pd.merge_asof(q, r[['_evt'] + cols], left_on='date', right_on='_evt',
                      direction='backward', allow_exact_matches=False)   # last record STRICTLY before D
    ok = m['_evt'] < m.date                      # strict: nothing from D onward
    m = m.where(ok)
    out = {c: m[c].to_numpy(dtype=np.float32) for c in cols}
    if prefix_days:
        out[prefix_days] = (m.date - m['_evt']).dt.days.to_numpy(dtype=np.float32)
    return out

def halt_columns(dates, hf):
    """Halt columns for one ticker's sorted date array from its halt event frame.
    halt_days/gap/rsn use the last event with halt_d < D; the gap only when that
    event's resume_d is also < D. halt_n20/halt_n60 count events in the trailing
    20/60 calendar days (T20-CNT style), strict < D."""
    d = pd.to_datetime(pd.Series(dates)).to_numpy(dtype='datetime64[ns]')
    n = len(d)
    nan = np.full(n, np.nan, dtype=np.float32)
    out = {'halt_days': nan.copy(), 'halt_gap': nan.copy(), 'halt_rsn': nan.copy(),
           'halt_n20': nan.copy(), 'halt_n60': nan.copy(), 'halt_duration_days': nan.copy()}
    if hf is None or not len(hf):
        return out
    he = np.sort(hf.halt_d.to_numpy(dtype='datetime64[ns]'))
    res = hf.sort_values('halt_d').resume_d.to_numpy(dtype='datetime64[ns]')
    rsn = hf.sort_values('halt_d').halt_rsn.to_numpy(dtype=np.float32)
    one_day = np.timedelta64(1, 'D')
    for i, D in enumerate(d):
        j = np.searchsorted(he, D, side='left')     # events with halt_d < D
        if j == 0:
            continue
        k = j - 1
        out['halt_days'][i] = (D - he[k]) / one_day
        out['halt_rsn'][i] = rsn[k]
        if not np.isnat(res[k]) and res[k] < D:
            out['halt_duration_days'][i] = (res[k] - he[k]) / one_day
        out['halt_n20'][i] = j - np.searchsorted(he, D - np.timedelta64(20, 'D'), side='left')
        out['halt_n60'][i] = j - np.searchsorted(he, D - np.timedelta64(60, 'D'), side='left')
    return out

# ---------------- Block J: dividends + splits events ----------------
def load_divsplits(tickers):
    """Dividend and split EVENTS (dictionary I196), Yahoo chart events API output
    (fetch_divsplits.py -> data-ext/divsplits_shard_*.parquet). Bars are already
    split-adjusted; these dates power 'split in last N days' / 'dividend in last
    N days' questions. Ex-date usable from the next session (strict date < D);
    the future-ex-date/declaration nuance is a groups-034+ definitional detail."""
    base = _data_ext_dir()
    if not os.path.isdir(base):
        return None
    fs = [os.path.join(base, f) for f in sorted(os.listdir(base))
          if f.startswith('divsplits_shard_') and f.endswith('.parquet')]
    if not fs:
        return None
    df = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    df = df[df.ticker.isin(tickers)]
    if not len(df):
        return None
    df['date'] = pd.to_datetime(df['date'])
    return df[['ticker', 'kind', 'date', 'value']].sort_values('date')

def event_columns(dates, evt, value_name, days_name, count_name, count_window=None):
    """Last-event days/value plus trailing-window count for one ticker's sorted
    date array. `evt` is a sorted DataFrame with columns date + value; only
    events strictly before each date are used (searchsorted side='left')."""
    d = pd.to_datetime(pd.Series(dates)).reset_index(drop=True)
    n = len(d)
    nan = np.full(n, np.nan, dtype=np.float32)
    out = {days_name: nan.copy(), value_name: nan.copy()}
    if count_name:
        out[count_name] = nan.copy()
    if evt is None or not len(evt):
        return out
    ed = evt.date.to_numpy(dtype='datetime64[ns]')
    dd = d.to_numpy(dtype='datetime64[ns]')
    one = np.timedelta64(1, 'D')
    pos = np.searchsorted(ed, dd, side='left')        # events with date < D
    has = pos > 0
    idx = np.clip(pos - 1, 0, len(ed) - 1)
    days = np.where(has, (dd - ed[idx]) / one, np.nan)
    out[days_name] = days.astype(np.float32)
    vals = evt.value.to_numpy(dtype=np.float32)
    out[value_name] = np.where(has, vals[idx], np.nan).astype(np.float32)
    if count_name:
        lo = np.searchsorted(ed, dd - np.timedelta64(count_window, 'D'), side='left') if count_window \
            else np.zeros(n, dtype=int)
        out[count_name] = np.where(has, (pos - lo).astype(np.float32), np.nan).astype(np.float32)
    return out

# ---------------- Block K extension: M008 / M047 breadth math ----------------
def extend_breadth(breadth):
    """M008 Advance/Decline Ratio and M047 Cumulative Volume Index, derived daily
    from the universe file — the SAME provenance as the existing breadth column
    (universe_2020_survivors; survivors-only bias unchanged, flagged in coverage).
    advdecl = n_adv / n_dec across the universe; cvi_m = cumulative (up-day volume
    − down-day volume) in $millions; cvi_chg20_m = its 20-day change. All are
    market-wide rows keyed by date, joined strict < D like the other breadth cols.
    Returns `breadth` unchanged if the universe or volume data is unavailable
    (then M047 stays pending; logged, not silent)."""
    u = D('/workspace/pricehist/universe_2020_survivors.parquet')
    if breadth is None or not os.path.exists(u):
        print('extend_breadth: skipped (no breadth frame or universe file)', flush=True)
        return breadth
    cols = ['ticker', 'date', 'close']
    try:
        import pyarrow.parquet as _pq
        has_vol = 'volume' in _pq.read_schema(u).names
    except Exception as e:
        print(f'extend_breadth: schema check failed ({e}); using close only', flush=True)
        has_vol = False
    if has_vol:
        cols.append('volume')
    px = pd.read_parquet(u, columns=cols)
    px['date'] = pd.to_datetime(px['date'])
    px = px.sort_values(['ticker', 'date'])
    px['prev'] = px.groupby('ticker')['close'].shift(1)
    up = px.close > px.prev
    dn = px.close < px.prev
    n_adv = up.groupby(px.date).sum()
    n_dec = dn.groupby(px.date).sum()
    adr = (n_adv / n_dec.replace(0, np.nan)).rename('advdecl').reset_index()
    out = breadth.merge(adr, on='date', how='left')
    if has_vol:
        uv = px.assign(vol_up=px.volume.where(up)).groupby('date')['vol_up'].sum()
        dv = px.assign(vol_dn=px.volume.where(dn)).groupby('date')['vol_dn'].sum()
        cvi = (uv - dv).cumsum() / 1e6
        cdf = pd.DataFrame({'date': cvi.index, 'cvi_m': cvi.to_numpy(),
                            'cvi_chg20_m': cvi.diff(20).to_numpy()})
        out = out.merge(cdf, on='date', how='left')
    print(f'extend_breadth: added advdecl{"+cvi_m+cvi_chg20_m" if has_vol else " (no volume col)"}', flush=True)
    return out

# ---------------- per-ticker assembly (single definition; main + leak test) ----------------
def ticker_frame(tk, d, funcs, etf, breadth, edf_tk, ext=None, peers=None, mkt=None, an=None, xb=None, gd=None, f13=None, fred=None):
    """Assemble one ticker's world rows from its sorted bar frame `d`.
    Every join is backward-looking and every TA-Lib array is shifted by one bar:
    row D uses bars <= D-1, ETF bars <= D-1, breadth dated < D, earnings with
    report_date < D. `edf_tk` is the ticker's earnings sub-frame (or None).
    `ext` is the ticker's box-only block dict: si/shvol/regsho frames and the
    halt event frame; every one of those joins is strict < D as well. `peers`
    is a frozen Peers object; cluster returns are consumed shifted one bar.
    `mkt` is the market-wide daily frame (VIX etc.); joined strict < D.
    `an` is the ticker's analyst-action day-count frame (strict < D)."""
    df = pd.DataFrame({'ticker': tk, 'date': d.date.to_numpy()})
    if len(d) >= 30:
        o = d.open.to_numpy(float); h = d.high.to_numpy(float); l = d.low.to_numpy(float)
        c = d.close.to_numpy(float); v = d.volume.to_numpy(float)
        cols = compute_talib(o, h, l, c, v, funcs)
        for k, arr in cols.items():
            df[k] = np.r_[np.nan, arr[:-1]]          # shift-by-one: D sees bars <= D-1
        for k, arr in compute_tv_extra(o, h, l, c, v, dates=d.date.to_numpy()).items():
            df[k] = np.r_[np.nan, arr[:-1]]          # same shift; bar-derived only
    # M113 Moon Phases: calendar-derived, computed from the row's own date (no shift).
    df['tv_moon_age'] = moon_age(df['date'].to_numpy())
    if mkt is not None:
        mcols = [c for c in mkt.columns if c != 'date']
        key = pd.to_datetime(df['date']) - pd.Timedelta(days=1)   # strict: mkt date < D
        m = pd.merge_asof(pd.DataFrame({'date': key}).sort_values('date'),
                          mkt, on='date', direction='backward')
        for mc in mcols:
            df[f'mkt_{mc}'] = m[mc].to_numpy(dtype=np.float32)
    if an is not None:
        for c, v in analyst_columns(df['date'].to_numpy(), an).items():
            df[c] = v
    if xb is not None:
        for c, v in xbrl_columns(df['date'].to_numpy(), xb).items():
            df[c] = v
    if gd is not None:
        for c, v in gd_columns(df['date'].to_numpy(), gd).items():
            df[c] = v
    if f13 is not None:
        for c, v in f13_columns(df['date'].to_numpy(), f13).items():
            df[c] = v
    if fred is not None:
        for c, v in fred_columns(df['date'].to_numpy(), fred).items():
            df[c] = v
    if breadth is not None:
        bcols = [c for c in breadth.columns if c != 'date']
        key = pd.to_datetime(df['date']) - pd.Timedelta(days=1)   # strict: breadth date < D
        m = pd.merge_asof(pd.DataFrame({'date': key}).sort_values('date'),
                          breadth, on='date', direction='backward')
        for bc in bcols:
            df[bc] = m[bc].to_numpy(dtype=np.float32)
    if etf is not None:
        ecols = [c for c in etf.columns if c != 'date']
        key = pd.to_datetime(df['date'])
        m = pd.merge_asof(pd.DataFrame({'date': key}), etf, on='date', direction='backward')
        for ec in ecols:
            df[ec] = m[ec].to_numpy(dtype=np.float32)
    e2 = earn_for(d.date.to_numpy(), edf_tk) if edf_tk is not None else None
    if e2 is not None:
        df = pd.concat([df.reset_index(drop=True), e2.reset_index(drop=True)], axis=1)
    if ext:
        dates = df['date'].to_numpy()
        if ext.get('si') is not None:
            for c, v in _asof_strict(dates, ext['si'], ['si_qty', 'si_dtc', 'si_chg'],
                                     'publication_date', prefix_days='si_days').items():
                df[c] = v
        if ext.get('shvol') is not None:
            for c, v in _asof_strict(dates, ext['shvol'], ['shv_ratio', 'shv_r5', 'shv_r20'], 'date').items():
                df[c] = v
        if ext.get('regsho') is not None:
            r = _asof_strict(dates, ext['regsho'], [], 'date', prefix_days='regsho_days')
            if 'regsho_days' in r:
                df['regsho_days'] = r['regsho_days']
                df['regsho_on'] = (df['regsho_days'] <= 7).astype(np.float32)
                df.loc[df['regsho_days'].isna(), 'regsho_on'] = np.nan
        if ext.get('halts') is not None:
            for c, v in halt_columns(dates, ext['halts']).items():
                df[c] = v
        if ext.get('f4') is not None:
            for c, v in event_columns(dates, ext['f4'], 'f4_n', 'f4_days', 'f4_n20', count_window=20).items():
                df[c] = v
            # 60-day count, same strict-<D window semantics
            d60 = event_columns(dates, ext['f4'], '_v', '_d', 'f4_n60', count_window=60)
            df['f4_n60'] = d60['f4_n60']
        if ext.get('divs') is not None:
            for c, v in event_columns(dates, ext['divs'], 'div_amt', 'div_days', 'div_n12', count_window=365).items():
                df[c] = v
        if ext.get('splits') is not None:
            for c, v in event_columns(dates, ext['splits'], 'split_ratio', 'split_days', 'split_n', count_window=None).items():
                df[c] = v
    if peers is not None:
        cid = peers.tk_cluster.get(tk, -1)
        for c, v in peer_columns(df['date'].to_numpy(), d, peers, cid).items():
            df[c] = v
    return df

# ---------------- build ----------------
def load_bars(tickers=None):
    p = D('/workspace/updown/bars_all.parquet')
    df = pd.read_parquet(p)
    df['date'] = pd.to_datetime(df['date'])       # file stores timestamp; filter after parse
    df = df[df.date <= END]
    if tickers: df = df[df.ticker.isin(tickers)]
    return df

def main():
    global COVERAGE_NOTE
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['build', 'coverage'])
    ap.add_argument('--shard', type=int, default=0); ap.add_argument('--shards', type=int, default=8)
    ap.add_argument('--out', default='world_out'); ap.add_argument('--tickers', default=None)
    a = ap.parse_args()
    funcs = discover()
    n_pat = sum(1 for k in funcs if funcs[k][0] == 'pattern')
    if a.cmd == 'coverage':
        for name, (kind, _) in sorted(funcs.items()): print(kind, name)
        print(f'coverage: {len(funcs)} functions ({n_pat} patterns) of {len(talib.get_functions())} total')
        return
    print(f'world build shard {a.shard}/{a.shards}: {len(funcs)} TA-Lib functions ({n_pat} patterns)', flush=True)

    u = pd.read_parquet(D('/workspace/pricehist/universe_2020_survivors.parquet'), columns=['ticker', 'date'])
    tickers = sorted(u.ticker.unique())
    if a.tickers: tickers = [t for t in a.tickers.split(',') if t in set(tickers)]
    mine = tickers[a.shard::a.shards]
    print('tickers in shard:', len(mine), flush=True)

    br = D('/workspace/updown/breadth_2020_24.parquet')
    breadth = None
    if os.path.exists(br):
        breadth = pd.read_parquet(br)
        if 'date' not in breadth.columns:
            breadth = breadth.reset_index()          # file stores date as the index
        breadth['date'] = pd.to_datetime(breadth['date'])
        breadth = breadth.sort_values('date')
    breadth = extend_breadth(breadth)
    if breadth is not None: print('breadth cols:', list(breadth.columns), flush=True)

    bars = load_bars(set(mine))
    os.makedirs(a.out, exist_ok=True)
    bcols = [c for c in breadth.columns if c != 'date'] if breadth is not None else []
    etf = etf_wide()
    ecols = [c for c in etf.columns if c != 'date'] if etf is not None else []
    if etf is not None: print('ETF overlay cols:', len(ecols), flush=True)
    edf_by_tk = None
    edf = load_earnings(set(mine))
    ecols2 = ['earn_days', 'earn_amc', 'earn_surp', 'earn_deps'] if edf is not None else []
    if edf is not None:
        edf_by_tk = dict(tuple(edf.groupby('symbol')))
        print('earnings rows for shard:', len(edf), flush=True)
    ext_by_tk = {}
    box = load_box_ext(set(mine))
    for blk, per in box.items():
        for tk, fr in per.items():
            ext_by_tk.setdefault(tk, {})[blk] = fr
    box_cols = {'si': ['si_qty', 'si_dtc', 'si_chg', 'si_days'],
                'shvol': ['shv_ratio', 'shv_r5', 'shv_r20'],
                'regsho': ['regsho_days', 'regsho_on'],
                'halts': ['halt_days', 'halt_gap', 'halt_rsn', 'halt_n20', 'halt_n60'],
                'divs': ['div_amt', 'div_days', 'div_n12'],
                'splits': ['split_ratio', 'split_days', 'split_n'],
                'f4': ['f4_n', 'f4_days', 'f4_n20', 'f4_n60']}
    if box:
        print('box-only blocks loaded:', {k: len(v) for k, v in box.items()}, flush=True)
    peers = build_peers(load_bars(None))
    if peers is not None:
        print('theme-peer clusters:', len(peers.cluster_n), 'formation year:', peers.formation_year,
              'usable from:', peers.usable_from, flush=True)
    mkt = load_mkt()
    mkt_cols = [f'mkt_{c}' for c in mkt.columns if c != 'date'] if mkt is not None else []
    if mkt is not None:
        print('market-wide cols:', mkt_cols, mkt.date.min().date(), '->', mkt.date.max().date(), flush=True)
    an = load_analyst(set(mine))
    an_by_tk = {tk: g.reset_index(drop=True) for tk, g in an.groupby('ticker')} if an is not None else {}
    an_cols = ['an_days', 'an_n20', 'an_up20', 'an_dn20', 'an_n60', 'an_up60', 'an_dn60', 'an_dir'] if an is not None else []
    if an is not None:
        print('analyst action rows for shard:', len(an), 'tickers with actions:', len(an_by_tk), flush=True)
    xb = load_xbrl(set(mine))
    xb_by_tk = {tk: g.reset_index(drop=True) for tk, g in xb.groupby('ticker')} if xb is not None else {}
    XB_COLS = ['xb_days', 'xb_rev', 'xb_rev_days', 'xb_rev_g', 'xb_ni', 'xb_ni_days', 'xb_ni_g',
               'xb_assets', 'xb_assets_days', 'xb_debt', 'xb_debt_days', 'xb_shares', 'xb_shares_days']
    xb_cols = XB_COLS if xb is not None else []
    if xb is not None:
        print('xbrl rows for shard:', len(xb), 'tickers covered:', len(xb_by_tk), flush=True)
    gdv = load_gdelt(set(mine))
    gd_by_tk = {tk: g.reset_index(drop=True) for tk, g in gdv.groupby('ticker')} if gdv is not None else {}
    GD_COLS = ['gd_days', 'gd_n7', 'gd_n30', 'gd_spike']
    gd_cols = GD_COLS if gdv is not None else []
    if gdv is not None:
        print('gdelt rows for shard:', len(gdv), 'tickers covered:', len(gd_by_tk), flush=True)
    f13 = load_f13(set(mine))
    f13_by_tk = {tk: g.reset_index(drop=True) for tk, g in f13.groupby('ticker')} if f13 is not None else {}
    F13_COLS = ['f13_days', 'f13_qdays', 'f13_n', 'f13_q4']
    f13_cols = F13_COLS if f13 is not None else []
    if f13 is not None:
        print('13f hits for shard:', len(f13), 'tickers covered:', len(f13_by_tk), flush=True)
    fred = load_fred()
    fred_cols = sorted({f'fred_{s.lower()}' for s in fred.series} |
                       {f'fred_{s.lower()}_odays' for s in fred.series}) if fred is not None else []
    if fred is not None:
        print('fred series:', sorted(fred.series.unique()), flush=True)
    parts, meta = [], {'talib_funcs': sorted(funcs), 'talib_exclusions': DISCOVERY_EXCLUSIONS, 'shift': 'value at D uses bars <= D-1',
                       'shard': a.shard, 'shards': a.shards, 'breadth_cols': bcols,
                       'etf_cols': ecols, 'etf_note': 'shifted 1 ETF bar, asof join; SPDR set uses current sector labels (bias flagged)',
                       'earn_cols': ecols2, 'earn_note': 'strict report_date < D (BMO-on-D excluded)',
                       'peer_cols': ['peer_id', 'peer_n', 'peer_r1', 'peer_r5', 'peer_r20',
                                     'vs_peer_r1', 'vs_peer_r5', 'vs_peer_r20', 'peer_corr60'] if peers is not None else [],
                       'peer_note': None if peers is None else
                           f'clusters frozen from {peers.formation_year} daily-return correlation >= {peers.corr_thresh} '
                           f'(connected components); fixed-taxonomy label bias flagged; NaN before {peers.usable_from}',
                       'box_cols': {k: box_cols[k] for k in box if box[k]},
                       'box_notes': {'si': 'I188: keyed publication_date < D, never settlement',
                                     'shvol': 'I189: dated X published after 18:00 ET, usable next session (strict < D)',
                                     'regsho': 'I190: file for d published after close of d, usable next session (strict < D); regsho_on = listed within 7 cal days',
                                     'halts': 'I191: halt_date < D strict; gap only when resume also < D; reason = factorized int',
                                     'f4': 'I187 date-count lens: Form 4 filingDate < D strict (public on filingDate, usable next session); value lens (shares/role) later'},
                       'mkt_cols': mkt_cols,
                       'mkt_notes': 'I178 VIX via keyless FRED CSV (never revised); strict date < D; mkt_ prefix',
                       'an_cols': an_cols,
                       'an_notes': 'I197 analyst actions (yfinance upgrades_downgrades); strict date < D; counts by direction',
                       'xb_cols': xb_cols,
                       'xb_notes': 'I192 XBRL via SEC frames API; keyed filed < D (restatement-safe); CY-frame coverage sparser for fiscal-offset filers',
                       'gd_cols': gd_cols,
                       'gd_notes': 'I200 GDELT 2.0 timelinevol mention counts; exact-symbol query (short-symbol noise uniform); strict < D; 0 = covered-but-silent, NaN = no data yet',
                       'f13_cols': f13_cols,
                       'f13_notes': 'I199 13F-HR(/A) via EDGAR FTS by CUSIP (OpenFIGI map); f13_n lower-bounds mega-cap filers (page cap); keyed file_date < D',
                       'fred_cols': fred_cols,
                       'fred_notes': 'I195 FRED/ALFRED vintages (BLOCKED_SECRET until FRED_API_KEY); keyed vintage_date < D'}
    for i, (tk, d) in enumerate(bars.groupby('ticker', sort=False)):
        d = d.sort_values('date')
        if len(d) < 30: continue
        df = ticker_frame(tk, d, funcs, etf if ecols else None,
                          breadth if bcols else None, edf_by_tk.get(tk) if ecols2 else None,
                          ext=ext_by_tk.get(tk), peers=peers, mkt=mkt if mkt_cols else None,
                          an=an_by_tk.get(tk) if an_cols else None,
                          xb=xb_by_tk.get(tk) if xb_cols else None,
                          gd=gd_by_tk.get(tk) if gd_cols else None,
                          f13=f13_by_tk.get(tk) if f13_cols else None,
                          fred=fred if fred_cols else None)
        parts.append(df)
        if i % 200 == 199: print(f'{i+1} tickers', flush=True)
    if parts:
        out = pd.concat(parts, ignore_index=True)
        fn = os.path.join(a.out, f'world_shard_{a.shard:03d}.parquet')
        out.to_parquet(fn, index=False)
        meta['rows'] = int(len(out)); meta['cols'] = int(out.shape[1]); meta['tickers'] = int(out.ticker.nunique())
        json.dump(meta, open(fn.replace('.parquet', '.json'), 'w'), indent=1)
        print('wrote', fn, len(out), 'rows x', out.shape[1], 'cols')
    else:
        print('no data for shard', a.shard)

if __name__ == '__main__':
    main()

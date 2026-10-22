"""New Bot reader (v4.4g rows) for the pre-open answer engine.

answer(ticker, date) -> list of dicts {row_id, ticker, date, answer, reason, data_as_of}
Answers all 2,576 full v4.4g rows (superset of the 650 compact rows in merged_draft_v8.1).
Cutoff: only data public before 09:25 ET on `date`:
  * Yahoo daily bars strictly before `date` (D-1 close known 16:15 ET D-1).
  * Theme Radar snapshots per snapshot_pins_new-bot.csv (known_from_session <= date; 08-07 -> 94cb047,
    3a6f843 counts from 08-10). AH rows start 2026-08-07; AH volume from sessions 08-06/08-10 skipped.
  * Option-expiry rows use the NYSE holiday rules (published years ahead), so D itself may be used.
Downloads are cached under engine/cache/newbot/ (first fetch is frozen => reruns are identical).
"""
import csv, re, subprocess, io, math
from pathlib import Path
from datetime import date as _date, timedelta
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[2]            # /workspace/checklist_brainstorm
ROWS = ROOT / "fetch_tests" / "new-bot-v4.4g.csv"
PINS = ROOT / "fetch_tests" / "snapshot_pins_new-bot.csv"
CACHE = ROOT / "engine" / "cache" / "newbot"
TR_REPO = Path("/workspace/theme-radar-repo")
AH_START = "2026-08-07"
AH_VOL_SKIP = {"2026-08-06", "2026-08-10"}

# ---------------------------------------------------------------- data
def _yahoo(t):
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"yahoo_{t}.csv"
    if not f.exists():
        import yfinance as yf
        df = yf.Ticker(t).history(start="2010-01-01", end="2026-10-22", auto_adjust=False, actions=False)
        if df is None or df.empty:
            raise RuntimeError(f"yahoo_empty:{t}")
        df.index = pd.to_datetime(df.index).tz_localize(None).strftime("%Y-%m-%d")
        df = df[["Open", "High", "Low", "Close", "Volume"]].round(6)
        df.to_csv(f, index_label="Date")
    df = pd.read_csv(f, index_col="Date")
    return df[df["Close"].notna()]

def _pins():
    out = {}
    for r in csv.DictReader(open(PINS)):
        out[r["known_from_session"]] = (r["date"], r["first_commit_sha"][:7])
    return dict(sorted(out.items()))

_SNAP = {}
def _snapshot(sha, fdate):
    key = (sha, fdate)
    if key not in _SNAP:
        f = CACHE / f"snap_{fdate}_{sha}.csv"
        if not f.exists():
            CACHE.mkdir(parents=True, exist_ok=True)
            raw = subprocess.run(["git", "-C", str(TR_REPO), "show", f"{sha}:data/snapshots/{fdate}.raw.csv"],
                                 capture_output=True, check=True).stdout
            f.write_bytes(raw)
        df = pd.read_csv(f, low_memory=False)
        _SNAP[key] = df.set_index("Ticker")
    return _SNAP[key]

def _num(v):
    if v is None or (isinstance(v, float) and math.isnan(v)): return np.nan
    s = str(v).replace("%", "").replace(",", "").strip()
    try: return float(s)
    except ValueError: return np.nan

# ---------------------------------------------------------------- NYSE calendar (rule-based)
def _obs(d):
    if d.weekday() == 5: return d - timedelta(1)
    if d.weekday() == 6: return d + timedelta(1)
    return d
def _nth(y, m, wd, n):
    d = _date(y, m, 1); d += timedelta((wd - d.weekday()) % 7); return d + timedelta(7 * (n - 1))
def _last(y, m, wd):
    d = _date(y, m + 1, 1) - timedelta(1) if m < 12 else _date(y, 12, 31)
    return d - timedelta((d.weekday() - wd) % 7)
def _easter(y):
    a=y%19;b=y//100;c=y%100;d=b//4;e=b%4;f=(b+8)//25;g=(b-f+1)//3;h=(19*a+b-d-g+15)%30
    i=c//4;k=c%4;l=(32+2*e+2*i-h-k)%7;m=(a+11*h+22*l)//451;mo=(h+l-7*m+114)//31;da=((h+l-7*m+114)%31)+1
    return _date(y, mo, da)
def _holidays(y):
    h = {_obs(_date(y,1,1)), _nth(y,1,0,3), _nth(y,2,0,3), _easter(y)-timedelta(2), _last(y,5,0),
         _obs(_date(y,7,4)), _nth(y,9,0,1), _nth(y,11,3,4), _obs(_date(y,12,25))}
    if y >= 2022: h.add(_obs(_date(y,6,19)))
    return h
def _is_session(d):
    return d.weekday() < 5 and d not in _holidays(d.year)
def _sessions_back(D, n):   # last n sessions ending at D inclusive (D need not be a session)
    out, d = [], D
    while len(out) < n:
        if _is_session(d): out.append(d)
        d -= timedelta(1)
    return out
def _expiry(y, m, quarterly=False):
    if quarterly and m not in (3, 6, 9, 12): return None
    d = _nth(y, m, 4, 3)
    while not _is_session(d): d -= timedelta(1)
    return d
def _cal_event(fam, d):
    if fam == "071": return d == _expiry(d.year, d.month)
    if fam == "073": return d == _expiry(d.year, d.month, True)
    if fam == "072":
        f = d + timedelta((4 - d.weekday()) % 7)      # this week's Friday
        while not _is_session(f): f -= timedelta(1)
        return d == f
    raise KeyError(fam)

# ---------------------------------------------------------------- X series
def _atr(df, n=14):
    pc = df["Close"].shift(1)
    tr = pd.concat([df["High"]-df["Low"], (df["High"]-pc).abs(), (df["Low"]-pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()

def _x_yahoo(fam, df, spy):
    C = df["Close"]
    if fam == "015":
        lvl = np.ceil(C)                               # nearest $1/$5/$10/$50/$100 level >= C is the next whole dollar
        return (C - lvl) / _atr(df)
    if fam == "029":
        return ((C / C.shift(1) - 1).abs() >= 0.20).astype(float).rolling(250).sum()
    if fam == "035":
        g = (df["Open"] > df["High"].shift(1)).astype(int)
        return g.groupby((g == 0).cumsum()).cumsum().astype(float)
    if fam == "025":
        r = C.pct_change(); s = spy["Close"].reindex(df.index).pct_change()
        b = lambda n: r.rolling(n).cov(s) / s.rolling(n).var()
        return b(20) / b(250)
    raise KeyError(fam)

import functools
@functools.lru_cache(maxsize=None)
def _x_snapshot(fam, ticker, D, universe=False):
    """Daily X series indexed by session (from pins), using snapshots known by D. Returns Series (or DataFrame if universe)."""
    col = {"022": "EPS Surprise", "023": "Revenue Surprise"}
    vals, asof = {}, {}
    for sess, (fdate, sha) in _pins().items():
        if sess > D: break
        if fam in ("008", "010") and sess < AH_START: continue
        if fam == "010" and sess in AH_VOL_SKIP: continue
        s = _snapshot(sha, fdate)
        if fam in col:
            v = s[col[fam]].map(_num) / 100.0
        elif fam == "008":
            v = s["After-Hours Close"].map(_num) / s["Price"].map(_num) - 1
        elif fam == "010":
            v = s["After-Hours Volume"].map(_num)
        vals[sess] = v if universe else v.get(ticker, np.nan)
        asof[sess] = fdate
    if universe:
        return pd.DataFrame(vals).T, asof
    ser = pd.Series(vals, dtype=float)
    if fam == "010":                                   # X = AH vol / mean AH vol prior 20 (kept) sessions
        ser = ser / ser.shift(1).rolling(20).mean()
    return ser, asof

# ---------------------------------------------------------------- lenses
class NR(Exception): pass

def _need(x, n):
    if x.notna().sum() < n or len(x) < n or pd.isna(x.iloc[-1]):
        raise NR(f"insufficient_history:need_{n}_values_have_{int(x.notna().sum())}")

def _pct(a, v):          # percentile rank of v in a (0..100)
    a = np.asarray(a[~np.isnan(a)]); return 100.0 * (a <= v).mean()

def _runs(flag):
    """current run length ending last element, and list of completed past run lengths."""
    f = list(flag); cur = 0
    for v in reversed(f):
        if v: cur += 1
        else: break
    past, n = [], 0
    for v in f[:len(f) - cur]:
        if v: n += 1
        elif n: past.append(n); n = 0
    return cur, past

def _fmt(v):
    try:
        v = float(v)
        if abs(v) >= 100: return f"{v:.1f}"
        if abs(v) >= 1: return f"{v:.3f}"
        return f"{v:.4f}"
    except Exception:
        return str(v)

def _lens(suffix, defn, x, price, but):
    """x: daily X series ending D-1. Returns (bool, reason_phrase)."""
    m = re.match(r"T(\d+)-(THR|CHG|EXT|CRS|STK|DIV)$", suffix) or re.match(r"P(\d+)-(POS[QD])$", suffix) \
        or re.match(r"DUR(\d+)-(SUP|SDN|ZTQ|ZBQ)$", suffix)
    if not m: raise NR("rule_vague:unparsed_lens")
    N, kind = int(m.group(1)), m.group(2)
    xn = x.rolling(N).mean() if suffix.startswith("T") else x
    if kind == "THR":
        t = re.search(r"YES if X_N\s*(>=|<=)\s*(-?[\d.]+)", defn)
        if not t: raise NR("rule_vague:no_threshold")
        _need(xn, 1); v = xn.iloc[-1]; th = float(t.group(2)); op = t.group(1)
        yes = (v >= th) if op == ">=" else (v <= th)
        return yes, f"X_N={_fmt(v)}{op}{th}"
    if kind == "CHG":
        d = xn - xn.shift(N); _need(d, 251)
        sd = d.iloc[-251:-1].std()
        if not sd > 0: raise NR("degenerate:zero_stdev_of_changes")
        dv = d.iloc[-1]
        yes = dv <= -sd if but else dv >= sd
        return yes, f"dX={_fmt(dv)}{'<=-' if but else '>='}{_fmt(sd)}_stdev"
    if kind == "EXT":
        _need(x, 250); _need(xn, 1); hist = x.iloc[-250:].values
        if np.nanpercentile(hist, 5) == np.nanpercentile(hist, 95): raise NR("degenerate:X_constant_over_250d")
        lo, hi = np.nanpercentile(hist, 5), np.nanpercentile(hist, 95); v = xn.iloc[-1]
        yes = v <= lo if but else v >= hi
        return yes, f"X_N={_fmt(v)}{'<=5th' if but else '>=95th'}({_fmt(lo if but else hi)})"
    if kind == "CRS":
        sma = x.rolling(N).mean(); _need(sma, 2)
        a, b = x.iloc[-1] - sma.iloc[-1], x.iloc[-2] - sma.iloc[-2]
        yes = (a < 0 <= b) if but else (a > 0 >= b)
        return yes, f"{'cross_below' if but else 'cross_above'}_SMA{N}"
    if kind == "STK":
        sma = x.rolling(20).mean(); _need(sma, N)
        d = (x - sma).iloc[-N:]
        if d.isna().any(): raise NR("insufficient_history:sma20_gap")
        yes = bool((d < 0).all()) if but else bool((d > 0).all())
        return yes, f"X_{'<' if but else '>'}SMA20_each_of_last_{N}d"
    if kind == "DIV":
        _need(xn, 250); pr = _pct(xn.iloc[-250:].values, xn.iloc[-1])
        if price is None or len(price) <= N: raise NR("missing_data:price")
        ret = price.iloc[-1] / price.iloc[-1 - N] - 1
        yes = (pr <= 20 and ret >= 0) if but else (pr >= 80 and ret <= 0)
        return yes, f"pct_rank={_fmt(pr)}_ret={_fmt(ret)}"
    if kind in ("POSQ", "POSD"):
        w = x.iloc[-N:]
        if len(w) < N or w.isna().any(): raise NR(f"insufficient_history:need_{N}_values")
        lo, hi = w.min(), w.max(); q = 0.25 if kind == "POSQ" else 0.10
        v = x.iloc[-1]
        yes = v <= lo + q * (hi - lo) if but else v >= lo + (1 - q) * (hi - lo)
        band = "bottom" if but else "top"
        name = "quartile" if kind == "POSQ" else "decile"
        return yes, f"X={_fmt(v)}_{band}_{name}_of_last_{N}d"
    # DUR
    pctl = N; xs = x.dropna()
    if len(xs) < 250: raise NR(f"insufficient_history:need_250_values_have_{len(xs)}")
    if kind in ("SUP", "SDN"):
        flag = (xs > xs.shift(1)) if kind == "SUP" else (xs < xs.shift(1))
    else:
        lo, hi = xs.rolling(60).min(), xs.rolling(60).max()
        flag = (xs >= lo + 0.75 * (hi - lo)) if kind == "ZTQ" else (xs <= lo + 0.25 * (hi - lo))
        flag = flag & lo.notna()
    cur, past = _runs(flag.values)
    if not past: raise NR("insufficient_history:no_completed_runs")
    thr = np.percentile(past, pctl)
    yes = cur > 0 and cur >= thr
    if but:
        yes = yes and xs.iloc[-1] >= xs.iloc[-cur:].max() and (cur == 1 or xs.iloc[-1] > xs.iloc[-cur:-1].max())
    return bool(yes), f"run={cur}_vs_{pctl}th={_fmt(thr)}_{kind}"

# ---------------------------------------------------------------- events
def _event_series(fam, df, spy):
    C, H, L, O = df["Close"], df["High"], df["Low"], df["Open"]
    if fam == "036":
        a = _atr(df); r2 = C.shift(1) / C.shift(2) - 1
        return (H < H.shift(1)) & (L > L.shift(1)) & (r2.abs() >= 2 * (a.shift(1) / C.shift(1)))
    if fam == "037":
        return (C < 1.0).astype(int).rolling(30).sum() >= 20
    if fam == "038":
        ok = (C >= 1.0).astype(int); streak = ok.groupby((ok == 0).cumsum()).cumsum()
        defic = ((C < 1.0).astype(int).rolling(30).sum() >= 20)
        prior_def = defic.shift(10).fillna(False).astype(bool).cummax()
        return (streak == 10) & prior_def
    if fam == "057":
        return L <= 0.9 * C.shift(1)
    if fam == "075":
        return C / C.shift(1) - 1 >= 0.20
    if fam == "076":
        s = spy["Close"].reindex(df.index)
        return (C / C.shift(1) - 1 > 0) & (s / s.shift(1) - 1 <= -0.01)
    raise KeyError(fam)

DIRECTION = {"036": 1, "037": -1, "038": 1, "057": 1, "075": -1, "076": 1}

_XY={}
def _xy(fam,t,D,df,spy):
    k=(fam,t,D)
    if k not in _XY: _XY[k]=_x_yahoo(fam,df,spy)
    return _XY[k]

def _event_lens(fam, suffix, defn, ev, df, spy, but):
    """Returns (bool, reason_phrase)."""
    m = re.match(r"W(\d+)-EVT$", suffix)
    if m:
        n = int(m.group(1)); w = ev.iloc[-max(n, 1):]
        if w.isna().all(): raise NR("insufficient_history")
        hit = bool(w.fillna(False).any())
        if not but:
            return hit, f"event_in_last_{n}d" if n else ("event_today" if hit else "no_event_today")
        if fam not in DIRECTION: raise NR("rule_vague:BUT_no_expected_direction")
        if not hit: return False, "no_event_for_BUT"
        last = w[w.fillna(False)].index[-1]
        a = _atr(df).iloc[-1]; mv = df["Close"].iloc[-1] - df["Close"].loc[last]
        yes = bool(-DIRECTION[fam] * mv >= a)
        return yes, f"move_vs_event={_fmt(mv)}_ATR={_fmt(a)}"
    m = re.match(r"T(\d+)-(CNT|RXM|RXS|EXT)$", suffix)
    if not m: raise NR("rule_vague:unparsed_lens")
    N, kind = int(m.group(1)), m.group(2)
    if len(ev) < N: raise NR("insufficient_history")
    w = ev.iloc[-N:].fillna(False)
    if kind == "CNT":
        cnt = int(w.sum())
        if but:
            return cnt == 0, f"event_count_{N}d={cnt}"
        t = re.search(r">=\s*(\d+)", defn.split("YES if")[1])
        th = int(t.group(1)); return cnt >= th, f"event_count_{N}d={cnt}>={th}"
    if kind == "RXS": raise NR("missing_data:finviz_industry_peer_returns_not_wired")
    if kind == "EXT":
        c = ev.fillna(False).astype(float).rolling(N).sum().dropna()
        if len(c) < 250: raise NR(f"insufficient_history:need_250_counts_have_{len(c)}")
        hist = c.values
        if np.percentile(hist, 5) == np.percentile(hist, 95): raise NR("degenerate:count_constant_over_history")
        lo, hi = np.percentile(hist, 5), np.percentile(hist, 95); v = c.iloc[-1]
        yes = v <= lo if but else v >= hi
        return yes, f"count={_fmt(v)}{'<=5th' if but else '>=95th'}({_fmt(lo if but else hi)})"
    C = df["Close"]; S = spy["Close"].reindex(df.index); idx = list(df.index)
    diffs = []
    for d in w[w].index:
        i = idx.index(d)
        if i + 3 < len(idx):
            diffs.append((C.iloc[i+3]/C.iloc[i]-1) - (S.iloc[i+3]/S.iloc[i]-1))
    if not diffs: return False, "no_events_with_3d_forward"
    v = float(np.mean(diffs))
    yes = v <= -0.03 if but else v >= 0.03
    return yes, f"mean_3d_vs_SPY={_fmt(v)}"

# ---------------------------------------------------------------- main
FIXED_NR = {
    "014": "held:earnings_dates_unchecked", "024": "held:earnings_dates_unchecked",
    "091": "held:earnings_dates_unchecked",
    "026": "missing_data:finviz_industry_peer_history_not_wired",
    "027": "missing_data:adr_home_listing_map_not_built",
    "028": "missing_data:linked_commodity_map_not_built",
    "050": "hold_finviz_shares", "051": "hold_finviz_shares",
    "039": "missing_data:nasdaqtrader_halts_not_wired",
    "042": "missing_data:nasdaq_dividend_calendar_not_wired",
    "043": "missing_data:nasdaq_dividend_calendar_not_wired",
    "056": "missing_data:regsho_threshold_list_not_wired",
    "074": "missing_data:nasdaq_ipo_calendar_not_wired",
}
YAHOO_X = {"015", "025", "029", "035"}
SNAP_X = {"008", "010", "022", "023"}
YAHOO_EVT = {"036", "037", "038", "057", "075", "076"}
CAL_EVT = {"071", "072", "073"}

def _rank(fam, suffix, ticker, D, but):
    m = re.match(r"T(\d+)-RNK$", suffix); N = int(m.group(1))
    U, asof = _x_snapshot(fam, None, D, universe=True)
    if fam == "010":
        U = U / U.shift(1).rolling(20).mean()
    if len(U) < N: raise NR(f"insufficient_history:need_{N}_snapshots_have_{len(U)}")
    xn = U.iloc[-N:].mean(skipna=False)
    if pd.isna(xn.get(ticker, np.nan)): raise NR("missing_data:ticker_value_absent_in_snapshot")
    last_sess = list(asof)[-1]; fdate, sha = _pins()[last_sess]; last = fdate
    sect = _snapshot(sha, fdate)["Sector"]
    xs = xn.dropna(); v = xs[ticker]; peers = xs[sect.reindex(xs.index) == sect.get(ticker)]
    if but:
        yes = bool(v <= xs.quantile(0.10) and v <= peers.quantile(0.10))
        return yes, f"bottom_decile_sector_and_market X={_fmt(v)}", last
    yes = bool(v >= xs.quantile(0.90) and v >= peers.quantile(0.90))
    return yes, f"top_decile_sector_and_market X={_fmt(v)}", last

COMPACT = ROOT / "fetch_tests" / "new-bot-v4.4g.compact.csv"

def answer(ticker, date, full=False):
    ticker = ticker.upper(); D = str(date)[:10]; Dd = _date.fromisoformat(D)
    rows = list(csv.DictReader(open(ROWS)))
    if not full:
        keep = {r["id"] for r in csv.DictReader(open(COMPACT))}
        rows = [r for r in rows if r["id"] in keep]
    cache = {}
    def yh(t):
        if t not in cache:
            try: cache[t] = _yahoo(t)
            except Exception as e: cache[t] = e
        v = cache[t]
        if isinstance(v, Exception): raise NR(f"missing_data:{v}")
        return v[v.index < D]
    out = []
    for r in rows:
        rid = r["id"]; defn = r["strict_definition"]
        m = re.match(r"nb4-[A-Z]+-NB-(\d+)-(.*?)(-BUT)?(-SNAP)?$", rid)
        fam, suffix, but = m.group(1), m.group(2), bool(m.group(3))
        ans, reason, asof = "NOT_READY", "", ""
        try:
            if D < r["data_available_from"]:
                raise NR(f"before_series_start:{r['data_available_from']}")
            if fam in FIXED_NR: raise NR(FIXED_NR[fam])
            if fam in YAHOO_X or fam in YAHOO_EVT:
                df = yh(ticker); spy = yh("SPY")
                if df.empty: raise NR("missing_data:no_bars_before_date")
                asof = df.index[-1]
                if (Dd - _date.fromisoformat(asof)).days > 5: raise NR(f"missing_data:stale_last_bar_{asof}")
                if suffix.endswith("RNK"): raise NR("missing_data:whole_market_daily_history_not_wired")
                if fam in YAHOO_X:
                    res, reason = _lens(suffix, defn, _xy(fam, ticker, D, df, spy), df["Close"], but)
                else:
                    res, reason = _event_lens(fam, suffix, defn, _event_series(fam, df, spy), df, spy, but)
            elif fam in CAL_EVT:
                n = re.match(r"W(\d+)", suffix)
                if n:
                    wn = int(n.group(1))
                    days = _sessions_back(Dd, max(wn, 1)) if wn else [Dd]
                    hit = any(_cal_event(fam, d) for d in days)
                    if but: raise NR("rule_vague:BUT_price_move_since_event_for_calendar_event")
                    res = hit
                    reason = f"cal_event_in_last_{wn}d" if wn else ("cal_event_today" if hit else "no_cal_event_today")
                else:
                    N, kind = re.match(r"T(\d+)-(\w+)", suffix).groups(); N = int(N)
                    days = _sessions_back(Dd - timedelta(1), N); cnt = sum(_cal_event(fam, d) for d in days)
                    if kind == "CNT":
                        if but:
                            res = cnt == 0; reason = f"cal_count_{N}d={cnt}"
                        else:
                            th = int(re.search(r">=\s*(\d+)", defn.split("YES if")[1]).group(1))
                            res = cnt >= th; reason = f"cal_count_{N}d={cnt}>={th}"
                    elif kind == "RXS": raise NR("missing_data:finviz_industry_peer_returns_not_wired")
                    elif kind == "RNK": raise NR("rule_vague:rank_of_calendar_event_same_for_every_ticker")
                    else:
                        df = yh(ticker); spy = yh("SPY")
                        ev = pd.Series([_cal_event(fam, _date.fromisoformat(i)) if _is_session(_date.fromisoformat(i)) else False for i in df.index], index=df.index)
                        res, reason = _event_lens(fam, suffix, defn, ev, df, spy, but); asof = df.index[-1]
                asof = asof or D
            elif fam == "088":
                x, a = _x_snapshot("008", ticker, D)
                raise NR(f"insufficient_history:outlier_needs_250_AH_sessions_have_{int(x.notna().sum())}")
            elif fam in SNAP_X:
                if suffix.endswith("RNK"):
                    res, reason, asof = _rank(fam, suffix, ticker, D, but)
                elif suffix.startswith("W"):
                    x, a = _x_snapshot(fam, ticker, D)
                    raise NR(f"insufficient_history:outlier_needs_250_sessions_have_{int(x.notna().sum())}")
                else:
                    x, a = _x_snapshot(fam, ticker, D)
                    if x.empty: raise NR("before_series_start:no_snapshot_known")
                    asof = a[x.index[-1]] if not x.empty else ""
                    if pd.isna(x.iloc[-1]): raise NR("missing_data:value_blank_in_snapshot")
                    res, reason = _lens(suffix, defn, x, None, but)
            else:
                raise NR("rule_vague:family_not_mapped")
            ans = "YES" if bool(res) else "NO"
            if not reason: reason = "condition_checked"
        except NR as e:
            reason = str(e)
        except Exception as e:
            reason = f"missing_data:{type(e).__name__}:{str(e)[:60]}"
        out.append({"row_id": rid, "ticker": ticker, "date": D, "answer": ans, "reason": reason, "data_as_of": asof})
    return out

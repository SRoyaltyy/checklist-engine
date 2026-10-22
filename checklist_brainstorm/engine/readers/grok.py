"""Grok Bot reader: answer(ticker, date) for the 1,874 grok-bot rows of merged_draft_v8.1.csv.
Cutoff 09:25 ET on D. Known-at rules used:
  Yahoo daily bars (indexes ^VIX/^VIX3M/^VIX9D, SPY, stock, futures): bar date < D  (close known D-1 16:15 ET)
  CFTC COT: Tuesday report counts only if its release (Fri 15:30 ET; Mon if a US federal holiday falls
            Mon-Fri of the release week) is on a calendar day < D
  Yahoo upgrades_downgrades: action date <= D-1 (date-only, known D-1 23:59 ET)
Held rows -> NOT_READY held:no_nightly_archive. Finviz-snapshot rows -> NOT_READY (reader not built).
Downloads cached in engine/cache/ (fetched once; delete the file to refresh)."""
import csv, json, math, os, re, time, datetime as dt
from pathlib import Path
import numpy as np, pandas as pd, requests

ENG = Path(__file__).resolve().parent.parent
SHEET = ENG.parent / "merged_draft_v8.1.csv"
CACHE = ENG / "cache" / "grok"; CACHE.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0"}

class NR(Exception):
    """raise NR(reason) -> NOT_READY"""

# ---------------- data ----------------
_mem = {}
def yahoo(sym):
    if sym in _mem:
        if isinstance(_mem[sym], NR): raise _mem[sym]
        return _mem[sym]
    try: return _yahoo(sym)
    except NR as e: _mem[sym] = e; raise
def _yahoo(sym):
    f = CACHE / f"yahoo_{re.sub(r'[^A-Za-z0-9]', '_', sym)}.csv"
    if not f.exists():
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
        for k in range(4):
            r = requests.get(url, params={"period1": 0, "period2": int(time.time()), "interval": "1d"},
                         headers=UA, timeout=30)
            if r.status_code == 200: break
            time.sleep(3 * (k + 1))
        if r.status_code != 200: raise NR(f"missing_data:yahoo {sym} http {r.status_code}")
        if not r.json()["chart"]["result"]: raise NR(f"missing_data:yahoo {sym} empty")
        j = r.json()["chart"]["result"][0]
        off = j["meta"].get("gmtoffset", -14400)
        q = j["indicators"]["quote"][0]
        adj = (j["indicators"].get("adjclose") or [{}])[0].get("adjclose") or q["close"]
        df = pd.DataFrame({"date": [dt.datetime.utcfromtimestamp(t + off).date().isoformat() for t in j["timestamp"]],
                           "close": q["close"], "adj": adj, "volume": q["volume"]}).dropna(subset=["close"])
        df = df.drop_duplicates("date", keep="last")
        df.to_csv(f, index=False)
    df = pd.read_csv(f, dtype={"date": str}).set_index("date").sort_index()
    _mem[sym] = df; return df

def bars_before(sym, D):
    df = yahoo(sym); df = df[df.index < D]
    if df.empty: raise NR(f"before_series_start:{sym}")
    return df

COT_DS = {"TFF": "gpe5-46if", "DISAGG": "72hh-3qpy", "LEGACY": "6dca-aqww"}
CODE = {'ES':'13874A','NQ':'209742','RTY':'239742','ZN':'043602','ZB':'020601','VX':'1170E1','DX':'098662','BTC':'133741',
        '6E':'099741','6J':'097741','CL':'067651','GC':'088691','HG':'085692','NG':'023651','ZC':'002602','ZS':'005602'}
FUT = {'ES':'ES=F','NQ':'NQ=F','RTY':'RTY=F','ZN':'ZN=F','ZB':'ZB=F','DX':'DX-Y.NYB','BTC':'BTC=F','VX':None,'6E':'6E=F',
       '6J':'6J=F','CL':'CL=F','GC':'GC=F','HG':'HG=F','NG':'NG=F','ZC':'ZC=F','ZS':'ZS=F'}
def cot(ds, code):
    k = (ds, code)
    if k in _mem:
        if isinstance(_mem[k], NR): raise _mem[k]
        return _mem[k]
    try: return _cot(ds, code)
    except NR as e: _mem[k] = e; raise
def _cot(ds, code):
    k = (ds, code)
    f = CACHE / f"cot_{ds}_{code}.json"
    if not f.exists():
        rows, off = [], 0
        while True:
            r = requests.get(f"https://publicreporting.cftc.gov/resource/{COT_DS[ds]}.json",
                             params={"$where": f"cftc_contract_market_code='{code}'", "$order": "report_date_as_yyyy_mm_dd",
                                     "$limit": 5000, "$offset": off}, timeout=60)
            if r.status_code != 200: raise NR(f"missing_data:cftc {ds} {code} http {r.status_code}")
            b = r.json(); rows += b
            if len(b) < 5000: break
            off += 5000
        f.write_text(json.dumps(rows))
    df = pd.DataFrame(json.loads(f.read_text()))
    df["rd"] = df.report_date_as_yyyy_mm_dd.str[:10]
    df = df.drop_duplicates("rd", keep="last").set_index("rd").sort_index()
    _mem[k] = df; return df

_hol = None
def release_date(rd):
    global _hol
    if _hol is None:
        from pandas.tseries.holiday import USFederalHolidayCalendar
        _hol = set(d.date() for d in USFederalHolidayCalendar().holidays("1990-01-01", "2030-12-31"))
    tue = dt.date.fromisoformat(rd); fri = tue + dt.timedelta(3); mon = fri - dt.timedelta(4)
    if any((mon + dt.timedelta(i)) in _hol for i in range(5)): return fri + dt.timedelta(3)  # conservative: next Monday
    return fri

def ratings(t):
    if ("ud", t) in _mem:
        if isinstance(_mem[("ud", t)], NR): raise _mem[("ud", t)]
        return _mem[("ud", t)]
    try: return _ratings(t)
    except NR as e: _mem[("ud", t)] = e; raise
def _ratings(t):
    f = CACHE / f"yahoo_ud_{t}.csv"
    if not f.exists():
        import yfinance as yf
        u = None
        for k in range(3):
            try: u = yf.Ticker(t).upgrades_downgrades; break
            except Exception: time.sleep(3)
        if u is None: raise NR(f"missing_data:yahoo upgrades_downgrades {t}")
        u = u.reset_index()
        u.to_csv(f, index=False)
    u = pd.read_csv(f)
    if len(u):
        u["d"] = pd.to_datetime(u["GradeDate"]).dt.strftime("%Y-%m-%d")
        u = u.sort_values(["d", "Firm"], kind="stable")
    else: u["d"] = []
    _mem[("ud", t)] = u; return u

# ---------------- helpers ----------------
def pct_rank(win, x):  # percent of window values <= x
    return 100.0 * (np.asarray(win) <= x).mean()

def stock_but(t, D, bullish):
    s = bars_before(t, D)
    if len(s) < 22: raise NR("insufficient_history:stock<22 bars")
    r = s.adj.iloc[-1] / s.adj.iloc[-2] - 1
    v = s.volume.iloc[-1]; avg = s.volume.iloc[-21:-1].mean()
    if not (avg > 0): raise NR("missing_data:stock volume")
    against = (r <= -0.03) if bullish else (r >= 0.03)
    return bool(against and v >= 2 * avg), s.index[-1]

# ---------------- VIX family ----------------
def vix_series(var, D):
    def c(sym): return bars_before(sym, D).close
    if var.startswith("VIX9D"): return c("^VIX9D")
    if var.startswith("VIX3M"): return c("^VIX3M")
    if var.startswith("VIX term slope"):
        a, b = c("^VIX3M"), c("^VIX"); return (a - b).dropna()
    if var.startswith("VIX/VIX3M"):
        a, b = c("^VIX"), c("^VIX3M"); return (a / b).dropna()
    raise NR("rule_not_parsed:series")

def vix_base(var, s, D):
    """s = definition before BUT. returns (bool, as_of)"""
    if var.startswith("mac_") or var.startswith("VIX > 30"):
        v, v3 = bars_before("^VIX", D).close, bars_before("^VIX3M", D).close
        ratio = (v / v3).dropna()
        if "VIX9D/VIX" in s:
            v9 = bars_before("^VIX9D", D).close; x = (v9 / v).dropna()
            _y = x.iloc[-1] > 1.1; return _y, x.index[-1], f"VIX9D/VIX={x.iloc[-1]:.3f}"
        if "crossed back below 1.0" in s:
            _y = (ratio.iloc[-2] >= 1.0 and ratio.iloc[-1] < 1.0)
            return _y, ratio.index[-1], f"ratio={ratio.iloc[-1]:.3f} prev={ratio.iloc[-2]:.3f}"
        if "VIX > 30" in s:
            _y = (v.loc[ratio.index[-1]] > 30 and ratio.iloc[-1] > ratio.iloc[-2])
            return _y, ratio.index[-1], f"VIX={float(v.loc[ratio.index[-1]]):.2f} ratio={ratio.iloc[-1]:.3f}"
        m = re.search(r"VIX/VIX3M > ([\d.]+)", s)
        if m:
            thr = float(m.group(1)); _y = ratio.iloc[-1] > thr
            return _y, ratio.index[-1], f"VIX/VIX3M={ratio.iloc[-1]:.3f} thr={thr}"
        raise NR("rule_not_parsed")
    x = vix_series(var, D); asof = x.index[-1]
    if len(x) < 275: raise NR("insufficient_history:<275 sessions before D")
    m = re.search(r"(\d+)-session change in .*?(>= \+|<= -)1\.0 x stdev of (?:its )?rolling \1-session changes over prior 252", s)
    if m:
        n = int(m.group(1)); ch = x.diff(n).dropna(); sd = ch.iloc[-253:-1].std()
        _y = (ch.iloc[-1] >= sd) if m.group(2).startswith(">=") else (ch.iloc[-1] <= -sd)
        return _y, asof, ("hit" if _y else "miss")
    if re.search(r"(value|level is) (>|above) its 252-session median", s):
        _y = x.iloc[-1] > x.iloc[-252:].median()
        return _y, asof, ("hit" if _y else "miss")
    if "is UP" in s and "was DOWN" in s:
        d = x.diff(); _y = (d.iloc[-1] > 0 and d.iloc[-2] < 0 and abs(d.iloc[-1]) > abs(d.iloc[-2]))
        return _y, asof, ("hit" if _y else "miss")
    if "preceding non-overlapping 5-session change" in s:
        _y = (x.iloc[-1] - x.iloc[-6]) > (x.iloc[-6] - x.iloc[-11])
        return _y, asof, ("hit" if _y else "miss")
    m = re.search(r"(\d+)-session change in .*? is in (top|bottom) 5% of its 252-session distribution", s)
    if m:
        n = int(m.group(1)); ch = x.diff(n).dropna(); p = pct_rank(ch.iloc[-252:], ch.iloc[-1])
        _y = (p >= 95) if m.group(2) == "top" else (p <= 5)
        return _y, asof, ("hit" if _y else "miss")
    m = re.search(r"percentile rank (>=|<=) (\d+) within prior 252", s)
    if m:
        p = pct_rank(x.iloc[-252:], x.iloc[-1]); k = float(m.group(2))
        _y = (p >= k) if m.group(1) == ">=" else (p <= k)
        return _y, asof, ("hit" if _y else "miss")
    if "top 5% of its 252-session range" in s:
        w = x.iloc[-252:]; _y = (x.iloc[-1] - w.min()) >= 0.95 * (w.max() - w.min())
        return _y, asof, ("hit" if _y else "miss")
    if "crossed above its 20-session SMA" in s:
        sma = x.rolling(20).mean(); _y = (x.iloc[-2] <= sma.iloc[-2] and x.iloc[-1] > sma.iloc[-1])
        return _y, asof, ("hit" if _y else "miss")
    if re.search(r"rose on >= 4 consecutive|risen 4\+ consecutive", s):
        _y = bool((x.diff().iloc[-4:] > 0).all())
        return _y, asof, ("hit" if _y else "miss")
    if "opposite sign to SPY 5-session change" in s:
        spy = bars_before("SPY", D).adj; ch = x.diff(5).dropna(); sc = spy.iloc[-1] - spy.iloc[-6]
        sd = ch.iloc[-253:-1].std(); c0 = ch.iloc[-1]
        if spy.index[-1] != asof: raise NR("missing_data:SPY/VIX date mismatch")
        _y = (c0 > 0 and sc < 0 and abs(c0) >= sd)
        return _y, asof, ("hit" if _y else "miss")
    raise NR("rule_not_parsed")

# ---------------- COT ----------------
def cot_eval(row, t, D):
    s = row["strict_definition"]; var = row["variant"]
    mm = [x for x in re.findall(r"\(([A-Z0-9]+)\)", s) if x in CODE]; dd = re.search(r"\[(TFF|DISAGG|LEGACY)\]", s)
    if not mm or not dd: raise NR("rule_not_parsed:cot market")
    m, ds = mm[0], dd.group(1); df = cot(ds, CODE[m])
    if "leveraged funds" in var: L, S = "lev_money_positions_long", "lev_money_positions_short"
    elif "asset managers" in var: L, S = "asset_mgr_positions_long", "asset_mgr_positions_short"
    elif "managed money" in var: L, S = "m_money_positions_long_all", "m_money_positions_short_all"
    elif "producer/merchant" in var: L, S = "prod_merc_positions_long", "prod_merc_positions_short"
    elif "large spec" in var: L, S = "noncomm_positions_long_all", "noncomm_positions_short_all"
    elif "commercials" in var: L, S = "comm_positions_long_all", "comm_positions_short_all"
    else: raise NR("rule_not_parsed:cot group")
    Dd = dt.date.fromisoformat(D)
    df = df[[release_date(r) < Dd for r in df.index]]
    if df.empty: raise NR("before_series_start:cot")
    net = pd.to_numeric(df[L]) - pd.to_numeric(df[S]); oi = pd.to_numeric(df["open_interest_all"])
    asof = df.index[-1]
    def need(n):
        if len(net) < n: raise NR(f"insufficient_history:<{n} COT reports")
    w = re.search(r"trailing (\d+) weeks", s); W = int(w.group(1)) if w else None
    if "95th pct" in s or "5th pct" in s:
        need(W); x = (net / oi).iloc[-W:]; p = pct_rank(x, x.iloc[-1])
        _y = (p >= 95) if "95th" in s else (p <= 5)
        return _y, asof, ("hit" if _y else "miss")
    if "sd of its trailing 52-week weekly changes" in s:
        need(54); ch = net.diff().dropna(); sd = ch.iloc[-53:-1].std()
        _y = (ch.iloc[-1] > 2 * sd) if "+2 sd" in s else (ch.iloc[-1] < -2 * sd)
        return _y, asof, ("hit" if _y else "miss")
    if "consecutive weekly reports" in s:
        need(5); d = net.diff().iloc[-4:]
        _y = bool((d > 0).all()) if "increased" in s else bool((d < 0).all())
        return _y, asof, ("hit" if _y else "miss")
    if "crossed from net short to net long" in s: need(2)
    _y = (net.iloc[-2] < 0 and net.iloc[-1] > 0)
    return _y, asof, ("hit" if _y else "miss")
    if "crossed from net long to net short" in s: need(2)
    _y = (net.iloc[-2] > 0 and net.iloc[-1] < 0)
    return _y, asof, ("hit" if _y else "miss")
    if "8-week" in s:
        need(8)
        if not FUT.get(m): raise NR(f"missing_data:no Yahoo front-month for {m}")
        px = yahoo(FUT[m]).close
        rds = list(net.index[-8:]); p = []
        for rd in rds:
            q = px[px.index <= rd]
            if q.empty or (dt.date.fromisoformat(rd) - dt.date.fromisoformat(q.index[-1])).days > 4: raise NR(f"missing_data:{FUT[m]} price on {rd}")
            p.append(q.iloc[-1])
        n8 = net.iloc[-8:]
        if "8-week low while net position at an 8-week high" in s:
            _y = (p[-1] <= min(p) and n8.iloc[-1] >= n8.max())
            return _y, asof, ("hit" if _y else "miss")
        _y = (p[-1] >= max(p) and n8.iloc[-1] <= n8.min())
        return _y, asof, ("hit" if _y else "miss")
    raise NR("rule_not_parsed")

# ---------------- ratings ----------------
BUY = {"buy","outperform","overweight","strong buy","positive","accumulate","market outperform","sector outperform","add",
       "conviction buy","top pick","long-term buy","speculative buy","outperformer","moderate buy"}
SELL = {"sell","underperform","underweight","reduce","strong sell","negative","sector underperform","market underperform","moderate sell"}
HOLD = {"hold","neutral","equal-weight","equal weight","market perform","sector perform","peer perform","in-line","sector weight",
        "mixed","perform","fair value","peer weight","market weight"}
def tier(g):
    g = str(g).strip().lower()
    return 3 if g in BUY else 1 if g in SELL else 2 if g in HOLD else None

def sessions(D): return list(bars_before("SPY", D).index)

def window(u, D, n):
    ss = sessions(D)
    lo = ss[-n - 1] if len(ss) > n else "0000"
    return u[(u.d > lo) & (u.d < D)]

def is_pos(r):
    a = str(r.Action).lower(); pa = str(r.get("priceTargetAction", "")).lower()
    return a == "up" or (a in ("init", "reit") and tier(r.ToGrade) == 3) or pa.startswith("raise")
def is_neg(r):
    a = str(r.Action).lower(); pa = str(r.get("priceTargetAction", "")).lower()
    return a == "down" or (a in ("init", "reit") and tier(r.ToGrade) == 1) or pa.startswith("lower")


def _rating_detail(w, pred, label_yes, label_no="no_match"):
    hits = []
    for _, r in w.iterrows():
        if pred(r):
            hits.append(f"{r.Firm} {r.Action} {str(r.d)[5:]}")
            if len(hits) >= 2: break
    if hits: return True, "; ".join(hits)
    return False, label_no

def ratings_eval(row, t, D):
    s = row["strict_definition"]; u = ratings(t)
    if len(u) == 0: raise NR("missing_data:no analyst actions for ticker")
    if u.d.min() >= D: raise NR("before_series_start:ratings")
    asof = u[u.d < D].d.max() if (u.d < D).any() else ""
    m = re.search(r"last (\d+)(?: trading days|d)\b", s) or re.search(r"within same (\d+) trading days|in (\d+)d,", s)
    n = int(next(g for g in m.groups() if g)) if m else 1
    w = window(u, D, n)
    def any_(f): return any(f(r) for _, r in w.iterrows())
    pt = lambda r: (pd.to_numeric(r.get("currentPriceTarget"), errors="coerce"), pd.to_numeric(r.get("priorPriceTarget"), errors="coerce"))
    close = lambda: bars_before(t, D).close.iloc[-1]
    if s.startswith(">=1 Upgrade"):
        _y, det = _rating_detail(w, lambda r: str(r.Action).lower() == "up", "upgrade")
        return _y, asof, det
    if s.startswith(">=1 Downgrade"):
        _y, det = _rating_detail(w, lambda r: str(r.Action).lower() == "down", "downgrade")
        return _y, asof, det
    if "Initiated/Resumed action with Buy" in s or "Initiated at Buy" in s:
        _y = any_(lambda r: str(r.Action).lower() == "init" and tier(r.ToGrade) == 3)
        return _y, asof, ("hit" if _y else "miss")
    if "Initiated/Resumed action with Sell/Hold" in s:
        _y = any_(lambda r: str(r.Action).lower() == "init" and tier(r.ToGrade) in (1, 2))
        return _y, asof, ("hit" if _y else "miss")
    if "Initiated at Sell" in s:
        _y = any_(lambda r: str(r.Action).lower() == "init" and tier(r.ToGrade) == 1)
        return _y, asof, ("hit" if _y else "miss")
    if "FROM Sell-equivalent" in s:
        _y = any_(lambda r: tier(r.FromGrade) == 1 and (tier(r.ToGrade) or 0) > 1)
        return _y, asof, ("hit" if _y else "miss")
    if "TO Sell-equivalent" in s:
        _y = any_(lambda r: tier(r.ToGrade) == 1 and tier(r.FromGrade) not in (None, 1))
        return _y, asof, ("hit" if _y else "miss")
    if "TO Buy-equivalent" in s:
        _y = any_(lambda r: tier(r.ToGrade) == 3 and tier(r.FromGrade) in (1, 2))
        return _y, asof, ("hit" if _y else "miss")
    if "FROM Buy-equivalent" in s:
        _y = any_(lambda r: tier(r.FromGrade) == 3 and tier(r.ToGrade) in (1, 2))
        return _y, asof, ("hit" if _y else "miss")
    if "Hold-equivalent -> Buy" in s:
        _y = any_(lambda r: tier(r.FromGrade) == 2 and tier(r.ToGrade) == 3)
        return _y, asof, ("hit" if _y else "miss")
    if "Buy-equivalent -> Hold" in s:
        _y = any_(lambda r: tier(r.FromGrade) == 3 and tier(r.ToGrade) == 2)
        return _y, asof, ("hit" if _y else "miss")
    if "target raised" in s:
        _y, det = _rating_detail(w, lambda r: str(r.Action).lower() in ("main", "reit") and pt(r)[0] > pt(r)[1] > 0, "target_raise")
        return _y, asof, det
    if "target cut" in s:
        _y, det = _rating_detail(w, lambda r: str(r.Action).lower() in ("main", "reit") and 0 < pt(r)[0] < pt(r)[1], "target_cut")
        return _y, asof, det
    if s.startswith("Sum of (PT to - PT from)"):
        c = close(); tot = 0.0
        for _, r in w.iterrows():
            a, b = pt(r)
            if a > 0 and b > 0: tot += (a - b) / c
        _y = (tot >= 0.10) if ">= +10%" in s else (tot <= -0.10)
        return _y, asof, ("hit" if _y else "miss")
    if ">=2 positive actions" in s:
        _y = sum(is_pos(r) for _, r in w.iterrows()) >= 2
        return _y, asof, ("hit" if _y else "miss")
    if ">=2 negative actions" in s:
        _y = sum(is_neg(r) for _, r in w.iterrows()) >= 2
        return _y, asof, ("hit" if _y else "miss")
    if ">=2 PT raises dated same day" in s or ">=2 PT cuts dated same day" in s:
        p = u[u.d < D]
        if p.empty: return False, asof, "miss"
        last = p[p.d == p.d.max()]; f = (lambda a, b: a > b > 0) if "raises" in s else (lambda a, b: 0 < a < b)
        _y = sum(bool(f(*pt(r))) for _, r in last.iterrows()) >= 2
        return _y, asof, ("hit" if _y else "miss")
    if ">=3 actions in 5d" in s:
        k = len(w); pos = sum(is_pos(r) for _, r in w.iterrows()); neg = sum(is_neg(r) for _, r in w.iterrows())
        _y = (k >= 3 and (pos > k / 2 if "positive" in s else neg > k / 2))
        return _y, asof, ("hit" if _y else "miss")
    if "target moved above price" in s:
        c = close()
        _y = any_(lambda r: pt(r)[1] > 0 and pt(r)[1] < c <= pt(r)[0])
        return _y, asof, ("hit" if _y else "miss")
    if "target moved below price" in s:
        c = close()
        _y = any_(lambda r: pt(r)[0] > 0 and pt(r)[1] > c >= pt(r)[0])
        return _y, asof, ("hit" if _y else "miss")
    raise NR("rule_not_parsed")

def net_daily(t, D, kind):
    """daily net count per session (sessions < D): upgrades-downgrades or PT raises-cuts. actions on non-session days roll forward."""
    u = ratings(t); ss = sessions(D)
    if len(u) == 0: raise NR("missing_data:no analyst actions for ticker")
    first = u.d.min()
    if kind == "ud": v = u.Action.str.lower().map({"up": 1, "down": -1}).fillna(0)
    else:
        pa = u.get("priceTargetAction", pd.Series([""] * len(u))).fillna("").astype(str).str.lower()
        v = pa.map(lambda x: 1 if x.startswith("raise") else -1 if x.startswith("lower") else 0)
    idx = np.searchsorted(np.array(ss), u.d.values, side="left")  # map action date to first session >= date
    s = pd.Series(0.0, index=ss)
    for i, val in zip(idx, v.values):
        if i < len(ss): s.iloc[i] += val
    s = s[s.index >= first]
    return s

def actions_eval(row, t, D):
    s = row["strict_definition"]; kind = "ud" if row["variant"].startswith("upgrades") else "pt"
    if "Finviz sector" in s or "Finviz universe" in s: raise NR("needs_universe:cross-sectional rank reader not built")
    x = net_daily(t, D, kind)
    if len(x) < 260: raise NR("insufficient_history:<260 sessions of analyst actions")
    asof = x.index[-1]
    m = re.search(r"(prev bar|(\d+)d)", s); n = 1 if (not m or m.group(1) == "prev bar") else int(m.group(2))
    ch = x.rolling(n).sum().dropna()   # "change over Nd" of the cumulative net count = sum of daily nets
    if re.search(r"change over (prev bar|\d+d) (>=|<=)", s):
        k = float(re.search(r"(>=|<=) ([+-]?\d+)", s).group(2))
        _y = (ch.iloc[-1] >= k) if ">=" in s.split("change over")[1][:15] else (ch.iloc[-1] <= k)
        return _y, asof, f"net_Nd={ch.iloc[-1]:+.0f} thr={k:+.0f}"
    mm = re.search(r"in (top|bottom) (\d+)% of its own trailing 252-day distribution", s)
    if mm:
        p = pct_rank(ch.iloc[-252:], ch.iloc[-1]); k = float(mm.group(2))
        _y = (p >= 100 - k and ch.iloc[-1] != ch.iloc[-252:].min()) if mm.group(1) == "top" else (p <= k)
        return _y, asof, ("hit" if _y else "miss")
    mm = re.search(r"minus prior .*? (>=|<=) ([+-]?[\d.]+) SD", s)
    if mm:
        diff = (ch - ch.shift(n)).dropna(); sd = diff.iloc[-253:-1].std(); k = float(mm.group(2))
        if not sd > 0: return False, asof, "miss"
        _y = (diff.iloc[-1] >= k * sd) if mm.group(1) == ">=" else (diff.iloc[-1] <= k * sd)
        return _y, asof, ("hit" if _y else "miss")
    mm = re.search(r"(rose|fell) on each of the last (\d+)", s)
    if mm:
        k = int(mm.group(2)); last = x.iloc[-k:]
        _y = bool((last > 0).all()) if mm.group(1) == "rose" else bool((last < 0).all())
        return _y, asof, ("hit" if _y else "miss")
    mm = re.search(r"(up|down) over \d+d \((top|bottom) (\d+)% of own 1y\) while stock price return over \d+d ([<>]) 0", s)
    if mm:
        p = pct_rank(ch.iloc[-252:], ch.iloc[-1]); k = float(mm.group(3))
        px = bars_before(t, D).adj
        if len(px) <= n: raise NR("insufficient_history:stock")
        r = px.iloc[-1] / px.iloc[-1 - n] - 1
        if mm.group(1) == "up":
            _y = (ch.iloc[-1] > 0 and p >= 100 - k and r < 0)
            return _y, asof, ("hit" if _y else "miss")
        _y = (ch.iloc[-1] < 0 and p <= k and r > 0)
        return _y, asof, ("hit" if _y else "miss")
    raise NR("rule_ambiguous:level/MA/range of a net-action count needs a defined counting window")

# ---------------- main ----------------
_rows = None
def grok_rows():
    global _rows
    if _rows is None:
        with open(SHEET, newline="") as f:
            _rows = [r for r in csv.DictReader(f) if (r.get("merge_owner") or "").strip() == "grok-bot"]
    return _rows

def start_date(r):
    m = re.search(r"\d{4}-\d{2}-\d{2}", r.get("history_start") or ""); return m.group(0) if m else None

def _phrase(r, detail=""):
    """Short human reason for a YES/NO; never empty."""
    var = (r.get("variant") or r["id"]).strip()
    var = re.sub(r"\s*\(BUT\)\s*$", "", var)
    d = (detail or "").strip()
    if d: return f"{var}: {d}"[:160]
    # fall back: compressed strict_definition head
    s = re.sub(r"\s+", " ", (r.get("strict_definition") or "")).strip()
    s = re.sub(r"^YES if\s+", "", s, flags=re.I)
    return f"{var}: {s[:90]}"[:160]

def one(r, t, D):
    """Returns (yes:bool, data_as_of:str, reason:str). Reason is always non-empty for YES/NO."""
    rid = r["id"]; src = r["source"]; dtp = r["data_type"]
    if (r.get("hold") or "").strip() or "HOLD=" in (r.get("notes") or ""):
        raise NR("held:no_nightly_archive")
    if "Theme Radar committed nightly Finviz snapshot" in src:
        raise NR("finviz_snapshot_reader_not_built (theme-radar snapshots from 2026-08-06)")
    sd = start_date(r)
    if rid.startswith("MKT-JA"):
        if sd and D <= sd: raise NR(f"before_series_start:{sd}")
        s = r["strict_definition"]; base = s.split(" BUT ")[0]
        bull = "bull" in (r.get("yes_means (bullish/bearish)") or "").lower()
        y, asof, detail = vix_base(r["variant"], base, D)
        if " BUT stock's own prior-session return" in s:
            b, a2 = stock_but(t, D, bull); y = bool(y) and b; asof = max(asof, a2)
            detail = f"{detail}; stock_BUT={'hit' if b else 'miss'}"
        return y, asof, _phrase(r, detail)
    if "CFTC" in dtp:
        y, asof, detail = cot_eval(r, t, D); return y, asof, _phrase(r, detail)
    if dtp == "analyst rating change":
        y, asof, detail = ratings_eval(r, t, D); return y, asof, _phrase(r, detail)
    if "upgrades_downgrades" in src:
        y, asof, detail = actions_eval(r, t, D); return y, asof, _phrase(r, detail)
    raise NR("rule_not_parsed:no family")

def answer(ticker, date):
    t = ticker.upper(); D = dt.date.fromisoformat(date).isoformat(); out = []
    for r in grok_rows():
        try:
            y, asof, why = one(r, t, D)
            if not why: why = _phrase(r, "met" if y else "not_met")
            out.append(dict(row_id=r["id"], ticker=t, date=D, answer="YES" if y else "NO", reason=why, data_as_of=str(asof)))
        except NR as e:
            out.append(dict(row_id=r["id"], ticker=t, date=D, answer="NOT_READY", reason=str(e), data_as_of=""))
        except Exception as e:
            out.append(dict(row_id=r["id"], ticker=t, date=D, answer="NOT_READY",
                            reason=f"row_error:{type(e).__name__}: {e}"[:200], data_as_of=""))
    return out

"""Theme Radar reader for the answer engine (Grok's runner: engine/answer.py).

answer(ticker, date) -> list of dicts {row_id, answer (YES/NO/NOT_READY), reason,
data_as_of, snapshot_date} for the 2,592 compact Theme Radar ids in v8.1 (-C);
answer(ticker, date, include_full=True) also returns the 13,188 full v5.2 ids.
universe(date) is re-exported from _theme_radar_universe (see README_theme_radar_universe.md).

Data: theme-radar's own dated Finviz snapshots (data/snapshots/<D>.raw.csv on origin/main),
read from the local clone with `git show` (nothing copied to disk). Cutoff = 09:25 ET on
`date`: a snapshot version counts only if committed before that cutoff, and a snapshot
dated D is never used for date D. One saved snapshot = one "session"/"value" in the row
definitions. Compact row X-C answers the same as its full base row X (base N = first timeframe).
NOT_READY always carries a reason (HOLD:..., history_too_short:..., field_empty_..., unsupported:...).
"""
import csv, re, datetime as dt, sys, os
from functools import lru_cache
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _theme_radar_universe as U
from _theme_radar_universe import universe  # noqa: F401  (public re-export)

TR = Path("/workspace/tr_checklist")
FULL, COMPACT = TR / "theme-radar.csv", TR / "theme-radar.compact.csv"
HOLDS = Path("/workspace/checklist_brainstorm/qa/beta_and_ratio_ids.csv")

# label -> (raw column or derived key, unit multiplier applied to raw value)
COL = {"Forward P/E":"Forward P/E","P/E":"P/E","P/S":"P/S","PEG":"PEG","EV/EBITDA":"EV/EBITDA","Market cap ($)":"Market Cap",
 "P/B":"P/B","P/Cash":"P/Cash","P/FCF":"P/Free Cash Flow","EV/Sales":"EV/Sales","Enterprise value ($)":"Enterprise Value",
 "EPS next Y %":"EPS Growth Next Year","EPS Q/Q %":"EPS Growth Quarter Over Quarter","Sales Q/Q %":"Sales Growth Quarter Over Quarter",
 "EPS growth this year % (estimate-driven)":"EPS Growth This Year","Analyst recommendation (1=Buy..5=Sell)":"Analyst Recom",
 "Insider transactions % (Insider Trans)":"Insider Transactions","Insider ownership %":"Insider Ownership",
 "Institutional ownership %":"Institutional Ownership","Institutional transactions %":"Institutional Transactions",
 "Short float %":"Short Float","Short ratio (days to cover)":"Short Ratio","Shares outstanding (M)":"Shares Outstanding",
 "Shares float (M)":"Shares Float","Opening gap %":"Gap","Prior close change %":"Change","Relative volume":"Relative Volume",
 "Average volume (3M)":"Average Volume","Prior-session share volume":"Volume","Volatility Week %":"Volatility (Week)",
 "Volatility Month %":"Volatility (Month)","Beta":"Beta","Distance from SMA20 %":"20-Day Simple Moving Average",
 "Distance from SMA50 %":"50-Day Simple Moving Average","Distance from SMA200 %":"200-Day Simple Moving Average",
 "Distance from 52w high %":"52-Week High","Distance from 52w low %":"52-Week Low","Distance from all-time high %":"All-Time High",
 "Distance from all-time low %":"All-Time Low","Distance from 50d high %":"50-Day High","Distance from 50d low %":"50-Day Low",
 "Perf % window":"Performance (Week)","Perf Half Year %":"Performance (Half Year)","Perf YTD %":"Performance (YTD)",
 "Perf Year %":"Performance (Year)","Prior-session change from open %":"Change from Open",
 "ETF price premium/discount to NAV %":"Net Asset Value %","ETF net flows % 1M":"Net Flows % (1 Month)",
 "ETF net flows $ 1M":"Net Flows (1 Month)","ETF net flows % 3M":"Net Flows % (3 Month)","ETF AUM ($)":"Assets Under Management"}
MULT = {"Market Cap":1e6,"Enterprise Value":1e6,"Average Volume":1e3}
DERIVED = {"Target price distance %","Dollar volume","SMA20 vs SMA50","SMA50 vs SMA200 (golden/death cross)",
 "Stock perf % minus sector perf %","Stock perf % minus industry perf %","Sessions until next earnings date",
 "Sessions since last earnings (BMO/AMC adjusted)","Sessions until dividend ex-date","Sessions since IPO date",
 "Prior-session trade count vs 20d avg (x)"}
UNSUPPORTED_FIELDS = {
 "EPS next Q estimate": "unsupported:definition_ambiguous(estimate level vs % threshold; revision needs nightly archive)",
 "Sector index position in own N-day high-low range": "unsupported:needs_sector_index_series",
 "Industry index position in own N-day high-low range": "unsupported:needs_industry_index_series",
 "Stock range position minus its sector range position": "unsupported:needs_sector_index_series",
 "Index": "unsupported:categorical_field_outlier"}
HOLD_FIELDS = {"Market cap ($)", "Shares outstanding (M)"}
BASE_COLS = ["Ticker","Sector","Industry","Index","Price","Volume","Relative Volume","Target Price","Earnings Date",
             "IPO Date","Dividend Ex Date","Trades","Performance (Week)","20-Day Simple Moving Average",
             "50-Day Simple Moving Average","200-Day Simple Moving Average"]

@lru_cache(None)
def _rows():
    full = list(csv.DictReader(open(FULL))); comp = list(csv.DictReader(open(COMPACT)))
    held = {r["id"] for r in csv.DictReader(open(HOLDS)) if r["set"] == "theme_radar_mcap_ratio"}
    held |= {h[:-2] for h in held if h.endswith("-C")}
    return full, comp, held

def _label(defn):
    m = re.search(r"'([^']+)'", defn); return m.group(1) if m else None

@lru_cache(None)
def _cols_needed():
    full, _, _ = _rows(); need = set(BASE_COLS)
    for r in full:
        lab = _label(r["strict_definition"])
        if lab in COL: need.add(COL[lab])
        elif r["data_type"] == "Slow field outlier" and lab: need.add(lab)
    return frozenset(need)

def _num(s, col):
    s = s.str.replace("%","",regex=False).str.replace(",","",regex=False).str.strip()
    s = s.replace({"Yes":"1","No":"0","-":""})
    return pd.to_numeric(s, errors="coerce") * MULT.get(col, 1.0)

_NUM = {}
def _numcol(df, col):
    k = (id(df), col)
    if k not in _NUM:
        _NUM[k] = _num(df[col], col) if col in df.columns else pd.Series(np.nan, index=df.index)
    return _NUM[k]

@lru_cache(None)
def _view(date):
    """Usable snapshots for `date`, oldest first (rule shared with theme_radar_universe)."""
    return U.history(date, _cols_needed())

def _bdays(a, b):  # business days from a to b (b>a positive)
    return int(np.busday_count(a, b)) if b >= a else -int(np.busday_count(b, a))

def _pdate(s):
    try:
        m, d, y = s.split(" ")[0].split("/"); return dt.date(int(y), int(m), int(d))
    except Exception: return None

class Series:
    """Per-date access to a field for one ticker and for the whole universe."""
    def __init__(self, view, date):
        self.view, self.date, self.cache = view, date, {}
    def uni(self, i, lab):
        """Universe values (Series indexed by ticker) for snapshot i, field label lab."""
        k = (i, lab)
        if k in self.cache: return self.cache[k]
        sd, df = self.view[i]
        g = lambda c: _numcol(df, c)
        if lab in COL: v = g(COL[lab])
        elif lab == "Target price distance %": v = (g("Target Price") / g("Price") - 1) * 100
        elif lab == "Dollar volume": v = g("Price") * g("Volume")
        elif lab == "SMA20 vs SMA50": v = ((1 + g("50-Day Simple Moving Average")/100) / (1 + g("20-Day Simple Moving Average")/100) - 1) * 100
        elif lab.startswith("SMA50 vs SMA200"): v = ((1 + g("200-Day Simple Moving Average")/100) / (1 + g("50-Day Simple Moving Average")/100) - 1) * 100
        elif lab in ("Stock perf % minus sector perf %", "Stock perf % minus industry perf %"):
            grp = df["Sector" if "sector" in lab else "Industry"]; p = g("Performance (Week)")
            v = p - p.groupby(grp).transform("median")
        elif lab.startswith("Sessions"):
            col = {"Sessions until next earnings date":"Earnings Date","Sessions since last earnings (BMO/AMC adjusted)":"Earnings Date",
                   "Sessions until dividend ex-date":"Dividend Ex Date","Sessions since IPO date":"IPO Date"}[lab]
            ref = dt.date.fromisoformat(self.date) if i == len(self.view) - 1 else dt.date.fromisoformat(self.view[i+1][0])
            def f(s):
                d = _pdate(s)
                if d is None: return np.nan
                n = _bdays(ref, d)
                if "until" in lab: return n if n >= 0 else np.nan
                return -n if n <= 0 else np.nan
            v = df[col].map(f).astype(float)
        elif lab == "Prior-session trade count vs 20d avg (x)":
            if i < 20: v = pd.Series(np.nan, index=df.index)
            else:
                prev = pd.concat([_numcol(self.view[j][1], "Trades") for j in range(i-20, i)], axis=1).mean(axis=1)
                v = g("Trades") / prev.reindex(df.index)
        else: v = g(lab)
        self.cache[k] = v; return v
    def win(self, k, lab):
        key = ("win", k, lab)
        if key not in self.cache:
            n = len(self.view); idx = self.view[-1][1].index
            self.cache[key] = pd.concat([self.uni(i, lab).reindex(idx) for i in range(n - k, n)], axis=1).mean(axis=1, skipna=False)
        return self.cache[key]
    def grp(self, kind, k, lab):
        key = ("grp", kind, k, lab)
        if key not in self.cache:
            W = self.win(k, lab); g = self.view[-1][1][kind]
            self.cache[key] = {name: sub.dropna().to_numpy() for name, sub in W.groupby(g)}
        return self.cache[key]
    def val(self, i, lab, t):
        u = self.uni(i, lab); x = u.get(t, np.nan)
        return float(x) if x is not None else np.nan

class NR(Exception): pass

def _need(n, have, what="values"):
    if have < n: raise NR(f"history_too_short:need_{n}_{what}_have_{have}")

def _thr(s):
    s = s.replace("$","").replace("%","").strip(); m = 1
    if s.endswith("M"): m, s = 1e6, s[:-1]
    if s.endswith("B"): m, s = 1e9, s[:-1]
    return float(s) * m

def _thr_field(lab, s):
    v = _thr(s)
    if lab in ("Shares outstanding (M)", "Shares float (M)") and v >= 1e6: v /= 1e6
    return v

def _eval(r, t, S):
    d = r["strict_definition"]; lens = r["lens"]; dtp = r["data_type"]; n = len(S.view); L = n - 1
    lab = _label(d)
    if dtp in ("Outlier anchor", "Exhaustion/duration"): raise NR(f"unsupported:row_type:{dtp}")
    if lab in UNSUPPORTED_FIELDS and dtp != "Index membership": raise NR(UNSUPPORTED_FIELDS[lab])
    if dtp == "Index membership":
        m = re.search(r"label (contains|lacks) '([^']+)' at D-1 AND (?:did not contain|contained) it on the snapshot (\d+) sessions earlier", d)
        k = int(m.group(3)); _need(k + 1, n)
        lbl = lambda i: (S.view[i][1]["Index"].get(t, "") if t in S.view[i][1].index else None)
        a, b = lbl(L), lbl(L - k)
        if a is None or b is None: raise NR("ticker_not_in_snapshot")
        has = lambda s: m.group(2) in s
        return (has(a) and not has(b)) if m.group(1) == "contains" else (has(b) and not has(a))
    if lab is None: raise NR(f"unsupported:unparsed_definition:{lens}")
    if t not in S.view[L][1].index: raise NR("ticker_not_in_latest_snapshot")
    x = lambda i: S.val(i, lab, t)
    def cur():
        v = x(L)
        if np.isnan(v): raise NR("field_empty_for_ticker")
        return v
    def series(k):  # last k values, oldest first
        _need(k, n); vs = [x(i) for i in range(n - k, n)]
        if any(np.isnan(v) for v in vs): raise NR("field_empty_in_window")
        return vs
    # ---- generic lenses
    if lens == "fixed threshold":
        m = re.search(r"(>=|<=) (\S+).*?held on each of last (\d+) values", d)
        op, th, k = m.group(1), _thr_field(lab, m.group(2)), int(m.group(3))
        vs = series(k); return all(v >= th for v in vs) if op == ">=" else all(v <= th for v in vs)
    if lens == "extreme vs own history":
        m = re.search(r"(\d+)d value (>=|<=) (\d+)\w\w percentile of its own prior (\d+) sessions", d)
        k, op, p, M = int(m.group(1)), m.group(2), float(m.group(3)), int(m.group(4))
        vs = series(k + M); hist, now = vs[:M], float(np.mean(vs[M:]))
        q = np.percentile(hist, p); return now >= q if op == ">=" else now <= q
    if lens == "change since last value":
        m = re.search(r"(rises|falls) by >= (\S+) (relative|pts) vs value (\d+) sessions ago", d)
        k = int(m.group(4)); vs = series(k + 1); a, b = vs[0], vs[-1]; th = _thr(m.group(2))
        if m.group(3) == "relative":
            if a == 0: raise NR("base_value_zero")
            ch = (b - a) / abs(a) * 100
        else: ch = b - a
        return ch >= th if m.group(1) == "rises" else ch <= -th
    if lens == "cross":
        m = re.search(r"crosses (above|below) (\S+?)(?: \w+)?:.*?T-(\d+)", d)
        th = _thr_field(lab, m.group(2)); k = int(m.group(3)); vs = series(k + 1)
        return (vs[0] < th <= vs[-1]) if m.group(1) == "above" else (vs[0] >= th > vs[-1])
    if lens == "streak":
        m = re.search(r"each of last (\d+) consecutive", d); k = int(m.group(1)); vs = series(k + 1)
        dif = np.diff(vs); return bool(all(dif > 0)) if "improved" in d else bool(all(dif < 0))
    if lens in ("divergence vs price", "divergence vs volume"):
        m = re.search(r"T-(\d+)", d); k = int(m.group(1)); vs = series(k + 1)
        other = "Price" if lens.endswith("price") else "Relative Volume"
        _need(k + 1, n); o = [_numcol(S.view[i][1], other).get(t, np.nan) for i in (L - k, L)]
        if any(np.isnan(v) for v in o): raise NR("price_or_relvol_missing")
        do, df_ = o[1] - o[0], vs[-1] - vs[0]
        return (do < 0 and df_ > 0) if "positive divergence" in d else (do > 0 and df_ < 0)
    if lens in ("rank vs sector", "rank vs industry", "rank vs SPY/market"):
        m = re.search(r"(\d+)d value in (top|bottom) (\d+)%", d); k, side, p = int(m.group(1)), m.group(2), float(m.group(3))
        _need(k, n); W = S.win(k, lab); me = W.get(t, np.nan)
        if np.isnan(me): raise NR("field_empty_in_window")
        df = S.view[L][1]
        if lens == "rank vs sector": Uv = S.grp("Sector", k, lab).get(df.at[t, "Sector"], np.array([]))
        elif lens == "rank vs industry": Uv = S.grp("Industry", k, lab).get(df.at[t, "Industry"], np.array([]))
        else:
            key = ("all", k, lab)
            if key not in S.cache: S.cache[key] = W.dropna().to_numpy()
            Uv = S.cache[key]
        U = Uv
        if len(U) < 10: raise NR("peer_group_too_small")
        q = np.percentile(U, 100 - p if side == "top" else p)
        ok = me >= q if side == "top" else me <= q
        spy = W.get("SPY", np.nan)
        if not np.isnan(spy): ok = ok and (me > spy if side == "top" else me < spy)
        return bool(ok)
    # ---- Position (Finviz field)
    if dtp == "Position (Finviz field)":
        m = re.search(r"(top|bottom) (quartile|decile) \((>=|<=) (\d+)%\) of its own (?:min-max range over prior )?(\d+)", d)
        if m:
            M = int(m.group(5)); vs = series(M); lo, hi = min(vs), max(vs)
            if hi == lo: raise NR("flat_range")
            pos = (vs[-1] - lo) / (hi - lo) * 100; th = float(m.group(4))
            return pos >= th if m.group(3) == ">=" else pos <= th
        m = re.search(r"latest value (>=|<=) (\d+)\w\w percentile of same-sector", d)
        if m:
            v = cur(); df = S.view[L][1]; U = S.uni(L, lab)[df["Sector"] == df.at[t, "Sector"]].dropna()
            if len(U) < 10: raise NR("peer_group_too_small")
            q = np.percentile(U, float(m.group(2))); return v >= q if m.group(1) == ">=" else v <= q
    # ---- Slow field outlier
    if dtp == "Slow field outlier":
        w = re.search(r"within last (\d+) sessions", d); k = int(w.group(1)) if w else 1
        if "3 x its mean" in d or "3x usual" in d:
            _need(252 + k + 1, n, "saved_snapshots_for_252_session_baseline")
        if "percentile of its own saved history" in d:
            _need(60 + k, n, "saved_snapshots_min_60_for_percentile_history")
            vs = [x(i) for i in range(n)]; up = "crossed from <" in d
            for j in range(n - k, n):
                hist = [v for v in vs[:j] if not np.isnan(v)]
                if len(hist) < 60 or np.isnan(vs[j]) or np.isnan(vs[j-1]): continue
                q = np.percentile(hist, 99 if up else 1)
                if (up and vs[j-1] < q <= vs[j]) or (not up and vs[j-1] > q >= vs[j]): return True
            return False
        if "percentile of same-sector" in d:
            _need(k + 1, n); up = "jumped" in d; df = S.view[L][1]; sec = df.at[t, "Sector"]
            def pr(i):
                key = ("secpct", i, lab)
                if key not in S.cache:
                    U = S.uni(i, lab); dfi = S.view[i][1]
                    grp = dfi["Sector"].reindex(U.index)
                    S.cache[key] = (U.groupby(grp).rank(pct=True, method="min") * 100, U.groupby(grp).transform("count"))
                P, cnt = S.cache[key]; v = P.get(t, np.nan)
                return np.nan if np.isnan(v) or cnt.get(t, 0) < 10 else v
            for j in range(n - k, n):
                a, b = pr(j - 1), pr(j)
                if np.isnan(a) or np.isnan(b): continue
                if (up and a < 90 and b >= 99) or (not up and a > 10 and b <= 1): return True
            return False
    raise NR(f"unsupported:unparsed_definition:{dtp}/{lens}")

DEBUG = False

def answer(ticker, date, include_full=False):
    """All Theme Radar rows for one ticker and date (cutoff 09:25 ET on `date`)."""
    t = ticker.upper(); full, comp, held = _rows()
    view = _view(date); S = Series(view, date)
    asof = view[-1][0] if view else ""
    res = {}
    for r in full:
        rid = r["id"]; lab = _label(r["strict_definition"])
        if rid in held: res[rid] = ("NOT_READY", "HOLD:theme_radar_mcap_ratio"); continue
        if lab in HOLD_FIELDS: res[rid] = ("NOT_READY", "HOLD:market_cap_or_shares_outstanding"); continue
        if not view: res[rid] = ("NOT_READY", "no_snapshot_yet(first usable theme-radar snapshot is dated 2026-08-06, usable from 2026-08-07)"); continue
        try: res[rid] = ("YES" if _eval(r, t, S) else "NO", "")
        except NR as e: res[rid] = ("NOT_READY", str(e))
        except Exception as e:
            if DEBUG: raise
            res[rid] = ("NOT_READY", f"reader_error:{type(e).__name__}")
    out = []
    for c in comp:
        a, why = res[c["id"][:-2]]
        if c["id"] in held: a, why = "NOT_READY", "HOLD:theme_radar_mcap_ratio"
        out.append({"row_id": c["id"], "answer": a, "reason": why or f"base_row={c['id'][:-2]}", "data_as_of": asof, "snapshot_date": asof})
    if include_full:
        out += [{"row_id": k, "answer": a, "reason": w, "data_as_of": asof, "snapshot_date": asof} for k, (a, w) in res.items()]
    return out

if __name__ == "__main__":
    import sys, collections
    t, d = sys.argv[1], sys.argv[2]
    rows = answer(t, d, include_full=len(sys.argv) > 3)
    w = csv.DictWriter(sys.stdout, ["row_id","ticker","date","answer","reason","data_as_of","snapshot_date"], lineterminator="\n"); w.writeheader()
    for r in rows: w.writerow({**r, "ticker": t.upper(), "date": d})

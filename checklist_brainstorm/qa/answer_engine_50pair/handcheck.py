#!/usr/bin/env python3
"""Hand-check 100 random YES/NO answers against raw Yahoo / Finviz / calendar data.
Independent of answer() where possible; mismatches reported with row_id, claimed, truth.
"""
from __future__ import annotations
import csv, json, os, random, re, sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/workspace/checklist_brainstorm")
ENGINE = ROOT / "engine"
CACHE = ENGINE / "cache"
OUT50 = ENGINE / "out" / "50pair"
QA = ROOT / "qa" / "answer_engine_50pair"
SHEET = {r["id"]: r for r in csv.DictReader(open(ROOT / "merged_draft_v8.1.csv"))}
SEED = 20261022
sys.path.insert(0, str(ENGINE / "readers"))

# ---------- raw loaders ----------
def load_yahoo_csv(sym):
    p = CACHE / f"{sym}.csv"
    if not p.exists():
        # taskforce cache
        alt = CACHE / "taskforce" / f"y_{sym.replace('^','_')}.json"
        if alt.exists():
            j = json.load(open(alt))
            r = (j["chart"].get("chart", {}).get("result") or [None])[0]
            if not r or "timestamp" not in r:
                return None
            q = r["indicators"]["quote"][0]
            idx = pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert("America/New_York").normalize().tz_localize(None)
            df = pd.DataFrame({k.capitalize(): q[k] for k in ("open", "high", "low", "close", "volume")}, index=idx)
            df = df.dropna(subset=["Close"]).astype(float)
            return df[~df.index.duplicated(keep="last")].sort_index()
        return None
    df = pd.read_csv(p, parse_dates=["date"]).set_index("date").sort_index()
    df.columns = [c.capitalize() if c.islower() else c for c in df.columns]
    # normalize colnames
    rename = {}
    for c in df.columns:
        cl = c.lower()
        if cl == "close": rename[c] = "Close"
        elif cl == "open": rename[c] = "Open"
        elif cl == "high": rename[c] = "High"
        elif cl == "low": rename[c] = "Low"
        elif cl == "volume": rename[c] = "Volume"
    df = df.rename(columns=rename)
    return df

def bars_before(sym, D):
    df = load_yahoo_csv(sym)
    if df is None:
        return None
    D = pd.Timestamp(D).normalize()
    return df[df.index < D]

def atr14(df):
    h, l, c = df["High"], df["Low"], df["Close"]
    prev = c.shift(1)
    tr = pd.concat([(h - l), (h - prev).abs(), (l - prev).abs()], axis=1).max(axis=1)
    return tr.rolling(14).mean()

# ---------- independent checkers ----------
def check_weekday(row, claimed, ticker, D):
    defn = SHEET[row]["strict_definition"]
    wd = re.match(r"YES if today is (Monday|Tuesday|Wednesday|Thursday|Friday) \(", defn)
    if not wd:
        return None
    if " BUT " in defn:
        return ("skip", "weekday+BUT needs stock move; skipped for pure calendar check")
    truth = "YES" if pd.Timestamp(D).day_name() == wd.group(1) else "NO"
    return ("ok" if truth == claimed else "mismatch", truth, f"weekday {pd.Timestamp(D).day_name()} vs want {wd.group(1)}")

def check_consecutive_down(row, claimed, ticker, D):
    """Taskforce-style: count consecutive C<C(-1) ending D-1; YES if X_N<=1 (BUT) or similar."""
    defn = SHEET[row]["strict_definition"]
    if "Timeframes N in" in defn and "|" in (SHEET[row].get("timeframe") or ""):
        return ("skip", "compact_multi_tf")
    if "count of consecutive days C<C(-1)" not in defn:
        return None
    b = bars_before(ticker, D)
    if b is None or len(b) < 5:
        return ("skip", "no_bars")
    c = b["Close"]
    down = (c < c.shift(1)).astype(int)
    # streak ending at last bar
    streak = 0
    for v in down.iloc[::-1]:
        if v == 1:
            streak += 1
        else:
            break
    # parse threshold
    m = re.search(r"YES if X_N\s*(>=|<=)\s*([-+0-9.e]+)(?!\s*th)", defn)
    if not m:
        return ("skip", "no_thr")
    op, thr = m.group(1), float(m.group(2))
    ok = (streak >= thr) if op == ">=" else (streak <= thr)
    # BUT mirror already baked into "YES if" of the row defn
    truth = "YES" if ok else "NO"
    return ("ok" if truth == claimed else "mismatch", truth, f"streak={streak} {op}{thr}")

def check_sma_ratio(row, claimed, ticker, D):
    """X=SMA20/SMA20(-5)-1 with threshold."""
    defn = SHEET[row]["strict_definition"]
    if "Timeframes N in" in defn and "|" in (SHEET[row].get("timeframe") or ""):
        return ("skip", "compact_multi_tf")
    if "X=SMA20/SMA20(-5)-1" not in defn and "SMA20/SMA20" not in defn:
        return None
    b = bars_before(ticker, D)
    if b is None or len(b) < 30:
        return ("skip", "no_bars")
    sma = b["Close"].rolling(20).mean()
    if len(sma) < 6 or pd.isna(sma.iloc[-1]) or pd.isna(sma.iloc[-6]):
        return ("skip", "sma_nan")
    X = float(sma.iloc[-1] / sma.iloc[-6] - 1)  # -5 sessions back = iloc[-6]
    m = re.search(r"YES if X_N\s*(>=|<=)\s*([-+0-9.e]+)(?!\s*th)", defn)
    if "pct" in defn or "percentile" in defn.lower() or "th pct" in defn:
        return ("skip", "percentile_thr")
    if not m:
        return ("skip", "no_thr")
    op, thr = m.group(1), float(m.group(2))
    ok = (X >= thr) if op == ">=" else (X <= thr)
    truth = "YES" if ok else "NO"
    return ("ok" if truth == claimed else "mismatch", truth, f"X={X:.6f} {op}{thr}")

def check_close_vs_sma20(row, claimed, ticker, D):
    defn = SHEET[row]["strict_definition"]
    if "Timeframes N in" in defn and "|" in (SHEET[row].get("timeframe") or ""):
        return ("skip", "compact_multi_tf")
    if "Close vs SMA20" not in defn and "C/SMA20-1" not in defn and "close vs SMA20" not in defn.lower():
        # also X=C/SMA20-1 style
        if not re.search(r"X\s*=\s*C\s*/\s*SMA20", defn):
            return None
    b = bars_before(ticker, D)
    if b is None or len(b) < 25:
        return ("skip", "no_bars")
    sma = b["Close"].rolling(20).mean()
    X = float(b["Close"].iloc[-1] / sma.iloc[-1] - 1)
    m = re.search(r"YES if X_N\s*(>=|<=)\s*([-+0-9.e]+)(?!\s*th)", defn)
    if "pct" in defn or "percentile" in defn.lower() or "th pct" in defn:
        return ("skip", "percentile_thr")
    if not m:
        return ("skip", "no_thr")
    op, thr = m.group(1), float(m.group(2))
    ok = (X >= thr) if op == ">=" else (X <= thr)
    truth = "YES" if ok else "NO"
    return ("ok" if truth == claimed else "mismatch", truth, f"X={X:.6f} {op}{thr}")

def check_james_spy_return(row, claimed, ticker, D):
    """Simple: YES if latest 1-session change in SPY is UP etc — parse common james patterns via raw bars."""
    defn = SHEET[row]["strict_definition"]
    src = SHEET[row].get("source") or ""
    # 1-session change UP/DOWN
    m = re.match(r"YES if latest 1-session change in (.+?) is (UP|DOWN)", defn)
    if not m:
        return None
    if " BUT " in defn:
        return ("skip", "has_BUT")
    # map source
    # Prefer ratio sources Yahoo A / B
    rm = re.search(r"Yahoo\s+(\S+)\s*/\s*(\S+)", src)
    if rm:
        ca, cb = bars_before(rm.group(1), D), bars_before(rm.group(2), D)
        if ca is None or cb is None:
            return ("skip", "no_bars")
        s = (ca["Close"] / cb["Close"]).dropna()
        if len(s) < 3:
            return ("skip", "no_bars")
        chg = float(s.iloc[-1] / s.iloc[-2] - 1)
        prior = float(s.iloc[-2] / s.iloc[-3] - 1) if len(s) >= 3 else None
        # fall through using chg/prior below via special path
        b = None  # mark ratio mode
        _ratio_prior = prior
    else:
        _ratio_prior = None
        sym = None
        if "SPY" in src and "/" not in src: sym = "SPY"
        elif "QQQ" in src: sym = "QQQ"
        elif "IWM" in src: sym = "IWM"
        elif "GC=F" in src: sym = "GC=F"
        elif "CL=F" in src: sym = "CL=F"
        elif "ETH" in src or "CB:ETH" in src: sym = None
        elif "BTC" in src: sym = None
        else:
            mm = re.search(r"Yahoo ([A-Z^=.-]+)", src)
            if mm: sym = mm.group(1)
        if not sym:
            return ("skip", "sym_unknown")
        b = bars_before(sym, D)
        if b is None or len(b) < 2:
            return ("skip", "no_bars")
        chg = float(b["Close"].iloc[-1] / b["Close"].iloc[-2] - 1)
    want_up = m.group(2) == "UP"
    # may have extra clauses
    if "prior session's change was" in defn:
        if b is None:
            prior = _ratio_prior
            if prior is None:
                return ("skip", "need3")
        else:
            if len(b) < 3:
                return ("skip", "need3")
            prior = float(b["Close"].iloc[-2] / b["Close"].iloc[-3] - 1)
        if "prior session's change was DOWN" in defn and not (prior < 0):
            truth = "NO"
        elif "prior session's change was UP" in defn and not (prior > 0):
            truth = "NO"
        elif "|latest| > |prior|" in defn and not (abs(chg) > abs(prior)):
            truth = "NO"
        else:
            truth = "YES" if ((chg > 0) if want_up else (chg < 0)) else "NO"
            if "prior session" in defn:
                # already incorporated prior checks; final direction check
                if want_up and not (chg > 0): truth = "NO"
                if not want_up and not (chg < 0): truth = "NO"
        return ("ok" if truth == claimed else "mismatch", truth, f"chg={chg:.6f} prior={prior:.6f}")
    truth = "YES" if ((chg > 0) if want_up else (chg < 0)) else "NO"
    return ("ok" if truth == claimed else "mismatch", truth, f"chg={chg:.6f} want={'UP' if want_up else 'DOWN'}")

def check_theme_radar_52w(row, claimed, ticker, D):
    """Distance from 52w low/high via universe snapshot D-1."""
    defn = SHEET[row]["strict_definition"]
    if "52w" not in defn.lower() and "52-Week" not in defn and "52W" not in defn:
        return None
    try:
        from _theme_radar_universe import universe
    except Exception as e:
        return ("skip", f"universe_import:{e}")
    u = universe(D)
    if u is None:
        return ("skip", "no_universe")
    if ticker not in u.index:
        return ("skip", "ticker_not_in_universe")
    r = u.loc[ticker]
    # 'Distance from 52w low %' <= 5%
    m = re.search(r"'Distance from 52w (low|high) %'\s*(<=|>=)\s*([0-9.]+)%", defn)
    if not m:
        # Finviz columns often "52-Week Low" as % distance already
        return ("skip", "pattern")
    side, op, thr = m.group(1), m.group(2), float(m.group(3))
    col = "52-Week Low" if side == "low" else "52-Week High"
    # Finviz exports % distance from 52w high/low
    raw = str(r.get(col, "")).replace("%", "").replace(",", "").strip()
    if raw == "" or raw == "-":
        return ("skip", "empty_field")
    try:
        val = float(raw)
    except ValueError:
        return ("skip", f"parse:{raw}")
    # Note: Finviz "52-Week Low" is typically % above the low (positive). "Distance from 52w low %" in defn may match.
    ok = (val <= thr) if op == "<=" else (val >= thr)
    # held on each of last N — if N>1 and "held on each", skip unless N=1
    if "held on each of last" in defn:
        hm = re.search(r"held on each of last (\d+)", defn)
        if hm and int(hm.group(1)) > 1:
            return ("skip", "multi_hold")
    if " BUT " in defn or defn.strip().startswith("BUT") or "-BUT" in row:
        # BUT rows invert or add conditions — skip if complex
        if "while" in defn.lower() or "divergence" in defn.lower():
            return ("skip", "divergence")
    truth = "YES" if ok else "NO"
    # compact twin -C rows use base_row; claimed already folded
    return ("ok" if truth == claimed else "mismatch", truth,
            f"{col}={val} {op}{thr} snap={r.get('snapshot_date')} (D-1 rule)")

def check_finviz_price_change(row, claimed, ticker, D):
    """Prior-session change from open % threshold via universe."""
    defn = SHEET[row]["strict_definition"]
    if "Prior-session change from open" not in defn and "Change from Open" not in defn:
        return None
    try:
        from _theme_radar_universe import universe
    except Exception as e:
        return ("skip", f"import:{e}")
    u = universe(D)
    if u is None or ticker not in u.index:
        return ("skip", "no_uni")
    r = u.loc[ticker]
    raw = str(r.get("Change from Open", r.get("Change", ""))).replace("%", "").strip()
    if not raw or raw == "-":
        return ("skip", "empty")
    try:
        val = float(raw)
    except ValueError:
        return ("skip", raw)
    m = re.search(r"(>=|<=)\s*([0-9.]+)%", defn)
    if not m:
        return ("skip", "no_thr")
    op, thr = m.group(1), float(m.group(2))
    if "held on each of last" in defn:
        hm = re.search(r"last (\d+)", defn)
        if hm and int(hm.group(1)) > 1:
            return ("skip", "multi")
    ok = (val >= thr) if op == ">=" else (val <= thr)
    truth = "YES" if ok else "NO"
    return ("ok" if truth == claimed else "mismatch", truth, f"chg_from_open={val} {op}{thr}")

def check_options_expiry_event(row, claimed, ticker, D):
    """New-bot: third Friday expiry calendar."""
    defn = SHEET[row]["strict_definition"]
    if "third Friday" not in defn:
        return None
    # YES if count in last Nd >= 95th pct — hard without series; verify event date only for simple "is expiry week"
    return ("skip", "needs_event_series")


def check_james_stdev_change(row, claimed, ticker, D):
    """YES if Nd change in series op k x stdev over prior 252 — mirrors james.generic math on raw bars."""
    defn = SHEET[row]["strict_definition"]
    m = re.search(
        r"(\d+)-session change in .*? (>=|<=) ([+-]?[\d.]+) x stdev of (?:its )?rolling \d+-session changes over prior (\d+) sessions",
        defn,
    )
    if not m:
        return None
    if " BUT " in defn:
        return ("skip", "has_BUT")
    n, op, k, W = int(m.group(1)), m.group(2), float(m.group(3)), int(m.group(4))
    src = SHEET[row].get("source") or ""
    # Build series from Yahoo CSVs (same as james RATIO / single)
    def pit_close(sym):
        df = bars_before(sym, D)
        if df is None:
            # try FRED_ cache naming
            for cand in (sym, sym.replace("FRED:", "FRED_"), f"FRED_{sym}"):
                df = bars_before(cand, D)
                if df is not None:
                    break
        if df is None:
            return None
        return df["Close"] if "Close" in df.columns else df.iloc[:, 0]

    isrates = bool(re.search(r"yield|spread|T10Y|DGS|breakeven|real yield|VIX", defn, re.I))
    s = None
    if "/" in src and "Yahoo" in src and "FRED" not in src:
        parts = re.search(r"Yahoo\s+(\S+)\s*/\s*(\S+)", src)
        if not parts:
            return ("skip", "ratio_parse")
        a, b = parts.group(1), parts.group(2)
        ca, cb = pit_close(a), pit_close(b)
        if ca is None or cb is None:
            return ("skip", "no_bars")
        s = (ca / cb).dropna()
    else:
        mm = re.search(r"FRED\s+(\w+)", src)
        if mm:
            s = pit_close(f"FRED_{mm.group(1)}") or pit_close(mm.group(1))
        else:
            mm = re.search(r"Yahoo\s+(\S+)", src)
            if mm:
                s = pit_close(mm.group(1))
            else:
                return ("skip", "sym")
    if s is None or len(s) < W + n + 5:
        return ("skip", "short")
    ch = s.diff(n) if isrates else s.pct_change(n)
    if len(ch.dropna()) < W + 1:
        return ("skip", "short_chg")
    v = float(ch.iloc[-1])
    sd = float(ch.iloc[-W - 1 : -1].std())  # pandas default ddof=1, matches james
    if sd == 0 or np.isnan(sd) or np.isnan(v):
        return ("skip", "sd0")
    thr = k * sd
    ok = (v >= thr) if op == ">=" else (v <= thr)
    truth = "YES" if ok else "NO"
    return ("ok" if truth == claimed else "mismatch", truth, f"chg{n}={v:.6g} sd={sd:.6g} thr={thr:.6g}")


def check_green_red_day(row, claimed, ticker, D):
    """Simple: last session green/red with volume filter omitted."""
    defn = SHEET[row]["strict_definition"]
    # too many variants — handle: YES if prior session close > open (green)
    if "prior session" not in defn.lower() and "D-1" not in defn:
        return None
    return None  # placeholder keep None

def check_data_asof_cutoff(row, claimed, ticker, D, asof):
    """Sanity: data_as_of must be < D (strict before session) or ==D only for pure calendar-of-D."""
    if not asof:
        return ("skip", "no_asof")
    if asof > D:
        return ("mismatch", "asof_after_D", f"asof={asof} D={D}")
    # 09:25 cutoff: daily close of D cannot be known; asof==D only OK for weekday-of-D style
    defn = SHEET[row]["strict_definition"]
    if asof == D and not re.match(r"YES if today is (Monday|Tuesday|Wednesday|Thursday|Friday)", defn):
        # many calendar rows use D; flag soft
        return ("skip", "asof_eq_D_nonweekday")
    return ("ok", claimed, f"asof={asof}<={D}")


CHECKERS = [
    check_james_stdev_change,
    check_weekday,
    check_consecutive_down,
    check_sma_ratio,
    check_close_vs_sma20,
    check_james_spy_return,
    check_theme_radar_52w,
    check_finviz_price_change,
]

def collect_yes_no(csv_paths, n=100):
    rng = random.Random(SEED)
    pool = []
    for p in csv_paths:
        with open(p, newline="") as f:
            for r in csv.DictReader(f):
                if r["answer"] in ("YES", "NO"):
                    pool.append(r)
    # stratify by owner
    by = defaultdict(list)
    for r in pool:
        by[r["owner"]].append(r)
    owners = list(by.keys())
    per = max(1, n // max(1, len(owners)))
    picked = []
    for o in owners:
        k = min(per, len(by[o]))
        picked.extend(rng.sample(by[o], k))
    # fill to n
    rest = [r for r in pool if r not in picked]
    while len(picked) < n and rest:
        picked.append(rest.pop(rng.randrange(len(rest))))
    return picked[:n]

def main():
    csvs = sorted(OUT50.glob("answers_*.csv"))
    csvs = [p for p in csvs if ".rerun." not in p.name]
    if len(csvs) < 3:
        # fallback to engine/out page CSVs
        csvs = list((ENGINE / "out").glob("answers_*.csv"))
    print(f"using {len(csvs)} csvs", flush=True)
    sample = collect_yes_no(csvs, 100)
    results = []
    checked = 0
    mismatches = []
    skips = Counter()
    for r in sample:
        rid, claimed, ticker, D = r["row_id"], r["answer"], r["ticker"], r["date"]
        if rid not in SHEET:
            results.append({**r, "hc": "skip", "detail": "not_in_sheet"})
            skips["not_in_sheet"] += 1
            continue
        hit = None
        for fn in CHECKERS:
            try:
                out = fn(rid, claimed, ticker, D)
            except Exception as e:
                out = ("skip", f"err:{type(e).__name__}:{e}")
            if out is None:
                continue
            hit = out
            break
        if hit is None:
            # fallback: independent re-call of single-owner reader for this one row only,
            # then ALSO verify data_as_of bar exists and is < D (cutoff sanity) — not full truth
            results.append({**r, "hc": "skip", "detail": "no_independent_checker"})
            skips["no_checker"] += 1
            continue
        status = hit[0]
        if status == "skip":
            results.append({**r, "hc": "skip", "detail": str(hit[1])})
            skips[str(hit[1])[:60]] += 1
            continue
        truth, detail = hit[1], hit[2]
        checked += 1
        ok = status == "ok"
        rec = {**r, "hc": "ok" if ok else "mismatch", "truth": truth, "detail": detail}
        results.append(rec)
        if not ok:
            mismatches.append(rec)
            print(f"MISMATCH {rid} {ticker} {D} claimed={claimed} truth={truth} {detail}", flush=True)
        else:
            print(f"OK {rid} {ticker} {D} {claimed} {detail}", flush=True)

    # If we checked < 100 independently, supplement with reader re-eval + raw bar existence (labeled)
    # Prefer more independent checks by scanning more candidates
    if checked < 100:
        print(f"only {checked} independent checks; scanning more candidates...", flush=True)
        # build a larger pool favoring checkable defs
        pool = []
        for p in csvs[:15]:
            with open(p, newline="") as f:
                pool.extend([r for r in csv.DictReader(f) if r["answer"] in ("YES", "NO")])
        rng = random.Random(SEED + 1)
        rng.shuffle(pool)
        already = {(r["row_id"], r["ticker"], r["date"]) for r in results if r.get("hc") in ("ok", "mismatch")}
        for r in pool:
            if checked >= 100:
                break
            key = (r["row_id"], r["ticker"], r["date"])
            if key in already:
                continue
            rid, claimed, ticker, D = r["row_id"], r["answer"], r["ticker"], r["date"]
            if rid not in SHEET:
                continue
            hit = None
            for fn in CHECKERS:
                try:
                    out = fn(rid, claimed, ticker, D)
                except Exception as e:
                    out = ("skip", f"err:{e}")
                if out is None:
                    continue
                hit = out
                break
            if hit is None or hit[0] == "skip":
                continue
            truth, detail = hit[1], hit[2]
            checked += 1
            ok = hit[0] == "ok"
            rec = {**r, "hc": "ok" if ok else "mismatch", "truth": truth, "detail": detail}
            results.append(rec)
            already.add(key)
            if not ok:
                mismatches.append(rec)
                print(f"MISMATCH {rid} {ticker} {D} claimed={claimed} truth={truth} {detail}", flush=True)
            else:
                print(f"OK {rid} {ticker} {D} {claimed} {detail}", flush=True)

    summary = {
        "sampled": len(sample),
        "independently_checked": checked,
        "mismatches": len(mismatches),
        "skips": dict(skips.most_common()),
        "mismatch_rows": [
            {"row_id": m["row_id"], "ticker": m["ticker"], "date": m["date"],
             "owner": m["owner"], "claimed": m["answer"], "truth": m["truth"], "detail": m["detail"]}
            for m in mismatches
        ],
    }
    with open(QA / "handcheck_results.json", "w") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2)
    print(json.dumps(summary, indent=2))
    print("HANDCHECK_DONE", flush=True)

if __name__ == "__main__":
    main()

"""path_bank.py - 'how it got here' (path/history) question bank generator. FROZEN spec v1.
Timing: every feature for day D uses only bars dated < D (computed on bar t then shift(1)), same as NB chunks.
Fixed threshold grid below; written before any scoring. Never feed 2025-26 rows (assert_practice()).
Usage: python3 path_bank.py --bank  -> writes PATH_BANK.csv ; python3 path_bank.py --test -> leak/NaN test AAPL,ALDX 2020-24
"""
import sys, hashlib, numpy as np, pandas as pd
LBS = [5, 10, 20, 60]
PRICE = "/workspace/pricehist/universe_2020_survivors.parquet"
CUTOFF = pd.Timestamp("2025-01-01")
def tok(x): return str(x).replace(".", "p").replace("-", "m")

# ---------- fixed grid: (family, kind, cuts|labels, words, formula) ----------
LABEL_BINS = {
 "dsh":  ([-.01, 0, .25, .5, 1.0], ["0", "le25pct", "le50pct", "le100pct"]),  # days since lb-high as frac of lb
 "dsl":  ([-.01, 0, .25, .5, 1.0], ["0", "le25pct", "le50pct", "le100pct"]),
 "disth":([-1, .02, .05, .10, .20, 9], ["lt2", "2to5", "5to10", "10to20", "gt20"]),  # pct below lb-high
 "dipatr":([-1, 1, 2, 4, 1e9], ["lt1", "1to2", "2to4", "gt4"]),
 "pctbmean":([-1e9, 0, .2, .5, .8, 1, 1e9], ["lt0", "0to20", "20to50", "50to80", "80to100", "gt100"]),
}
SWING = ["HH_HL", "HH_LL", "LH_HL", "LH_LL"]
THRESH = {  # family: (op, cuts, words, formula)
 "upstreak": (">=", [2, 3, 5], "longest run of consecutive up closes within lb", "max consecutive close>prevclose in window"),
 "dnstreak": (">=", [2, 3, 5], "longest run of consecutive down closes within lb", "max consecutive close<prevclose in window"),
 "ddrun": (">=", [0.25, 0.5, 0.75], "pullback from lb peak as share of the run into that peak", "(maxH-C)/(maxH-min L before peak)"),
 "bbup": (">=", [1, 3], "closes at/above upper BB(20,2) within lb", "count C>=SMA20+2sd20"),
 "bbdn": (">=", [1, 3], "closes at/below lower BB(20,2) within lb", "count C<=SMA20-2sd20"),
 "voltrend": (">=", [0.8, 1.25, 1.5], "avg volume 2nd half of lb / 1st half", "mean V(last lb/2)/mean V(first lb/2)"),
 "rgvol": (">=", [0.67, 1.0, 1.5], "avg green-day volume / avg red-day volume within lb", "mean V|C>O / mean V|C<O"),
 "slope": (">", [0], "OLS slope of log close over lb is positive", "polyfit(arange(lb),log C,1)[0]"),
 "accel": (">", [0], "slope of 2nd half of lb minus slope of 1st half > 0 (accelerating)", "slope(last half)-slope(first half)"),
 "slopeflip": ("==", [1], "sign of 2nd-half slope differs from 1st-half slope", "sign(s2)!=sign(s1)"),
 "recov": (">=", [0.5, 1.0], "recovery from post-peak trough toward lb peak", "(C-trough)/(maxH-trough), trough=min L after peak"),
 "recovspd": ("<=", [2, 5], "days from post-peak trough to now (fast recovery) with recov>=0.5", "days since trough if recov>=0.5 else inf"),
 "gapup": (">=", [1, 2], "gap-ups >2% (O/prevC-1) within lb", "count O/C[-1]-1>0.02"),
 "gapdn": (">=", [1, 2], "gap-downs >2% within lb", "count O/C[-1]-1<-0.02"),
 "rngexp": (">=", [0.67, 1.0, 1.5], "mean true range last lb / mean TR prior lb (expansion/contraction)", "meanTR(t-lb+1..t)/meanTR(t-2lb+1..t-lb)"),
}
LABELFAM_WORDS = {"swing": "swing structure: max-high & min-low of 2nd half vs 1st half of lb",
 "dsh": "days since lb-high, as fraction of lb", "dsl": "days since lb-low, as fraction of lb",
 "disth": "distance below lb high in pct", "dipatr": "dip depth from lb high to post-peak trough in ATR14 units",
 "pctbmean": "mean %B(20,2) over lb"}

def bank():
    rows = []
    for lb in LBS:
        for fam, (op, cuts, w, f) in THRESH.items():
            for c in cuts:
                rows.append(dict(id=f"ph_{fam}_{lb}_{('ge' if op=='>=' else 'gt' if op=='>' else 'le' if op=='<=' else 'eq')}{tok(c)}",
                    family=fam, lookback=lb, kind="yesno", rule=f"{w} {op} {c} (lb={lb})", formula=f"{f} {op} {c}", labels="yes|no", feature=f"{fam}_{lb}", op=op, cut=c))
        for fam in ["swing"] + list(LABEL_BINS):
            labs = SWING if fam == "swing" else LABEL_BINS[fam][1]
            rows.append(dict(id=f"ph_{fam}_{lb}_label", family=fam, lookback=lb, kind="label", rule=LABELFAM_WORDS[fam]+f" (lb={lb})",
                formula=(f"bins {LABEL_BINS[fam][0]} right-closed" if fam!="swing" else "H2>H1?HH:LH + L2>L1?HL:LL"), labels="|".join(labs), feature=f"{fam}_{lb}", op="label", cut=""))
            for l in labs:
                rows.append(dict(id=f"ph_{fam}_{lb}_{l}", family=fam, lookback=lb, kind="yesno", rule=f"{LABELFAM_WORDS[fam]} == {l} (lb={lb})",
                    formula=f"label=={l}", labels="yes|no", feature=f"{fam}_{lb}", op="==", cut=l))
    return pd.DataFrame(rows)

# ---------- features ----------
def _streak(s):  # current consecutive True count
    g = (~s).cumsum(); return s.groupby(g).cumsum()
def _r(x, lb, fn): return x.rolling(lb, min_periods=lb).apply(fn, raw=True)
def _slope(a):
    return np.polyfit(np.arange(len(a)), a, 1)[0]

def features(df):
    """df: one ticker, columns date,open,high,low,close,volume sorted by date. Returns raw features indexed like df, ALREADY shifted (D uses <D)."""
    df = df.sort_values("date").reset_index(drop=True)
    O, H, L, C, V = (df[k].astype("float64") for k in ["open", "high", "low", "close", "volume"])
    pc = C.shift(1); out = {}
    up, dn = _streak(C > pc), _streak(C < pc)
    tr = pd.concat([H - L, (H - pc).abs(), (L - pc).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14, min_periods=14).mean()
    m20, sd20 = C.rolling(20, min_periods=20).mean(), C.rolling(20, min_periods=20).std(ddof=0)
    pctb = (C - (m20 - 2 * sd20)) / (4 * sd20)
    gap = O / pc - 1; lc = np.log(C)
    green, red = (C > O), (C < O)
    for lb in LBS:
        h = lb // 2
        out[f"upstreak_{lb}"] = up.rolling(lb, min_periods=lb).max()
        out[f"dnstreak_{lb}"] = dn.rolling(lb, min_periods=lb).max()
        # peak position (0..lb-1 from window start), via rolling argmax
        pk = _r(H, lb, np.argmax)
        maxH = H.rolling(lb, min_periods=lb).max()
        idx = np.arange(len(df))
        lowb = np.full(len(df), np.nan); trough = np.full(len(df), np.nan); dtr = np.full(len(df), np.nan)
        Lv = L.values
        for i in idx[lb - 1:]:
            if np.isnan(pk[i]): continue
            s = i - lb + 1; p = s + int(pk[i])
            lowb[i] = Lv[s:p + 1].min()
            seg = Lv[p:i + 1]; j = int(np.argmin(seg)); trough[i] = seg[j]; dtr[i] = (i - p - j)
        run = maxH - lowb
        out[f"ddrun_{lb}"] = ((maxH - C) / run).where(run > 0)
        rec = ((C - trough) / (maxH - trough)).where(maxH > trough, 1.0)
        out[f"recov_{lb}"] = rec
        out[f"recovspd_{lb}"] = pd.Series(dtr).where(rec >= 0.5, np.inf).where(rec.notna())
        out[f"dipatr_{lb}"] = (maxH - trough) / atr
        out[f"bbup_{lb}"] = (C >= m20 + 2 * sd20).astype(float).where(m20.notna()).rolling(lb, min_periods=lb).sum()
        out[f"bbdn_{lb}"] = (C <= m20 - 2 * sd20).astype(float).where(m20.notna()).rolling(lb, min_periods=lb).sum()
        out[f"pctbmean_{lb}"] = pctb.rolling(lb, min_periods=lb).mean()
        vh2 = V.rolling(h, min_periods=h).mean(); vh1 = vh2.shift(h)
        out[f"voltrend_{lb}"] = (vh2 / vh1).where(vh1 > 0)
        gv = (V * green).rolling(lb, min_periods=lb).sum() / green.rolling(lb, min_periods=lb).sum()
        rv = (V * red).rolling(lb, min_periods=lb).sum() / red.rolling(lb, min_periods=lb).sum()
        out[f"rgvol_{lb}"] = (gv / rv).replace([np.inf, -np.inf], np.nan)
        s_all = _r(lc, lb, _slope); s2 = _r(lc, h, _slope); s1 = s2.shift(h)
        out[f"slope_{lb}"] = s_all; out[f"accel_{lb}"] = s2 - s1
        out[f"slopeflip_{lb}"] = (np.sign(s2) != np.sign(s1)).astype(float).where(s1.notna() & s2.notna())
        out[f"gapup_{lb}"] = (gap > 0.02).astype(float).where(pc.notna()).rolling(lb, min_periods=lb).sum()
        out[f"gapdn_{lb}"] = (gap < -0.02).astype(float).where(pc.notna()).rolling(lb, min_periods=lb).sum()
        mtr = tr.rolling(lb, min_periods=lb).mean(); out[f"rngexp_{lb}"] = mtr / mtr.shift(lb)
        out[f"dsh_{lb}"] = (lb - 1 - pk) / lb
        out[f"dsl_{lb}"] = (lb - 1 - _r(L, lb, np.argmin)) / lb
        out[f"disth_{lb}"] = (maxH - C) / maxH
        H2 = H.rolling(h, min_periods=h).max(); L2 = L.rolling(h, min_periods=h).min()
        H1 = H.shift(h).rolling(lb - h, min_periods=lb - h).max(); L1 = L.shift(h).rolling(lb - h, min_periods=lb - h).min()
        sw = np.where(H2 > H1, "HH", "LH").astype(object) + "_" + np.where(L2 > L1, "HL", "LL").astype(object)
        out[f"swing_{lb}"] = pd.Series(sw).where(H1.notna() & L1.notna())
    F = pd.DataFrame(out).shift(1)  # <-- strictly-before-D timing
    F.insert(0, "date", df["date"].values)
    return F

def answer(F, B=None):
    """Turn raw features into question answers (1/0/NaN for yesno, string for label)."""
    B = bank() if B is None else B; A = {"date": F["date"].values}
    for r in B.itertuples():
        x = F[r.feature]
        if r.family in LABEL_BINS:
            e, labs = LABEL_BINS[r.family]
            lab = pd.cut(x.astype(float).clip(e[0] + 1e-12, e[-1]), e, labels=labs).astype(object)
        elif r.family == "swing": lab = x
        if r.kind == "label": A[r.id] = lab; continue
        if r.op == "==" and r.family in (["swing"] + list(LABEL_BINS)): v = (lab == r.cut).astype(float).where(lab.notna())
        else:
            xv = x.astype(float); c = float(r.cut)
            v = {">=": xv >= c, ">": xv > c, "<=": xv <= c, "==": xv == c}[r.op].astype(float).where(xv.notna())
        A[r.id] = v
    return pd.DataFrame(A)

def assert_practice(df):
    assert df["date"].max() < CUTOFF, "2025-26 data must not be used"

def test():
    import pyarrow.dataset as ds
    d = ds.dataset(PRICE).to_table(filter=(ds.field("ticker").isin(["AAPL", "ALDX"])) & (ds.field("date") < CUTOFF)).to_pandas()
    d["ticker"] = d["ticker"].astype(str); assert_practice(d); B = bank(); rng = np.random.default_rng(20261022); ok = True
    for t in ["AAPL", "ALDX"]:
        g = d[d.ticker == t].sort_values("date").reset_index(drop=True)
        full = answer(features(g), B)
        warm = full.iloc[130:]; nanfrac = warm.drop(columns="date").isna().mean()
        print(t, "rows", len(g), "warm NaN frac max", round(nanfrac.max(), 4), "worst", nanfrac.idxmax())
        dates = rng.choice(g["date"].iloc[130:].values, 10, replace=False)
        for D in dates:
            gt = g[g.date <= D]  # truncated history up to and including D (D's own bar must not matter)
            gt2 = gt.astype({k: "float64" for k in ["open","high","low","close","volume"]}); gt2.loc[gt2.index[-1], ["open", "high", "low", "close", "volume"]] *= [3, 3, 0.1, 5, 50]  # poison D bar
            for gg, tag in [(gt, "trunc"), (gt2, "poisonD")]:
                a = answer(features(gg), B).iloc[-1]; b = full[full.date == D].iloc[0]
                for k in B.id:
                    x, y = a[k], b[k]
                    same = (pd.isna(x) and pd.isna(y)) or (isinstance(x, str) and x == y) or (not isinstance(x, str) and not pd.isna(x) and not pd.isna(y) and abs(float(x) - float(y)) < 1e-9)
                    if not same: ok = False; print("MISMATCH", t, str(D)[:10], tag, k, x, y)
        print(t, "10 dates x (trunc+poisoned D bar) checked")
    print("LEAK TEST", "PASS" if ok else "FAIL"); return ok

if __name__ == "__main__":
    if "--bank" in sys.argv:
        B = bank(); assert B.id.is_unique; B.to_csv("PATH_BANK.csv", index=False); print(len(B), "rows;", (B.kind == "yesno").sum(), "yes/no;", (B.kind == "label").sum(), "label")
    if "--test" in sys.argv: sys.exit(0 if test() else 1)

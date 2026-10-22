"""path_bank_v2.py - 'how it got here' (path/history) question bank v2, snapshot scale. FROZEN spec v2.
v1 (path_bank/, sha 985e4469...) is untouched; v2 widens every v1 cutoff grid and adds new path families.
Timing: every feature for day D uses only bars dated < D (computed on bar t then shift(1)).
All cutoffs are hard-coded below, written before any scoring; never tuned on outcomes. Nothing is scored here.
Lookbacks: 3,5,7,10,15,20,25,30,40,50,60 trading days (max 60). Scoring horizons later: 5/10/20 trading days only.
Refuses any data dated >= 2025-01-01 (assert_practice).
Usage: python3 path_bank_v2.py --bank -> PATH_BANK_V2.csv ; --test -> truncation + poisoned-D-bar leak test, 5 tickers x 10 dates
"""
import sys, numpy as np, pandas as pd
LBS = [3, 5, 7, 10, 15, 20, 25, 30, 40, 50, 60]
PRICE = "/workspace/pricehist/universe_2020_survivors.parquet"
CUTOFF = pd.Timestamp("2025-01-01")
WARM = 140  # bars: 60 lb + 60 prior-volume base + 20 MA/BB + slack
def tok(x): return str(x).replace(".", "p").replace("-", "m")
FR = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]            # fraction grid
RATIO = [0.5, 0.67, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 2.0, 3.0]  # ratio grid
CNT = [1, 2, 3, 4, 5, 7, 10, 15, 20, 30]                      # count grid (kept only if cut <= lb)
RET = [-0.3, -0.2, -0.15, -0.1, -0.05, -0.02, 0, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3]
SLP = [-0.02, -0.01, -0.005, -0.002, -0.001, 0, 0.001, 0.002, 0.005, 0.01, 0.02]  # per-day log slope
# family: (op, cuts, words, formula, min_lb, count_family)
THRESH = {
 # ---- v1 families, wider grids ----
 "upstreak": (">=", [2,3,4,5,6,7,8,10,12,15], "longest run of consecutive up closes within lb", "max consecutive C>C[-1] in window", 3, True),
 "dnstreak": (">=", [2,3,4,5,6,7,8,10,12,15], "longest run of consecutive down closes within lb", "max consecutive C<C[-1] in window", 3, True),
 "ddrun":    (">=", [0.1,0.2,0.25,0.3,0.382,0.5,0.618,0.75,0.9,1.0], "pullback from lb peak as share of the run into that peak", "(maxH-C)/(maxH-min L before peak)", 5, False),
 "bbup":     (">=", CNT, "closes at/above upper BB(20,2) within lb", "count C>=SMA20+2sd20", 3, True),
 "bbdn":     (">=", CNT, "closes at/below lower BB(20,2) within lb", "count C<=SMA20-2sd20", 3, True),
 "voltrend": (">=", RATIO, "avg volume 2nd half of lb / 1st half", "mean V(last h)/mean V(prior lb-h), h=lb//2", 5, False),
 "rgvol":    (">=", [0.33,0.5,0.67,0.8,1.0,1.25,1.5,2.0,3.0], "avg green-day volume / avg red-day volume within lb", "mean V|C>O / mean V|C<O", 5, False),
 "slope":    (">", SLP, "OLS slope of log close per day over lb", "rolling OLS slope of log C on 0..lb-1", 5, False),
 "accel":    (">", [-0.02,-0.01,-0.005,-0.002,0,0.002,0.005,0.01,0.02], "slope of 2nd half minus slope of 1st half", "slope(last h)-slope(prior h)", 10, False),
 "slopeflip":("==", [1], "sign of 2nd-half slope differs from 1st-half slope", "sign(s2)!=sign(s1)", 10, False),
 "recov":    (">=", [0.1,0.25,0.382,0.5,0.618,0.75,0.9,1.0], "recovery from post-peak trough toward lb peak", "(C-trough)/(maxH-trough), trough=min L at/after peak; 1 if no dip", 5, False),
 "recovspd": ("<=", [1,2,3,5,7,10,15,20], "bars from post-peak trough to now, given recov>=0.5 (inf otherwise)", "bars since trough if recov>=0.5 else inf", 5, True),
 "gapup1":   (">=", CNT, "gap-ups >1% within lb", "count O/C[-1]-1>0.01", 3, True),
 "gapup2":   (">=", CNT, "gap-ups >2% within lb", "count O/C[-1]-1>0.02", 3, True),
 "gapup5":   (">=", [1,2,3,5], "gap-ups >5% within lb", "count O/C[-1]-1>0.05", 3, True),
 "gapdn1":   (">=", CNT, "gap-downs >1% within lb", "count O/C[-1]-1<-0.01", 3, True),
 "gapdn2":   (">=", CNT, "gap-downs >2% within lb", "count O/C[-1]-1<-0.02", 3, True),
 "gapdn5":   (">=", [1,2,3,5], "gap-downs >5% within lb", "count O/C[-1]-1<-0.05", 3, True),
 "rngexp":   (">=", RATIO, "mean true range last lb / mean TR prior lb", "meanTR(t-lb+1..t)/meanTR(t-2lb+1..t-lb)", 3, False),
 "dsh":      ("<=", [0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9], "bars since lb high, as fraction of lb", "(lb-1-argmax H)/lb", 3, False),
 "dsl":      ("<=", [0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9], "bars since lb low, as fraction of lb", "(lb-1-argmin L)/lb", 3, False),
 "disth":    ("<=", [0.01,0.02,0.03,0.05,0.075,0.1,0.15,0.2,0.3,0.5], "distance below lb high (pct)", "(maxH-C)/maxH", 3, False),
 "distl":    ("<=", [0.01,0.02,0.03,0.05,0.075,0.1,0.15,0.2,0.3,0.5], "distance above lb low (pct)", "(C-minL)/minL", 3, False),
 "dipatr":   (">=", [0.5,1,1.5,2,2.5,3,4,5,6,8], "dip depth lb-high to post-peak trough in ATR14 units", "(maxH-trough)/ATR14", 5, False),
 "pctbmean": (">=", [-0.2,0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0,1.2], "mean %B(20,2) over lb", "mean (C-lowerBB)/(4sd20)", 3, False),
 # ---- new path families ----
 "hlfrac":   (">=", FR, "share of bars in lb with a higher low than prior bar", "mean L>L[-1]", 5, False),
 "hhfrac":   (">=", FR, "share of bars in lb with a higher high than prior bar", "mean H>H[-1]", 5, False),
 "hlrun":    (">=", [2,3,4,5,6,8,10], "longest run of consecutive higher lows within lb", "max consecutive L>L[-1]", 5, True),
 "lhrun":    (">=", [2,3,4,5,6,8,10], "longest run of consecutive lower highs within lb", "max consecutive H<H[-1]", 5, True),
 "abv10frac":(">=", FR+[1.0], "share of lb closes above SMA10", "mean C>SMA10", 3, False),
 "abv20frac":(">=", FR+[1.0], "share of lb closes above SMA20", "mean C>SMA20", 3, False),
 "abv50frac":(">=", FR+[1.0], "share of lb closes above SMA50", "mean C>SMA50", 3, False),
 "abv20run": (">=", [2,3,5,7,10,15,20,30,40,60], "longest run of consecutive closes above SMA20 within lb", "max consecutive C>SMA20", 3, True),
 "abv20now": (">=", [1,2,3,5,7,10,15,20,30,40,60], "current consecutive closes above SMA20, capped at lb", "min(current streak C>SMA20, lb)", 3, True),
 "blw20now": (">=", [1,2,3,5,7,10,15,20,30,40,60], "current consecutive closes below SMA20, capped at lb", "min(current streak C<SMA20, lb)", 3, True),
 "gx5_20":   ("==", [1], "SMA5 crossed above SMA20 within lb", "any(SMA5>SMA20 & SMA5[-1]<=SMA20[-1]) in window", 3, False),
 "dx5_20":   ("==", [1], "SMA5 crossed below SMA20 within lb", "any(SMA5<SMA20 & SMA5[-1]>=SMA20[-1])", 3, False),
 "gx10_50":  ("==", [1], "SMA10 crossed above SMA50 within lb", "golden cross 10/50 in window", 3, False),
 "dx10_50":  ("==", [1], "SMA10 crossed below SMA50 within lb", "death cross 10/50 in window", 3, False),
 "gx20_50":  ("==", [1], "SMA20 crossed above SMA50 within lb", "golden cross 20/50 in window", 3, False),
 "dx20_50":  ("==", [1], "SMA20 crossed below SMA50 within lb", "death cross 20/50 in window", 3, False),
 "xc20up":   ("==", [1], "close crossed above SMA20 within lb", "any(C>SMA20 & C[-1]<=SMA20[-1])", 3, False),
 "xc20dn":   ("==", [1], "close crossed below SMA20 within lb", "any(C<SMA20 & C[-1]>=SMA20[-1])", 3, False),
 "nh20":     (">=", CNT, "closes making a new 20-bar closing high within lb", "count C>max(C[-20..-1])", 3, True),
 "nl20":     (">=", CNT, "closes making a new 20-bar closing low within lb", "count C<min(C[-20..-1])", 3, True),
 "nh60":     (">=", CNT, "closes making a new 60-bar closing high within lb", "count C>max(C[-60..-1])", 3, True),
 "nl60":     (">=", CNT, "closes making a new 60-bar closing low within lb", "count C<min(C[-60..-1])", 3, True),
 "clvmean":  (">=", [-0.6,-0.4,-0.2,-0.1,0,0.1,0.2,0.4,0.6], "mean close-location value over lb", "mean ((C-L)-(H-C))/(H-L), 0 if H==L", 3, False),
 "clvtrend": (">", [-0.1,-0.05,-0.02,0,0.02,0.05,0.1], "OLS slope of CLV per day over lb", "rolling OLS slope of CLV", 5, False),
 "volrel":   (">=", [0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0,1.25,1.5,2.0,3.0], "mean volume over lb / mean volume of the 60 bars before the window", "meanV(lb)/meanV(prior 60)", 3, False),
 "vdry":     ("<=", [0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0], "min 3-bar mean volume within lb / mean V of 60 bars before window (dry-up)", "min roll3 meanV in lb / meanV(prior 60)", 5, False),
 "vdrymove": ("==", [1], "volume dried up (min 3-bar meanV <= 0.6x prior-60 base) earlier in lb, then last bar |ret| >= 1.5 ATR14", "vdry<=0.6 & |C/C[-1]-1|*C[-1]>=1.5ATR14", 5, False),
 "vdryup":   ("==", [1], "volume dry-up (<=0.6x) earlier in lb, then net close up over last 3 bars by >= 1 ATR14", "vdry<=0.6 & C-C[-3]>=ATR14", 5, False),
 "rngcomp":  ("<=", [0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0], "min 3-bar mean TR within lb / ATR of 60 bars before window (compression)", "min roll3 meanTR in lb / meanTR(prior 60)", 5, False),
 "sqzexp":   (">=", [1.0,1.25,1.5,2.0,2.5,3.0,4.0], "last-bar TR / min 3-bar mean TR within lb (expansion after compression)", "TR[t]/min roll3 meanTR in lb", 5, False),
 "nr7cnt":   (">=", CNT, "NR7 bars (narrowest TR of last 7) within lb", "count TR==min(TR last 7)", 3, True),
 "insidecnt":(">=", CNT, "inside bars (H<=H[-1] & L>=L[-1]) within lb", "count inside", 3, True),
 "maxdd":    (">=", [0.02,0.03,0.05,0.075,0.1,0.15,0.2,0.3,0.5], "max close-to-close drawdown within lb", "max over window of 1-C/cummax(C)", 3, False),
 "ddrecfrac":(">=", [0.1,0.25,0.382,0.5,0.618,0.75,0.9,1.0], "fraction of the lb max drawdown recovered (closes)", "(C-Ctrough)/(Cpeak-Ctrough) of max-DD episode; NaN if dd<1%", 5, False),
 "grnfrac":  (">=", FR, "share of green candles (C>O) in lb", "mean C>O", 3, False),
 "upfrac":   (">=", FR, "share of up closes (C>C[-1]) in lb", "mean C>C[-1]", 3, False),
 "upvolfrac":(">=", [0.3,0.4,0.45,0.5,0.55,0.6,0.7], "share of lb volume on up-close days", "sum V|C>C[-1] / sum V", 3, False),
 "atrtrend": (">=", RATIO, "ATR14 now / ATR14 lb bars ago", "ATR14[t]/ATR14[t-lb]", 3, False),
 "natr":     (">=", [0.01,0.015,0.02,0.03,0.04,0.05,0.07,0.1], "mean TR/C over lb (volatility level)", "mean TR/C", 3, False),
 "ret":      (">=", RET, "close-to-close return over lb", "C/C[-lb]-1", 3, False),
 "rngpos":   (">=", FR, "close position in lb high-low range", "(C-minL)/(maxH-minL)", 3, False),
 "maxup1d":  (">=", [0.02,0.03,0.05,0.075,0.1,0.15,0.2,0.3], "largest 1-day close gain within lb", "max C/C[-1]-1", 3, False),
 "maxdn1d":  (">=", [0.02,0.03,0.05,0.075,0.1,0.15,0.2,0.3], "largest 1-day close loss within lb (positive)", "max 1-C/C[-1]", 3, False),
 "bigvolday":(">=", [1,2,3,5], "bars with V >= 2x mean V of prior 20 bars within lb", "count V>=2*meanV(-20..-1)", 3, True),
 "bodymean": (">=", [0.2,0.3,0.4,0.5,0.6,0.7], "mean body/range over lb", "mean |C-O|/(H-L)", 3, False),
 "uwickmean":(">=", [0.1,0.2,0.3,0.4,0.5], "mean upper wick/range over lb", "mean (H-max(O,C))/(H-L)", 3, False),
 "lwickmean":(">=", [0.1,0.2,0.3,0.4,0.5], "mean lower wick/range over lb", "mean (min(O,C)-L)/(H-L)", 3, False),
}
LABELS = {  # family: (labels, words, formula, min_lb)
 "swing": (["HH_HL","HH_LL","LH_HL","LH_LL"], "swing structure: max-high & min-low of last h vs prior lb-h", "H2>H1?HH:LH + L2>L1?HL:LL", 5),
 "rngposq": (["q1","q2","q3","q4","q5"], "close position in lb range, quintile (fixed 0.2 bins)", "bins [0,.2,.4,.6,.8,1]", 3),
 "retq": (["lt_m10","m10_m3","m3_0","0_3","3_10","gt10"], "lb return bucket (pct, fixed)", "bins -inf,-10,-3,0,3,10,inf (right-closed)", 3),
 "seq3": (["GGG","GGR","GRG","GRR","RGG","RGR","RRG","RRR"], "up/down close sequence of last 3 bars (G=C>C[-1])", "pattern of last 3 closes vs prior", 3),
}
LBMIN_ONLY = {"seq3": [3]}

def opword(op): return {">=": "ge", ">": "gt", "<=": "le", "==": "eq"}[op]
def bank():
    rows = []
    for lb in LBS:
        for fam, (op, cuts, w, f, mlb, isc) in THRESH.items():
            if lb < mlb: continue
            for c in cuts:
                if isc and c > lb: continue
                if fam in ('dsh', 'dsl') and c >= (lb - 1) / lb: continue  # structurally always yes
                if fam == 'recovspd' and c >= lb - 1: continue            # structurally always yes when defined
                rows.append(dict(id=f"ph2_{fam}_{lb}_{opword(op)}{tok(c)}", family=fam, lookback=lb, kind="yesno",
                    rule=f"{w} {op} {c} (lb={lb})", formula=f"{f} {op} {c}", labels="yes|no", feature=f"{fam}_{lb}", op=op, cut=c))
        for fam, (labs, w, f, mlb) in LABELS.items():
            if lb < mlb or (fam in LBMIN_ONLY and lb not in LBMIN_ONLY[fam]): continue
            rows.append(dict(id=f"ph2_{fam}_{lb}_label", family=fam, lookback=lb, kind="label", rule=f"{w} (lb={lb})", formula=f,
                labels="|".join(labs), feature=f"{fam}_{lb}", op="label", cut=""))
            for l in labs:
                rows.append(dict(id=f"ph2_{fam}_{lb}_{l}", family=fam, lookback=lb, kind="yesno", rule=f"{w} == {l} (lb={lb})",
                    formula=f"label=={l}", labels="yes|no", feature=f"{fam}_{lb}", op="==", cut=l))
    return pd.DataFrame(rows)

# ---------- features ----------
def _streak(s):
    s = s.fillna(False).astype(bool); g = (~s).cumsum(); return s.astype(float).groupby(g).cumsum()
def _rsum(x, lb): return x.rolling(lb, min_periods=lb).sum()
def _rmean(x, lb): return x.rolling(lb, min_periods=lb).mean()
def _rmax(x, lb): return x.rolling(lb, min_periods=lb).max()
def _rmin(x, lb): return x.rolling(lb, min_periods=lb).min()
def _slope(y, n):
    """rolling OLS slope over n bars, exact via loop over windows (prefix-stable)."""
    a = y.values.astype(float); out = np.full(len(a), np.nan); x = np.arange(n) - (n - 1) / 2; den = (x * x).sum()
    if len(a) >= n:
        W = np.lib.stride_tricks.sliding_window_view(a, n)
        out[n - 1:] = (W - W.mean(axis=1, keepdims=True)) @ x / den
    return pd.Series(out, index=y.index)
def _bool(cond, valid): return cond.astype(float).where(valid)

def features(df):
    """df: one ticker sorted by date with open,high,low,close,volume. Returns features ALREADY shifted (row D uses bars < D)."""
    df = df.sort_values("date").reset_index(drop=True); n = len(df)
    O, H, L, C, V = (df[k].astype("float64") for k in ["open", "high", "low", "close", "volume"])
    pc = C.shift(1); out = {}
    up, dn = _streak(C > pc), _streak(C < pc)
    hl, lh = _streak(L > L.shift(1)), _streak(H < H.shift(1))
    tr = pd.concat([H - L, (H - pc).abs(), (L - pc).abs()], axis=1).max(axis=1).where(pc.notna())
    atr = _rmean(tr, 14)
    m5, m10, m20, m50 = (_rmean(C, k) for k in (5, 10, 20, 50)); sd20 = C.rolling(20, min_periods=20).std(ddof=0)
    pctb = ((C - (m20 - 2 * sd20)) / (4 * sd20)).where(sd20 > 0)
    gap = O / pc - 1; lc = np.log(C); green, red = (C > O), (C < O); upd = (C > pc)
    rng = (H - L); rngz = rng.where(rng > 0)
    clv = (((C - L) - (H - C)) / rngz).fillna(0.0).where(C.notna())
    ab20 = C > m20; vm20 = m20.notna()
    abv20now_raw, blw20now_raw = _streak(ab20 & vm20), _streak((C < m20) & vm20)
    def cross(a, b):
        v = a.notna() & b.notna() & a.shift(1).notna() & b.shift(1).notna()
        return _bool((a > b) & (a.shift(1) <= b.shift(1)), v), _bool((a < b) & (a.shift(1) >= b.shift(1)), v)
    X = {"gx5_20,dx5_20": cross(m5, m20), "gx10_50,dx10_50": cross(m10, m50), "gx20_50,dx20_50": cross(m20, m50), "xc20up,xc20dn": cross(C, m20)}
    nh20 = _bool(C > _rmax(C, 20).shift(1), pc.notna() & C.shift(20).notna()); nl20 = _bool(C < _rmin(C, 20).shift(1), C.shift(20).notna())
    nh60 = _bool(C > _rmax(C, 60).shift(1), C.shift(60).notna()); nl60 = _bool(C < _rmin(C, 60).shift(1), C.shift(60).notna())
    nr7 = _bool(tr <= _rmin(tr, 7), tr.rolling(7, min_periods=7).count() == 7)
    inside = _bool((H <= H.shift(1)) & (L >= L.shift(1)), pc.notna())
    bigv = _bool(V >= 2 * _rmean(V, 20).shift(1), V.shift(20).notna())
    v3, tr3 = _rmean(V, 3), _rmean(tr, 3); r1 = C / pc - 1
    body = ((C - O).abs() / rngz).fillna(0.0).where(C.notna())
    uw = ((H - np.maximum(O, C)) / rngz).fillna(0.0).where(C.notna()); lw = ((np.minimum(O, C) - L) / rngz).fillna(0.0).where(C.notna())
    Lv, Hv, Cv = L.values, H.values, C.values
    for lb in LBS:
        h = max(lb // 2, 1)
        out[f"upstreak_{lb}"] = _rmax(up.where(pc.notna()), lb); out[f"dnstreak_{lb}"] = _rmax(dn.where(pc.notna()), lb)
        out[f"hlrun_{lb}"] = _rmax(hl.where(pc.notna()), lb); out[f"lhrun_{lb}"] = _rmax(lh.where(pc.notna()), lb)
        maxH, minL = _rmax(H, lb), _rmin(L, lb)
        pk = np.full(n, np.nan); lowb = np.full(n, np.nan); trough = np.full(n, np.nan); dtr = np.full(n, np.nan); argl = np.full(n, np.nan)
        mdd = np.full(n, np.nan); ddr = np.full(n, np.nan)
        for i in range(lb - 1, n):
            s = i - lb + 1; wh = Hv[s:i + 1]; wl = Lv[s:i + 1]; wc = Cv[s:i + 1]
            p = int(np.argmax(wh)); pk[i] = p; argl[i] = int(np.argmin(wl))
            lowb[i] = wl[:p + 1].min(); seg = wl[p:]; j = int(np.argmin(seg)); trough[i] = seg[j]; dtr[i] = lb - 1 - p - j
            cm = np.maximum.accumulate(wc); dd = 1 - wc / cm; k = int(np.argmax(dd)); mdd[i] = dd[k]
            if dd[k] >= 0.01:
                pkc = cm[k]; ddr[i] = (wc[-1] - wc[k]) / (pkc - wc[k])
        run = maxH - lowb
        out[f"ddrun_{lb}"] = ((maxH - C) / run).where(run > 0)
        rec = ((C - trough) / (maxH - trough)).where(maxH > trough, 1.0).where(maxH.notna())
        out[f"recov_{lb}"] = rec
        out[f"recovspd_{lb}"] = pd.Series(dtr).where(rec >= 0.5, np.inf).where(rec.notna())
        out[f"dipatr_{lb}"] = (maxH - trough) / atr
        out[f"maxdd_{lb}"] = pd.Series(mdd); out[f"ddrecfrac_{lb}"] = pd.Series(ddr).where(pd.Series(mdd) >= 0.01)
        out[f"bbup_{lb}"] = _rsum(_bool(C >= m20 + 2 * sd20, vm20), lb); out[f"bbdn_{lb}"] = _rsum(_bool(C <= m20 - 2 * sd20, vm20), lb)
        out[f"pctbmean_{lb}"] = _rmean(pctb, lb)
        vh2 = _rmean(V, h); vh1 = _rmean(V, lb - h).shift(h)
        out[f"voltrend_{lb}"] = (vh2 / vh1).where(vh1 > 0)
        gv = _rsum(V * green, lb) / _rsum(green.astype(float), lb); rv = _rsum(V * red, lb) / _rsum(red.astype(float), lb)
        out[f"rgvol_{lb}"] = (gv / rv).replace([np.inf, -np.inf], np.nan)
        if lb >= 5:
            out[f"slope_{lb}"] = _slope(lc, lb); out[f"clvtrend_{lb}"] = _slope(clv, lb)
        if lb >= 10:
            s2 = _slope(lc, h); s1 = s2.shift(h); out[f"accel_{lb}"] = s2 - s1
            out[f"slopeflip_{lb}"] = (np.sign(s2) != np.sign(s1)).astype(float).where(s1.notna() & s2.notna())
        for th, nm in [(0.01, "1"), (0.02, "2"), (0.05, "5")]:
            out[f"gapup{nm}_{lb}"] = _rsum(_bool(gap > th, pc.notna()), lb); out[f"gapdn{nm}_{lb}"] = _rsum(_bool(gap < -th, pc.notna()), lb)
        mtr = _rmean(tr, lb); out[f"rngexp_{lb}"] = mtr / mtr.shift(lb)
        out[f"dsh_{lb}"] = (lb - 1 - pd.Series(pk)) / lb; out[f"dsl_{lb}"] = (lb - 1 - pd.Series(argl)) / lb
        out[f"disth_{lb}"] = (maxH - C) / maxH; out[f"distl_{lb}"] = (C - minL) / minL
        H2, L2 = _rmax(H, h), _rmin(L, h); H1, L1 = _rmax(H, lb - h).shift(h), _rmin(L, lb - h).shift(h)
        sw = np.where(H2 > H1, "HH", "LH").astype(object) + "_" + np.where(L2 > L1, "HL", "LL").astype(object)
        out[f"swing_{lb}"] = pd.Series(sw).where(H1.notna() & L1.notna())
        out[f"hlfrac_{lb}"] = _rmean(_bool(L > L.shift(1), pc.notna()), lb); out[f"hhfrac_{lb}"] = _rmean(_bool(H > H.shift(1), pc.notna()), lb)
        for k, m in [(10, m10), (20, m20), (50, m50)]: out[f"abv{k}frac_{lb}"] = _rmean(_bool(C > m, m.notna()), lb)
        out[f"abv20run_{lb}"] = _rmax(abv20now_raw.where(vm20), lb)
        out[f"abv20now_{lb}"] = np.minimum(abv20now_raw, lb).where(_rmin(vm20.astype(float), lb) == 1)
        out[f"blw20now_{lb}"] = np.minimum(blw20now_raw, lb).where(_rmin(vm20.astype(float), lb) == 1)
        for names, (gu, gd) in X.items():
            a, b = names.split(","); out[f"{a}_{lb}"] = (_rmax(gu, lb)); out[f"{b}_{lb}"] = (_rmax(gd, lb))
        for nm, s in [("nh20", nh20), ("nl20", nl20), ("nh60", nh60), ("nl60", nl60), ("nr7cnt", nr7), ("insidecnt", inside), ("bigvolday", bigv)]:
            out[f"{nm}_{lb}"] = _rsum(s, lb)
        out[f"clvmean_{lb}"] = _rmean(clv, lb)
        base = _rmean(V, 60).shift(lb); out[f"volrel_{lb}"] = (_rmean(V, lb) / base).where(base > 0)
        vd = (_rmin(v3, lb) / base).where(base > 0); out[f"vdry_{lb}"] = vd
        trb = _rmean(tr, 60).shift(lb); out[f"rngcomp_{lb}"] = (_rmin(tr3, lb) / trb).where(trb > 0)
        mn3 = _rmin(tr3, lb); out[f"sqzexp_{lb}"] = (tr / mn3).where(mn3 > 0)
        okv = vd.notna() & atr.notna() & C.shift(3).notna()
        out[f"vdrymove_{lb}"] = _bool((vd <= 0.6) & ((C - pc).abs() >= 1.5 * atr), okv)
        out[f"vdryup_{lb}"] = _bool((vd <= 0.6) & ((C - C.shift(3)) >= atr), okv)
        out[f"grnfrac_{lb}"] = _rmean(green.astype(float).where(C.notna()), lb); out[f"upfrac_{lb}"] = _rmean(_bool(upd, pc.notna()), lb)
        sv = _rsum(V.where(pc.notna()), lb); out[f"upvolfrac_{lb}"] = (_rsum((V * upd).where(pc.notna()), lb) / sv).where(sv > 0)
        out[f"atrtrend_{lb}"] = atr / atr.shift(lb); out[f"natr_{lb}"] = _rmean(tr / C, lb)
        out[f"ret_{lb}"] = C / C.shift(lb) - 1
        rr = maxH - minL; out[f"rngpos_{lb}"] = ((C - minL) / rr).where(rr > 0)
        out[f"maxup1d_{lb}"] = _rmax(r1, lb); out[f"maxdn1d_{lb}"] = _rmax(-r1, lb)
        out[f"bodymean_{lb}"] = _rmean(body, lb); out[f"uwickmean_{lb}"] = _rmean(uw, lb); out[f"lwickmean_{lb}"] = _rmean(lw, lb)
        rp = out[f"rngpos_{lb}"]
        out[f"rngposq_{lb}"] = pd.cut(rp, [-1e-9, .2, .4, .6, .8, 1.0], labels=LABELS["rngposq"][0]).astype(object).where(rp.notna())
        rt = out[f"ret_{lb}"]
        out[f"retq_{lb}"] = pd.cut(rt, [-np.inf, -.10, -.03, 0, .03, .10, np.inf], labels=LABELS["retq"][0]).astype(object).where(rt.notna())
        if lb == 3:
            g = np.where(upd, "G", "R").astype(object)
            seq = pd.Series(g).shift(2) + pd.Series(g).shift(1) + pd.Series(g)
            out["seq3_3"] = seq.where(C.shift(3).notna())
    F = pd.DataFrame(out).shift(1)  # <-- strictly-before-D timing
    F.insert(0, "date", df["date"].values)
    return F

def answer(F, B=None):
    B = bank() if B is None else B; A = {"date": F["date"].values}
    for r in B.itertuples():
        x = F[r.feature]
        if r.kind == "label": A[r.id] = x.values; continue
        if r.family in LABELS: v = (x == r.cut).astype(float).where(x.notna())
        else:
            xv = x.astype(float); c = float(r.cut)
            v = {">=": xv >= c, ">": xv > c, "<=": xv <= c, "==": xv == c}[r.op].astype(float).where(xv.notna())
        A[r.id] = v.values
    return pd.DataFrame(A)

def assert_practice(df):
    assert pd.to_datetime(df["date"]).max() < CUTOFF, "REFUSED: rows dated >= 2025-01-01 (2025-26 is the exam set)"

def load(tickers):
    import pyarrow.dataset as ds
    d = ds.dataset(PRICE).to_table(filter=(ds.field("ticker").isin(tickers)) & (ds.field("date") < CUTOFF)).to_pandas()
    d["ticker"] = d["ticker"].astype(str); assert_practice(d); return d

def test(tickers=("AAPL", "ALDX", "NVDA", "CELH", "F")):
    d = load(list(tickers)); B = bank(); rng = np.random.default_rng(20261022); ok = True; nanrep = []
    # refusal check
    try: assert_practice(pd.DataFrame({"date": [pd.Timestamp("2025-01-02")]})); print("REFUSAL CHECK FAIL"); ok = False
    except AssertionError: print("refusal check: 2025-01-02 row refused OK")
    for t in tickers:
        g = d[d.ticker == t].sort_values("date").reset_index(drop=True)
        full = answer(features(g), B)
        warm = full.iloc[WARM:].drop(columns="date"); nf = warm.isna().mean()
        nanrep.append((t, nf)); print(t, "rows", len(g), f"| after {WARM}-bar warmup: mean NaN {nf.mean():.4f}, max {nf.max():.4f} ({nf.idxmax()}), cols with any NaN {(nf>0).sum()}")
        dates = rng.choice(g["date"].iloc[WARM:].values, 10, replace=False); nmis = 0
        for D in dates:
            gt = g[g.date <= D].copy(); gt2 = gt.astype({k: "float64" for k in ["open","high","low","close","volume"]})
            gt2.loc[gt2.index[-1], ["open", "high", "low", "close", "volume"]] *= [3, 3, 0.1, 5, 50]
            b = full[full.date == D].iloc[0]
            for gg, tag in [(gt, "trunc"), (gt2, "poisonD")]:
                a = answer(features(gg), B).iloc[-1]
                for k in B.id:
                    x, y = a[k], b[k]
                    same = (pd.isna(x) and pd.isna(y)) or (isinstance(x, str) and x == y) or (not isinstance(x, str) and not pd.isna(x) and not pd.isna(y) and abs(float(x) - float(y)) < 1e-9)
                    if not same:
                        ok = False; nmis += 1
                        if nmis <= 20: print("MISMATCH", t, str(D)[:10], tag, k, x, y)
        print(t, "10 dates:", ", ".join(str(x)[:10] for x in sorted(dates)), f"| {len(B)} answers x (trunc + poisoned D bar) | mismatches {nmis}")
    allnf = pd.concat([x for _, x in nanrep], axis=1).mean(axis=1)
    print(f"NaN share after warmup, avg over 5 tickers: overall {allnf.mean():.4f}; questions >5%: {(allnf>0.05).sum()}; >20%: {(allnf>0.2).sum()}")
    print("worst 10:", "; ".join(f"{k}={v:.3f}" for k, v in allnf.sort_values(ascending=False).head(10).items()))
    fam = B.set_index("id").family; byf = allnf.groupby(fam).mean().sort_values(ascending=False)
    print("family mean NaN (top 10):", "; ".join(f"{k}={v:.3f}" for k, v in byf.head(10).items()))
    print("LEAK TEST", "PASS" if ok else "FAIL"); return ok

if __name__ == "__main__":
    if "--bank" in sys.argv:
        B = bank(); assert B.id.is_unique; B.to_csv("PATH_BANK_V2.csv", index=False)
        print(len(B), "rows;", (B.kind == "yesno").sum(), "yes/no;", (B.kind == "label").sum(), "label;", B.family.nunique(), "families")
    if "--test" in sys.argv: sys.exit(0 if test() else 1)

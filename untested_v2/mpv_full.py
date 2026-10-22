"""master.csv price/volume rows -> deterministic formulas (ported from strict_definition). PRACTICE 2020-24 HINT.
Every value computed on bars <= t then shifted 1 => day D sees only bars < D ("C" = close of D-1). Price sha fb9bbe69…ef337; rows > 2024 never read.
Sector/industry membership = current Finviz map (not point-in-time; labelled). Rows that need intraday, after-hours, VWAP, halts or earnings dates -> NOT_READY.
Output TMP/A_MPV.npz (0=NA,1=NO,2=YES) aligned with cells.parquet, plus TMP/mpv_status.csv."""
import sys, os, numpy as np, pandas as pd, pyarrow.parquet as pq
from multiprocessing import Pool
sys.path.insert(0, "/workspace/ce_untested/practice_results/lookalike_features"); from build import PX, PX_SHA, HI, sha, TMP
FV = "/workspace/fullscan/data/finviz/latest.csv"
SPDR = {"Technology": "XLK", "Financial": "XLF", "Energy": "XLE", "Healthcare": "XLV", "Consumer Cyclical": "XLY", "Consumer Defensive": "XLP",
        "Industrials": "XLI", "Basic Materials": "XLB", "Utilities": "XLU", "Real Estate": "XLRE", "Communication Services": "XLC"}
NOT_READY = {"SEC-JA-031": "needs after-hours prints of industry peers", "STR-NB-005": "needs intraday last-hour bars", "STR-NB-006": "needs intraday VWAP",
             "STR-NB-007": "needs earnings dates (AVWAP anchor) not on box PIT", "STR-NB-011": "needs LULD halt records"}
def rsi(c, n):
    d = c.diff(); u = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); w = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + u / w.replace(0, np.nan))
def feats(g, R):
    g = g.set_index("date"); O, H, L, C, V = g.open, g.high, g.low, g.close, g.volume
    O1, H1, L1, C1 = O.shift(1), H.shift(1), L.shift(1), C.shift(1); rng = (H - L).replace(0, np.nan); body = (C - O).abs()
    uw = H - np.maximum(O, C); lw = np.minimum(O, C) - L; grn = C > O; red = C < O; clv = (C - L) / rng
    tr = pd.concat([H - L, (H - C1).abs(), (L - C1).abs()], axis=1).max(axis=1); atr = tr.ewm(alpha=1 / 14, adjust=False).mean()
    dec = C / C.shift(5) < 0.97; adv = C / C.shift(5) > 1.03; ret = C.pct_change(); X = {}
    sma = {n: C.rolling(n).mean() for n in (5, 9, 10, 20, 21, 50, 80, 100, 200)}
    X["CDL-001"] = grn.rolling(10).mean() >= 0.7; X["IND-001"] = (sma[20] > sma[50]) & (sma[50] > sma[80]); X["OSC-001"] = rsi(C, 14) < 20
    # sector / benchmarks
    def rel(b, n): return C / C.shift(n) - (b / b.shift(n))
    spy, iwm, sec = R["SPY"].reindex(C.index), R["IWM"].reindex(C.index), R.get("SEC")
    sec = sec.reindex(C.index) if sec is not None else pd.Series(np.nan, C.index)
    X["SEC-JA-007"] = rel(sec, 60) >= 0.05; X["SEC-JA-008"] = (sec / sec.shift(60)) - (spy / spy.shift(60)) >= 0.03
    rs = C / sec; X["SEC-JA-009"] = (rs > rs.rolling(50).mean()) & (rs.rolling(50).mean().diff() > 0)
    X["SEC-JA-010"] = rs >= rs.rolling(252).max(); X["SEC-JA-011"] = rs <= rs.rolling(252).min()
    for k, s in (("SEC", sec),): pass
    X["STR-NB-001"] = clv >= 0.9; X["STR-NB-002"] = clv <= 0.1
    X["STR-NB-004"] = (H <= H1) & (L >= L1) & (ret.shift(1).abs() >= 0.05)
    step = np.where(C < 20, 1, np.where(C < 100, 5, 10)); X["STR-NB-008"] = (C - np.round(C / step) * step).abs() / C <= 0.005
    X["STR-NB-009"] = (C < 1).rolling(30).sum() >= 20
    spyr = spy.pct_change(); dn = spyr < 0
    up_on_dn = ((ret > 0) & dn).astype(float); X["REL-NB-002"] = pd.Series([np.nan] * len(C), C.index)
    idx = np.flatnonzero(dn.values); cum = np.full(len(C), np.nan); u = up_on_dn.values
    for t in range(len(C)):
        k = idx[idx <= t][-10:]
        if len(k) == 10: cum[t] = u[k].sum()
    X["REL-NB-002"] = pd.Series(cum >= 6, C.index).where(~np.isnan(cum))
    X["HST-NB-001"] = (ret.abs() >= 0.2).rolling(250).sum() >= 3; X["HST-NB-002"] = ret >= 0.2
    lo252 = L.rolling(252).min(); dl = pd.Series(np.arange(len(C)), C.index) - L.rolling(252).apply(lambda w: np.argmin(w), raw=True) - 0
    X["HST-NB-003"] = ((251 - L.rolling(252).apply(np.argmin, raw=True)) <= 10) & (C / lo252 - 1 >= 0.2)
    mo = C.resample("ME").last().pct_change(); mstat = {}
    cur_m = C.index.month; hm = np.full(len(C), np.nan)
    for i, d in enumerate(C.index):
        past = mo[(mo.index.month == d.month) & (mo.index < d.replace(day=1)) & (mo.index >= d - pd.DateOffset(years=10, months=1))].dropna()
        if len(past) >= 10: hm[i] = float((past.mean() >= 0.03) and ((past > 0).sum() >= 7))
    X["HST-NB-004"] = pd.Series(hm, C.index)
    gu = O > H1; X["HST-NB-005"] = gu & gu.shift(1) & gu.shift(2)
    X["PRC-TR-007"] = O / C1 - 1 >= 0.05; X["VOL-TR-001"] = V / V.rolling(50).mean().shift(1) >= 3; X["VOL-TR-002"] = V.rolling(63).mean() < 200_000
    X["TEC-TR-001"] = C > 1.5 * sma[200]; X["TEC-TR-002"] = sma[20] > sma[50]
    # PV-TF candlestick patterns, each in 3 contexts (any / after decline / after advance)
    pats = {1: body <= 0.1 * rng, 4: (lw >= 2 * body) & (uw <= 0.1 * rng) & (body > 0) & (clv >= 2 / 3), 7: (uw >= 2 * body) & (lw <= 0.1 * rng) & (clv <= 1 / 3),
            10: grn & (body >= 0.9 * rng), 13: red & (body >= 0.9 * rng), 16: (C1 < O1) & grn & (O <= C1) & (C >= O1), 19: (C1 > O1) & red & (O >= C1) & (C <= O1),
            22: (H < H1) & (L > L1), 25: (H > H1) & (L < L1) & grn}
    O2, C2, H2, L2 = O.shift(2), C.shift(2), H.shift(2), L.shift(2); r2 = (H2 - L2).replace(0, np.nan); r1 = (H1 - L1).replace(0, np.nan)
    pats[28] = (C2 < O2) & ((O2 - C2) >= 0.6 * r2) & ((C1 - O1).abs() <= 0.3 * r1) & grn & (C > (O2 + C2) / 2)
    pats[31] = (C2 > O2) & ((C2 - O2) >= 0.6 * r2) & ((C1 - O1).abs() <= 0.3 * r1) & red & (C < (O2 + C2) / 2)
    def inbody(o, cp, op): return (o >= np.minimum(cp, op)) & (o <= np.maximum(cp, op))
    pats[34] = grn & grn.shift(1) & grn.shift(2) & (C > C1) & (C1 > C2) & inbody(O, C1, O1) & inbody(O1, C2, O2)
    pats[37] = red & red.shift(1) & red.shift(2) & (C < C1) & (C1 < C2) & inbody(O, C1, O1) & inbody(O1, C2, O2)
    pats[40] = (C1 < O1) & (O < L1) & (C > (O1 + C1) / 2) & (C < O1); pats[43] = (C1 > O1) & (O > H1) & (C < (O1 + C1) / 2) & (C > O1)
    pats[46] = clv >= 0.9; pats[49] = clv <= 0.1; pats[52] = (H - L) >= 2 * atr.shift(1); pats[55] = (H - L) <= (H - L).rolling(7).min()
    for b, p in pats.items():
        X[f"PV-TF-{b:03d}"] = p; X[f"PV-TF-{b + 1:03d}"] = p & dec; X[f"PV-TF-{b + 2:03d}"] = p & adv
    for k, n in zip(range(58, 70, 3), (2, 3, 4, 5)):
        X[f"PV-TF-{k:03d}"] = red.rolling(n).sum() == n; X[f"PV-TF-{k + 1:03d}"] = grn.rolling(n).sum() == n; X[f"PV-TF-{k + 2:03d}"] = (C < C1).rolling(n).sum() == n
    for k, n in zip(range(70, 82, 3), (5, 10, 20, 50)):
        gr = grn.rolling(n).mean(); X[f"PV-TF-{k:03d}"] = gr >= 0.7; X[f"PV-TF-{k + 1:03d}"] = gr <= 0.3; X[f"PV-TF-{k + 2:03d}"] = gr - gr.shift(n) >= 0.3
    X["PV-TF-090"] = L > H1; X["PV-TF-091"] = H < L1
    for k, n in zip(range(92, 136, 6), (5, 10, 20, 50, 100, 200)):
        rr = C / C.shift(n) - 1
        if n in (5, 10): X[f"PV-TF-{k:03d}"] = rr >= 0.05; X[f"PV-TF-{k + 2:03d}"] = rr >= 0.1; X[f"PV-TF-{k + 4:03d}"] = rr <= rr.rolling(252).min(); X[f"PV-TF-{k + 5:03d}"] = rr >= rr.rolling(252).max()
    for k, n in zip(range(104, 136, 8), (20, 50, 100, 200)):
        rr = C / C.shift(n) - 1; X[f"PV-TF-{k:03d}"] = rr >= 0.05; X[f"PV-TF-{k + 2:03d}"] = rr >= 0.1; X[f"PV-TF-{k + 4:03d}"] = rr >= 0.2
        X[f"PV-TF-{k + 6:03d}"] = rr <= rr.rolling(252).min(); X[f"PV-TF-{k + 7:03d}"] = rr >= rr.rolling(252).max()
    for k, n in zip(range(136, 196, 10), (5, 10, 20, 50, 100, 200)):
        s = sma[n] if n in sma else C.rolling(n).mean(); d = C / s - 1
        X[f"PV-TF-{k:03d}"] = C > s; X[f"PV-TF-{k + 1:03d}"] = (C > s) & (C1 <= s.shift(1)); X[f"PV-TF-{k + 2:03d}"] = (C < s) & (C1 >= s.shift(1))
        X[f"PV-TF-{k + 3:03d}"] = s > s.shift(5); X[f"PV-TF-{k + 4:03d}"] = d <= -0.05; X[f"PV-TF-{k + 6:03d}"] = d <= -0.1; X[f"PV-TF-{k + 8:03d}"] = d <= -0.2
    for k, (a, b) in zip(range(196, 206, 2), ((5, 20), (10, 50), (20, 50), (50, 200), (20, 100))):
        x = sma[a] > sma[b]; X[f"PV-TF-{k:03d}"] = x & ~x.shift(1, fill_value=True); X[f"PV-TF-{k + 1:03d}"] = ~x & x.shift(1, fill_value=False)
    X["PV-TF-206"] = (sma[5] > sma[20]) & (sma[20] > sma[50]) & (sma[50] > sma[200])
    X["PV-TF-208"] = C.ewm(span=9, adjust=False).mean() > sma[9]; X["PV-TF-209"] = C.ewm(span=21, adjust=False).mean() > sma[21]
    for k, n in zip((210, 220, 230), (2, 5, 14)):
        r = rsi(C, n)
        for j, th in enumerate((5, 10, 20, 30)): X[f"PV-TF-{k + j:03d}"] = r < th
        for j, th in enumerate((70, 80, 90, 95)): X[f"PV-TF-{k + 4 + j:03d}"] = r > th
        X[f"PV-TF-{k + 8:03d}"] = r - r.shift(1) >= 10; X[f"PV-TF-{k + 9:03d}"] = (r > 30) & (r.shift(1) <= 30)
    r14 = rsi(C, 14)
    for k, n in zip((240, 242, 244), (5, 10, 20)):
        atlo = C <= C.rolling(n).min(); athi = C >= C.rolling(n).max()
        X[f"PV-TF-{k:03d}"] = atlo & (r14 > r14.where(atlo).shift(1).ffill()); X[f"PV-TF-{k + 1:03d}"] = athi & (r14 < r14.where(athi).shift(1).ffill())
    for k, n in ((246, 5), (249, 14)):
        K = 100 * (C - L.rolling(n).min()) / (H.rolling(n).max() - L.rolling(n).min()).replace(0, np.nan); D_ = K.rolling(3).mean()
        X[f"PV-TF-{k:03d}"] = K < 20; X[f"PV-TF-{k + 1:03d}"] = K > 80; X[f"PV-TF-{k + 2:03d}"] = (K > D_) & (K.shift(1) <= D_.shift(1)) & (K < 20)
    tp = (H + L + C) / 3
    for k, n in ((252, 14), (255, 20)):
        Wr = -100 * (H.rolling(n).max() - C) / (H.rolling(n).max() - L.rolling(n).min()).replace(0, np.nan)
        md = tp.rolling(n).apply(lambda w: np.abs(w - w.mean()).mean(), raw=True); cci = (tp - tp.rolling(n).mean()) / (0.015 * md.replace(0, np.nan))
        X[f"PV-TF-{k:03d}"] = Wr < -90; X[f"PV-TF-{k + 1:03d}"] = cci < -200; X[f"PV-TF-{k + 2:03d}"] = cci > 200
    m = C.ewm(span=12, adjust=False).mean() - C.ewm(span=26, adjust=False).mean(); sg = m.ewm(span=9, adjust=False).mean(); hs = m - sg
    X["PV-TF-258"] = (m > sg) & (m.shift(1) <= sg.shift(1)); X["PV-TF-259"] = (m < sg) & (m.shift(1) >= sg.shift(1))
    X["PV-TF-260"] = (hs > hs.shift(1)) & (hs.shift(1) > hs.shift(2)) & (hs.shift(2) > hs.shift(3)) & (hs < 0)
    nl20 = C <= C.rolling(20).min(); X["PV-TF-261"] = nl20 & (hs > hs.where(nl20).shift(1).ffill())
    for k, n, z in ((264, 20, 2), (267, 20, 2.5), (270, 10, 1.5), (273, 50, 2)):
        mid, sd = C.rolling(n).mean(), C.rolling(n).std(); lb = mid - z * sd
        X[f"PV-TF-{k:03d}"] = C < lb; X[f"PV-TF-{k + 1:03d}"] = C > mid + z * sd; X[f"PV-TF-{k + 2:03d}"] = (C1 < lb.shift(1)) & (C > lb)
    for k, n in ((276, 20), (277, 50)):
        bw = 4 * C.rolling(n).std() / C.rolling(n).mean(); X[f"PV-TF-{k:03d}"] = bw <= bw.rolling(126).min()
    s60 = ret.rolling(60).std()
    for k, n in ((278, 5), (280, 10), (282, 20)): X[f"PV-TF-{k:03d}"] = ret.rolling(n).std() >= 2 * s60
    for k, th in ((279, 0.05), (281, 0.1), (283, 0.2)): X[f"PV-TF-{k:03d}"] = atr / C >= th
    mid, sd = C.rolling(20).mean(), C.rolling(20).std(); X["PV-TF-284"] = (mid + 2 * sd < mid + 1.5 * atr) & (mid - 2 * sd > mid - 1.5 * atr)
    for k, n in ((285, 252), (294, 126), (303, 63), (312, 20)):
        mh, ml = H.rolling(n).max(), L.rolling(n).min()
        for j, p in enumerate((0.0, 0.02, 0.05)): X[f"PV-TF-{k + 2 * j:03d}"] = C >= (1 - p) * mh; X[f"PV-TF-{k + 2 * j + 1:03d}"] = C <= (1 + p) * ml
        X[f"PV-TF-{k + 6:03d}"] = H > H.shift(1).rolling(n).max(); X[f"PV-TF-{k + 7:03d}"] = L < L.shift(1).rolling(n).min()
        X[f"PV-TF-{k + 8:03d}"] = (C - ml) / (mh - ml).replace(0, np.nan) <= 0.1
    upv = V.where(C > C1, 0)
    for k, n in ((321, 5), (329, 10), (337, 20), (345, 50)):
        av = V.rolling(n).mean(); rv = V / av
        for j, th in enumerate((1.5, 2, 3, 5)): X[f"PV-TF-{k + j:03d}"] = rv >= th
        X[f"PV-TF-{k + 4:03d}"] = av / av.shift(n) >= 1.5; f = upv.rolling(n).sum() / V.rolling(n).sum().replace(0, np.nan)
        X[f"PV-TF-{k + 5:03d}"] = f >= 0.65; X[f"PV-TF-{k + 6:03d}"] = f <= 0.35
        X[f"PV-TF-{k + 7:03d}"] = (C / C.shift(n) > 1.05) & (V.rolling(5).mean() < (V.rolling(5).mean() if n == 5 else av) * 0.8) if n != 5 else (C / C.shift(5) > 1.05) & (V.rolling(5).mean() < V.rolling(5).mean().shift(5) * 0.8)
    X["PV-TF-353"] = V <= V.rolling(20).min(); X["PV-TF-354"] = (C * V).rolling(20).mean() >= 5e6
    a20 = V.rolling(20).mean(); X["PV-TF-355"] = (V >= 2 * a20) & red & (clv < 0.2); X["PV-TF-356"] = (V >= 2 * a20) & grn & (clv > 0.8)
    rmf = tp * V; pos = rmf.where(tp > tp.shift(1), 0); neg = rmf.where(tp < tp.shift(1), 0)
    mfm = ((C - L) - (H - C)) / rng; obv = (np.sign(C.diff()).fillna(0) * V).cumsum(); ad = (mfm.fillna(0) * V).cumsum()
    for k, n in ((357, 10), (363, 14), (369, 20)):
        mfi = 100 - 100 / (1 + pos.rolling(n).sum() / neg.rolling(n).sum().replace(0, np.nan)); cmf = (mfm * V).rolling(n).sum() / V.rolling(n).sum().replace(0, np.nan)
        X[f"PV-TF-{k:03d}"] = mfi < 20; X[f"PV-TF-{k + 1:03d}"] = mfi > 80; X[f"PV-TF-{k + 2:03d}"] = cmf > 0.1; X[f"PV-TF-{k + 3:03d}"] = cmf < -0.1
        X[f"PV-TF-{k + 4:03d}"] = obv > obv.shift(n); X[f"PV-TF-{k + 5:03d}"] = (C <= C.rolling(n).min()) & (obv > obv.rolling(n).min())
    X["PV-TF-375"] = ad > ad.shift(20)
    for base, b in ((376, spy), (386, sec), (396, iwm)):
        for j, n in enumerate((5, 20, 60, 126)): rr = rel(b, n); X[f"PV-TF-{base + 2 * j:03d}"] = rr >= 0.05; X[f"PV-TF-{base + 2 * j + 1:03d}"] = rr <= -0.05
        X[f"PV-TF-{base + 8:03d}"] = (b / b.shift(5) - 1 <= -0.02) & (C / C.shift(5) > 1); q = C / b; X[f"PV-TF-{base + 9:03d}"] = q >= q.rolling(252).max()
    cov = ret.rolling(60).cov(spy.pct_change()); X["PV-TF-410"] = cov / spy.pct_change().rolling(60).var() >= 1.5
    out = {}
    for k, v in X.items():
        v = pd.Series(v, index=C.index); na = v.isna()
        out[k] = np.where(na, 0, np.where(v.astype(bool), 2, 1)).astype(np.uint8)
    F = pd.DataFrame(out, index=C.index).shift(1).fillna(0).astype(np.uint8)  # PIT: D sees bars < D
    F.iloc[:252] = np.where(F.iloc[:252] > 0, F.iloc[:252], 0); return F
G = {}; REF = {}
def one(tk):
    g, sec = G[tk]; R = dict(REF); R["SEC"] = REF.get(sec); return tk, feats(g, R)
if __name__ == "__main__":
    assert sha(PX) == PX_SHA
    cells = pd.read_parquet("/workspace/tmp_utv2/U.parquet", columns=["ticker", "date"]); cells["row"] = np.arange(len(cells))
    px = pq.read_table(PX, columns=["ticker", "date", "open", "high", "low", "close", "volume"], filters=[("date", "<=", HI)]).to_pandas()
    assert px.date.max() <= HI; px["ticker"] = px.ticker.astype(str); px = px.drop_duplicates(["ticker", "date"]).sort_values(["ticker", "date"])
    for e in ["SPY", "IWM"] + list(SPDR.values()): REF[e] = px[px.ticker == e].set_index("date").close
    fv = pd.read_csv(FV, usecols=["Ticker", "Sector", "Industry"]).drop_duplicates("Ticker").set_index("Ticker")
    # cross-sectional rows on the whole file: ret20/60 decile of same-day universe; Finviz industry performance (current map)
    c = px.pivot(index="date", columns="ticker", values="close"); XS = {}
    for k, n in ((406, 20), (408, 60)):
        r = c / c.shift(n) - 1; pr = r.rank(axis=1, pct=True); XS[f"PV-TF-{k:03d}"] = pr >= 0.9; XS[f"PV-TF-{k + 1:03d}"] = pr <= 0.1; XS[f"PV-TF-{k:03d}_na"] = r.isna()
    ind = fv.Industry.reindex(c.columns)
    def indperf(n):
        r = (c / c.shift(n) - 1).T.groupby(ind).median().T; return r
    ip126, ip5, ip21 = indperf(126), indperf(5), indperf(21)
    def tomap(df, q, hi=True):
        pr = df.rank(axis=1, pct=True); m = (pr >= q) if hi else (pr <= q); return m.T.reindex(ind.values).set_axis(c.columns).T
    XS["SEC-JA-028"] = tomap(ip126, 0.9); XS["SEC-JA-029"] = tomap(ip5, 0.9)
    r21 = c / c.shift(21) - 1; wr = r21.T.groupby(ind).rank(pct=True).T
    XS["SEC-JA-030"] = tomap(ip21, 0.8) & (wr <= 0.2); XS["SEC-JA-030_na"] = r21.isna()
    del c
    for tk, g in px[px.ticker.isin(set(cells.ticker))].groupby("ticker"):
        G[tk] = (g.drop(columns="ticker"), SPDR.get(fv.Sector.get(tk), None))
    del px
    with Pool(3) as p: res = dict(p.map(one, sorted(G), chunksize=10))
    ids = list(next(iter(res.values())).columns) + ["PV-TF-406", "PV-TF-407", "PV-TF-408", "PV-TF-409", "SEC-JA-028", "SEC-JA-029", "SEC-JA-030"]
    import pickle
    L = pd.read_csv("../untested_v1/untested_results_v1.csv"); need = set(L[L.status.str.startswith("TOO")].col) & set(ids)
    YES = {c: [] for c in need}; ANS = {c: 0 for c in need}; nb = len(ids) - 7
    for tk, ix in cells.groupby("ticker").indices.items():
        if tk not in res: continue
        F = res[tk].reindex(cells.date.values[ix]).fillna(0)
        for c in need:
            if c in F.columns: v = F[c].values.astype(np.uint8); ANS[c] += int((v > 0).sum()); YES[c].append(ix[v == 2])
    dd = cells.date.values; tt = cells.ticker.values
    for k in ids[nb:]:
        if k not in need: continue
        T = XS[k].shift(1); v = T.stack(future_stack=True).reindex(pd.MultiIndex.from_arrays([dd, tt])).values
        a = np.where(pd.isna(v), 0, np.where(v == True, 2, 1)); ANS[k] = int((a > 0).sum()); YES[k] = [np.flatnonzero(a == 2)]
    out = {c: (np.concatenate(v) if v else np.array([], np.int64)) for c, v in YES.items()}
    pickle.dump(dict(yes=out, ans=ANS), open("/workspace/tmp_utv2/answers_mpv.pkl", "wb")); print("mpv cols", len(out))

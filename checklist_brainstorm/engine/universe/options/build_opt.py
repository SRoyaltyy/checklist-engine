#!/usr/bin/env python3
"""Grok options (DoltHub volatility_history) YES/NO engine, 2020-2024 ONLY. survivor_only=true.
Point-in-time: a DoltHub row dated D (end-of-day, committed ~02:35 ET next day) is usable for the 09:25 ET decision of the
first trading session strictly after D. For session S we take the latest D < S per ticker.
lag = sessions between S and the first session after D. lag=0 -> fresh (stale=0); lag 1..2 -> carried forward, stale=1;
lag>2 or no reading -> NOT_READY for every question (Manager Bot rule 2026-10-22: carry max 2 trading days).
In 2020..~Oct-2024 DoltHub is Mon/Wed/Fri only, so Wed and Fri sessions are typically stale=1.
Codes 0=NR 1=NO 2=YES packed 2-bit 4/byte along ids (nb_year.pack). Universe/sector files = New Bot 2024 survivor set."""
import sys, json, glob, re, os
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; U = HERE.parent; CH = U / "chunks"
sys.path.insert(0, str(U)); from nb_year import pack, sessions_all
IDS = ["GK-OPX-IVR-HI", "GK-OPX-IVR-LO", "GK-OPX-IVHV-HI", "GK-OPX-IVHV-LO", "GK-OPX-IVCHG-UP", "GK-OPX-IVCHG-DN"]
DEF = {"GK-OPX-IVR-HI": "IV rank (iv_current within its own DoltHub 1y iv_year_low..high) >= 0.80",
       "GK-OPX-IVR-LO": "IV rank <= 0.20", "GK-OPX-IVHV-HI": "iv_current / hv_current > 1.3",
       "GK-OPX-IVHV-LO": "iv_current / hv_current < 0.8",
       "GK-OPX-IVCHG-UP": "iv_current / iv_current of the ticker's prior DoltHub reading (<=7 cal days earlier) - 1 >= +0.15",
       "GK-OPX-IVCHG-DN": "same change <= -0.15"}
def secmap():
    m = {}
    for f in glob.glob(str(CH / "2024__NB__*.json")):
        sec = Path(f).name[len("2024__NB__"):-5]
        for t in pd.read_parquet(f.replace(".json", ".parquet"), columns=["ticker"]).ticker.unique(): m[t] = sec
    return pd.Series(m)
def run(y):
    assert 2020 <= y <= 2024
    v = pd.read_parquet(HERE / f"raw/vh_{y}.parquet")
    if y > 2020: v = pd.concat([pd.read_parquet(HERE / f"raw/vh_{y-1}.parquet"), v])  # for prior reading + carry into Jan
    v["ticker"] = v.act_symbol.str.replace(".", "-", regex=False).str.replace("/", "-", regex=False)
    v["D"] = pd.to_datetime(v.date); v = v.sort_values(["ticker", "D"])
    pv = v.groupby("ticker").iv_current.shift(); pd_ = v.groupby("ticker").D.shift()
    chg = np.where((v.D - pd_).dt.days <= 7, v.iv_current / pv - 1, np.nan)
    rng = v.iv_year_high - v.iv_year_low; ivr = np.where(rng > 0, (v.iv_current - v.iv_year_low) / rng, np.nan)
    ivhv = np.where(v.hv_current > 0, v.iv_current / v.hv_current, np.nan)
    feat = {"GK-OPX-IVR-HI": (ivr, ivr >= .8), "GK-OPX-IVR-LO": (ivr, ivr <= .2), "GK-OPX-IVHV-HI": (ivhv, ivhv > 1.3),
            "GK-OPX-IVHV-LO": (ivhv, ivhv < .8), "GK-OPX-IVCHG-UP": (chg, chg >= .15), "GK-OPX-IVCHG-DN": (chg, chg <= -.15)}
    with np.errstate(invalid="ignore"):
        codes = np.stack([np.where(np.isfinite(np.asarray(a, float)), np.where(b, 2, 1), 0) for a, b in feat.values()], 1).astype(np.uint8)
    sess = sessions_all().index.values
    sess = sess[(sess >= np.datetime64(f"{y-1}-11-01")) & (sess <= np.datetime64(f"{y}-12-31"))]
    ys = sess[sess >= np.datetime64(f"{y}-01-01")]
    usable = np.searchsorted(sess, v.D.values, side="right")  # index of first session > D
    sm = secmap(); tick = sorted(sm.index); ti = {t: i for i, t in enumerate(tick)}
    ok = v.ticker.isin(ti).values
    C = np.zeros((len(tick), len(ys), len(IDS)), np.uint8); ST = np.zeros((len(tick), len(ys)), np.uint8)
    LAG = np.full((len(tick), len(ys)), 99, np.int16); y0 = np.searchsorted(sess, ys[0])
    tix = v.ticker.map(ti).fillna(-1).astype(int).values
    # rows are sorted by ticker,D: later rows overwrite earlier for same usable session; then forward fill up to 2
    for r in np.nonzero(ok & (usable < len(sess)))[0]:
        k = usable[r] - y0
        for lag in range(3):
            kk = k + lag
            if 0 <= kk < len(ys) and lag <= LAG[tix[r], kk]:
                LAG[int(tix[r]), kk] = lag; C[int(tix[r]), kk] = codes[r]; ST[int(tix[r]), kk] = 1 if lag else 0
    dstr = ys.astype("datetime64[D]").astype(str); cov = {}
    for sec in sorted(sm.unique()):
        tk = [t for t in tick if sm[t] == sec]; ix = [ti[t] for t in tk]
        CC = C[ix].reshape(-1, len(IDS)); P = pack(CC)
        df = pd.DataFrame({"ticker": np.repeat(tk, len(ys)), "date": np.tile(dstr, len(tk)), "packed": [bytes(x) for x in P],
                           "stale": ST[ix].reshape(-1), "lag": np.minimum(LAG[ix].reshape(-1), 99).astype(np.int8)})
        fn = CH / f"{y}__OPT__{sec}.parquet"; df.to_parquet(fn, index=False)
        json.dump(dict(year=y, sector=sec, ids=IDS, defs=DEF, n_ids=len(IDS), survivor_only=True,
                       survivor_note="DoltHub repo created 2021-04-20; rows dated before are a one-day backfill (which names included is not point-in-time)",
                       source="dolthub post-no-preference/options volatility_history", pit_rule=__doc__,
                       layout="rows ticker-major then date; packed 2-bit 0=NR 1=NO 2=YES; stale=1 carried reading (lag 1-2 sessions); lag=99 none",
                       n_tickers=len(tk), n_cells=len(df)), open(str(fn).replace(".parquet", ".json"), "w"), indent=1)
        cov[sec] = int((CC[:, 0] > 0).sum())
    rd = (C > 0).any(2); out = dict(year=y, sessions=len(ys), universe=len(tick),
        tickers_with_any=int(rd.any(1).sum()), cells_ready=int(rd.sum()), cells_fresh=int((rd & (ST == 0)).sum()),
        cells_stale=int((rd & (ST == 1)).sum()), per_id_yes_ready={i: [int((C[..., j] == 2).sum()), int((C[..., j] > 0).sum())] for j, i in enumerate(IDS)},
        dolthub_dates=int(v[v.D.dt.year == y].D.nunique()), dolthub_symbols=int(v[v.D.dt.year == y].act_symbol.nunique()),
        symbols_unmatched=int(v[(v.D.dt.year == y) & ~ok].act_symbol.nunique()))
    json.dump(out, open(HERE / f"coverage_{y}.json", "w"), indent=1); print(json.dumps(out))
if __name__ == "__main__": run(int(sys.argv[1]))

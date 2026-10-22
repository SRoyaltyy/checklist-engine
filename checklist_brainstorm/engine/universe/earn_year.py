#!/usr/bin/env python3
"""EARN add-on (New Bot): Nasdaq earnings-calendar answers, 2020-2024 ONLY.
See data/earnings/COVERAGE.md for PIT. Codes 0=NR 1=NO 2=YES via nb_year.pack."""
import sys, json, re, time, argparse, gc
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent; ENG = HERE.parent; sys.path.insert(0, str(HERE))
import nb_year as NB

EARN = Path("/workspace/checklist_brainstorm/data/earnings")
TAGS = ENG / "out/tags/new-bot_earn_tags.csv"
IDS = list(pd.read_csv(TAGS).row_id)
MEET_PP = 0.5
MEET_ABS = 0.005

def norm(s):
    return s.astype(str).str.strip().str.upper().str.replace(r"[./ ]", "-", regex=True)

def load_cal(year, tickers):
    parts = []
    for y in range(max(2020, year - 1), year + 1):
        fn = EARN / f"nasdaq_calendar_{y}.parquet"
        if not fn.exists(): continue
        x = pd.read_parquet(fn); x["ticker"] = norm(x.symbol)
        parts.append(x[x.ticker.isin(tickers)])
    if not parts:
        return pd.DataFrame(columns=["ticker", "report_date", "time_label", "surprise_pct_fill", "eps_delta"])
    x = pd.concat(parts, ignore_index=True)
    x["report_date"] = x.report_date.astype("datetime64[ns]")
    return x.sort_values(["ticker", "report_date"]).drop_duplicates(["ticker", "report_date"], keep="last")[
        ["ticker", "report_date", "time_label", "surprise_pct_fill", "eps_actual", "eps_forecast", "eps_delta"]
    ]

def run_year(year, block=1000, only=None):
    assert 2020 <= year <= 2024
    t0 = time.time(); col = {r: j for j, r in enumerate(IDS)}
    spy = NB.sessions_all(); sess = spy.index.values.astype("datetime64[ns]")
    ys = sess[(sess >= np.datetime64(f"{year}-01-01")) & (sess <= np.datetime64(f"{year}-12-31"))]
    last = pd.read_parquet(NB.CACHE / "last.parquet").date
    funds = set(pd.read_csv(NB.CACHE / "fund_exclusion_tickers.csv").ticker)
    tickers = sorted(only or [t for t in last.index if t not in funds])
    cur = pd.read_csv(NB.SECT, usecols=["Ticker", "Sector"]).set_index("Ticker")
    sec_of = pd.Series(tickers, index=tickers).map(cur.Sector).fillna("Unknown")
    nD = len(ys); ys_list = [pd.Timestamp(d) for d in ys]
    # session rank for window math
    sess_ts = [pd.Timestamp(d) for d in sess]
    sess_rank = {d: i for i, d in enumerate(sess_ts)}

    allC = {}
    for i0 in range(0, len(tickers), block):
        bt = tickers[i0:i0 + block]
        cal = load_cal(year, set(bt))
        by = {t: g for t, g in cal.groupby("ticker", sort=False)} if len(cal) else {}
        C = np.ones((len(bt) * nD, len(IDS)), np.uint8)  # default NO

        for ti, t in enumerate(bt):
            base = ti * nD
            sub = by.get(t)
            # stale -> NR whole year tail
            lastd = last.get(t, pd.NaT)
            stale_from = None
            if pd.notna(lastd) and np.datetime64(lastd) < NB.STALE_CUT:
                stale_from = pd.Timestamp(lastd)

            if sub is None or sub.empty:
                if stale_from is not None:
                    for di, D in enumerate(ys_list):
                        if D > stale_from:
                            C[base + di, :] = 0
                continue

            rd = [pd.Timestamp(x) for x in sub.report_date.values]
            tl = sub.time_label.astype(str).tolist()
            sp = sub.surprise_pct_fill.astype("float64").to_numpy()
            ed = sub.eps_delta.astype("float64").to_numpy()
            rd_set = set(rd)

            # usable session per report
            usable = []
            for k, rdk in enumerate(rd):
                if tl[k] == "BMO":
                    # session on report_date if trading day else next
                    if rdk in sess_rank:
                        usable.append(rdk)
                    else:
                        j = int(np.searchsorted(sess, np.datetime64(rdk), side="left"))
                        usable.append(pd.Timestamp(sess[j]) if j < len(sess) else pd.NaT)
                else:
                    j = int(np.searchsorted(sess, np.datetime64(rdk), side="right"))
                    usable.append(pd.Timestamp(sess[j]) if j < len(sess) else pd.NaT)
            usable_map = {u: k for k, u in enumerate(usable) if pd.notna(u)}

            # precompute report session ranks (session on or after report_date)
            rep_rank = []
            for rdk in rd:
                if rdk in sess_rank:
                    rep_rank.append(sess_rank[rdk])
                else:
                    j = int(np.searchsorted(sess, np.datetime64(rdk), side="left"))
                    rep_rank.append(j if j < len(sess) else -1)

            for di, D in enumerate(ys_list):
                if stale_from is not None and D > stale_from:
                    C[base + di, :] = 0
                    continue
                jD = sess_rank[D]
                # TODAY-BMOUNK
                if D in rd_set:
                    k = rd.index(D)
                    if tl[k] in ("BMO", "unknown"):
                        C[base + di, col["nbx-EARN-TODAY-BMOUNK"]] = 2
                # prior session
                prev = sess_ts[jD - 1] if jD > 0 else None
                if prev is not None and prev in rd_set:
                    k = rd.index(prev)
                    C[base + di, col["nbx-EARN-POST1"]] = 2
                    if tl[k] == "AMC":
                        C[base + di, col["nbx-EARN-AMC-YDAY"]] = 2
                    elif tl[k] == "unknown":
                        C[base + di, col["nbx-EARN-AMC-YDAY"]] = 0
                    # else BMO prior -> AMC-YDAY stays NO
                # POST1 for non-session report dates whose next session is D
                for k, rdk in enumerate(rd):
                    if rdk in sess_rank:
                        continue  # handled via prior==report when report is a session
                    jn = int(np.searchsorted(sess, np.datetime64(rdk), side="right"))
                    if jn < len(sess) and pd.Timestamp(sess[jn]) == D:
                        C[base + di, col["nbx-EARN-POST1"]] = 2
                        if tl[k] == "AMC":
                            C[base + di, col["nbx-EARN-AMC-YDAY"]] = 2
                        elif tl[k] == "unknown":
                            C[base + di, col["nbx-EARN-AMC-YDAY"]] = 0
                # NEXT5: report session rank in (jD+1 .. jD+5)
                for rr in rep_rank:
                    if rr < 0: continue
                    if jD + 1 <= rr <= jD + 5:
                        C[base + di, col["nbx-EARN-NEXT5"]] = 2
                    if jD - 4 <= rr <= jD:
                        C[base + di, col["nbx-EARN-LAST5"]] = 2
                # surprise on usable session only
                if D in usable_map:
                    k = usable_map[D]
                    s, delta = sp[k], ed[k]
                    if np.isnan(s) and np.isnan(delta):
                        for rid in ("nbx-EARN-BEAT", "nbx-EARN-MISS", "nbx-EARN-MEET", "nbx-EARN-BEAT-BIG", "nbx-EARN-MISS-BIG"):
                            C[base + di, col[rid]] = 0
                    else:
                        is_meet = (not np.isnan(s) and abs(s) < MEET_PP) or (not np.isnan(delta) and abs(delta) < MEET_ABS)
                        if is_meet:
                            C[base + di, col["nbx-EARN-MEET"]] = 2
                            # beat/miss already NO
                        elif not np.isnan(s):
                            if s > 0:
                                C[base + di, col["nbx-EARN-BEAT"]] = 2
                                if s >= 5: C[base + di, col["nbx-EARN-BEAT-BIG"]] = 2
                            else:
                                C[base + di, col["nbx-EARN-MISS"]] = 2
                                if s <= -5: C[base + di, col["nbx-EARN-MISS-BIG"]] = 2
                        else:
                            if delta > 0: C[base + di, col["nbx-EARN-BEAT"]] = 2
                            elif delta < 0: C[base + di, col["nbx-EARN-MISS"]] = 2
                # else surprise rows stay NO

        P = NB.pack(C)
        for j, t in enumerate(bt):
            allC[t] = P[j * nD:(j + 1) * nD]
        del C, P, cal, by; gc.collect()
        print(f"  block {i0 // block}/{len(tickers)//block} t={time.time()-t0:.0f}s", flush=True)
    return dict(ids=IDS, ys=ys, tickers=tickers, sec_of=sec_of, allC=allC, secs=time.time() - t0)

def write_year(year, R):
    ids, ys, sec_of = R["ids"], R["ys"], R["sec_of"]
    sha = open(str(TAGS) + ".sha256").read().split()[0]
    jobs = []
    for sec0 in sorted(sec_of.unique()):
        tk0 = [t for t in R["tickers"] if sec_of[t] == sec0]
        jobs += [(sec0, tk0)] if len(tk0) <= 2000 else [(f"{sec0}_part{k}", tk0[i:i+2000]) for k, i in enumerate(range(0, len(tk0), 2000))]
    cov = np.zeros((len(ids), 3), np.int64)
    dstr = ys.astype("datetime64[D]").astype(str)
    for sec, tk in jobs:
        P = np.concatenate([R["allC"][t] for t in tk])
        U = NB.unpack(P, len(ids))
        for k in range(3): cov[:, k] += (U == k).sum(0)
        df = pd.DataFrame({"ticker": np.repeat(tk, len(ys)), "date": np.tile(dstr, len(tk)), "packed": [bytes(x) for x in P]})
        fn = NB.CHUNKS / f"{year}__EARN__{re.sub(r'[^A-Za-z0-9]', '_', sec)}.parquet"
        df.to_parquet(fn, index=False)
        json.dump(dict(
            year=year, sector=sec,
            layout="rows ticker-major then date; packed = 2-bit codes 0=NR 1=NO 2=YES, 4/byte along ids (nb_year.pack)",
            addon="EARN: Nasdaq earnings calendar (New Bot rows nbx-EARN-*)",
            survivor_only=True, sector_map="current_backfilled",
            source="data/earnings/nasdaq_calendar_{y}.parquet",
            point_in_time="BMO: surprise usable on report_date session (else next). AMC/unknown: surprise usable next session after report_date. TODAY-BMOUNK: report_date==D & time in {BMO,unknown}. AMC-YDAY NR when prior print time unknown. Guide held/raised/cut UNAVAILABLE.",
            meet_rule=f"|surprise_pct|<{MEET_PP} pp OR |eps-fc|<{MEET_ABS}; meet excludes beat/miss",
            earn_tags_sha256=sha, n_ids=len(ids), ids=ids, n_tickers=len(tk), n_cells=len(df),
        ), open(str(fn).replace(".parquet", ".json"), "w"), indent=1)
    pd.DataFrame(cov, columns=["nr", "no", "yes"], index=ids).to_csv(NB.CHUNKS / f"{year}__EARN_coverage.csv")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("year", type=int); ap.add_argument("--only")
    a = ap.parse_args()
    R = run_year(a.year, only=a.only.split(",") if a.only else None)
    if not a.only: write_year(a.year, R)
    print(f"YEAR {a.year} secs={R['secs']:.0f}", flush=True)

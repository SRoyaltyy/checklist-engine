#!/usr/bin/env python3
"""Spot-check >=10 EARN cells vs raw Nasdaq calendar parquet."""
import json, glob, random, sys
import numpy as np, pandas as pd
sys.path.insert(0, "."); import nb_year as NB
EARN = "/workspace/checklist_brainstorm/data/earnings/"
random.seed(42); y = 2024
fs = sorted(glob.glob(f"chunks/{y}__EARN__*.parquet"))
ids = json.load(open(fs[0].replace(".parquet", ".json")))["ids"]
cal = pd.concat([pd.read_parquet(f"{EARN}nasdaq_calendar_{k}.parquet") for k in (2023, 2024)])
cal["t"] = cal.symbol.astype(str).str.upper().str.replace(r"[./ ]", "-", regex=True)
cal["report_date"] = cal.report_date.astype("datetime64[ns]")
sess = NB.sessions_all().index.astype("datetime64[ns]")
sess_ts = [pd.Timestamp(d) for d in sess]
want = ["nbx-EARN-TODAY-BMOUNK", "nbx-EARN-POST1", "nbx-EARN-NEXT5", "nbx-EARN-LAST5",
        "nbx-EARN-BEAT", "nbx-EARN-MISS", "nbx-EARN-MEET", "nbx-EARN-AMC-YDAY",
        "nbx-EARN-BEAT-BIG", "nbx-EARN-MISS-BIG", "nbx-EARN-TODAY-BMOUNK", "nbx-EARN-POST1"]

def next_sess(rd):
    j = int(np.searchsorted(sess, np.datetime64(rd), side="right"))
    return pd.Timestamp(sess[j]) if j < len(sess) else None

rows = []
for rid in want:
    f = random.choice(fs); df = pd.read_parquet(f); j = ids.index(rid)
    picked = None
    for tr in range(5000):
        r = df.iloc[random.randrange(len(df))]
        c = int(NB.unpack(np.frombuffer(r.packed, np.uint8)[None], len(ids))[0][j])
        if c == 2 or (c > 0 and tr > 800):
            picked = (r, c); break
    if picked is None: continue
    r, c = picked
    D = pd.Timestamp(r.date); t = r.ticker
    sub = cal[cal.t == t]
    exp = None; note = ""
    if rid == "nbx-EARN-TODAY-BMOUNK":
        hit = sub[(sub.report_date == D) & (sub.time_label.isin(["BMO", "unknown"]))]
        exp = len(hit) > 0; note = f"reports_on_D={len(sub[sub.report_date==D])}"
    elif rid == "nbx-EARN-POST1":
        # prior session report OR non-session report with next==D
        jD = sess_ts.index(D); prev = sess_ts[jD - 1] if jD > 0 else None
        hit = False
        if prev is not None and len(sub[sub.report_date == prev]): hit = True
        for _, row in sub.iterrows():
            if row.report_date in sess_ts: continue
            ns = next_sess(row.report_date)
            if ns == D: hit = True
        exp = hit; note = f"prev={prev.date() if prev is not None else None}"
    elif rid == "nbx-EARN-AMC-YDAY":
        jD = sess_ts.index(D); prev = sess_ts[jD - 1] if jD > 0 else None
        if prev is None: exp = False
        else:
            hit = sub[sub.report_date == prev]
            if not len(hit): exp = False
            elif hit.iloc[0].time_label == "AMC": exp = True
            elif hit.iloc[0].time_label == "unknown": exp = None  # NR
            else: exp = False
        note = f"prev={prev}"
    elif rid in ("nbx-EARN-NEXT5", "nbx-EARN-LAST5"):
        jD = sess_ts.index(D)
        if rid.endswith("NEXT5"):
            window = set(sess_ts[jD + 1:jD + 6]); exp = any(pd.Timestamp(x) in window for x in sub.report_date if pd.Timestamp(x) in sess_ts)
            # also non-session reports whose on-or-after session rank in window
            for _, row in sub.iterrows():
                rd = pd.Timestamp(row.report_date)
                if rd in sess_ts: rr = sess_ts.index(rd)
                else:
                    jj = int(np.searchsorted(sess, np.datetime64(rd), side="left")); rr = jj
                if jD + 1 <= rr <= jD + 5: exp = True
        else:
            exp = False
            for _, row in sub.iterrows():
                rd = pd.Timestamp(row.report_date)
                if rd in sess_ts: rr = sess_ts.index(rd)
                else:
                    jj = int(np.searchsorted(sess, np.datetime64(rd), side="left")); rr = jj
                if jD - 4 <= rr <= jD: exp = True
        note = "window"
    else:
        # surprise rows
        # find report whose usable == D
        hit = None
        for _, row in sub.iterrows():
            rd = pd.Timestamp(row.report_date)
            if row.time_label == "BMO":
                u = rd if rd in sess_ts else next_sess(rd - pd.Timedelta(days=1))  # rough
                if rd in sess_ts: u = rd
                else:
                    jj = int(np.searchsorted(sess, np.datetime64(rd), side="left"))
                    u = pd.Timestamp(sess[jj]) if jj < len(sess) else None
            else:
                u = next_sess(rd)
            if u == D: hit = row; break
        if hit is None:
            exp = False; note = "no usable"
        else:
            s = hit.surprise_pct_fill; delta = hit.eps_delta
            if pd.isna(s) and pd.isna(delta):
                exp = None; note = "NR no surprise"
            else:
                meet = (pd.notna(s) and abs(s) < 0.5) or (pd.notna(delta) and abs(delta) < 0.005)
                if rid == "nbx-EARN-MEET": exp = bool(meet)
                elif rid == "nbx-EARN-BEAT": exp = (not meet) and pd.notna(s) and s > 0
                elif rid == "nbx-EARN-MISS": exp = (not meet) and pd.notna(s) and s < 0
                elif rid == "nbx-EARN-BEAT-BIG": exp = (not meet) and pd.notna(s) and s >= 5
                elif rid == "nbx-EARN-MISS-BIG": exp = (not meet) and pd.notna(s) and s <= -5
                note = f"s={s}"
    eng = {0: "NR", 1: "NO", 2: "YES"}[c]
    raw = "NR" if exp is None else ("YES" if exp else "NO")
    rows.append(dict(ticker=t, date=str(D.date()), row=rid, engine=eng, raw=raw, note=note))

o = pd.DataFrame(rows); o["match"] = o.engine == o.raw
print(o.to_string()); print("MATCH", o.match.sum(), "/", len(o))
o.to_csv(f"chunks/{y}__EARN_spotcheck.csv", index=False)

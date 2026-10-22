#!/usr/bin/env python3
"""Pre-burn train panel: owners that do NOT need Theme Radar Finviz nightly snapshots.

Default: james + grok-bot on 20 tickers × ~60 sessions in 2024 (train smoke),
labels from updown/bars_all.parquet. Jul–Oct 2026 excluded.

Usage:
  python3 build_preburn_matrix.py --workers 2 --limit 40   # small kickoff
  python3 build_preburn_matrix.py --workers 2             # full 20×60
"""
from __future__ import annotations
import argparse, csv, importlib.util, json, os, time, traceback
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import datetime as dt

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SHEET = ROOT / "merged_draft_v8.2.csv"
OUT = HERE / "out" / "pilot_matrix" / "preburn"
CELLS = OUT / "cells"
READERS_WANTED = {"james", "grok"}  # stems in readers/
HOL = {
    "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-29", "2024-05-27",
    "2024-06-19", "2024-07-04", "2024-09-02", "2024-11-28", "2024-12-25",
    "2025-01-01", "2025-01-20", "2025-02-17", "2025-04-18", "2025-05-26",
    "2025-06-19", "2025-07-04", "2025-09-01", "2025-11-27", "2025-12-25",
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25",
    "2026-06-19", "2026-07-03",
}

def is_td(d: dt.date) -> bool:
    return d.weekday() < 5 and d.isoformat() not in HOL

def load_sheet_owners():
    with open(SHEET, newline="") as f:
        rows = list(csv.DictReader(f))
    owner = {r["id"].strip(): (r.get("merge_owner") or "").strip() for r in rows}
    # only keep james + grok-bot rows in output join (others -> still NOT_READY no_reader if we want full sheet)
    return owner

def load_readers():
    out = []
    for stem in READERS_WANTED:
        p = HERE / "readers" / f"{stem}.py"
        spec = importlib.util.spec_from_file_location(stem, p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        out.append((stem, m))
    return out

def cell_path(t, d):
    return CELLS / f"{t}_{d}.csv"

def run_cell(owner, readers, ticker, date, keep_owners):
    claims = defaultdict(list)
    for name, m in readers:
        try:
            res = list(m.answer(ticker, date) or [])
        except Exception as e:
            print(f"ERR {name} {ticker} {date}: {e}", flush=True)
            continue
        for r in res:
            rid = str(r.get("row_id", "")).strip()
            if rid not in owner:
                continue
            if owner[rid] not in keep_owners:
                continue
            ans = r.get("answer")
            why = str(r.get("reason") or "").strip()
            if ans not in {"YES", "NO", "NOT_READY"}:
                ans, why = "NOT_READY", f"contract_error:{ans!r}"
            elif ans == "NOT_READY" and not why:
                why = "contract_error:no_reason"
            claims[rid].append((ans, why, str(r.get("data_as_of") or "")))
    op = cell_path(ticker, date)
    op.parent.mkdir(parents=True, exist_ok=True)
    tmp = op.with_suffix(".tmp")
    cnt = Counter()
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["row_id", "owner", "ticker", "date", "answer", "reason", "data_as_of"])
        for rid in sorted(claims):
            ans, why, asof = claims[rid][0]
            if len(claims[rid]) > 1:
                ans, why, asof = "NOT_READY", "conflict", ""
            cnt[ans] += 1
            w.writerow([rid, owner[rid], ticker, date, ans, why, asof])
    tmp.replace(op)
    return cnt

def _worker(pairs, keep_owners):
    owner = load_sheet_owners()
    readers = load_readers()
    out = []
    for t, d in pairs:
        op = cell_path(t, d)
        if op.exists() and op.stat().st_size > 500:
            out.append((t, d, "skip"))
            continue
        t0 = time.time()
        try:
            cnt = run_cell(owner, readers, t, d, keep_owners)
            print(f"OK {t} {d} {dict(cnt)} {time.time()-t0:.1f}s", flush=True)
            out.append((t, d, "ok"))
        except Exception as e:
            traceback.print_exc()
            out.append((t, d, f"fail:{e}"))
    return out

def build_labels(tickers, dates):
    bars = pd.read_parquet("/workspace/updown/bars_all.parquet", columns=["date", "ticker", "open", "close"])
    bars["date"] = pd.to_datetime(bars["date"]).dt.strftime("%Y-%m-%d")
    bars = bars[bars["ticker"].isin(tickers)].copy()
    sessions = sorted(bars["date"].unique())
    nxt = {sessions[i]: sessions[i + 1] for i in range(len(sessions) - 1)}
    px = bars.set_index(["ticker", "date"])
    rows = []
    for t in tickers:
        for d in dates:
            dp1 = nxt.get(d)
            if not dp1:
                continue
            try:
                oD = float(px.loc[(t, d), "open"])
                cD = float(px.loc[(t, d), "close"])
                oP = float(px.loc[(t, dp1), "open"])
            except Exception:
                continue
            if oD == 0:
                continue
            rows.append(
                {
                    "ticker": t,
                    "date": d,
                    "ret_open_next_open": oP / oD - 1.0,
                    "ret_open_close": cD / oD - 1.0,
                    "open_D": oD,
                    "open_Dp1": oP,
                    "close_D": cD,
                }
            )
    lab = pd.DataFrame(rows)
    lab.to_parquet(OUT / "labels.parquet", index=False)
    return lab

def pick_dates(n=60, start="2024-01-02", end="2024-12-31"):
    bars = pd.read_parquet("/workspace/updown/bars_all.parquet", columns=["date"])
    sessions = sorted(pd.to_datetime(bars["date"]).dt.strftime("%Y-%m-%d").unique())
    cand = [d for d in sessions if start <= d <= end]
    # need next session exists and next < Jul 2026 burn for safety on confirm; for 2024 train OK
    out = []
    for i, d in enumerate(cand):
        if i + 1 < len(cand) or (i + 1 < len(sessions) and sessions[sessions.index(d) + 1]):
            out.append(d)
    # evenly sample n dates
    if len(out) <= n:
        return out
    step = len(out) / n
    return [out[int(i * step)] for i in range(n)]

def aggregate(tickers=None, dates=None):
    cells = sorted(CELLS.glob("*.csv"))
    if not cells:
        print("no cells"); return
    frames = [pd.read_csv(p, dtype=str) for p in cells]
    long = pd.concat(frames, ignore_index=True)
    long.to_parquet(OUT / "answers_long_preburn_james_grok.parquet", index=False)
    lab = pd.read_parquet(OUT / "labels.parquet")
    yn = long[long["answer"].isin(["YES", "NO"])].merge(lab, on=["ticker", "date"], how="inner")
    yn.to_parquet(OUT / "panel_yesno_preburn_james_grok.parquet", index=False)
    cnt = Counter(long["answer"])
    tickers = sorted(long["ticker"].unique().tolist())
    dates = sorted(long["date"].unique().tolist())
    man = {
        "tag": "preburn_james_grok",
        "window_kind": "preburn_train",
        "promote_eligible": True,
        "note": "Pre-burn (before Jul 2026). James+Grok only. Theme-radar/new-bot excluded (need Finviz snaps).",
        "sheet": str(SHEET),
        "sheet_row_count": sum(1 for _ in open(SHEET)) - 1,
        "n_tickers": len(tickers),
        "n_dates": len(dates),
        "n_cells_present": len(cells),
        "n_answer_cells": int(len(long)),
        "n_yes": int(cnt.get("YES", 0)),
        "n_no": int(cnt.get("NO", 0)),
        "n_not_ready": int(cnt.get("NOT_READY", 0)),
        "n_panel_rows": int(len(yn)),
        "tickers": tickers,
        "dates": dates,
        "owners": ["james", "grok-bot"],
        "primary_label": "ret_open_next_open",
        "fees_note": "10 bp/side not netted into labels",
    }
    (OUT / "manifest_preburn_james_grok.json").write_text(json.dumps(man, indent=2) + "\n")
    print(json.dumps({k: man[k] for k in ["tag", "promote_eligible", "n_tickers", "n_dates", "n_cells_present", "n_yes", "n_no", "n_not_ready"]}, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--aggregate-only", action="store_true")
    ap.add_argument("--n-dates", type=int, default=60)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    CELLS.mkdir(parents=True, exist_ok=True)

    tickers = [ln.strip() for ln in (HERE / "out/pilot_matrix/tickers_mvp20.txt").read_text().splitlines() if ln.strip()][:20]
    dates = pick_dates(args.n_dates)
    (OUT / "tickers.txt").write_text("\n".join(tickers) + "\n")
    (OUT / "dates_train.txt").write_text("\n".join(dates) + "\n")
    build_labels(tickers, dates)
    keep = {"james", "grok-bot"}

    if args.aggregate_only:
        aggregate(tickers, dates)
        return

    pairs = [(t, d) for t in tickers for d in dates]
    pairs = [(t, d) for t, d in pairs if not (cell_path(t, d).exists() and cell_path(t, d).stat().st_size > 500)]
    if args.limit:
        pairs = pairs[: args.limit]
    print(f"preburn todo={len(pairs)} tickers={len(tickers)} dates={len(dates)} workers={args.workers}", flush=True)
    if not pairs:
        aggregate(tickers, dates)
        return
    nW = max(1, args.workers)
    chunks = [[] for _ in range(nW)]
    for i, p in enumerate(pairs):
        chunks[i % nW].append(p)
    chunks = [c for c in chunks if c]
    if nW == 1:
        _worker(pairs, keep)
    else:
        with ProcessPoolExecutor(max_workers=len(chunks)) as ex:
            futs = [ex.submit(_worker, ch, keep) for ch in chunks]
            for f in as_completed(futs):
                f.result()
    aggregate(tickers, dates)

if __name__ == "__main__":
    main()

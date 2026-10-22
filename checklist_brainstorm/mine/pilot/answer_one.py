#!/usr/bin/env python3
"""CLI: answer one ticker×date with given readers; write YES-only parquet cache.
Used by build_panel.py so each ticker can run in its own process (warm readers).
"""
from __future__ import annotations
import argparse, csv, importlib.util, json, sys
from pathlib import Path
import pandas as pd

READERS = Path("/workspace/checklist_brainstorm/engine/readers")
SHEET = Path("/workspace/checklist_brainstorm/merged_draft_v8.1.csv")


def load_sheet_meta():
    owner, sg = {}, {}
    with open(SHEET, newline="") as f:
        for r in csv.DictReader(f):
            rid = r["id"].strip()
            owner[rid] = (r.get("merge_owner") or "").strip()
            sg[rid] = (r.get("signal_group") or "").strip()
    return owner, sg


def load_reader(name: str):
    fname = {
        "james": "james.py",
        "trading-bot-taskforce": "trading-bot-taskforce.py",
        "taskforce": "trading-bot-taskforce.py",
        "grok": "grok.py",
        "new-bot": "new-bot.py",
        "theme_radar": "theme_radar.py",
        "theme-radar": "theme_radar.py",
    }.get(name, name if name.endswith(".py") else name + ".py")
    path = READERS / fname
    spec = importlib.util.spec_from_file_location(f"r_{path.stem}", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--dates", required=True, help="comma-separated YYYY-MM-DD")
    ap.add_argument("--readers", default="james")
    ap.add_argument("--cache-dir", required=True)
    args = ap.parse_args()
    owner_map, sg_map = load_sheet_meta()
    cache = Path(args.cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    names = [x.strip() for x in args.readers.split(",") if x.strip()]
    mods = [(n, load_reader(n)) for n in names]
    ticker = args.ticker.upper()
    dates = [d.strip() for d in args.dates.split(",") if d.strip()]
    total = 0
    for d in dates:
        out_p = cache / f"yes_{ticker}_{d}.parquet"
        if out_p.exists():
            total += len(pd.read_parquet(out_p))
            continue
        day = []
        for name, mod in mods:
            try:
                res = list(mod.answer(ticker, d) or [])
            except Exception as e:
                print(f"WARN {name} {ticker} {d}: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
                continue
            for r in res:
                if (r.get("answer") or "").upper() != "YES":
                    continue
                rid = str(r.get("row_id", "")).strip()
                day.append(
                    {
                        "row_id": rid,
                        "owner": owner_map.get(rid, name),
                        "signal_group": sg_map.get(rid, ""),
                        "ticker": ticker,
                        "date": d,
                        "answer": "YES",
                        "reason": str(r.get("reason") or ""),
                        "data_as_of": str(r.get("data_as_of") or ""),
                        "src_file": f"reader:{name}",
                    }
                )
        df = pd.DataFrame(day) if day else pd.DataFrame(
            columns=["row_id","owner","signal_group","ticker","date","answer","reason","data_as_of","src_file"]
        )
        df.to_parquet(out_p, index=False)
        total += len(df)
        print(f"{ticker} {d} YES={len(df)}", flush=True)
    print(json.dumps({"ticker": ticker, "yes_rows": total}))


if __name__ == "__main__":
    main()

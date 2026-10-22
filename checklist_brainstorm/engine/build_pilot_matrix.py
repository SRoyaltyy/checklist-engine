#!/usr/bin/env python3
"""Build War-room checklist→probability pilot matrix (smoke + helpers).

BURNED WINDOW: Jul–Oct 2026 is report/smoke only — never a promote candidate.
Sheet: merged_draft_v8.2.csv (21409 ids).

Usage examples:
  python3 build_pilot_matrix.py --mode smoke-mvp   # 20 tickers × 30 dates (burned)
  python3 build_pilot_matrix.py --mode smoke-full  # 50 × all labelable Aug–Oct dates
  python3 build_pilot_matrix.py --mode tiny        # 5 × 10 for quick plumbing check
  python3 build_pilot_matrix.py --aggregate-only   # rebuild parquet/manifest from cells/

Workers keep readers loaded (LRU/cache warm). Skip cells that already exist.
"""
from __future__ import annotations
import argparse, csv, importlib.util, json, os, sys, time, traceback
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SHEET = ROOT / "merged_draft_v8.2.csv"
READER_DIRS = [HERE / "readers", Path("/workspace/tf/engine/readers")]
OUT = HERE / "out" / "pilot_matrix"
CELLS = OUT / "cells"
VALID = {"YES", "NO", "NOT_READY"}
ALIAS = {
    "grok": "grok-bot",
    "theme_radar": "theme-radar",
    "james": "james",
    "trading-bot-taskforce": "taskforce",
    "newbot": "new-bot",
    "themeradar": "theme-radar",
}

# --- universe / dates files (written by setup or this script) ---
def load_list(path: Path) -> list[str]:
    return [ln.strip() for ln in path.read_text().splitlines() if ln.strip() and not ln.startswith("#")]

def load_sheet():
    with open(SHEET, newline="") as f:
        rows = list(csv.DictReader(f))
    owner, dup = {}, []
    for r in rows:
        i = r["id"].strip()
        if i in owner:
            dup.append(i)
        owner[i] = (r.get("merge_owner") or "").strip()
    return owner, dup

def find_readers():
    seen, out = set(), []
    for d in READER_DIRS:
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.py")):
            if p.name.startswith("_"):
                continue
            rp = os.path.realpath(p)
            if rp in seen:
                continue
            seen.add(rp)
            out.append((p.stem, rp))
    return out

def cell_path(ticker: str, date: str) -> Path:
    return CELLS / f"{ticker}_{date}.csv"

def run_cell(owner: dict, readers: list, ticker: str, date: str, out_path: Path) -> dict:
    """Run all readers for one ticker-date; write CSV; return summary counts."""
    claims = defaultdict(list)
    crashed = {}
    warn = []
    owners = set(owner.values())
    for name, m in readers:
        try:
            res = list(m.answer(ticker, date) or [])
        except Exception as e:
            crashed[name] = f"{type(e).__name__}: {e}".replace("\n", " ")[:200]
            warn.append(f"READER_ERROR {name}: {crashed[name]}")
            continue
        for r in res:
            rid = str(r.get("row_id", "")).strip()
            if rid not in owner:
                continue
            ans = r.get("answer")
            why = str(r.get("reason") or "").strip()
            if ans not in VALID:
                ans, why = "NOT_READY", f"contract_error: answer={ans!r} from {name}"
            elif ans == "NOT_READY" and not why:
                why = f"contract_error: no reason from {name}"
            claims[rid].append((name, ans, why, str(r.get("data_as_of") or "")))

    def crash_reason(rid):
        for name, msg in crashed.items():
            o = ALIAS.get(name, name)
            if o == owner[rid] or (
                o not in owners and owner[rid].replace("-", "") == name.replace("-", "")
            ):
                return f"reader_error: {msg}"
        return None

    cnt = Counter()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".tmp")
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["row_id", "owner", "ticker", "date", "answer", "reason", "data_as_of"])
        for rid in sorted(owner):
            c = claims.get(rid)
            if not c:
                ans, why, asof = "NOT_READY", crash_reason(rid) or "no_reader", ""
            elif len(c) > 1:
                names = ",".join(x[0] for x in c)
                ans, why, asof = "NOT_READY", f"conflict: {names}", ""
            else:
                _, ans, why, asof = c[0]
            cnt[ans] += 1
            w.writerow([rid, owner[rid], ticker, date, ans, why, asof])
    tmp.replace(out_path)
    return {"ticker": ticker, "date": date, "YES": cnt["YES"], "NO": cnt["NO"], "NOT_READY": cnt["NOT_READY"], "path": str(out_path)}


def _worker_chunk(pairs: list[tuple[str, str]], skip_existing: bool) -> list[dict]:
    """Process a list of (ticker, date) in one process (readers stay warm)."""
    owner, _ = load_sheet()
    readers = []
    for name, path in find_readers():
        spec = importlib.util.spec_from_file_location(f"reader_{name}", path)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        readers.append((name, m))
    results = []
    for ticker, date in pairs:
        op = cell_path(ticker, date)
        if skip_existing and op.exists() and op.stat().st_size > 1000:
            # count quickly
            c = Counter()
            with open(op) as f:
                next(f)
                for line in f:
                    parts = line.split(",")
                    if len(parts) >= 5:
                        c[parts[4]] += 1
            results.append({"ticker": ticker, "date": date, "YES": c.get("YES", 0), "NO": c.get("NO", 0), "NOT_READY": c.get("NOT_READY", 0), "path": str(op), "skipped": True})
            continue
        t0 = time.time()
        try:
            summary = run_cell(owner, readers, ticker, date, op)
            summary["secs"] = round(time.time() - t0, 1)
            summary["skipped"] = False
            results.append(summary)
            print(f"OK {ticker} {date} Y={summary['YES']} N={summary['NO']} NR={summary['NOT_READY']} {summary['secs']}s", flush=True)
        except Exception as e:
            print(f"FAIL {ticker} {date}: {e}", flush=True)
            traceback.print_exc()
            results.append({"ticker": ticker, "date": date, "error": str(e)})
    return results


def aggregate(tickers: list[str], dates: list[str], tag: str):
    """Build answers_long / panel_yesno / manifest / README snippets from cells/."""
    import pandas as pd

    paths = []
    missing = []
    for t in tickers:
        for d in dates:
            p = cell_path(t, d)
            if p.exists():
                paths.append(p)
            else:
                missing.append(f"{t}_{d}")
    if not paths:
        print("No cell files to aggregate")
        return

    frames = []
    for p in paths:
        frames.append(pd.read_csv(p, dtype=str))
    long = pd.concat(frames, ignore_index=True)
    # ensure v8.2 ids only (drop cut calendar rows if any leaked)
    owner, _ = load_sheet()
    long = long[long["row_id"].isin(owner)].copy()

    out_long = OUT / f"answers_long_{tag}.parquet"
    long.to_parquet(out_long, index=False)
    # also gz csv for portability
    long.to_csv(OUT / f"answers_long_{tag}.csv.gz", index=False, compression="gzip")

    labels = pd.read_parquet(OUT / "labels.parquet")
    labels = labels[labels["ticker"].isin(tickers) & labels["date"].isin(dates)].copy()

    yn = long[long["answer"].isin(["YES", "NO"])].copy()
    panel = yn.merge(labels, on=["ticker", "date"], how="inner")
    panel_path = OUT / f"panel_yesno_{tag}.parquet"
    panel.to_parquet(panel_path, index=False)

    cnt = Counter(long["answer"])
    manifest = {
        "tag": tag,
        "window_kind": "burned_smoke" if tag.startswith(("smoke", "tiny", "mvp")) else tag,
        "promote_eligible": False,
        "note": "Jul–Oct 2026 is BURNED for promote (report/smoke only).",
        "sheet": str(SHEET),
        "sheet_row_count": len(owner),
        "sheet_mtime": SHEET.stat().st_mtime,
        "n_tickers": len(tickers),
        "n_dates": len(dates),
        "n_cells_expected": len(tickers) * len(dates),
        "n_cells_present": len(paths),
        "n_cells_missing": len(missing),
        "missing_sample": missing[:20],
        "n_answer_cells": int(len(long)),
        "n_yes": int(cnt.get("YES", 0)),
        "n_no": int(cnt.get("NO", 0)),
        "n_not_ready": int(cnt.get("NOT_READY", 0)),
        "answers_long": str(out_long),
        "panel_yesno": str(panel_path),
        "labels": str(OUT / "labels.parquet"),
        "tickers": tickers,
        "dates": dates,
        "fees_note": "10 bp/side for later mining — NOT netted into label columns",
        "primary_label": "ret_open_next_open",
        "secondary_label": "ret_open_close",
        "cutoff": "09:25 ET feature freeze; labels from post-open prices only",
    }
    (OUT / f"manifest_{tag}.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({k: manifest[k] for k in ["tag", "n_tickers", "n_dates", "n_cells_present", "n_yes", "n_no", "n_not_ready", "promote_eligible"]}, indent=2))
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["tiny", "smoke-mvp", "smoke-full", "custom"], default="smoke-mvp")
    ap.add_argument("--tickers-file")
    ap.add_argument("--dates-file")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--aggregate-only", action="store_true")
    ap.add_argument("--no-skip", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="max cells this invocation")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    CELLS.mkdir(parents=True, exist_ok=True)

    if args.mode == "tiny":
        tickers = load_list(OUT / "tickers_mvp20.txt")[:5]
        dates = load_list(OUT / "dates_mvp30.txt")[-10:]
        tag = "tiny"
    elif args.mode == "smoke-mvp":
        tickers = load_list(OUT / "tickers_mvp20.txt")
        dates = load_list(OUT / "dates_mvp30.txt")
        tag = "smoke_mvp20x30"
    elif args.mode == "smoke-full":
        tickers = load_list(OUT / "tickers.txt")
        dates = load_list(OUT / "dates.txt")
        tag = "smoke_full50"
    else:
        tickers = load_list(Path(args.tickers_file))
        dates = load_list(Path(args.dates_file))
        tag = "custom"

    pairs = [(t, d) for t in tickers for d in dates]
    # prefer later dates first (more Finviz history) then by ticker
    pairs.sort(key=lambda x: (x[1], x[0]), reverse=True)

    if args.aggregate_only:
        aggregate(tickers, dates, tag)
        return

    # skip existing
    if not args.no_skip:
        todo = [(t, d) for t, d in pairs if not (cell_path(t, d).exists() and cell_path(t, d).stat().st_size > 1000)]
    else:
        todo = pairs
    if args.limit:
        todo = todo[: args.limit]
    print(f"mode={args.mode} tag={tag} tickers={len(tickers)} dates={len(dates)} todo={len(todo)} workers={args.workers}", flush=True)

    if not todo:
        print("Nothing to do; aggregating.")
        aggregate(tickers, dates, tag)
        return

    # split into worker chunks (round-robin by date to keep cache diversity ok)
    nW = max(1, args.workers)
    chunks = [[] for _ in range(nW)]
    for i, pair in enumerate(todo):
        chunks[i % nW].append(pair)
    chunks = [c for c in chunks if c]

    t0 = time.time()
    if nW == 1 or len(chunks) == 1:
        _worker_chunk(todo, skip_existing=not args.no_skip)
    else:
        with ProcessPoolExecutor(max_workers=len(chunks)) as ex:
            futs = [ex.submit(_worker_chunk, ch, not args.no_skip) for ch in chunks]
            for fut in as_completed(futs):
                fut.result()
    print(f"done cells in {time.time()-t0:.0f}s; aggregating", flush=True)
    aggregate(tickers, dates, tag)


if __name__ == "__main__":
    main()

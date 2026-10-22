#!/usr/bin/env python3
"""Build YES-only checklist panel for the pilot miner.

Prefer Grok dumps under engine/out/pilot_matrix/ (answers_*.csv, *.parquet long
panel, or per-owner dumps). If missing, call readers locally (james + optional
taskforce) for the universe×sessions grid and cache YES rows.

Usage:
  python3 build_panel.py                  # full universe×sessions, auto source
  python3 build_panel.py --thin           # 12 names × 20 dates × james-only
  python3 build_panel.py --readers james,trading-bot-taskforce
  python3 build_panel.py --from-dir /path/to/dumps
"""
from __future__ import annotations
import argparse, csv, importlib.util, json, os, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
ENGINE = Path("/workspace/checklist_brainstorm/engine")
READERS = ENGINE / "readers"
SHEET = Path("/workspace/checklist_brainstorm/merged_draft_v8.1.csv")
GROK_DIR = ENGINE / "out" / "pilot_matrix"
PANEL_DIR = HERE / "panel"
CACHE_DIR = HERE / "cache" / "answers"

# Thin-pilot defaults (documented cut when full grid is too slow)
THIN_N_TICKERS = 12
THIN_N_DATES = 20
THIN_READERS = ["james"]


def load_sheet_meta():
    owner, sg = {}, {}
    with open(SHEET, newline="") as f:
        for r in csv.DictReader(f):
            rid = r["id"].strip()
            owner[rid] = (r.get("merge_owner") or "").strip()
            sg[rid] = (r.get("signal_group") or "").strip()
    return owner, sg


def load_list(path: Path) -> list[str]:
    return [x.strip() for x in path.read_text().splitlines() if x.strip()]


def find_grok_answer_files(d: Path) -> list[Path]:
    if not d.is_dir():
        return []
    files = []
    # long panel
    for pat in ("panel_yes.parquet", "panel_yes.csv", "yes_panel.parquet", "matrix_yes.parquet",
                "answers_long.parquet", "answers_long.csv", "panel.parquet", "panel.csv"):
        p = d / pat
        if p.exists():
            files.append(p)
    # per ticker×date dumps
    files += sorted(d.glob("answers_*.csv"))
    files += sorted(d.glob("*_answers_*.csv"))
    files += sorted(d.glob("james_*.csv"))
    files += sorted(d.glob("taskforce_*.csv"))
    files += sorted(d.glob("tf_*.csv"))
    # nested
    for sub in d.iterdir() if d.is_dir() else []:
        if sub.is_dir():
            files += sorted(sub.glob("answers_*.csv"))
    # de-dupe
    seen, out = set(), []
    for p in files:
        rp = str(p.resolve())
        if rp in seen:
            continue
        seen.add(rp)
        out.append(p)
    return out


def ingest_answer_csv(path: Path, owner_map: dict, sg_map: dict) -> list[dict]:
    """Keep YES rows only from an answers dump (engine or reader format)."""
    rows = []
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        cols = set(r.fieldnames or [])
        for rec in r:
            ans = (rec.get("answer") or "").strip().upper()
            if ans != "YES":
                continue
            rid = (rec.get("row_id") or rec.get("id") or "").strip()
            if not rid:
                continue
            t = (rec.get("ticker") or "").strip().upper()
            d = (rec.get("date") or "").strip()[:10]
            own = (rec.get("owner") or owner_map.get(rid) or "").strip()
            rows.append(
                {
                    "row_id": rid,
                    "owner": own,
                    "signal_group": sg_map.get(rid, ""),
                    "ticker": t,
                    "date": d,
                    "answer": "YES",
                    "reason": (rec.get("reason") or "").strip(),
                    "data_as_of": (rec.get("data_as_of") or "").strip(),
                    "src_file": path.name,
                }
            )
    return rows


def ingest_long_panel(path: Path, owner_map: dict, sg_map: dict) -> pd.DataFrame:
    df = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)
    cols = {c.lower(): c for c in df.columns}
    # normalize
    rename = {}
    for want in ("row_id", "ticker", "date", "answer", "owner", "signal_group"):
        if want in df.columns:
            continue
        for alt in (want, want.upper(), "id" if want == "row_id" else want):
            if alt in cols:
                rename[cols[alt]] = want
                break
    if rename:
        df = df.rename(columns=rename)
    if "answer" in df.columns:
        df = df[df["answer"].astype(str).str.upper() == "YES"]
    df["ticker"] = df["ticker"].astype(str).str.upper()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    if "owner" not in df.columns:
        df["owner"] = df["row_id"].map(owner_map)
    if "signal_group" not in df.columns:
        df["signal_group"] = df["row_id"].map(sg_map)
    return df


def load_reader(name: str):
    # map short names to files
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
    if not path.exists():
        raise FileNotFoundError(path)
    spec = importlib.util.spec_from_file_location(f"reader_{path.stem}", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _worker_ticker(args):
    """One process per ticker: warm reader once, answer all dates, cache YES."""
    ticker, dates, reader_names, cache_dir, owner_map, sg_map = args
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    readers = [(n, load_reader(n)) for n in reader_names]
    out_rows = []
    for d in dates:
        cache_p = cache_dir / f"yes_{ticker}_{d}.parquet"
        if cache_p.exists():
            out_rows.append(pd.read_parquet(cache_p))
            continue
        day = []
        for name, mod in readers:
            try:
                res = list(mod.answer(ticker, d) or [])
            except Exception as e:
                print(f"WARN reader_error {name} {ticker} {d}: {type(e).__name__}: {e}", flush=True)
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
        df = pd.DataFrame(day)
        if len(df):
            df.to_parquet(cache_p, index=False)
            out_rows.append(df)
        else:
            # write empty marker so we don't re-call
            pd.DataFrame(columns=["row_id","owner","signal_group","ticker","date","answer","reason","data_as_of","src_file"]).to_parquet(cache_p, index=False)
    if not out_rows:
        return pd.DataFrame()
    return pd.concat(out_rows, ignore_index=True)


def build_from_readers(tickers, dates, reader_names, workers: int) -> pd.DataFrame:
    import subprocess
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    helper = str(HERE / "answer_one.py")
    dates_arg = ",".join(dates)
    readers_arg = ",".join(reader_names)
    cmds = [
        [sys.executable, helper, "--ticker", t, "--dates", dates_arg,
         "--readers", readers_arg, "--cache-dir", str(CACHE_DIR)]
        for t in tickers
    ]
    if workers <= 1:
        for cmd in cmds:
            print("RUN", cmd[3], cmd[4], flush=True)
            subprocess.run(cmd, check=False)
    else:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        def run(cmd):
            print("RUN", cmd[3], cmd[4], flush=True)
            return subprocess.run(cmd, check=False)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            list(ex.map(run, cmds))
    frames = []
    for t in tickers:
        for d in dates:
            p = CACHE_DIR / f"yes_{t}_{d}.parquet"
            if p.exists():
                df = pd.read_parquet(p)
                if len(df):
                    frames.append(df)
    if not frames:
        return pd.DataFrame(columns=["row_id","owner","signal_group","ticker","date","answer","reason","data_as_of","src_file"])
    return pd.concat(frames, ignore_index=True)


def build_from_dumps(files: list[Path]) -> pd.DataFrame:
    owner_map, sg_map = load_sheet_meta()
    frames = []
    for p in files:
        if p.suffix == ".parquet" or p.name.endswith((".parquet",)):
            try:
                frames.append(ingest_long_panel(p, owner_map, sg_map))
                print(f"ingest {p.name} long", flush=True)
                continue
            except Exception as e:
                print(f"WARN skip {p}: {e}", flush=True)
                continue
        # csv — detect long panel vs answers dump
        if p.name in ("panel_yes.csv", "answers_long.csv", "panel.csv") or "panel" in p.name.lower():
            try:
                frames.append(ingest_long_panel(p, owner_map, sg_map))
                print(f"ingest {p.name} long-csv", flush=True)
                continue
            except Exception:
                pass
        rows = ingest_answer_csv(p, owner_map, sg_map)
        if rows:
            frames.append(pd.DataFrame(rows))
            print(f"ingest {p.name} YES={len(rows)}", flush=True)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    # drop OHLC-only accidental ingest
    if "row_id" not in df.columns:
        return pd.DataFrame()
    df = df[df["answer"].astype(str).str.upper() == "YES"]
    df = df.drop_duplicates(["row_id", "ticker", "date"])
    return df


def join_labels(yes: pd.DataFrame) -> pd.DataFrame:
    sys.path.insert(0, str(HERE))
    from labels import build_labels, load_ohlc
    tickers = sorted(yes.ticker.unique()) if len(yes) else load_list(HERE / "universe.txt")
    lab = build_labels(load_ohlc(tickers))
    lab_i = lab.set_index(["ticker", "date"])[["ret_o2o", "ret_o2c", "next_date", "prior_close"]]
    yes = yes.copy()
    yes["ticker"] = yes["ticker"].astype(str).str.upper()
    yes["date"] = yes["date"].astype(str).str[:10]
    j = yes.join(lab_i, on=["ticker", "date"], how="left")
    # drop rows without primary label
    before = len(j)
    j = j[j["ret_o2o"].notna()].copy()
    print(f"label join: {before} -> {len(j)} with o2o", flush=True)
    return j


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thin", action="store_true", help="12×20×james-only smoke cut")
    ap.add_argument("--readers", default="james,trading-bot-taskforce")
    ap.add_argument("--from-dir", default=str(GROK_DIR))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--force-readers", action="store_true", help="ignore dumps; call readers")
    ap.add_argument("--tickers-file", default=str(HERE / "universe.txt"))
    ap.add_argument("--sessions-file", default=str(HERE / "sessions.txt"))
    args = ap.parse_args()

    tickers = load_list(Path(args.tickers_file))
    sessions = load_list(Path(args.sessions_file))
    reader_names = [x.strip() for x in args.readers.split(",") if x.strip()]
    cut_note = "full"

    if args.thin:
        tickers = tickers[:THIN_N_TICKERS]
        sessions = sessions[-THIN_N_DATES:]
        reader_names = list(THIN_READERS)
        cut_note = f"thin:{THIN_N_TICKERS}x{THIN_N_DATES}x{','.join(reader_names)}"
        print("THIN cut", cut_note, tickers, sessions[0], "->", sessions[-1], flush=True)

    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    meta = {
        "cut": cut_note,
        "n_tickers": len(tickers),
        "n_sessions": len(sessions),
        "tickers": tickers,
        "sessions_first": sessions[0] if sessions else None,
        "sessions_last": sessions[-1] if sessions else None,
        "readers": reader_names,
        "source": None,
    }

    yes = pd.DataFrame()
    dump_dir = Path(args.from_dir)
    extra_dirs = [
        ENGINE / "out",
        ENGINE / "out" / "50pair",
        ENGINE / "out" / "50pair_r2",
        ENGINE / "out" / "pilot_matrix",
        ENGINE / "out" / "pilot_matrix" / "preburn" / "cells",
        ENGINE / "out" / "pilot_matrix" / "cells",
    ]
    if not args.force_readers:
        files = []
        for d in [dump_dir] + extra_dirs:
            files += find_grok_answer_files(Path(d))
        # ignore pure OHLC parquet / de-dupe
        seen=set(); uniq=[]
        for pth in files:
            if "ohlc" in pth.name.lower() or "yahoo" in pth.name.lower():
                continue
            rp=str(pth.resolve())
            if rp in seen: continue
            seen.add(rp); uniq.append(pth)
        files = uniq
        if files:
            print(f"Found {len(files)} dump file(s)", flush=True)
            yes = build_from_dumps(files)
            if len(yes):
                yes = yes[yes.ticker.isin(tickers) & yes.date.isin(sessions)]
                meta["source"] = "dumps:pilot_matrix+engine/out+50pair"
                meta["n_dump_files"] = len(files)

    if not len(yes):
        print("No usable Grok YES matrix yet — calling readers:", reader_names, flush=True)
        meta["source"] = f"readers:{','.join(reader_names)}"
        yes = build_from_readers(tickers, sessions, reader_names, args.workers)

    yes_path = PANEL_DIR / "yes_panel.parquet"
    yes.to_parquet(yes_path, index=False)
    print("wrote", yes_path, yes.shape, flush=True)

    panel = join_labels(yes)
    panel_path = PANEL_DIR / "panel_labeled.parquet"
    panel.to_parquet(panel_path, index=False)
    meta["n_yes_rows"] = int(len(yes))
    meta["n_labeled"] = int(len(panel))
    meta["n_unique_row_ids"] = int(panel.row_id.nunique()) if len(panel) else 0
    (PANEL_DIR / "panel_meta.json").write_text(json.dumps(meta, indent=2))
    print("META", json.dumps(meta), flush=True)
    print(panel_path, flush=True)


if __name__ == "__main__":
    main()

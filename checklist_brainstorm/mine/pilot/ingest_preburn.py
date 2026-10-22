#!/usr/bin/env python3
"""Ingest YES rows from Grok preburn/cells + local cache/answers into selection panel.

Joins labels from preburn/labels.parquet (preferred for 2024) and labels.py merge.
Only dates <= 2026-06-30 enter the selection panel.
"""
from __future__ import annotations
import csv, json, sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_panel import load_sheet_meta, join_labels
from labels import build_labels, load_ohlc

GROK_PREBURN = Path("/workspace/checklist_brainstorm/engine/out/pilot_matrix/preburn")
LOCAL_CACHE = HERE / "cache" / "answers"
PANEL = HERE / "panel"
SELECT_END = "2026-06-30"


def yes_from_answer_csv(path: Path, owner_map, sg_map) -> list[dict]:
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if (r.get("answer") or "").upper() != "YES":
                continue
            rid = (r.get("row_id") or "").strip()
            d = (r.get("date") or "").strip()[:10]
            if d > SELECT_END:
                continue
            rows.append(
                {
                    "row_id": rid,
                    "owner": (r.get("owner") or owner_map.get(rid, "")).strip(),
                    "signal_group": sg_map.get(rid, ""),
                    "ticker": (r.get("ticker") or "").strip().upper(),
                    "date": d,
                    "answer": "YES",
                    "reason": (r.get("reason") or "").strip(),
                    "data_as_of": (r.get("data_as_of") or "").strip(),
                    "src_file": path.name,
                }
            )
    return rows


def main():
    owner_map, sg_map = load_sheet_meta()
    rows = []
    # Grok preburn cells
    cell_dir = GROK_PREBURN / "cells"
    n_grok = 0
    if cell_dir.is_dir():
        for p in sorted(cell_dir.glob("*.csv")):
            part = yes_from_answer_csv(p, owner_map, sg_map)
            rows.extend(part)
            n_grok += 1
    # local reader cache (pre-Jul only)
    n_local = 0
    if LOCAL_CACHE.is_dir():
        for p in sorted(LOCAL_CACHE.glob("yes_*.parquet")):
            # filename yes_TICKER_DATE.parquet
            parts = p.stem.split("_")
            if len(parts) >= 3:
                d = parts[-1]
                if d > SELECT_END:
                    continue
            df = pd.read_parquet(p)
            if not len(df):
                continue
            df = df[df["date"].astype(str) <= SELECT_END]
            if not len(df):
                continue
            rows.extend(df.to_dict("records"))
            n_local += 1

    if not rows:
        print("no pre-Jul YES rows yet")
        return
    yes = pd.DataFrame(rows).drop_duplicates(["row_id", "ticker", "date"])
    PANEL.mkdir(parents=True, exist_ok=True)
    yes.to_parquet(PANEL / "yes_panel.parquet", index=False)

    # labels: prefer merging Grok preburn labels + ds1016 via labels.py
    tickers = sorted(yes.ticker.unique())
    lab = build_labels(load_ohlc(tickers))
    # Union Grok preburn labels (2024 train) — must ADD rows, not only overlay cols
    gp = GROK_PREBURN / "labels.parquet"
    if gp.exists():
        g = pd.read_parquet(gp)
        g = g.rename(columns={"ret_open_next_open": "ret_o2o", "ret_open_close": "ret_o2c"})
        g["date"] = pd.to_datetime(g["date"]).dt.strftime("%Y-%m-%d")
        keep = [c for c in ("ticker", "date", "ret_o2o", "ret_o2c") if c in g.columns]
        g = g[keep]
        lab = pd.concat([lab[keep] if set(keep)<=set(lab.columns) else lab, g], ignore_index=True)
        lab = lab.drop_duplicates(["ticker", "date"], keep="last")

    lab_i = lab.set_index(["ticker", "date"])[["ret_o2o", "ret_o2c"]]
    # next_date/prior optional
    panel = yes.join(lab_i, on=["ticker", "date"], how="left")
    before = len(panel)
    panel = panel[panel["ret_o2o"].notna()].copy()
    panel.to_parquet(PANEL / "panel_labeled.parquet", index=False)
    meta = {
        "cut": "selection_prejul_ingest",
        "source": f"grok_preburn_cells={n_grok}; local_cache={n_local}",
        "n_tickers": int(panel.ticker.nunique()) if len(panel) else 0,
        "n_sessions": int(panel.date.nunique()) if len(panel) else 0,
        "n_yes_rows": int(len(yes)),
        "n_labeled": int(len(panel)),
        "n_unique_row_ids": int(panel.row_id.nunique()) if len(panel) else 0,
        "date_min": str(panel.date.min()) if len(panel) else None,
        "date_max": str(panel.date.max()) if len(panel) else None,
        "selection_ready": True,
        "burned_excluded": True,
    }
    (PANEL / "panel_meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta))
    print(f"labeled {before} -> {len(panel)}")


if __name__ == "__main__":
    main()

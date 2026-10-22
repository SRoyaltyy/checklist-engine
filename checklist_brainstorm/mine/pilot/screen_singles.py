#!/usr/bin/env python3
"""Single-question first screen on YES fires.

SELECTION tape = dates < 2026-07-01 only.
Jul–Oct 2026 is BURNED: report metrics, never set clear_test / promote.

James bar (selection test half): n≥30, win>55%, mean_aft>0 after 10 bp/side.
Primary label: open→next open.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PANEL = HERE / "panel" / "panel_labeled.parquet"
OUT = HERE / "reports"
FEE_RT = 0.002
MIN_N = 30
MIN_WIN = 0.55
BURNED_START = "2026-07-01"
SELECT_END = "2026-06-30"


def stats(rets) -> dict:
    rets = np.asarray(rets, dtype=float)
    rets = rets[np.isfinite(rets)]
    n = len(rets)
    if n == 0:
        return {"n": 0, "win": np.nan, "mean_raw": np.nan, "mean_aft": np.nan}
    aft = rets - FEE_RT
    return {
        "n": n,
        "win": float(np.mean(aft > 0)),
        "mean_raw": float(np.mean(rets)),
        "mean_aft": float(np.mean(aft)),
    }


def clears(s: dict) -> bool:
    return s["n"] >= MIN_N and s["win"] > MIN_WIN and s["mean_aft"] > 0


def screen(df: pd.DataFrame, key_col: str = "row_id") -> tuple[pd.DataFrame, dict]:
    select = df[df["date"] <= SELECT_END].copy()
    burned = df[df["date"] >= BURNED_START].copy()

    dates = sorted(select["date"].unique())
    mid = max(1, len(dates) // 2) if dates else 0
    train_dates = set(dates[:mid])
    test_dates = set(dates[mid:])

    keys = sorted(set(select[key_col].astype(str)) | set(burned[key_col].astype(str)))
    rows = []
    for kid in keys:
        g_sel = select[select[key_col].astype(str) == kid]
        g_brn = burned[burned[key_col].astype(str) == kid]

        if len(g_sel):
            st_tr = stats(g_sel[g_sel.date.isin(train_dates)]["ret_o2o"])
            st_te = stats(g_sel[g_sel.date.isin(test_dates)]["ret_o2o"])
            st_all = stats(g_sel["ret_o2o"])
            st_te_c = stats(g_sel[g_sel.date.isin(test_dates)]["ret_o2c"])
            owner = g_sel["owner"].mode().iloc[0] if "owner" in g_sel and len(g_sel["owner"].mode()) else ""
            sg = g_sel["signal_group"].mode().iloc[0] if "signal_group" in g_sel and len(g_sel["signal_group"].mode()) else ""
        else:
            st_tr = st_te = st_all = st_te_c = {"n": 0, "win": np.nan, "mean_raw": np.nan, "mean_aft": np.nan}
            owner = g_brn["owner"].mode().iloc[0] if len(g_brn) and "owner" in g_brn and len(g_brn["owner"].mode()) else ""
            sg = g_brn["signal_group"].mode().iloc[0] if len(g_brn) and "signal_group" in g_brn and len(g_brn["signal_group"].mode()) else ""

        st_brn = stats(g_brn["ret_o2o"]) if len(g_brn) else {"n": 0, "win": np.nan, "mean_raw": np.nan, "mean_aft": np.nan}

        rows.append(
            {
                key_col: kid,
                "owner": owner,
                "signal_group": sg,
                "n_train": st_tr["n"],
                "win_train": st_tr["win"],
                "mean_aft_train": st_tr["mean_aft"],
                "n_test": st_te["n"],
                "win_test": st_te["win"],
                "mean_raw_test": st_te["mean_raw"],
                "mean_aft_test": st_te["mean_aft"],
                "clear_test": clears(st_te),  # selection tape only
                "n_all_select": st_all["n"],
                "win_all_select": st_all["win"],
                "mean_aft_all_select": st_all["mean_aft"],
                "n_test_o2c": st_te_c["n"],
                "win_test_o2c": st_te_c["win"],
                "mean_aft_test_o2c": st_te_c["mean_aft"],
                "n_burned": st_brn["n"],
                "win_burned": st_brn["win"],
                "mean_aft_burned": st_brn["mean_aft"],
                "burned_report_only": True,
                "promote_stub": "pending: NW_t / Bonferroni / RANDOM4+IWM; burned Jul-Oct never select",
            }
        )

    out = pd.DataFrame(rows)
    if len(out):
        out = out.sort_values(["clear_test", "mean_aft_test"], ascending=[False, False])
    split = {
        "train_dates": sorted(train_dates),
        "test_dates": sorted(test_dates),
        "n_select_rows": int(len(select)),
        "n_burned_rows": int(len(burned)),
        "selection_rule": "date <= 2026-06-30",
        "burned_rule": "date >= 2026-07-01 report only",
    }
    return out, split


def write_report(scores: pd.DataFrame, split: dict, meta: dict) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    scores_path = OUT / "first_screen_singles.csv"
    scores.to_csv(scores_path, index=False)
    cleared = scores[scores.clear_test] if len(scores) else scores
    lines = [
        "# Taskforce pilot — single-question first screen",
        "",
        "**Selection tape: dates ≤ 2026-06-30 only. Jul–Oct 2026 is BURNED (report never select).**",
        "",
        f"- Panel: `{PANEL}`",
        f"- Cut / source: `{meta.get('cut')}` / `{meta.get('source')}`",
        f"- Select rows / burned rows: **{split.get('n_select_rows', 0)}** / **{split.get('n_burned_rows', 0)}**",
        f"- Unique keys scored: **{len(scores)}**",
    ]
    td, vd = split.get("train_dates") or [], split.get("test_dates") or []
    lines += [
        f"- Train (pre-Jul): {td[0] if td else '—'} → {td[-1] if td else '—'} ({len(td)})",
        f"- Test (pre-Jul): {vd[0] if vd else '—'} → {vd[-1] if vd else '—'} ({len(vd)})",
        f"- Fees: 10 bp/side (0.20% RT) on open→next-open",
        f"- Clear bar (pre-Jul test): n≥{MIN_N}, win>{MIN_WIN:.0%}, mean_aft>0",
        f"- **Cleared on selection test: {int(cleared.shape[0]) if len(scores) else 0}**",
        "",
        "## Top clears (pre-Jul test o2o)",
        "",
    ]
    if len(scores) == 0:
        lines.append("_No scored rows — panel empty or still building pre-Jul._")
    elif cleared.empty:
        lines += [
            "_None cleared on selection tape. Top 15 by mean_aft_test:_",
            "",
            "| row_id | owner | n_test | win_test | mean_aft_test | n_burned |",
            "|---|---|---:|---:|---:|---:|",
        ]
        for _, r in scores.head(15).iterrows():
            w = r.win_test if pd.notna(r.win_test) else float("nan")
            m = r.mean_aft_test if pd.notna(r.mean_aft_test) else float("nan")
            lines.append(
                f"| {r.row_id} | {r.get('owner','')} | {int(r.n_test)} | {w:.1%} | {m:+.4%} | {int(r.n_burned)} |"
            )
    else:
        lines += [
            "| row_id | owner | n_test | win_test | mean_aft_test |",
            "|---|---|---:|---:|---:|",
        ]
        for _, r in cleared.head(50).iterrows():
            lines.append(
                f"| {r.row_id} | {r.get('owner','')} | {int(r.n_test)} | {r.win_test:.1%} | {r.mean_aft_test:+.4%} |"
            )
    lines += [
        "",
        "## Burned window (Jul–Oct 2026) — report only",
        "",
        "Columns `n_burned` / `win_burned` / `mean_aft_burned` must **not** drive KEEP/promote.",
        "",
    ]
    if len(scores) and scores.n_burned.sum() > 0:
        br = scores[scores.n_burned > 0].sort_values("mean_aft_burned", ascending=False).head(10)
        lines += [
            "| row_id | n_burned | win_burned | mean_aft_burned |",
            "|---|---:|---:|---:|",
        ]
        for _, r in br.iterrows():
            w = r.win_burned if pd.notna(r.win_burned) else float("nan")
            m = r.mean_aft_burned if pd.notna(r.mean_aft_burned) else float("nan")
            lines.append(f"| {r.row_id} | {int(r.n_burned)} | {w:.1%} | {m:+.4%} |")
    else:
        lines.append("_No burned-window YES rows in this panel (expected for pure pre-Jul builds)._")
    lines += [
        "",
        "## Stubbed for full walk-forward promote",
        "- Train/pick 2020–24, confirm 2025–mid-2026; **Jul–Oct 2026 burned**.",
        "- Newey–West t ≥ 3.37 after fees; beat RANDOM4 + IWM; Bonferroni.",
        "- Pairs miner next after singles clear on selection tape.",
        "",
        "## Files",
        f"- `{scores_path}`",
        f"- `{OUT / 'smoke_report.md'}`",
    ]
    report = OUT / "smoke_report.md"
    report.write_text("\n".join(lines) + "\n")
    (OUT / "split_meta.json").write_text(json.dumps(split, indent=2))
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=str(PANEL))
    ap.add_argument("--by-signal-group", action="store_true")
    args = ap.parse_args()
    meta = {}
    meta_path = HERE / "panel" / "panel_meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
    df = pd.read_parquet(args.panel)
    key = "signal_group" if args.by_signal_group else "row_id"
    if args.by_signal_group and len(df):
        df = df[df.signal_group.astype(str).str.len() > 0]
    if len(df) == 0:
        scores = pd.DataFrame()
        split = {"train_dates": [], "test_dates": [], "n_select_rows": 0, "n_burned_rows": 0}
    else:
        scores, split = screen(df, key)
    report = write_report(scores, split, meta)
    n_clear = int(scores.clear_test.sum()) if len(scores) and "clear_test" in scores.columns else 0
    print(
        f"cleared_test={n_clear} scored={len(scores)} "
        f"select_rows={split.get('n_select_rows')} burned_rows={split.get('n_burned_rows')} report={report}"
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Chart-picture / story-question gate for Friday 2026-10-23 23:00 HKT joint lock.

Two stock-days are the same setup ONLY if HARD core gates match first.
Thresholds copied from FROZEN_RECIPE.md CS line / match2.py CS lambda — not retuned.
Survivors-only 2020-24 price path. Never open 2025-26 sealed tars.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

# Pack-local feature code (same shas as FROZEN_RECIPE)
_PACK = Path(__file__).resolve().parents[1] / "chart_picture"
_CASE = Path("/workspace/state_test/case_arqt")
_PRICE = Path("/workspace/pricehist/universe_2020_survivors.parquet")
_ARQT_CSV = _CASE / "ARQT.csv"
_REF_TICKER, _REF_DATE = "ARQT", "2026-10-07"

# HARD gates — frozen CS (match2.py): 
# (gr_body20>=.9)&(mid_slope_up==1)&(dip_atr<=4.2)&(pctB>=.12)&(dd_vs_run>=.5)&days_since_h20.between(5,18)
HARD_GATES = (
    ("mid_slope_up", "BB middle slope up?", lambda v: bool(v == 1 or v is True)),
    ("gr_body20", "body green:red 20d >= 0.9?", lambda v: bool(v >= 0.9)),
    ("pctB", "%B >= 0.12?", lambda v: bool(v >= 0.12)),
    ("dip_atr", "dip <= 4.2 ATR?", lambda v: bool(v <= 4.2)),
    ("days_since_h20", "days since 20d high in [5,18]?", lambda v: bool(5 <= v <= 18)),
    ("dd_vs_run", "dd_vs_run >= 0.5?", lambda v: bool(v >= 0.5)),
)
# WARN only — does not veto alone
WARN_GATES = (
    ("redgreen_vol10", "red/green volume 10d > 1.0? (warn side)", lambda v: bool(v > 1.0)),
)
# lower_highs10: continuous for shape match only — not a binary gate (not in frozen CS)

FEATURE_KEYS = [k for k, _, _ in HARD_GATES] + [k for k, _, _ in WARN_GATES] + ["lower_highs10", "slope20"]


def _load_feat_mods():
    sys.path.insert(0, str(_PACK if (_PACK / "feats2.py").exists() else _CASE))
    from feats import feats  # noqa: WPS433
    from feats2 import add2, add3  # noqa: WPS433
    return feats, add2, add3


def features_from_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """df indexed by date with Open,High,Low,Close,Volume."""
    feats, add2, add3 = _load_feat_mods()
    return add3(add2(feats(df)))


def load_ticker_features(ticker: str, date: str, warm_years: int = 2) -> dict[str, float]:
    """Load one survivors row's chart-picture features. Refuses dates in 2025+ for non-ARQT."""
    d = pd.Timestamp(date)
    if ticker != _REF_TICKER and d >= pd.Timestamp("2025-01-01"):
        raise RuntimeError(
            f"refusing {ticker} {date}: 2025-26 is sealed until Fri 2026-10-23 23:00 HKT"
        )
    if ticker == _REF_TICKER:
        raw = pd.read_csv(_ARQT_CSV, index_col=0, parse_dates=True)
        D = features_from_ohlcv(raw)
        if d not in D.index:
            raise KeyError(f"ARQT missing {date}")
        row = D.loc[d]
    else:
        import pyarrow.parquet as pq

        start = d - pd.Timedelta(days=365 * warm_years + 60)
        end = d + pd.Timedelta(days=5)
        # survivors parquet only; never sealed 2025-26 tars
        px = pq.read_table(
            _PRICE,
            columns=["ticker", "date", "open", "high", "low", "close", "volume"],
            filters=[
                ("ticker", "==", ticker),
                ("date", ">=", start),
                ("date", "<=", end),
            ],
        ).to_pandas()
        if px.empty:
            raise KeyError(f"no rows for {ticker}")
        px = px.drop_duplicates(["ticker", "date"]).sort_values("date")
        px = px.rename(
            columns={
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume",
            }
        )
        px = px.set_index("date")
        D = features_from_ohlcv(px)
        if d not in D.index:
            raise KeyError(f"{ticker} missing {date}")
        row = D.loc[d]
    out = {}
    for k in FEATURE_KEYS:
        if k in row.index and pd.notna(row[k]):
            out[k] = float(row[k])
        else:
            out[k] = float("nan")
    return out


def gate_answers(feats: Mapping[str, Any]) -> dict[str, bool | None]:
    """Map feature dict -> YES/NO (True/False) per gate; None if missing."""
    ans: dict[str, bool | None] = {}
    for key, _label, pred in list(HARD_GATES) + list(WARN_GATES):
        v = feats.get(key)
        if v is None or (isinstance(v, float) and np.isnan(v)):
            ans[key] = None
        else:
            ans[key] = bool(pred(v))
    return ans


def check_core(
    candidate: Mapping[str, Any],
    reference: Mapping[str, Any] | None = None,
    *,
    mode: str = "vs_ref",
) -> dict[str, Any]:
    """Return pass/fail + which gates failed.

    mode='vs_ref': candidate must match reference HARD answers (default = ARQT YES on 1-6).
    mode='pairwise': HARD answers must be identical on both sides.
    """
    c_ans = gate_answers(candidate)
    if reference is None:
        # ARQT frozen answers on HARD gates are all YES
        r_ans = {k: True for k, _, _ in HARD_GATES}
        r_ans["redgreen_vol10"] = False  # ARQT ~1.0
    else:
        r_ans = gate_answers(reference)

    failed: list[str] = []
    details: list[dict[str, Any]] = []
    for key, label, _ in HARD_GATES:
        ca, ra = c_ans.get(key), r_ans.get(key)
        if ca is None or ra is None:
            failed.append(key)
            ok = False
            note = "missing"
        elif mode == "pairwise":
            ok = ca == ra
            note = f"cand={ca} ref={ra}"
            if not ok:
                failed.append(key)
        else:  # vs_ref: require same answer as ref (ARQT YES on all HARD)
            ok = ca == ra
            note = f"cand={ca} ref={ra}"
            if not ok:
                failed.append(key)
        details.append(
            {
                "gate": key,
                "label": label,
                "role": "HARD",
                "ok": ok,
                "note": note,
                "cand_value": candidate.get(key),
                "ref_value": None if reference is None else reference.get(key),
            }
        )

    warns: list[str] = []
    for key, label, _ in WARN_GATES:
        ca, ra = c_ans.get(key), r_ans.get(key)
        if mode == "vs_ref":
            # warn if candidate YES while ref NO (heavier red-day volume)
            side = bool(ca is True and ra is False)
        else:
            side = bool(ca is not None and ra is not None and ca != ra)
        if side:
            warns.append(key)
        details.append(
            {
                "gate": key,
                "label": label,
                "role": "WARN",
                "ok": not side,
                "note": f"cand={ca} ref={ra}",
                "cand_value": candidate.get(key),
                "ref_value": None if reference is None else reference.get(key),
            }
        )

    passed = len(failed) == 0
    return {
        "pass": passed,
        "failed_hard": failed,
        "warn": warns,
        "details": details,
        "candidate_answers": c_ans,
        "reference_answers": r_ans,
        "note_lower_highs10": (
            "lower_highs10 is continuous for shape match only; not a binary CS gate"
        ),
    }


def check_ticker_date(
    ticker: str,
    date: str,
    ref_ticker: str = _REF_TICKER,
    ref_date: str = _REF_DATE,
) -> dict[str, Any]:
    cand = load_ticker_features(ticker, date)
    if ref_ticker == _REF_TICKER and ref_date == _REF_DATE:
        ref = load_ticker_features(_REF_TICKER, _REF_DATE)
    else:
        ref = load_ticker_features(ref_ticker, ref_date)
    out = check_core(cand, ref, mode="vs_ref")
    out["candidate"] = {"ticker": ticker, "date": date, "features": cand}
    out["reference"] = {"ticker": ref_ticker, "date": ref_date, "features": ref}
    return out


def selftest() -> int:
    print("=== chart_picture_gate selftest (2020-24 survivors only) ===")
    aapl = check_ticker_date("AAPL", "2022-09-01")
    print("AAPL 2022-09-01 vs ARQT:", "PASS" if aapl["pass"] else "FAIL",
          "failed=", aapl["failed_hard"], "warn=", aapl["warn"])
    aldx = check_ticker_date("ALDX", "2021-11-18")
    print("ALDX 2021-11-18 vs ARQT:", "PASS" if aldx["pass"] else "FAIL",
          "failed=", aldx["failed_hard"], "warn=", aldx["warn"])

    ok_aapl = (not aapl["pass"]) and set(aapl["failed_hard"]) >= {
        "mid_slope_up",
        "gr_body20",
        "pctB",
        "dip_atr",
    }
    ok_aldx = aldx["pass"] is True
    print("expect AAPL FAIL (4+ hard):", "OK" if ok_aapl else "BAD")
    print("expect ALDX PASS hard:", "OK" if ok_aldx else "BAD")
    if ok_aapl and ok_aldx:
        print("SELFTEST PASS")
        return 0
    print("SELFTEST FAIL")
    return 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--ticker")
    p.add_argument("--date")
    p.add_argument("--ref-ticker", default=_REF_TICKER)
    p.add_argument("--ref-date", default=_REF_DATE)
    args = p.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.ticker or not args.date:
        p.error("need --ticker/--date or --selftest")
    r = check_ticker_date(args.ticker, args.date, args.ref_ticker, args.ref_date)
    print("PASS" if r["pass"] else "FAIL", "failed_hard=", r["failed_hard"], "warn=", r["warn"])
    for d in r["details"]:
        print(f"  [{d['role']}] {d['gate']}: {'ok' if d['ok'] else 'FAIL'} ({d['note']})")
    return 0 if r["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

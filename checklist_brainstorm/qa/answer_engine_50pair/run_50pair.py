#!/usr/bin/env python3
"""50-pair acceptance test for checklist answer engine (Manager Bot verifier)."""
from __future__ import annotations
import csv, hashlib, json, os, random, subprocess, sys, time
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path("/workspace/checklist_brainstorm")
ENGINE = ROOT / "engine"
OUT_DIR = ENGINE / "out" / "50pair"
QA_DIR = ROOT / "qa" / "answer_engine_50pair"
SHEET = ROOT / "merged_draft_v8.1.csv"
EXPECTED_ROWS = 21423
VALID = {"YES", "NO", "NOT_READY"}
SEED = 20261022

OUT_DIR.mkdir(parents=True, exist_ok=True)
QA_DIR.mkdir(parents=True, exist_ok=True)

# --- NYSE sessions 2024-01-02 .. 2026-10-21 ---
NYSE_HOLIDAYS = {
    "2024-01-01","2024-01-15","2024-02-19","2024-03-29","2024-05-27","2024-06-19",
    "2024-07-04","2024-09-02","2024-11-28","2024-12-25",
    "2025-01-01","2025-01-09","2025-01-20","2025-02-17","2025-04-18","2025-05-26",
    "2025-06-19","2025-07-04","2025-09-01","2025-11-27","2025-12-25",
    "2026-01-01","2026-01-19","2026-02-16","2026-04-03","2026-05-25","2026-06-19",
    "2026-07-03","2026-09-07","2026-11-26","2026-12-25",
}

def sessions():
    out = []
    d = date(2024, 1, 2)
    end = date(2026, 10, 21)
    while d <= end:
        iso = d.isoformat()
        if d.weekday() < 5 and iso not in NYSE_HOLIDAYS:
            out.append(iso)
        d += timedelta(days=1)
    return out

SESS = sessions()
PRE = [s for s in SESS if s < "2026-08-06"]
POST = [s for s in SESS if s >= "2026-08-06"]

# Prefer liquid US names + a few small caps
LIQUID = [
    "AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","JPM","XOM","JNJ",
    "UNH","V","MA","HD","PG","KO","PEP","WMT","COST","AVGO",
    "AMD","NFLX","CRM","ORCL","INTC","BA","CAT","GE","DIS","SPY",
    "QQQ","IWM","GS","BAC","C","WFC","CVX","LLY","ABBV","MRK",
]
SMALL = [
    "CRMT","CELH","PLUG","FIZZ","PACB","QSI","NAUT","UPST","SOFI","RIOT",
    "MARA","CLOV","NKLA","SPCE","BYND","GME","AMC","PLTR","RIVN","LCID",
]

def pick_pairs(n=50):
    rng = random.Random(SEED)
    pairs = []
    # 35 liquid, 15 small; mix pre/post 08-06 (~60% post for snapshot coverage, 40% pre)
    n_post = 30
    n_pre = n - n_post
    for i in range(n):
        if i < 15:
            t = SMALL[i % len(SMALL)]
        else:
            t = LIQUID[(i - 15) % len(LIQUID)]
        if i < n_pre:
            d = PRE[rng.randrange(len(PRE))]
            era = "pre_08-06"
        else:
            d = POST[rng.randrange(len(POST))]
            era = "post_08-06"
        pairs.append({"ticker": t, "date": d, "era": era, "kind": "small" if i < 15 else "liquid"})
    # ensure uniqueness of (t,d); reshuffle collisions
    seen = set()
    fixed = []
    pool_pre, pool_post = list(PRE), list(POST)
    rng.shuffle(pool_pre); rng.shuffle(pool_post)
    pi = po = 0
    for p in pairs:
        key = (p["ticker"], p["date"])
        tries = 0
        while key in seen and tries < 200:
            if p["era"] == "pre_08-06":
                p["date"] = pool_pre[pi % len(pool_pre)]; pi += 1
            else:
                p["date"] = pool_post[po % len(pool_post)]; po += 1
            key = (p["ticker"], p["date"]); tries += 1
        seen.add(key)
        fixed.append(p)
    # pin a few known page tickers for continuity
    fixed[0] = {"ticker": "AAPL", "date": "2026-10-21", "era": "post_08-06", "kind": "liquid"}
    fixed[1] = {"ticker": "NVDA", "date": "2026-10-21", "era": "post_08-06", "kind": "liquid"}
    fixed[2] = {"ticker": "CRMT", "date": "2026-10-21", "era": "post_08-06", "kind": "small"}
    # ensure date diversity: force a few early-2024 and mid-range
    fixed[3] = {"ticker": "MSFT", "date": "2024-01-02", "era": "pre_08-06", "kind": "liquid"}
    fixed[4] = {"ticker": "CELH", "date": "2024-06-12", "era": "pre_08-06", "kind": "small"}
    fixed[5] = {"ticker": "SPY", "date": "2025-04-07", "era": "pre_08-06", "kind": "liquid"}  # tariff stress
    fixed[6] = {"ticker": "AAPL", "date": "2026-08-06", "era": "post_08-06", "kind": "liquid"}  # first snapshot day
    fixed[7] = {"ticker": "IWM", "date": "2026-08-07", "era": "post_08-06", "kind": "liquid"}
    return fixed

def sheet_ids():
    with open(SHEET, newline="") as f:
        return {r["id"].strip() for r in csv.DictReader(f)}

def run_one(ticker, date_s, out_path):
    cmd = [
        "python3", str(ENGINE / "answer.py"),
        "--ticker", ticker, "--date", date_s, "--out", str(out_path),
    ]
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0
    return p.returncode, p.stdout, p.stderr, elapsed

def validate_csv(path, expected_ids):
    issues = []
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != EXPECTED_ROWS:
        issues.append(f"row_count={len(rows)} expected={EXPECTED_ROWS}")
    got_ids = [r["row_id"] for r in rows]
    if len(got_ids) != len(set(got_ids)):
        issues.append("duplicate_row_ids")
    if set(got_ids) != expected_ids:
        missing = expected_ids - set(got_ids)
        extra = set(got_ids) - expected_ids
        if missing: issues.append(f"missing_ids={len(missing)}")
        if extra: issues.append(f"extra_ids={len(extra)}")
    blank = 0
    bad_ans = 0
    empty_reason = 0
    ans_c = Counter()
    nr_reasons = Counter()
    empty_by_owner = Counter()
    for r in rows:
        a = (r.get("answer") or "").strip()
        why = (r.get("reason") or "").strip()
        if not a:
            blank += 1
        elif a not in VALID:
            bad_ans += 1
        else:
            ans_c[a] += 1
            if a == "NOT_READY":
                key = why.split(":")[0] if why else "(empty)"
                nr_reasons[key] += 1
                if not why:
                    empty_reason += 1
                    empty_by_owner[r.get("owner","?")+"|NOT_READY"] += 1
            elif not why:
                empty_reason += 1
                empty_by_owner[r.get("owner","?")+"|"+a] += 1
    if blank:
        issues.append(f"blank_answer={blank}")
    if bad_ans:
        issues.append(f"invalid_answer={bad_ans}")
    if empty_reason:
        issues.append(f"empty_reason={empty_reason}")
    return {
        "issues": issues,
        "pass_strict": not issues,
        # criterion 2 as stated: YES/NO/NOT_READY + non-empty reason + 21423 rows + zero blanks
        "answers": dict(ans_c),
        "nr_reasons": dict(nr_reasons),
        "empty_by_owner": dict(empty_by_owner),
        "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        "nbytes": Path(path).stat().st_size,
    }

def main():
    pairs = pick_pairs(50)
    with open(QA_DIR / "pairs.json", "w") as f:
        json.dump(pairs, f, indent=2)
    expected_ids = sheet_ids()
    assert len(expected_ids) == EXPECTED_ROWS, len(expected_ids)

    results = []
    nr_hist = Counter()
    overall_ans = Counter()
    overall_empty_owner = Counter()

    for i, p in enumerate(pairs):
        t, d = p["ticker"], p["date"]
        out = OUT_DIR / f"answers_{t}_{d}.csv"
        print(f"[{i+1}/50] {t} {d} ...", flush=True)
        rc, stdout, stderr, elapsed = run_one(t, d, out)
        # keep warn sample (first 5 lines)
        warn_lines = [ln for ln in stderr.splitlines() if ln.startswith("WARN")]
        unknown = sum(1 for ln in warn_lines if "UNKNOWN_ID" in ln)
        v = validate_csv(out, expected_ids) if out.exists() else {
            "issues": ["no_output"], "pass_strict": False, "answers": {}, "nr_reasons": {},
            "empty_by_owner": {}, "sha256": "", "nbytes": 0,
        }
        for k, c in v.get("nr_reasons", {}).items():
            nr_hist[k] += c
        for k, c in v.get("answers", {}).items():
            overall_ans[k] += c
        for k, c in v.get("empty_by_owner", {}).items():
            overall_empty_owner[k] += c
        rec = {
            **p,
            "out": str(out),
            "rc": rc,
            "elapsed_s": round(elapsed, 2),
            "stdout_tail": stdout.strip().splitlines()[-1] if stdout.strip() else "",
            "warn_count": len(warn_lines),
            "unknown_id_warns": unknown,
            **v,
        }
        results.append(rec)
        status = "PASS" if v["pass_strict"] else "FAIL:" + ",".join(v["issues"])
        print(f"  {status} elapsed={elapsed:.1f}s ans={v.get('answers')} empty_reason={v.get('empty_by_owner') and sum(v['empty_by_owner'].values())}", flush=True)
        with open(QA_DIR / "progress.json", "w") as f:
            json.dump({"done": i+1, "results": results}, f)

    # --- Rerun 5 pairs for byte identity ---
    # Prefer pairs that already passed row-count (all should); pick indices 0,7,15,30,45
    rerun_idx = [0, 7, 15, 30, 45]
    rerun = []
    for idx in rerun_idx:
        p = pairs[idx]
        t, d = p["ticker"], p["date"]
        first = OUT_DIR / f"answers_{t}_{d}.csv"
        second = OUT_DIR / f"answers_{t}_{d}.rerun.csv"
        print(f"[rerun] {t} {d} ...", flush=True)
        rc, stdout, stderr, elapsed = run_one(t, d, second)
        h1 = hashlib.sha256(first.read_bytes()).hexdigest() if first.exists() else ""
        h2 = hashlib.sha256(second.read_bytes()).hexdigest() if second.exists() else ""
        identical = h1 == h2 and bool(h1)
        rerun.append({
            "ticker": t, "date": d, "identical": identical,
            "sha_first": h1, "sha_second": h2, "elapsed_s": round(elapsed, 2), "rc": rc,
        })
        print(f"  identical={identical}", flush=True)

    summary = {
        "seed": SEED,
        "expected_rows": EXPECTED_ROWS,
        "n_pairs": len(pairs),
        "n_pass_strict": sum(1 for r in results if r["pass_strict"]),
        "n_fail": sum(1 for r in results if not r["pass_strict"]),
        "overall_answers": dict(overall_ans),
        "not_ready_reason_histogram": dict(nr_hist.most_common()),
        "empty_reason_by_owner_answer": dict(overall_empty_owner.most_common()),
        "issue_histogram": dict(Counter(iss for r in results for iss in r["issues"]).most_common()),
        "rerun": rerun,
        "rerun_all_identical": all(x["identical"] for x in rerun),
        "total_elapsed_s": round(sum(r["elapsed_s"] for r in results), 1),
        "pairs_pre": sum(1 for p in pairs if p["era"] == "pre_08-06"),
        "pairs_post": sum(1 for p in pairs if p["era"] == "post_08-06"),
    }
    with open(QA_DIR / "results.json", "w") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2)
    print(json.dumps(summary, indent=2))
    print("DONE", flush=True)

if __name__ == "__main__":
    main()

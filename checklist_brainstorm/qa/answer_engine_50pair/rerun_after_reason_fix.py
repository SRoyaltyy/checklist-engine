#!/usr/bin/env python3
"""Re-run same 50 pairs after YES/NO reason fix. Strict empty-reason check."""
from __future__ import annotations
import csv, hashlib, json, subprocess, time
from collections import Counter
from pathlib import Path

ROOT = Path("/workspace/checklist_brainstorm")
ENGINE = ROOT / "engine"
OUT = ENGINE / "out" / "50pair_r2"
QA = ROOT / "qa" / "answer_engine_50pair"
SHEET = ROOT / "merged_draft_v8.1.csv"
EXPECTED = 21423
VALID = {"YES", "NO", "NOT_READY"}
OUT.mkdir(parents=True, exist_ok=True)

pairs = json.load(open(QA / "pairs.json"))
assert len(pairs) == 50
expected_ids = {r["id"].strip() for r in csv.DictReader(open(SHEET))}
assert len(expected_ids) == EXPECTED

def run_one(t, d, out):
    cmd = ["python3", str(ENGINE / "answer.py"), "--ticker", t, "--date", d, "--out", str(out)]
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr, time.time() - t0

def validate(path):
    rows = list(csv.DictReader(open(path)))
    issues = []
    if len(rows) != EXPECTED:
        issues.append(f"row_count={len(rows)} expected={EXPECTED}")
    if set(r["row_id"] for r in rows) != expected_ids:
        issues.append("id_set_mismatch")
    ans_c, nr_c = Counter(), Counter()
    empty_by = Counter()
    blank = bad = empty = conflict = 0
    for r in rows:
        a = (r.get("answer") or "").strip()
        why = (r.get("reason") or "").strip()
        if not a:
            blank += 1
        elif a not in VALID:
            bad += 1
        else:
            ans_c[a] += 1
            if a == "NOT_READY":
                nr_c[why.split(":")[0] if why else "(empty)"] += 1
                if why.startswith("conflict"):
                    conflict += 1
            if not why:
                empty += 1
                empty_by[f"{r.get('owner','?')}|{a}"] += 1
    if blank: issues.append(f"blank_answer={blank}")
    if bad: issues.append(f"invalid_answer={bad}")
    if empty: issues.append(f"empty_reason={empty}")
    if conflict: issues.append(f"conflict_rows={conflict}")
    return {
        "issues": issues,
        "pass_strict": not issues,
        "answers": dict(ans_c),
        "nr_reasons": dict(nr_c),
        "empty_by_owner": dict(empty_by),
        "empty_total": empty,
        "conflict_rows": conflict,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "nbytes": path.stat().st_size,
    }

results = []
nr_hist = Counter()
overall_ans = Counter()
empty_owner = Counter()

for i, p in enumerate(pairs):
    t, d = p["ticker"], p["date"]
    out = OUT / f"answers_{t}_{d}.csv"
    print(f"[{i+1}/50] {t} {d} ...", flush=True)
    rc, stdout, stderr, elapsed = run_one(t, d, out)
    warn = [ln for ln in stderr.splitlines() if ln.startswith("WARN")]
    conflicts = sum(1 for ln in warn if "CONFLICT" in ln)
    unknown = sum(1 for ln in warn if "UNKNOWN_ID" in ln)
    v = validate(out)
    for k, c in v["nr_reasons"].items(): nr_hist[k] += c
    for k, c in v["answers"].items(): overall_ans[k] += c
    for k, c in v["empty_by_owner"].items(): empty_owner[k] += c
    rec = {**p, "out": str(out), "rc": rc, "elapsed_s": round(elapsed, 2),
           "stdout_tail": stdout.strip().splitlines()[-1] if stdout.strip() else "",
           "warn_count": len(warn), "conflict_warns": conflicts, "unknown_id_warns": unknown, **v}
    results.append(rec)
    status = "PASS" if v["pass_strict"] else "FAIL:" + ",".join(v["issues"])
    print(f"  {status} empty={v['empty_total']} elapsed={elapsed:.1f}s ans={v['answers']}", flush=True)
    json.dump({"done": i+1, "results": results}, open(QA / "progress_r2.json", "w"))

# 5 byte-identical reruns (same indices as before: 21,30,35,44,49)
rerun = []
for idx in [21, 30, 35, 44, 49]:
    p = pairs[idx]
    t, d = p["ticker"], p["date"]
    first = OUT / f"answers_{t}_{d}.csv"
    second = OUT / f"answers_{t}_{d}.rerun.csv"
    print(f"[rerun] {t} {d} ...", flush=True)
    rc, stdout, stderr, elapsed = run_one(t, d, second)
    h1 = hashlib.sha256(first.read_bytes()).hexdigest()
    h2 = hashlib.sha256(second.read_bytes()).hexdigest()
    identical = h1 == h2
    rerun.append({"ticker": t, "date": d, "identical": identical, "sha_first": h1, "sha_second": h2,
                  "elapsed_s": round(elapsed, 2), "rc": rc})
    print(f"  identical={identical}", flush=True)

# Spot-check: sample YES/NO reasons from taskforce/grok/new-bot on 3 pairs
spot = []
for t, d in [("AAPL", "2026-10-21"), ("CELH", "2024-06-12"), ("TSLA", "2026-08-25")]:
    path = OUT / f"answers_{t}_{d}.csv"
    if not path.exists():
        continue
    rows = list(csv.DictReader(open(path)))
    for o in ["taskforce", "grok-bot", "new-bot"]:
        yn = [r for r in rows if r["owner"] == o and r["answer"] in ("YES", "NO")]
        empty = sum(1 for r in yn if not (r.get("reason") or "").strip())
        samples = [r["reason"][:80] for r in yn[:3]]
        spot.append({"ticker": t, "date": d, "owner": o, "yes_no": len(yn), "empty": empty, "samples": samples})

summary = {
    "seed": 20261022,
    "run": "r2_after_reason_fix",
    "expected_rows": EXPECTED,
    "n_pairs": 50,
    "n_pass_strict": sum(1 for r in results if r["pass_strict"]),
    "n_fail": sum(1 for r in results if not r["pass_strict"]),
    "overall_answers": dict(overall_ans),
    "not_ready_reason_histogram": dict(nr_hist.most_common()),
    "empty_reason_by_owner_answer": dict(empty_owner.most_common()),
    "empty_reason_total": sum(empty_owner.values()),
    "issue_histogram": dict(Counter(iss.split("=")[0] if "=" in iss else iss for r in results for iss in r["issues"]).most_common()),
    "rerun": rerun,
    "rerun_all_identical": all(x["identical"] for x in rerun),
    "spot_check": spot,
    "total_elapsed_s": round(sum(r["elapsed_s"] for r in results), 1),
    "pairs_pre": sum(1 for p in pairs if p["era"] == "pre_08-06"),
    "pairs_post": sum(1 for p in pairs if p["era"] == "post_08-06"),
    "note_duplicate_reader": "Renamed identical trading-bot-taskforce-v1.2-reasons.py -> _trading-bot-taskforce-v1.2-reasons.py so runner loads one Taskforce reader (was causing 8513 CONFLICT rows).",
}
json.dump({"summary": summary, "results": results}, open(QA / "results_r2.json", "w"), indent=2)
print(json.dumps(summary, indent=2))
print("R2_DONE", flush=True)

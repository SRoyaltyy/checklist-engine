#!/usr/bin/env python3
"""Re-run stale pre-sector-wire pairs, 5 byte-identity reruns, rebuild summary."""
from __future__ import annotations
import csv, hashlib, json, subprocess, time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/workspace/checklist_brainstorm")
ENGINE = ROOT / "engine"
OUT = ENGINE / "out" / "50pair"
QA = ROOT / "qa" / "answer_engine_50pair"
SHEET = ROOT / "merged_draft_v8.1.csv"
EXPECTED = 21423
VALID = {"YES", "NO", "NOT_READY"}

pairs = json.load(open(QA / "pairs.json"))
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
    ans_c, nr_c, empty_owner = Counter(), Counter(), Counter()
    blank = bad = empty = 0
    old_sector_gap = 0
    for r in rows:
        a = (r.get("answer") or "").strip()
        why = (r.get("reason") or "").strip()
        if not a: blank += 1
        elif a not in VALID: bad += 1
        else:
            ans_c[a] += 1
            if a == "NOT_READY":
                nr_c[why.split(":")[0] if why else "(empty)"] += 1
                if not why: empty += 1; empty_owner[r["owner"]+"|NOT_READY"] += 1
            elif not why:
                empty += 1; empty_owner[r["owner"]+"|"+a] += 1
        if "no point-in-time stock->SPDR" in why:
            old_sector_gap += 1
    if blank: issues.append(f"blank_answer={blank}")
    if bad: issues.append(f"invalid_answer={bad}")
    if empty: issues.append(f"empty_reason={empty}")
    return {
        "issues": issues,
        "pass_strict": not issues,
        "answers": dict(ans_c),
        "nr_reasons": dict(nr_c),
        "empty_by_owner": dict(empty_owner),
        "old_sector_gap": old_sector_gap,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "nbytes": path.stat().st_size,
    }

# Detect stale
stale_idx = []
for i, p in enumerate(pairs):
    f = OUT / f"answers_{p['ticker']}_{p['date']}.csv"
    if not f.exists():
        stale_idx.append(i); continue
    v = validate(f)
    if v["old_sector_gap"] > 0:
        stale_idx.append(i)
print("stale_or_missing", [i+1 for i in stale_idx], flush=True)

results = []
# load prior progress for non-stale metadata if useful
prior = {}
if (QA / "progress.json").exists():
    for r in json.load(open(QA / "progress.json"))["results"]:
        prior[(r["ticker"], r["date"])] = r

for i, p in enumerate(pairs):
    t, d = p["ticker"], p["date"]
    out = OUT / f"answers_{t}_{d}.csv"
    if i in stale_idx or not out.exists():
        print(f"[refresh {i+1}/50] {t} {d} ...", flush=True)
        rc, stdout, stderr, elapsed = run_one(t, d, out)
        warn = [ln for ln in stderr.splitlines() if ln.startswith("WARN")]
        unknown = sum(1 for ln in warn if "UNKNOWN_ID" in ln)
        v = validate(out)
        rec = {**p, "out": str(out), "rc": rc, "elapsed_s": round(elapsed, 2),
               "stdout_tail": stdout.strip().splitlines()[-1] if stdout.strip() else "",
               "warn_count": len(warn), "unknown_id_warns": unknown, **v, "refreshed": True}
        print(f"  {'PASS' if v['pass_strict'] else 'FAIL:'+','.join(v['issues'])} old_gap={v['old_sector_gap']} ans={v['answers']}", flush=True)
    else:
        v = validate(out)
        old = prior.get((t, d), {})
        rec = {**p, "out": str(out), "rc": 0, "elapsed_s": old.get("elapsed_s", 0),
               "stdout_tail": old.get("stdout_tail", ""), "warn_count": old.get("warn_count", 0),
               "unknown_id_warns": old.get("unknown_id_warns", 0), **v, "refreshed": False}
        print(f"[keep {i+1}/50] {t} {d} {'PASS' if v['pass_strict'] else 'FAIL:'+','.join(v['issues'])} old_gap={v['old_sector_gap']}", flush=True)
    results.append(rec)

# Rerun 5 FRESH pairs (prefer post-patch, post-08-06): indices 21, 30, 35, 44, 49
rerun_idx = [21, 30, 35, 44, 49]
rerun = []
for idx in rerun_idx:
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

# Aggregate
nr_hist = Counter(); overall_ans = Counter(); empty_owner = Counter(); issue_hist = Counter()
for r in results:
    for k, c in r["nr_reasons"].items(): nr_hist[k] += c
    for k, c in r["answers"].items(): overall_ans[k] += c
    for k, c in r["empty_by_owner"].items(): empty_owner[k] += c
    for iss in r["issues"]: issue_hist[iss.split("=")[0] if "=" in iss else iss] += 1

summary = {
    "seed": 20261022,
    "expected_rows": EXPECTED,
    "n_pairs": 50,
    "n_pass_strict": sum(1 for r in results if r["pass_strict"]),
    "n_fail": sum(1 for r in results if not r["pass_strict"]),
    "n_refreshed": sum(1 for r in results if r.get("refreshed")),
    "overall_answers": dict(overall_ans),
    "not_ready_reason_histogram": dict(nr_hist.most_common()),
    "empty_reason_by_owner_answer": dict(empty_owner.most_common()),
    "issue_histogram": dict(issue_hist.most_common()),
    "rerun": rerun,
    "rerun_all_identical": all(x["identical"] for x in rerun),
    "total_elapsed_s": round(sum(r["elapsed_s"] for r in results), 1),
    "pairs_pre": sum(1 for p in pairs if p["era"] == "pre_08-06"),
    "pairs_post": sum(1 for p in pairs if p["era"] == "post_08-06"),
    "any_old_sector_gap": sum(r["old_sector_gap"] for r in results),
    "james_patched_note": "pairs with old SPDR gap string were re-run after james sector wire (universe D-1)",
}
json.dump({"summary": summary, "results": results}, open(QA / "results.json", "w"), indent=2)
json.dump({"done": 50, "results": results}, open(QA / "progress.json", "w"))
print(json.dumps(summary, indent=2))
print("FINALIZE_DONE", flush=True)

# Venice progress

Updated 2026-11-07T17:15 UTC

## Goal
Report each failed `nai-sec-*` / `nai-occ-oi-daily` run once with run ID + error, then stop. (TODO.md Venice lane @c7c31b0 — thin chatbot poke; GPT owns fixes.)

Gantt row: Venice lane (thin chatbot poke)
Verified progress: 87%
Current subtask: t6 (checkpoint rewrite)

| ID | Subtask | Status | Evidence |
|---|---|---|---|
| t1 | Confirm lane text in TODO.md, scan runs | done | TODO.md@c7c31b02e530a35d9944c705d19422d606956809 |
| t2 | Report run 42284432095 (nai-occ-oi-daily) | done | issues/220 |
| t3 | Replace inferred wording with report_failure canonical record | done | issues/220#issuecomment-6710271739 |
| t4 | Report run 42156926867 (nai-sec-form345) | done | issues/221 |
| t5 | First checkpoint | done | ba179d2306dbc448f85c9caa6ae07554e07cf192 |
| t6 | Rewrite checkpoint to cite canonical record | doing | this commit |

## Reported run IDs (do not re-report)

### 42284432095 — nai-occ-oi-daily, sha e85547a, job 128121492870 → #220
Canonical verified record: https://github.com/SRoyaltyy/checklist-engine/issues/220#issuecomment-6710271739
- Failed step: `Run python scripts/nai/occ_oi_daily.py`
- Skipped step: `Run python scripts/nai/oi_probe.py`
- Error lines:
  - `Traceback (most recent call last):`
  - `ValueError: invalid literal for int() with base 10: ''`
  - `##[error]Process completed with exit code 1.`

This report_failure record supersedes both the original body's inferred unguarded-DELO diagnosis and the earlier "oi_probe ran / logs truncated" correction. The unguarded DELO call at `scripts/nai/occ_oi_daily.py` line 8 remains an unverified inference and is not cited as cause.

### 42156926867 — nai-sec-form345, sha 8ec34d48, job 127693199421 → #221
- Failing step: `Run python scripts/nai/sec_datasets.py form345`, exit code 1.
- Traceback not captured for this run.

## Method
Use `report_failure(run_id)` for scheduled SEC/OI failures: it derives failed/skipped steps and exact error lines from the GitHub API, corrects earlier inferred reports, and dedupes persistently. Do not write freeform diagnoses. A failed probe differs from a skipped probe.

## Intentionally not reported
- 42106074154, 41906860199, 41710121137 — earlier occurrences of the same occ_oi_daily failure already covered by #220.
- 41413535355, 41413529249, 41413022188, 41413017909, 41413013359 — pre-e85547a superseded shas; historical, not current breakage.

## Last healthy run
42332789888 — nai-sec-form13f — success.

## Exact next step
Nothing open. Wait for the next scheduled `nai-sec-*` / `nai-occ-oi-daily` run; if it fails, get the job ID via `run_jobs`, then `report_failure(run_id)`, then stop.

## Blockers
None.

# Venice progress

Updated 2026-11-07T16:44 UTC

## Goal
Report each failed `nai-sec-*` / `nai-occ-oi-daily` run once with run ID + error, then stop. (TODO.md Venice lane @c7c31b0 — thin chatbot poke; GPT owns fixes.)

Gantt row: Venice lane (thin chatbot poke)
Verified progress: 86%
Current subtask: t5 (checkpoint)

| ID | Subtask | Status | Evidence |
|---|---|---|---|
| t1 | Confirm lane text in TODO.md, scan runs | done | TODO.md@c7c31b02e530a35d9944c705d19422d606956809 |
| t2 | Report run 42284432095 (nai-occ-oi-daily) | done | issues/220 |
| t3 | Correct #220 (oi_probe ran; logs truncated) | done | issues/220#issuecomment-6710061417 |
| t4 | Report run 42156926867 (nai-sec-form345) | done | issues/221 |
| t5 | Checkpoint this file | doing | — |

## Reported run IDs (do not re-report)
- 42284432095 — nai-occ-oi-daily, sha e85547a, job 128121492870, failing step `scripts/nai/occ_oi_daily.py`, exit 1 → #220 + correction comment
- 42156926867 — nai-sec-form345, sha 8ec34d48, job 127693199421, failing step `scripts/nai/sec_datasets.py form345`, exit 1 → #221

## Known limit of this lane
Every step on both failed jobs renders "This step has been truncated due to its large size. View the raw logs from the menu once the workflow run has completed." The bridge `job_log` therefore returns only runner/checkout scaffolding, never the Python traceback. Failure *step* is always provable; the exception text is not. Reports must say so rather than guess a cause. The unguarded OCC DELO call at `scripts/nai/occ_oi_daily.py` line 8 remains an unverified inference.

## Intentionally not reported
- 42106074154, 41906860199, 41710121137 — earlier occurrences of the same occ_oi_daily failure already covered by #220.
- 41413535355, 41413529249, 41413022188, 41413017909, 41413013359 — pre-e85547a superseded sha; historical, not current breakage.

## Last healthy run
42332789888 — nai-sec-form13f — success.

## Exact next step
Nothing open. Wait for the next scheduled `nai-sec-*` / `nai-occ-oi-daily` run; if it fails, get the job ID via `run_jobs`, then `job_log`, then one issue with `dedupe_key=run-<run_id>` and stop.

## Blockers
None.

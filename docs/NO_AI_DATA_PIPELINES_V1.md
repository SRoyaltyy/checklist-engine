# NO_AI_DATA_PIPELINES_V1

Plain-code collectors on GitHub-hosted runners (cron + workflow_dispatch). **No LLM calls, no bots in the loop.**
All output lands as release assets (not in git, not on the box). Scripts: `scripts/nai/`. UA: `checklist-engine research cyrus-checklist@users.noreply.github.com`.

| Workflow | Script | Schedule (UTC) | Release tag | Gantt row |
|---|---|---|---|---|
| nai-sec-bulk | sec_bulk.py | Sat 22:17 weekly | nai-sec-bulk-v1 | 1 Data / SEC |
| nai-sec-form345 | sec_datasets.py form345 | 5th monthly | nai-form345-v1 | 1 Data / SEC |
| nai-sec-form13f | sec_datasets.py form13f | 6th monthly | nai-form13f-v1 | 1 Data / SEC |
| nai-occ-oi-daily | oi_probe.py + occ_oi_daily.py | Tue-Sat 13:30 | nai-occ-oi-daily-v1 | 1 Data / Options + money-flow (#165) |
| nai-daily-forward | daily_forward.py | Tue-Sat 00:15 | nai-daily-forward-v1 | Options + money-flow / context |

Idempotent: per-file assets are skipped if present (form345/13f, OCC day, FINRA day); sec-bulk overwrites with `--clobber`.

## Run results
(filled in below after first runs)

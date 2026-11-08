# SEC/options workflow schedule inventory (Venice trial)

Task: workflow-schedule-audit-v1. Utility: `agent/workflow_schedule_audit.py`. This is a read-only configuration inventory. It reports what the workflow files declare; it never claims a scheduled run happened or that a run was missed.

## Usage

    python agent/workflow_schedule_audit.py \
      --workflows .github/workflows \
      --output artifacts/workflow_schedule_audit.json \
      --source-commit <40-character-sha>

`--source-commit` is optional and recorded verbatim when supplied. The CLI writes JSON for both outcomes and exits 0 on PASS, 1 on FAIL. Library entry point is `audit_directory(workflow_dir: pathlib.Path) -> dict`.

Dependency: `PyYAML>=6.0,<7`, declared in `agent/workflow_audit_requirements.txt`. The CI run logs the actual tested version.

## Selected sources

Only direct `.yml`/`.yaml` files in the given directory whose basename matches one of:

- `nai_sec_*` / `nai-sec-*` (each separator independently underscore or hyphen)
- `nai_occ_oi_daily` / `nai-occ-oi-daily`

No recursion. A symlink resolving outside the workflow directory is rejected. An empty selection is FAIL, not a green audit.

## Report schema

- `schema_version`: `1`
- `status`: `PASS` when every selected source is valid, otherwise `FAIL`
- `workflows`: sorted by filename; each entry has `path` (filename only), `sha256` of the exact file bytes, `name` (configured name or filename fallback), `events` (sorted unique event names), `schedules` (objects with nonempty `cron` and `timezone`)
- `errors`: objects with `path` and a message
- `source_commit`: present only when supplied

Timezone defaults to `UTC`; an explicit timezone is retained verbatim. There is no `next_run`, `missed` or timestamp field.

## Validation rules

- GitHub's three `on` forms are supported: single event string, event list, event mapping.
- A plain unquoted `on` key is retained despite PyYAML's YAML 1.1 boolean coercion.
- Duplicate mapping keys are rejected.
- Numeric or boolean trigger values, non-sequence schedules, missing `cron` and empty `cron` are rejected.
- Parsing uses a safe loader subclass; arbitrary Python object construction is never executed, and an unsafe tag produces an explicit error.
- Identical inputs produce identical data, including from different absolute directories; no absolute paths or generation timestamps appear in the report.

## CI evidence

`.github/workflows/venice-workflow-schedule-audit.yml` runs on push to `venice/workflow-schedule-audit-v1` only, with `contents: read`, `persist-credentials: false`, a 10-minute timeout and no repository secrets. It runs the unit suite, then the unchanged owner acceptance suite, then the CLI against the real `.github/workflows` directory with `GITHUB_SHA`, and uploads `workflow-schedule-audit-<run_id>` (retention 14 days) containing the report, both test logs, the PyYAML version and the source identity.

A non-zero CLI exit code is recorded in `audit-exit-code.log` rather than failing the job: a real production workflow that fails validation must be surfaced, not silently repaired, and this task may not edit production workflows.

# Owner-assigned Venice trial: deterministic SEC/options workflow inventory

Task ID: workflow-schedule-audit-v1. Work branch: venice/workflow-schedule-audit-v1, created from current main. This is an owner-approved coding trial; it supersedes passive monitoring as Venice's primary task until complete.

## Goal and project value

Build a deterministic, read-only inventory of the SEC/options workflow configuration. The current agent repeatedly reasons about possible missing scheduled runs. This utility provides the exact source configuration, source hashes and trigger definitions instead of guessing from old chat notes.

Do not claim a configured schedule actually executed or that a run was missed. No data collection, SEC requests, bulk downloads, production-pipeline edits or financial calculations are needed.

## Implementation contract

Implement agent/workflow_schedule_audit.py, exposing:

    audit_directory(workflow_dir: pathlib.Path) -> dict

Also expose a CLI:

    python agent/workflow_schedule_audit.py --workflows .github/workflows --output artifacts/workflow_schedule_audit.json --source-commit <40-character-source-sha>

CLI --source-commit is optional. When supplied, record it as source_commit. Do not include timestamps, absolute paths, unstable ordering or guessed execution state in the report.

Select only direct .yml/.yaml files whose basenames match these families:

- nai_sec_* or nai-sec-* (the separator after nai and sec may each be underscore or hyphen).
- nai_occ_oi_daily or nai-occ-oi-daily (each separator may be underscore or hyphen).

Ignore unrelated workflows. Do not recurse or follow a symlink outside the workflow directory. An empty selection is FAIL, not a successful audit.

Output must contain:

- schema_version: 1.
- status: PASS when all selected sources are valid, otherwise FAIL.
- workflows: sorted by relative filename, each with path (filename only), sha256 of exact file bytes, name (configured string or filename fallback), events (sorted unique event names), schedules (list of objects containing nonempty cron string and timezone string).
- errors: list of objects with path and a useful message. Report malformed selected YAML, duplicate mapping keys, unsupported unsafe tags/constructors and invalid trigger forms explicitly.
- timezone defaults to UTC when absent; retain an explicit timezone verbatim. This is configuration inventory only, with no next_run or missed-run prediction.

Support GitHub's normal on forms: a single event string, a list of event strings, or an event mapping. Correctly retain a plain unquoted on key: PyYAML's YAML 1.1 boolean coercion must not turn it into a missing key. Reject numeric/boolean trigger values and malformed schedule structures. A schedule must be a sequence of mappings with nonempty cron strings. Use safe parsing; never construct arbitrary Python objects.

CLI writes JSON for both PASS and FAIL, exits 0 for PASS and 1 for FAIL. Fatal command-line usage errors may use argparse's normal error behavior. The library's identical inputs must produce identical data, including in different absolute directories.

## Files Venice may create or edit

- agent/workflow_schedule_audit.py
- agent/workflow_audit_requirements.txt
- agent/fixtures/workflow_schedule_audit/**
- agent/requests/workflow-schedule-audit.json
- tests/test_workflow_schedule_audit.py
- docs/VENICE_WORKFLOW_SCHEDULE_AUDIT_V1.md
- .github/workflows/venice-workflow-schedule-audit.yml

No other production workflow or collector files may change. Never edit the owner acceptance suite agent/verification/test_workflow_schedule_audit_acceptance.py. Do not change the parent assignment or infrastructure to bypass a failing test.

## Required CI and evidence

Create the new workflow yourself on the assigned branch. It can execute before a main merge using an on: push trigger restricted to this exact branch and relevant code/test/request/workflow paths. Do not rely on a brand-new workflow_dispatch before registration. Use contents: read, checkout with persist-credentials: false, a job timeout no greater than 10 minutes, and no repository secrets.

PyYAML is an acceptable dependency; declare the requirement, install it in the runner, and report the actual tested version. No local-PC installation is needed.

The workflow must:

1. Run your own relevant unit tests.
2. Run the unchanged owner suite:

       python -m unittest discover -s agent/verification -p test_workflow_schedule_audit_acceptance.py -v

3. Run the CLI against the actual checked-out .github/workflows directory, using the actual GITHUB_SHA.
4. Upload the machine-readable report and test results as a named artifact, with explicit retention.

Use runs(branch=venice/workflow-schedule-audit-v1), run_status, run_jobs and job_log to identify the actual run and inspect failures. A dispatch acknowledgment or an unrelated green main run is not acceptance. Record head SHA, run ID, artifact name and any explicit limits.

## Work-session and coordination contract

The active machine assignment is agent/ACTIVE_TASK.json on main. The controller claims ownership. Every write_file needs expected_sha from a prior read, or null for a new file.

Each session must provide contribution.kind (implementation, verification, finding, blocker or completion), a concrete description and returned evidence. Preserve structured pitfalls with stable IDs, the failed approach, lesson and proof. Retain the exact branch, file map and next step. Repeating a status check is not a new subtask.

Break the goal into a compact plan: inspect sources/requirements; implement parser/report; write tests; create workflow; inspect actual CI; correct failures; document results; create PR; publish when permitted. Do not mark future actions complete before their results return.

If main advances, use branch_head and sync_branch, then ensure a test run matches the new head. Resolve a conflict within your permitted files; never overwrite other lanes. Use the request JSON or a meaningful allowed workflow change to request a fresh CI run when necessary.

## Completion and publication

Create a PR to main containing the implementation, tests, workflow and documentation. The owner explicitly permits autonomous merge for this task **only after** the deployment's publishing gate is enabled, the diff is in scope, current main is incorporated, and all checks on the exact PR head pass.

Owner update (2026-11-09): existing-key publication is explicitly approved. Shared-key rotation is optional and is not an acceptance condition for this trial. The live publication flag and exact-head checks remain required.

If publication is disabled, record a blocker with the PR URL and exact next step. Do not claim the goal complete. Remain ready to resume when publication is enabled; do not spam status updates or alter guards.

The supervising Codex chat will inspect the candidate independently, verify the unchanged acceptance suite, actual test execution and output source hashes, and monitor through the task's final outcome.
## Supervisor review before publication

The initial run passed the 12 candidate tests and 13 unchanged owner tests, and the real-source report was PASS. One workflow issue still needs correction: the audit step records a nonzero CLI exit but ends successfully, so a future invalid inventory could leave CI green. Preserve the report and logs with if: always(), then fail the audit step on a nonzero CLI result or report status FAIL. Update the documentation accordingly. Add agent/requests/workflow-schedule-audit.json to the workflow path filter so an explicit request can trigger a fresh run after sync. Incorporate current main and rerun on the resulting exact PR head before merge. Do not change the protected owner suite.

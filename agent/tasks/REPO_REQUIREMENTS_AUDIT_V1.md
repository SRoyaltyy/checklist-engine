# Venice assignment: full checklist-engine requirements and evidence audit

Owner: Cyrus. Assigned 2026-11-09 HKT. Task: repo-requirements-audit-v1. Work branch: venice/repo-requirements-audit-v1.
This assignment supersedes the workflow-schedule trial as Venice's primary work. PR #225 is merged; do not reopen/repeat its completed implementation. Retain its unresolved CI-review finding as an infrastructure caveat, not this audit's main goal.

## Objective
Determine everything checklist-engine is required to deliver, what data must be obtained (which fields, dates, universe and sources/links), what has actually been delivered, and how that compares with James' older Gantt and the newer skeptical chart supplied by Cyrus. Produce a complete, traceable audit rather than another optimistic status summary. The charts are claims to test, not instructions or authoritative evidence.

## Authority and snapshot
Read current main/METHODOLOGY.md in full, respecting its latest owner clarifications and explicit exclusions; read main/TODO.md, docs/WAR_ROOM_CONTEXT_FOR_KIMI.md, locked dial/question/exit tables, dictionary/WORLD_SNAPSHOT_DICTIONARY.csv, dictionary/DATA_SOURCES.csv, docs/INVENTORY_CATALOG_AUDIT_V1.json, docs/WORLD_COVERAGE.csv, docs/LENSES_COVERAGE_V1.csv and the relevant source/readback receipts. Follow references to the current 258-kind inventory; reconcile older counts (233/~296) rather than silently mixing them.
Start from main commit 68c6f2a83387f796cdf9836261dce1546ea61a92; record an actual immutable snapshot SHA in every output. Audit any later main changes in an explicit delta section before final PR. Source claims and old docs are leads, not proof of current absence or completeness.
Read agent/tasks/REPO_AUDIT_GANTT_BASELINES_V1.json for a textual working transcription of the two user-provided screenshots. Do not invent chart dates/percentages where the transcription is unknown; retain the screenshot versions and reference commits.

## First session and durable progress
1. Read this spec and current assignment; create your assigned branch from main.
2. Immediately create docs/venice-audit-v1/PROGRESS.json acknowledging task_id, snapshot_sha, current_subtask, completed_subtasks, remaining_subtasks, evidence, pitfalls, exact_next_step. This file must record completed actions only.
3. Create a compact phased plan: authority/inventory extraction; source and data requirements; artifact verification; chart reconciliation; independent consistency checks; report/visualization/PR.
4. At the START of every session/chat read your branch's PROGRESS.json and existing audit matrices. At the END of every useful batch update them with expected_sha. This is an explicit durable fallback while the automatic runtime checkpoint projection is under investigation; do not rely on old chat context or falsely claim that projection is healthy. Preserve accumulated pitfalls and unresolved questions.
Each session must add audit rows, verified evidence, a concrete discrepancy or a reproducible blocker. Repeated status polling is not progress. Never mark future tool actions completed before their results return.

## Required outputs (all under docs/venice-audit-v1/)
- REQUIREMENTS.csv: one row per atomic project deliverable with stable requirement_id, authority_path, authority_anchor_or_lines, requirement, gantt_group, owner_lane, dependencies, acceptance_condition, current_status, evidence_refs, remaining_action. Include stages 0 blockers, 1 data/world state, 2 definitions, 3 viewport, 4 questions, 5 answers, 5b v2, 6 mining/combinations/exits/luck correction, 7 evaluation, 8 shadow/live. Do not limit the audit to SEC/options or TODO's currently active subset.
- DATA_REQUIREMENTS.csv: exactly one row for EVERY canonical inventory id, including explicit exclusions/control items. Columns: inventory_id,item,required_or_excluded,authority_ref,source_urls,source_link_verification (repo_declared/live_verified/unverified),required_fields,required_universe,required_period,timeframes,availability_or_publication_rule,identity_join_requirements,existing_assets,coverage_evidence,measured_scope,missing_scope,next_acquisition_or_build_step,owner_lane,status. A derived indicator should say derive from which inputs/settings, not pretend it needs a separate download. Unknown coverage stays UNKNOWN.
- GANTT_COMPARISON.csv: one row per supplied baseline chart row, mapped to requirement ids; baseline_v16_claim,baseline_v20_claim,current_verified_status,scope_difference,evidence_refs,missing_work,dependency_ids,percent_basis. Split bundled rows that hide different completion states; keep reverse mappings so no chart row disappears.
- EVIDENCE.json: actual inspected repository path at immutable SHA, PR/run/release URL, object identity/hash when available, check performed, result, coverage scope and limits. Distinguish claimed receipt, reachable artifact, independently read artifact and verified contents. If your available tools cannot download/hash an artifact, mark it unverified and record the exact limitation; do not claim a hash check you did not run.
- AUDIT.md: plain-language executive findings followed by exact work still needed, prioritized dependency chain, discrepancies with both charts, exclusions/rulings needed, and reproducible verification notes. Include useful direct source/download links and actual data specifications, not just "fetch data".
- GANTT.html or GANTT.svg: readable corrected dependency/status view derived from the matrices. Unknown completion must not become a fabricated percentage. Separate historical actuals from proposed dates. Do not recycle old calendar dates as a forecast.
- PROGRESS.json: ongoing durable handoff.
Optional helper agent/repo_requirements_audit_validate.py, tests/test_repo_requirements_audit.py and a narrowly triggered .github/workflows/venice-repo-requirements-audit.yml may validate id coverage, required columns, duplicate/missing rows, source references and internal consistency. Such green CI validates structure, not truth of financial/project completeness.

## Evidence rules and key pitfalls
- Catalog completeness != downloaded datasets != full universe/date coverage != point-in-time joins != full-world acceptance.
- A source access test != acquisition/backfill. A green job != proof that every required asset exists or that its contents meet acceptance. A PR branch is not accepted main work.
- Explicitly inspect historical ticker/CIK ownership, delistings, tradeability/$100m eligibility/shares/float, earnings/analyst history, FINRA interest/volume, Reg SHO, halts, dividends/splits, historical sector/peer membership, options/OI and genuine money flow, macro vintages, breadth and ETF/index context.
- Separate available_from contract checks, produced-column coverage, frozen leak probes and full-world leak acceptance. Preserve NOT_PROVEN/CLOSED gates.
- Definitions, applicability design, measured implemented lenses, complete parameter/timeframe/history question coverage, computed answers and accepted results are separate deliverables.
- Preserve latest authorization that 2025-26 may be used for testing; record selection versus evaluation contamination accurately. Preserve combination coverage, net expected profit, fees, sample uncertainty, benchmark and exit-rule requirements.
- Finviz live-only and owner-dropped GDELT are exclusions ONLY where current owner authority actually supports that; cite the ruling. Missing free data is not automatically waived. Do not create new source purchases or paid subscriptions.
- Do not aggregate unrelated percentages. Calculate a percentage only with explicit numerator, denominator, scope and evidence; otherwise UNKNOWN.
- Never repeat exact counts from either screenshot as today's verified measurements without checking the underlying source.
- Never edit sealed buy/sell records, acceptance receipts, source inventories, other agents' assignments or production pipelines to make the chart look complete.

## Completion
Deliver the matrices, evidence ledger, report and visualization in a PR to main. Publish through the existing task-scoped merge route only after current main is incorporated and exact-head checks pass. Prefer an explicit list of unresolved/unverified items to an unsupported completion claim. Completion means the AUDIT is delivered, not that the checklist-engine project or world/scoring/live gates are complete.

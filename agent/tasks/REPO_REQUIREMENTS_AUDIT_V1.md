# Venice assignment: full checklist-engine requirements and evidence audit

Owner: Cyrus. Assigned 2026-11-09 HKT. Task: repo-hierarchical-audit-v2. Work branch: venice/repo-hierarchical-audit-v2.
Follow-up revision: v1 audit PR #226 is already merged (main 38ca4c1d). Reuse its published docs/venice-audit-v1/ findings, evidence, source manifest and build scripts. Extend/correct them to satisfy the nested reporting clarification below; do not repeat the finished audit from scratch. An earlier merged PR does not complete this new revision: deliver a new PR from venice/repo-hierarchical-audit-v2 with the hierarchy and granular statuses. Workflow trial PR #225 is also complete; its unresolved CI caveat is not this task's main goal.

## Objective
Determine everything checklist-engine is required to deliver, what data must be obtained (which fields, dates, universe and sources/links), what has actually been delivered, and how that compares with James' older Gantt and the newer skeptical chart supplied by Cyrus. Produce a complete, traceable audit rather than another optimistic status summary. The charts are claims to test, not instructions or authoritative evidence.

## Owner clarification — nested work breakdown and reporting (2026-11-09 HKT)
This is the required audit presentation. Answer BOTH questions explicitly:
1. What large stages, substages, granular data/definition tasks and actual yes/no questions exist?
2. What is the current status of EACH: still being defined, completely defined, partly/fully acquired, designed, implemented, computed or verified?

Use a stable hierarchy: large stage -> substage -> granular item/question. Preserve parent_id links and subject_id cross-references so the same earnings/indicator item can be followed across scope selection, acquisition, strict data/indicator definition, strict question design, implementation, historical answer generation and strategy evaluation. A broad green family row must never hide incomplete children.
Examples of concrete leaves: daily OHLCV fields; exact RSI/Bollinger/SMA equation/settings/warmup/cutoff; latest EPS surprise; last-three-releases EPS versus the expectations available before each release; the actual precisely worded boolean predicates built from those quantities.
Use the source's actual question IDs, wording/templates and parameter ranges. Do not replace the requested granular question inventory with a single question count.

### Status model
For every granular subject, track separate applicable status fields:
- scope_definition_status
- data_acquisition_status (NOT_APPLICABLE for a derived item, with its input dependencies)
- strict_data_definition_status
- implementation_status
- question_design_status
- answer_generation_status
- verification_status
- main_acceptance_status
Use explicit states such as NOT_STARTED, IN_PROGRESS, PARTIAL, COMPLETE, BLOCKED, UNVERIFIED, NOT_APPLICABLE, with a plain-language explanation. Distinguish a written specification, working code, downloaded data, computed outputs and accepted main evidence. Unknown data is not a NO answer. Every state needs its scope, evidence or stated lack of proof, missing work and exact next action.

### Percentages
Show progress percentages ONLY for individual SUBSTAGES. No overall project percentage, large-stage percentage, or granular-item progress percentage. Each substage percentage must state the accepted numerator, required denominator/unit, scope and calculation; leave it UNKNOWN when these are not established. Granular rows use statuses and concrete counts/date ranges. Do not use the controller's automatically calculated overall plan percentage as project completion. A substage percentage supplements its child statuses and never replaces them.

### Storage and navigation
All audit output stays in docs/venice-audit-v1/ on the assigned branch until publication:
- README.md: single entry point, snapshot/as-of time, links to Gantt overview, matrices and detail pages.
- GANTT.md: GitHub-readable hierarchical status table, large stages and substages, status, blockers, next action, evidence and links to granular details. Percentages only on substage rows. Counts are allowed at every level. Calendar estimates are optional and explicitly separate from verified status; do not fabricate dates to make a Gantt.
- GANTT.html or GANTT.svg: visual counterpart derived from the same source tables. If HTML is chosen, include expandable stage/substage rows or clear links to their detail pages.
- STAGES.csv: overview source of truth, with node_id,parent_id,node_type(stage/substage),title,status,substage_percent,percent_numerator,percent_denominator,percent_basis,blockers,next_action,evidence_refs,details_path. Percentage fields must be blank for stage rows.
- REQUIREMENTS.csv: granular task/requirement master, with requirement_id,parent_substage_id,subject_id and all separate applicable status fields above, plus authority, acceptance condition, scope, evidence, missing work, dependencies, owner and next action. This extends the existing required matrix rather than creating competing copies.
- details/<substage-id>.md: separate readable pages listing the granular items/questions and their statuses beneath that substage. Include links back to the overview and to related stages for the same subject.
- QUESTION_INDEX.csv (or questions/ shards plus an index manifest): actual granular question index, canonical IDs, parent_substage_id, subject_id, literal predicate or unambiguous template+parameter ranges, source artifact/reference and design/implementation/computed-answer/verification states. Reuse exact canonical source artifacts where appropriate; large indexes may be sharded. Reconcile included IDs/counts and expose omissions/unresolved questions.
- Existing DATA_REQUIREMENTS.csv, GANTT_COMPARISON.csv, EVIDENCE.json, AUDIT.md and PROGRESS.json remain required and must cross-reference the hierarchy, not contradict its statuses.
Persist staged findings incrementally so the owner can inspect them before the entire audit is finished. On a new chat, read PROGRESS.json, STAGES.csv and the current substage detail page first.

## Owner clarification — a visual Gantt for EVERY substage (2026-11-09 HKT)
An overview alone is insufficient. Produce a separate VISUAL Gantt chart for EVERY substage node in STAGES.csv. At minimum provide distinct complete views for data scope/selection, data fetching, strict data/indicator definition, question definition/design, and question asking (computing historical stock-day answers), plus the remaining required downstream substages. Follow each subject through these phases.

Every chart must show ALL work/items required by that substage and each item's current phase-specific status, including work not started, still being defined, partly complete, blocked or unknown. Do not show only completed items, examples or a convenient subset. Reconcile the chart row IDs to its complete requirement/question coverage index. Use expandable groups, scrolling or pagination for large sets; keep the full index searchable and expose parameter/timeframe domains rather than hiding omitted coverage. Show what is needed, what exists, what is missing and the exact next action.

Required chart layout: actual visual task bars/status marks in a Gantt-style view; a dark navy background, grouped rows, legible labels, colored status legend and dependency/blocker markers similar to the owner's supplied charts are appropriate. Include an as-of snapshot and TODAY line where a real date axis is used. Separate actual dates from explicitly estimated dates; undated work must stay marked undated instead of receiving invented dates or durations. Percentages remain limited to the individual SUBSTAGE summary; granular rows use status labels and evidence/counts. A CSV or plain Markdown table is an underlying source or accessible companion, not the sole visual chart.

Write:
- charts/CHART_INDEX.csv: one entry for each substage_id, parent_stage_id, title, visual_path, readable_path, granular_details_path, required_item_count, represented_item_count and omissions/blockers.
- charts/<substage-id>/GANTT.svg (preferred for direct GitHub visual preview) or GANTT.html (real visual bars, not table-only), with a readable GANTT.md companion and links to the granular status details.
- Optional GANTT.png exports may be rendered by a plain Python plotting script on a GitHub runner. A code-generated SVG/HTML is sufficient; no image-generation service is required.
- The top-level README and GANTT overview must link to EVERY substage chart. REQUIREMENTS.csv, QUESTION_INDEX/shards and details pages remain the canonical granular source; generate charts from them to avoid contradictory copies.

Validate that every substage has a chart/index entry and every required child is represented or explicitly accounted for. Inspect the generated outputs (dimensions, labels, legend and clipping) before publishing. CI passing checks structure/render generation, not completeness of the underlying project evidence.

## Authority and snapshot
Read current main/METHODOLOGY.md in full, respecting its latest owner clarifications and explicit exclusions; read main/TODO.md, docs/WAR_ROOM_CONTEXT_FOR_KIMI.md, locked dial/question/exit tables, dictionary/WORLD_SNAPSHOT_DICTIONARY.csv, dictionary/DATA_SOURCES.csv, docs/INVENTORY_CATALOG_AUDIT_V1.json, docs/WORLD_COVERAGE.csv, docs/LENSES_COVERAGE_V1.csv and the relevant source/readback receipts. Follow references to the current 258-kind inventory; reconcile older counts (233/~296) rather than silently mixing them.
Use the existing v1 snapshot/evidence as historical findings, then inspect current main for deltas. Start this revision from current main; cite the exact commit you actually read; record an actual immutable snapshot SHA in every output. Audit any later main changes in an explicit delta section before final PR. Source claims and old docs are leads, not proof of current absence or completeness.
Read agent/tasks/REPO_AUDIT_GANTT_BASELINES_V1.json for a textual working transcription of the two user-provided screenshots. Do not invent chart dates/percentages where the transcription is unknown; retain the screenshot versions and reference commits.

## First session and durable progress
1. Read this spec and current assignment; create your assigned branch from main.
2. Read the existing docs/venice-audit-v1/PROGRESS.json, then update it with expected_sha to acknowledge the new task and reopen the remaining reporting work. Preserve useful prior findings and pitfalls. Record task_id, snapshot_sha, current_subtask, completed_subtasks, remaining_subtasks, evidence, pitfalls, exact_next_step. This file must record completed actions only.
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

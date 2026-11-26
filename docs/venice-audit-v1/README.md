# Repository requirements audit v2

Evidence-only audit of every project stage, substage and granular requirement in this repository, including the yes/no questions the scanner needs and where each item stands in its lifecycle. It is a reporting layer: it changes no production pipeline, inventory, receipt or sealed record, and completing the audit opens no world, scoring or live gate.

## Read in this order

1. `GANTT.md` — nested overview: every large stage, its substages and their granular detail pages.
2. `details/<substage-id>.md` — one page per substage, listing every child requirement with its eight separate lifecycle statuses, authority path and remaining action.
3. `charts/<substage-id>.svg` — one actual visual Gantt per substage, one lane per child requirement and one cell per lifecycle status. Indexed in `charts/CHART_INDEX.csv`.
4. The matrices: `REQUIREMENTS.csv` (granular requirements and statuses), `DATA_REQUIREMENTS.csv` (fields, universe, periods, source links), `STAGES.csv` (stage and substage rows), `GANTT_COMPARISON.csv` (v16 and v20 chart claims against main evidence), `QUESTION_INDEX.csv` and `questions/` (the concrete yes/no questions), `EVIDENCE.json` (evidence ledger), `SOURCE_MANIFEST.json` (provenance).

## Percentage scope

A percentage exists only on an individual substage row. It is numerator = child requirements whose main_acceptance_status is COMPLETE over denominator = child requirements in that substage. Large stages, the whole audit and every granular item carry no computed percentage, and nothing is aggregated upward.

## The eight status dimensions

- **Scope** (`scope_definition_status`) — is the requirement written down precisely enough to act on.
- **Data** (`data_acquisition_status`) — is the required data actually present in the repo or a linked source.
- **Strict data** (`strict_data_definition_status`) — are universe, period and field contracts pinned.
- **Impl** (`implementation_status`) — does code that uses the data exist.
- **Design** (`question_design_status`) — is a yes/no question with a literal predicate written.
- **Answer** (`answer_generation_status`) — has the question been evaluated over the data.
- **Verify** (`verification_status`) — has the answer been checked against evidence.
- **Main** (`main_acceptance_status`) — is the result merged and accepted on main.

A single item can be fully scoped and still unimplemented, or implemented and unverified; the dimensions are recorded separately on purpose so a green step cannot be read as completion.

## Structure

10 large stages > 20 substages > 47 granular requirements. 2 requirements are main-accepted.

## Provenance and regeneration

Every artifact here is generated offline from authority files under `docs/`, `agent/tasks/` and the inventories, in this order: `build_extra.py`, `build_gantt.py`, `build_hierarchy.py`, `build_questions.py`, `build_charts.py`, `build_report.py`. The CI workflow `.github/workflows/venice-repo-requirements-audit.yml` runs the same order on the audit branch, runs the source-matched tests, and commits any drift. Hand-editing a generated file is therefore temporary.

Statuses are read from evidence: a catalog row or a green job alone is not treated as completion. Where evidence was absent the status is UNVERIFIED and the gap is named in `missing_work`.

## Limits

This is a v2 revision of the published v1 audit and reuses its findings; it adds the requested hierarchy, the per-item status separation and the per-substage visuals. Percentages are descriptive of main-acceptance only, not an estimate of remaining effort.

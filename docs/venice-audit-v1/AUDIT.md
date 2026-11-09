# checklist-engine - corrected requirement status audit

Task: `agent/tasks/REPO_REQUIREMENTS_AUDIT_V1.md` (assignment `repo-requirements-audit-v1`).
Branch: `venice/repo-requirements-audit-v1`. Deliverable: a tested PR.

This report audits requirements and evidence. It acquires no data, opens no gate, and
changes no other lane's work. Nothing here may be read as proof that the world state,
scoring, or live trading is ready.

## 1. Snapshot

| Field | Value |
| --- | --- |
| Audit spec base | `68c6f2a83387f796cdf9836261dce1546ea61a92` |
| Live `main` observed during this audit | `c30c23bed24dc986b2bbf5a4b559a022e2df4300` |
| Older chart (v16) | as_of 2026-11-07 08:55 HKT, ref `e85547ac99a28737321c063cf15cd96729c229ce` |
| Skeptical chart (v20) | as_of 2026-11-09 01:13 HKT, ref `2ba3ebdf977df51e7ab7e1993fdfee27faf19939` |
| Canonical inventory | 258 ids: `C01`...`C3x`, `I1`...`I228` |
| Control exclusions | `C28` (bucket/threshold boundary), `C29` (leak/PIT) - exclusions, not gaps |
| Authority files | `WORLD_SNAPSHOT_DICTIONARY.csv@9412f478`, `DATA_SOURCES.csv@c9d9af05`, `LENSES_COVERAGE_V1.csv@fa338f19`, `WORLD_COVERAGE.csv@756f6a36` |

Every artifact in this directory records the snapshot it was generated from. Main has
advanced past the audit spec base; section 9 states what still needs re-checking.

## 2. Evidence tiers

A chart claim, a reachable file, and a re-read file are three different things. This
audit separates them and never upgrades one into another.

| Tier | Meaning |
| --- | --- |
| Claimed receipt | A run ID, commit, or count asserted by a chart or a prior note. Not proof. |
| Reachable artifact | The path exists at an immutable blob SHA. Existence only. |
| Independently read artifact | This audit opened the artifact and read the relevant rows or header. |
| Verified contents | The read artifact actually supports the claim at the stated scope, and the limits are written down. |

The machine-readable ledger is `EVIDENCE.json`. Each entry carries `kind`, `check_performed`,
`result`, `coverage_scope`, and `limits`. A `reachable_artifact` entry is never presented as
verified contents.

## 3. Gate status

The three gates stay shut. This is not a judgement call; it follows from the evidence.

- **World state: NOT PROVEN.** `docs/WORLD_COVERAGE.csv` still contains `PENDING` and
  unmeasured rows; the price row used by every downstream stage is
  `dictionary/C01/1d` with status `PENDING` and universe
  `SIX_STOCK_PROVISIONAL_NOT_FULL_UNIVERSE`.
- **Scoring / final results: CLOSED.** Prerequisites (measured world coverage, genuine
  resampled timeframes, complete question coverage, comprehensive leak verification) are
  not met, so any probability figure produced today remains provisional.
- **Shadow / live: CLOSED by design.** No paper-to-live promotion is in scope for an audit.

## 4. Requirement status by stage

The row-level detail is `REQUIREMENTS.csv` (11 columns, stages 0 through 8).

### Stage 0 - Blockers
- `R0.1` Legacy replay and quarantine closure: **NOT_PROVEN**. The v20 chart reports 166
  unresolved replay mismatches; no row-by-row reconciliation exists.
- `R0.2` 100-name price sample: **VERIFIED_PARTIAL**. Green as a sample only; it must never
  be cited as full-universe coverage.
- `R0.3` Full world gate: **NOT_PROVEN**. Depends on `R1.1`, `R1.3`, `R1.12`, `R1.13`, `R1.14`.
- `R0.4` Full-cohort PIT measurement with packet replay: **NOT_PROVEN**. 8439/8439 measured is
  not the same claim as packet replay passing; the v20 chart reports 1308 replay failures.
- `R0.5` Price `available_from` contract: **VERIFIED_PARTIAL**. 22968 bindings only.
- `R0.6` Price join identity contract: **NOT_PROVEN**. Identity proven for 8439 keys / 9271
  sessions is not historical identity for the whole retained universe.
- `R0.7` SEC runner access: **VERIFIED_ACCESS_ONLY**. Access is not acquisition and must not be
  reported as a downloaded panel.

### Stage 1 - Data
- `R1.1` Canonical inventory: **VERIFIED**. 258 ids enumerated from the authority CSVs, with
  `C28`/`C29` recorded as explicit controls. This proves catalog membership only.
- `R1.2` One data-requirement row per id: **VERIFIED** structurally.
  `DATA_REQUIREMENTS.csv@531b1d19` has the 19-column contract and 258 data rows; `UNKNOWN`
  fields are left as `UNKNOWN` rather than guessed.
- `R1.3` Full-universe daily OHLCV 2015-2026: **NOT_PROVEN**. The authoritative coverage row is
  `PENDING` with a six-stock provisional universe.
- `R1.4` Macro PIT vintages: **VERIFIED_PARTIAL**. A 21-series FRED/ALFRED PIT pass exists;
  joins into the world remain `UNKNOWN`.
- `R1.5` Earnings history: **NOT_PROVEN**. 112760 rows over 4195 names is not the 8439-name
  universe.
- `R1.6` Analyst estimate history: **NOT_PROVEN**. 350374 rows over 4041 names; PIT unproven.
- `R1.7` / `R1.8` FINRA short interest and short volume: **NOT_PROVEN**.
- `R1.9` Reg SHO daily list: **NOT_PROVEN**. Only a legacy asset exists.
- `R1.10` Halts: **NOT_PROVEN**. Only derived result tables exist, not the raw tape.
- `R1.11` Dividends and splits: **NOT_PROVEN**.
- `R1.12` Historical index membership: **NOT_PROVEN**. Current-only membership cannot support
  point-in-time work.
- `R1.13` Historical sector and peer membership: **NOT_PROVEN**. Rank lenses depend on it.
- `R1.14` Options chains and open interest: **NOT_PROVEN**. OCC probe failed, the Dolt any-row
  figure is 21.42 percent of the tested set, and no open interest source is accepted. Source
  selection is unresolved and no new paid source is authorized.
- `R1.15` Signed money flow, block/dark-pool prints, ETF flows: **NOT_PROVEN**.
- `R1.16` SEC bulk submissions panel: **VERIFIED_PARTIAL**. Readback passed on 246 assets;
  identity join reported at 61.13 percent; world coverage `UNKNOWN`.
- `R1.17` / `R1.18` SEC Form 4 and 13F panels: **NOT_PROVEN**. A draft workflow and a cached
  green run are not an accepted panel on main.
- `R1.19` Tradeability, dollar volume, shares outstanding, float: **NOT_PROVEN**.
- `R1.20` Market breadth: **VERIFIED_PARTIAL**. Native computation passes with a survivor-only
  caveat that has not been resolved.
- `R1.21` ETF and index context joins: **NOT_PROVEN**.
- `R1.22` Finviz live-only fields: **EXCLUDED_PENDING_RULING**. The owner ruling must be located
  and cited; it may not be waived by assumption.
- `R1.23` GDELT: **EXCLUDED_PENDING_RULING**. Same requirement.
- `R1.24` No-AI pipeline document: **NOT_PROVEN**. A skeleton exists with blank run results.
- `R1.25` Webull money-flow snapshots: **NOT_PROVEN**. Zero accepted, no main delivery proof.

### Stage 2 - Definitions
- `R2.1` Fourteen-lens design and 114 strict definitions: **VERIFIED_PARTIAL**. Design is on
  main; rulings 5-8 have no main proof.
- `R2.2` Measured implemented-lens count per id: **NOT_PROVEN**. Rows are `UNMEASURED` with
  class-level applicability only.

### Stage 3 - Viewport
- `R3.1` Chart viewport: **NOT_PROVEN** in this lane. PR #163 is unmerged work owned by another
  lane; this audit records the state and does not start that work.

### Stage 4 - Questions
- `R4.1` Complete question framework with the history lever: **VERIFIED_PARTIAL**. 107201 bound
  definitions exist; answers are not passed; semantic completion is `UNKNOWN`.
- `R4.2` Question batch 27: **NOT_PROVEN**. PR #224 shows CI PASS but is unmerged, so the batch
  is not accepted main work.

### Stage 5 and 5b - Answers and V2 ladders
- `R5.1` Computed answers for the full question set: **NOT_PROVEN**. Zero accepted.
- `R5B.1` V2 ladder and alias completion: **NOT_PROVEN**. 2664 ladders plus 80 aliases exist;
  semantic completion is `UNKNOWN`.

### Stage 6 - Mining
- `R6.1` Combination coverage with published interaction orders: **NOT_PROVEN**. No
  searched-interaction evidence exists on main. A low-rank state-by-rule result is not proof
  that every question-by-question combination was searched.
- `R6.2` Exit-rule registry applied per setup: **NOT_PROVEN**. 26100 exit rules planned, zero
  accepted.
- `R6.3` Luck correction and same-day benchmark: **NOT_PROVEN**. Zero accepted.

### Stage 7 - Evaluation
- `R7.1` Required per-tuple statistics: **NOT_PROVEN**. No accepted results. A win probability
  is not expected profit and must never be reported as if it were.
- `R7.2` Selection versus evaluation period labelling: **NOT_PROVEN**. There is no result
  inventory to label yet. 2025-2026 is authorized for testing, but any period that informed
  tuning cannot later be described as untouched out-of-sample evidence.
- `R7.3` Comprehensive leak and look-ahead verification: **NOT_PROVEN**. Three probe names
  (BPOP, DJCO, KGRN) do not cover the produced field set.

### Stage 8 - Shadow and live
- `R8.1` Shadow trading: **CLOSED**. Paper only, gates closed by design.
- `R8.2` Live trading: **CLOSED**. Never opened by an audit.

## 5. Chart reconciliation

Where the older v16 chart and the skeptical v20 chart disagree, this audit does not pick a
winner by seniority. It records the scope difference and what evidence would settle it. The
row-level version is `GANTT_COMPARISON.csv`; the rendered version is `GANTT.html`.

Settled by evidence:
- Catalog membership (258 ids) is verified; **downloaded datasets are not**. Any chart row that
  treats a catalog entry as acquired data is wrong.
- SEC endpoint access is proven; **acquisition is not**. A green access probe is not a panel.
- The 100-name price sample is green as a sample and is not world coverage.
- FRED/ALFRED PIT vintages pass for 21 series; world joins remain `UNKNOWN`.
- Breadth computes natively; the survivor-only caveat is unresolved.

Bundled rows split (each component now carries `split_from`):
- `D2` splits into macro vintages (`R1.4`), earnings (`R1.5`), short interest (`R1.7`),
  halts (`R1.10`), dividends and splits (`R1.11`), and breadth (`R1.20`). A single verdict for
  that bundle hid six different states.

Claims neither chart settles:
- The 166 replay mismatches (`R0.1`) and 1308 packet-replay failures (`R0.4`) have no row-level
  reconciliation, so "almost done" is not a supportable reading.
- Historical identity (`R0.6`, `R1.12`, `R1.13`) is asserted at partial scope only.
- The options/open-interest source decision (`R1.14`) is open, and no new paid source is
  authorized, so the resolution must come from an existing acceptable source or an owner ruling.

## 6. Dependency-ordered backlog

Ordered by what unblocks the most downstream work. Each step names the requirement it advances.

1. `R1.3` Price full-universe acquisition and measurement. This is the root blocker: eligibility,
   corporate actions, joins, breadth, and every backtest read price.
2. `R1.12` and `R1.13` Dated index, sector, and peer membership. Rank lenses cannot be honest
   without point-in-time membership.
3. `R0.6` Historical ticker/CIK identity for the full retained universe. Without it, SEC and price
   joins silently mis-attribute history.
4. `R0.1` and `R0.4` Replay and packet-replay reconciliation. Publish a row-level mismatch list
   rather than a count.
5. `R1.19` Tradeability, dollar volume, shares outstanding, and float per name per date.
6. `R1.14` Options chain and open-interest source decision, constrained to existing acceptable
   sources or an owner ruling.
7. `R1.16` to `R1.18` SEC panels on main with a proven identity join, extending the current
   61.13 percent identity figure.
8. `R1.5` to `R1.11` Remaining fundamentals and event histories, each measured against the full
   universe rather than a subset.
9. `R1.15` and `R1.25` Signed money flow, block/dark-pool prints, ETF flows, and the Webull
   snapshot pipeline.
10. `R2.2` Per-id implemented-lens measurement, once `R2.1` rulings 5-8 are cited.
11. `R5.1` Answer computation, then `R6.1` to `R6.3` searched combinations, exit rules, and the
    luck-corrected benchmark.
12. `R7.1` to `R7.3` Per-tuple statistics, period labelling, and comprehensive leak verification.
13. `R0.3` World gate, then scoring. Only after 1-12 can a final shortlist be described as
    supported.
14. `R8.1` and `R8.2` remain closed regardless of the above; opening them is an owner decision,
    not an audit output.

## 7. What this audit does not prove

- It downloaded nothing and measured no coverage itself. Every status is a verdict on a cited
  artifact; `GANTT_COMPARISON.csv` marks a row `UNVERIFIED` wherever this audit did not re-read
  the underlying artifact.
- It did not re-run other lanes' pipelines and does not diagnose their failures.
- It does not open, and cannot open, the world, scoring, or live gates.
- A green CI run proves the matrices were regenerated from the pinned authority files. It proves
  nothing about data quality.

## 8. Reproducing these outputs

```
python docs/venice-audit-v1/build_matrices.py
```

That writes `DATA_REQUIREMENTS.csv`, `SOURCE_MANIFEST.json`, then `REQUIREMENTS.csv`,
`GANTT_COMPARISON.csv`, `EVIDENCE.json`, and `GANTT.html`. The generator aborts if any baseline
chart row is missing from the comparison, so the rendered chart cannot silently lose a row.

## 9. Delta since the audit spec base

The spec was written against `68c6f2a8`; live main was observed at `c30c23be`. Re-check before
treating any status above as current:

- Any new commit touching `docs/WORLD_COVERAGE.csv`, `docs/LENSES_COVERAGE_V1.csv`,
  `dictionary/DATA_SOURCES.csv`, or `dictionary/WORLD_SNAPSHOT_DICTIONARY.csv` invalidates the
  pinned blob SHAs in `SOURCE_MANIFEST.json` and requires a rebuild.
- PRs #163 and #224 are tracked as unmerged. If either merges, `R3.1` and `R4.2` change state and
  this report must be updated rather than left stale.
- Any accepted SEC panel landing on main changes `R1.16` to `R1.18`.
- No percentage in this audit moves on its own. Every figure needs a stated numerator,
  denominator, and scope, or it stays `UNKNOWN`.

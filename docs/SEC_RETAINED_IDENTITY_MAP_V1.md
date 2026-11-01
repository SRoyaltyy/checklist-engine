# Retained-cohort SEC identity map (archive-only)

Gantt: **`[1 Data / SEC / analyst / sector history]`** — measured identity coverage for the price retained cohort (**8,439** names from `compact-world-build-composed-v1-41221028803-1`).

## Counts

| Metric | N | % of 8,439 |
| --- | ---: | ---: |
| UNIQUE CIK safe for companyfacts join | 3,996 | 47.35% |
| … with shares-outstanding **filed-dated** ticker↔CIK association | 3,996 | 47.35% |
| Formal ticker `valid_from`/`valid_to` ledger rows | 0 | 0% |
| Quarantined issuer/ETN product aliases (submissions undated) | 24 | 0.28% |
| NO_CIK (unresolved) | 4,419 | 52.36% |

Machine-readable: [`SEC_RETAINED_IDENTITY_MAP_V1.json`](SEC_RETAINED_IDENTITY_MAP_V1.json) (per-ticker records + method).

## Method (provider_requests = 0)

1. **Retained cohort** = `completed[]` tickers in release `compact-world-build-composed-v1-41221028803-1` / `COMPACT_WORLD_BUILD_COMPOSED.json`.
2. **Dated association** = `data-2020-24-v1` / `sec_shares_out_filed_le_2024.parquet` (`ticker`,`cik`,`filed`,`form`,`accn`). A row means that ticker was used on a shares-outstanding fact filed on `filed` — **not** a full symbol-history ledger.
3. **Undated alias scan** = verified root `*.submissions.json.gz` members from all **208** archives bound by `docs/SEC_CIK_SOURCE_INDEX_V1.json` (releases `sec-world-v4-40267486206-1` + `sec-world-shard9-repair-40282669220-1`). Member SHA-256 checked; **4,034/4,034** extracted; **0** hash mismatches.
4. **Baseline** = release `SEC_WORLD_IDENTITIES.json` (4,040 UNIQUE / 4,687 NO_CIK on the 8,727 universe; `company_tickers.json` was `BLOCKED_OR_ERROR`).
5. **Issuer/ETN quarantine** = 24 retained tickers that appear only as undated tickers on bank issuer submissions (BMO / Deutsche Bank / JPM). Listed in JSON quarantine; **excluded** from safe join counts.

## Quarantine

- CIK **1790169** ZeroStack Corp. — integrity quarantine from `SEC_FULL_SOURCE_PROOF_SUMMARY.json` (unchanged).
- **24** issuer/ETN aliases — see JSON `quarantine[]`.

## What this does *not* claim

- Not historical tradeability / point-in-time ticker ownership.
- Not Form 4 / 13F / analyst / sector history.
- Not full-world SEC native production (still the 20-CIK sample only).
- Does not resolve GOOGL / META / ABT / most ETFs: those CIKs were never in the frozen shares map, so they were never collected into sec-world archives. Archive-only reuse cannot create them.

## Honest Gantt %

Propose **~18%** amber for this row (was ~15%): identity map for the retained cohort is now **measured and published**. Do **not** read 47% unique-CIK as bar completion — downloads/joins for Form4/13F/XBRL/analyst/sector and `world_gate` remain open.

## Exact next step (Form4 / 13F / XBRL) — no CDN hammer

1. **Fix relay** so `www.sec.gov/files/company_tickers.json` returns 200 (known UA/contact issue in METHODOLOGY). Re-run **only** `fetch_sec_world prepare` (workflow `world_full_sec.yml` prepare job) to extend the identity map — **do not** recollect all companyfacts yet.
2. **Missing-CIK collect (bounded):** after prepare, collect submissions+companyfacts **only for newly resolved CIKs absent from** `SEC_CIK_SOURCE_INDEX_V1`, checkpoint to a new release tag.
3. **XBRL/companyfacts join for the existing 4,033 eligible CIKs:** offline native expansion from `sec-native-sample-v1-40633006364-1` using `ci/sec_archive_state_measure.py` / `SEC_FILING_STATE_V1.md`; `available_from` = acceptance/filed **&lt; D**.
4. **Form4:** hold `world_fetch_form4.yml` / `phase1_sec_bulk_launch.yml` until relay allows SEC quarterly bulk zips; then join on CIK with `available_from` = acceptance/filed &lt; D.
5. **13F:** hold `world_fetch_13f.yml` against [Form 13F Data Sets](https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets) until relay OK; same `available_from` rule.

**Reuse tags:** `sec-world-v4-40267486206-1`, `sec-world-shard9-repair-40282669220-1`, `sec-world-proof-v5-40283469118-1`, `sec-native-sample-v1-40633006364-1`, `data-2020-24-v1`, `compact-world-build-composed-v1-41221028803-1`.

# Versioned SEC bulk sources for the retained price cohort

Task5 proved SEC source access in [run42260180822](https://github.com/SRoyaltyy/checklist-engine/actions/runs/42260180822),
merged and read back on main as `e85547a` (PR217). This next collector downloads
the official current ticker maps, `submissions.zip` and `companyfacts.zip` through
that same verified relay. It runs as ordinary scheduled GitHub Actions code,
without an AI service call. Actual complete bulk-run evidence is pending.

## Bound cohort and identity meaning

The collector authenticates the existing retained identity map (LF SHA256
`50323efcd9855061501d88010d8e812371fda7c9dd48d3a54c0f5f19cdad97ce`)
and [price join keys](PRICE_WORLD_JOIN_CONTRACT_V1.md). The exact8,439ticker sets
must agree. No price-world rebuild, new eligibility filter or cohort exclusion
is performed.

The two current SEC maps are matched by exact ticker spelling. Dot/dash, class
shares, option roots and renames are not silently conflated. Identity rows record
archived-only candidates, current-only candidates, agreement, conflict, ambiguity,
unresolved names and quarantines. A conflicting archived/current pair preserves
both retrieval candidates, with no selected unique CIK. The24product/issuer alias
quarantines and CIK1790169 integrity quarantine are preserved. Quarantined CIKs
never enter produced fact or filing data.

`with_unique_cik` and `with_retrieval_candidates` measure different coverage. The
latter may include conflicting candidates collected for later resolution.
Current identities may target source acquisition; they never establish ownership
of a historical price ticker. Formal `valid_from`/`valid_to_exclusive` remain
unknown, and `historical_join_allowed` remains false for every identity row.

## Produced data and source provenance

Each run/attempt creates its own `nai-sec-bulk-v2-<run>-<attempt>` release. Existing
published assets are never clobbered. The original fixed `nai-sec-bulk-v1` release
is preserved. `scripts/nai/sec_bulk.py` is a compatibility entry point to the new
`ci.sec_bulk_retained` collector.

The release contains:

- Exact raw `company_tickers.json` and `company_tickers_exchange.json` responses.
- `sec_identity_map_v2-*.parquet` plus `SEC_IDENTITY_COVERAGE_V2.json`.
- `sec_submissions_filings_retained-*.parquet`, with accession, filing date,
  acceptance timestamp, report date, enumerated form/XBRL fields and source document
  identifier. Root and historical submissions members are read. Each reported
  source observation is preserved with `source_member` and `source_row`; rows
  are not collapsed into a canonical accession. Disputed populated values are
  marked in `conflict_fields` on every affected observation. Unknown values are
  not filled from another copy, and no disputed timestamp is selected for a join.
- `sec_submissions_entities_retained-*.parquet`, with structured current ticker,
  exchange, SIC and incorporation-state codes. Current entity metadata is labelled
  explicitly; company names, descriptions and former-name prose are not features.
- `sec_companyfacts_retained-*.parquet`, with taxonomy/concept/unit identifiers,
  period and filing dates, accession/fiscal metadata and fixed numeric values.
  `val_text` preserves the exact JSON number, including integers above2^53 and
  decimal fractions. `val_float64` is a convenience projection;
  `float64_exact` states whether that projection is exact. Non-numeric source
  values and missing filing dates are counted explicitly.
- Filtered raw JSON members in `sec_<kind>_raw-*.tar.gz`, each paired with a
  JSON ledger containing every member's source ZIP name, CIK, byte count and
  SHA256. The downloaded full ZIP's URL, timestamps, size and SHA256 are recorded
  in the final receipt. Retained ZIP member CRCs are checked by the ZIP reader.
- `SEC_BULK_COVERAGE_V2.json`, the final status, actual source/run/attempt,
  CIK coverage, source hashes, extraction counts/date bounds, unknowns and all
  published asset bindings.

Filing `rows` counts source observations. `distinct_accessions`,
`duplicate_accession_observations`, `exact_duplicate_observations` and
`accessions_with_conflicting_metadata` are reported separately. Conflict examples
retain the reported values. Consumers must resolve or quarantine disputed
filing/acceptance clocks before any PIT join; multiple observations must not be
counted as multiple economic filings.
Flags compare literal reported values; they do not assert that differently
formatted timestamps represent different instants.

Immutable per-input and per-extraction receipts are published as each stage
finishes. The release becomes public after identity publication and is labelled
INCOMPLETE until the final coverage receipt exists. A live run's raw/parquet
assets are checkpoints, not a complete result. This also preserves source ZIP
hashes and completed work if a runner stops before the final report.

Raw source members can contain issuer metadata, retained only as source evidence.
No free-text interpretation or prose-derived feature is produced. Report periods
are separate from filing/acceptance availability; source acquisition performs no
stock-date join, world snapshot rebuild, eligibility proof or scoring.

## Resource bounds and failure behavior

The two full source ZIPs are handled sequentially. Each download is limited by
the actual free runner disk minus2GiB of processing reserve. Completed ZIPs and
successfully published output chunks are removed from the ephemeral runner.
Raw shards close at about256MiB of uncompressed member data; parquet files close
at approximately500,000rows, with at most100,000fact rows buffered at once.
Each emitted parquet file is read back for actual row count and complete CIK
membership before its immutable publication.

HTTP requests use the verified production relay and at least one-second spacing.
A403 stops the request. A429 permits one retry of the identical source through
the same route after at least601seconds, honoring a longer `Retry-After` (up to
one hour). A second429 or longer requested wait stops the run. Waits are logged
in60second increments and rate-limit evidence is retained. No automatic route
or identity rotation is used.
The private owner-approved SEC contact remains in the Worker, restricted to SEC
destinations, and is omitted from public code and receipts.

If one archive or upload fails, the runner exits nonzero and publishes an explicit
`FAIL_PARTIAL_SOURCE_SNAPSHOT` receipt identifying the failed stage and already
durable assets. It cannot claim full bulk success from an identity-only run or a
successful first archive. Missing source CIKs remain visible, not converted to
zero values or silently removed from the retained price cohort.

## Schedule and verification

`nai-sec-bulk` retains the Saturday22:17UTC weekly schedule and manual dispatch.
Manual `identity_only=true` produces a distinctly labelled identity snapshot and
does not prove complete bulk coverage. A one-shot request on
`gpt/sec-bulk-retained-v2` allows the initial reviewed full run; PR checks use only
synthetic inputs.

All22bulk synthetic tests and26shared HTTP/access tests pass locally using existing dependencies. They cover
quarantines, exact symbol matching, identity conflicts, nullable historical filing
  schemas, preserved accession conflicts, raw-member hashes, exact numeric preservation,
actual parquet round trips, complete output CIK checks and honest partial-failure
publication. The initial local attempt hit Windows' restricted default temporary
folder; rerunning with a verified workspace temporary directory passed. No local
dependency installation or market-data calculation was performed.

Actual run ID, released coverage and independent public readback will be added
after the runner finishes. **Task6 remains unchecked. World gate NOT_PROVEN;
scoring CLOSED.**

## First actual run and source-observation correction

[Run42264090366/attempt1](https://github.com/SRoyaltyy/checklist-engine/actions/runs/42264090366),
source `f0c11a24066a0182f14a8f5883d1d9bed8d55d55`, authenticated the exact cohort
and downloaded both current maps plus the1,573,297,672-byte submissions ZIP
(SHA256 `54cd920bd9cf6be1aca79588437c6f051afc313f4fef070b46b28cb8c6be44f8`).
Its identity snapshot measured5,159unique CIK candidates /8,439names (61.13%):
1,165current-only additions,2archived/current conflicts,3,254unresolved names and
24product aliases. All six initial identity checkpoint assets were independently
downloaded/hash-checked.

The initial one-row-per-accession implementation stopped at a conflicting
`acceptance_datetime` for accession `0000950123-09-041625`. Its public release
preserves completed chunks and an explicit failed receipt. The exact
[49,070-byte receipt](SEC_BULK_FIRST_FAILURE_42264090366_V2.json), SHA256
`25d17cae568021ed07ef528b315a4af99f904ef3e207d6816d7e2693ce837ab7`,
was independently downloaded/hash-checked. This failure is not promoted to
complete bulk coverage.

The corrected source-observation model above retains every reported record and
marks disagreements, without choosing a timestamp, normalizing away a difference
or excluding a CIK. Synthetic parquet tests check conflicting clocks survive
unchanged and unknown clocks stay unknown. The old partial result remains
immutable; a fresh complete run under the corrected schema is required.

## Rate-limit recovery

[Run42266176849/attempt1](https://github.com/SRoyaltyy/checklist-engine/actions/runs/42266176849),
source `ac52e8eade13d0b95075f93d5356891576b2411b`, passed its19synthetic
checks but received SEC429 on the first ticker-map request. It produced no
identity or archive data. The independently downloaded exact
[1,892-byte failed receipt](SEC_BULK_RATE_LIMIT_42266176849_V2.json), SHA256
`272d6960dca2913619e9641fd558e913afd5653ae4784a28638113bc36975667`,
remains an explicit failure.

The recovery request enforces a not-before boundary after the stated ten-minute
provider cooldown. For this push only, it reuses the two exact raw ticker maps
already published by run42264090366, independently checked against pinned raw
and acquisition-receipt hashes. Their original acquisition times and release/
commit lineage remain in the new receipts. This avoids redundant SEC requests;
it does not reuse the incompatible partial filing outputs. Scheduled and manual
runs acquire fresh maps. Both complete source archives still require extraction
under the corrected observation schema and independent public readback.

## Independent public readback

`sec-bulk-public-readback` runs separately from the vendor collector. Its request
must freeze a successful producer run, attempt, source commit and final receipt
SHA256. It validates the actual GitHub run and public release, paginates the
complete asset inventory, and downloads every manifest asset with size/SHA256
verification. It makes no SEC requests and cannot change the producer release.

The reader independently reconstructs all8,439identity rows from the two raw maps
and pinned archived metadata. For both source kinds it streams every retained
raw member, checks its ledger name/CIK/size/SHA256, and reconstructs every fixed
field without importing the producer transforms. Ordered per-CIK row hashes
cover every field of every published parquet row, including duplicates, source
positions, unknown and disputed clocks, exact decimal strings and float-exactness
flags. Actual schemas, file row counts and CIK sets are checked. All source/
extraction receipts, aggregate counts, missing CIK lists and date bounds must agree.

The readback covers **all published retained raw members and parquet values**.
It does not redownload the full unfiltered SEC ZIPs or independently establish
historical ticker ownership. Those limits are explicit in its receipt; world
gate remains NOT_PROVEN and scoring CLOSED. The reader publishes its own
immutable PASS/FAIL release and an Actions receipt. Eight synthetic tests include
an8,439-name fixture and unchanged-count value corruption, raw hash/path
corruption and parquet CIK binding corruption. Actual public readback is pending.

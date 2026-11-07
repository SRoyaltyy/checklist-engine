# Versioned SEC bulk sources for the retained price cohort

Task5 proved SEC source access in [run42260180822](https://github.com/SRoyaltyy/checklist-engine/actions/runs/42260180822),
merged and read back on main as `e85547a` (PR217). This next collector downloads
the official current ticker maps, `submissions.zip` and `companyfacts.zip` through
that same verified relay. It runs as ordinary scheduled GitHub Actions code,
without an AI service call. The complete producer and independent public
readback have succeeded, as recorded below.

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
  `cik` records the official ZIP filename key; `body_cik` stays nullable and
  `cik_evidence` distinguishes corroborated body/filename agreement from an
  absent body identifier. A present conflicting body CIK always fails.
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

All39bulk/recovery/readback synthetic tests and26shared HTTP/access tests pass locally using existing dependencies. They cover
quarantines, exact symbol matching, identity conflicts, nullable historical filing
  schemas, preserved accession conflicts, raw-member hashes, exact numeric preservation,
actual parquet round trips, complete output CIK checks and honest partial-failure
publication. The initial local attempt hit Windows' restricted default temporary
folder; rerunning with a verified workspace temporary directory passed. No local
dependency installation or market-data calculation was performed.

Actual producer coverage and independent public readback are recorded below.
**Task6 source acquisition is complete. World gate NOT_PROVEN;
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

## Complete submissions and companyfacts source exception

[Run42368480194/attempt1](https://github.com/SRoyaltyy/checklist-engine/actions/runs/42368480194),
source `69b000ee571c1773374e14dd6502ec17e2075a01`, completed the submissions
stage for all5,103retrieval CIKs:7,772raw members,6,446,806observations,
6,446,784distinct accessions,22duplicate observations (21exact duplicates),
one accession with disputed metadata and no missing filing/acceptance clocks.
Filing dates range1993-08-13 through2026-11-06. The disputed accession's two
reported acceptance values remain `2009-09-08T19:29:58Z` and
`2009-09-08T23:29:58Z` on CIK886136; neither was selected as canonical.

The full1,421,776,943-byte companyfacts ZIP (SHA256
`dfb8896a994040bccf5be76a9e65a3fb009453389cbe9268ab3d28629cc06bec`)
downloaded successfully, but extraction stopped on a source member missing its
body `cik`. The explicit [182,281-byte failed receipt](SEC_BULK_COMPANYFACTS_FAILURE_42368480194_V2.json),
SHA256 `2bc049c37c3b19bf8c95c2ac56e978b0697d1917345bc9330e4ca3b8cc0cc641`,
was independently downloaded and hash-checked. All78published assets remain
immutable; this is not a complete two-source result.

The full-acquisition switch is disabled while a separate runner diagnostic
reproduces the exact source ZIP hash, inspects every retained member's body
identity/container and retains exceptional raw members plus the complete ZIP.
It does not infer a missing body identity or silently drop a CIK. Task6 stays
unchecked pending an evidence-based correction and complete independent readback.

The exact-source diagnostic
[42369629763/attempt1](https://github.com/SRoyaltyy/checklist-engine/actions/runs/42369629763)
succeeded at `e09730426be10de4fd2ed829d7e9ea8a76543e39`. Its public
`sec-companyfacts-source-v1-42369629763-1` release retains the full ZIP with
the same `dfb8896a...` SHA256 and all nine exceptional raw members. The exact
1,358,988-byte diagnostic receipt, SHA256
`87c9d9372573bf849a84cc6d871f49a31e58ea15b47a13292075554534176d0a`,
and both nonempty exceptional members were independently downloaded/hash-checked.
It measured4,976retained archive CIKs (127missing):4,967body identifiers agree,
seven members are literal `{}`, and two contain fixed numeric facts without
a body CIK. No conflicting body identifier was found.

The correction preserves the latter facts under their explicit official filename
key, with `body_cik=null` and `cik_evidence=FILENAME_ONLY_BODY_CIK_ABSENT`.
It never fills a body identifier. Empty members and absent body identifiers have
separate counts and CIK lists; no numeric zero is invented. Current source keys
still establish no historical ticker ownership. A conflicting present identifier
remains terminal. Recovery copies only the complete corrected-schema submissions
stage from run42368480194 and reads the exact retained companyfacts ZIP from
the diagnostic release. Every input keeps its original acquisition time and
release/commit/receipt lineage. This push requires no new SEC request; scheduled
and manual runs still acquire fresh inputs.

## Successful complete producer

[Run42370671052/attempt1](https://github.com/SRoyaltyy/checklist-engine/actions/runs/42370671052)
succeeded at `ce282c977dd91a22cbf5340caa1abba435f682e2`. Its public
`nai-sec-bulk-v2-42370671052-1` release contains246assets, including the exact
[295,904-byte final receipt](SEC_BULK_RETAINED_SUCCESS_42370671052_V2.json), SHA256
`695fd933f5959c48f32a49ce12d0678bbfcd088290f6b1097cea27e58f7b340b`,
independently downloaded/hash-checked before readback activation.

Submissions retain6,446,806observations/6,446,784distinct accessions for all5,103
retrieval CIKs, with5,103entity rows and7,772raw members. Companyfacts retain
68,436,577numeric facts in135parquet chunks:4,976source members,4,885populated
CIKs,91source CIKs without numeric output and127absent retrieval CIKs. All nine
missing-body-CIK cases and seven empty objects remain explicit; the two nonempty
filename-only records contribute exactly two facts. No fact is missing its filed
date, and no nonnumeric values were silently coerced. Fact filing dates range
2009-04-15 through2026-11-06. This supplies facts for4,941unique-CIK ticker
matches (4,943names including conflicting retrieval candidates), with unresolved
identities and historical ownership still unproven.

Recovery reused the authenticated complete submissions stage and exact cached
companyfacts ZIP; original source times and lineage are preserved. Acquisition
is disabled. Readback
[42372758947](https://github.com/SRoyaltyy/checklist-engine/actions/runs/42372758947)
is bound to this exact producer/attempt/commit/final receipt and has passed.
Producer success and independent verification are separate evidence below.

## Independent public readback

`sec-bulk-public-readback` runs separately from the vendor collector. Its request
must freeze a successful producer run, attempt, source commit and final receipt
SHA256. It validates the actual GitHub run and public release, paginates the
complete asset inventory, and downloads every manifest asset with size/SHA256
verification. It makes no SEC requests and cannot change the producer release.

Reused identity inputs are independently downloaded from their original release;
the original acquisition receipt hash, commit and timestamps must still agree.
The reader independently reconstructs all8,439identity rows from the two raw maps
and pinned archived metadata. For both source kinds it streams every retained
raw member, checks its ledger name/CIK/size/SHA256, and reconstructs every fixed
field without importing the producer transforms. Ordered per-CIK row hashes
cover every field of every published parquet row, including duplicates, source
positions, unknown and disputed clocks, exact decimal strings and float-exactness
flags. Actual schemas, file row counts and CIK sets are checked. All source/
extraction receipts, aggregate counts, missing CIK lists and date bounds must agree.

The readback covers **all published retained raw members and parquet values**.
For recovery it also downloads the retained full companyfacts ZIP from GitHub,
verifies its exact bytes and checks that all selected ZIP members match the raw
ledgers with no omission. The unfiltered submissions ZIP is not retained, and
historical ticker ownership is not established. Those limits are explicit in its receipt; world
gate remains NOT_PROVEN and scoring CLOSED. The reader publishes its own
immutable PASS/FAIL release and an Actions receipt. Twelve reader synthetic tests include
an8,439-name fixture and unchanged-count value corruption, raw hash/path
corruption, parquet CIK binding corruption, actual-run/final-receipt guards and
reused acquisition-time corruption.

[Independent run42372758947/attempt1](https://github.com/SRoyaltyy/checklist-engine/actions/runs/42372758947)
succeeded at reader commit `c7842549bec75b920f08f7701eccdae5e1aa13d0`.
The public `sec-bulk-readback-v1-42372758947-1` release retains its exact
[1,570,706-byte PASS receipt](SEC_BULK_PUBLIC_READBACK_42372758947_V1.json), SHA256
`2051171d632020bc6f1c9de2025468c97e2d45b5db20b64ccc0cd31255a2475e`,
independently downloaded and hash-checked. It read all246producer assets,
all8,439identity rows, every6,446,806filing/5,103entity/68,436,577fact row value,
all raw ledgers, schemas, counters, date bounds and missing-data lists. It also
verified all4,976retained companyfacts members against the exact full ZIP and
authenticated the original identity and copied-submissions provenance. The
unfiltered submissions ZIP was not retained; its published retained members were
fully checked. Source acquisition and this scoped readback are complete; formal
historical ticker ownership and world/scoring approval remain unproven.

The acquisition, diagnostic and audit one-shot switches are all false. Scheduled
bulk acquisition remains enabled and refreshes its SEC inputs normally.

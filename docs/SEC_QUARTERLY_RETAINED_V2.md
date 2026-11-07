# SEC quarterly structured-source preparation

Task7 is pending. This branch prepares strict readers and a disabled source
profile workflow. All54official source ZIPs have now been acquired and profiled;
the fixed-field data run and independent data readback remain pending.
Task6 is complete on main `2ba3ebdf` (PR218), with producer42370671052 and
independent readback42372758947 both successful.
Activation requires a frozen PASS readback receipt and its successful actual
GitHub run; the collector checks both before any SEC request. This prerequisite
is now bound to the exact PASS receipt; both quarterly execution switches remain
false pending current GitHub checks and initial fixed-field extraction.

The catalog reads actual HTTPS ZIP links from the official
[insider](https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets)
and [13F](https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets)
indexes, requesting published windows intersecting2020 onward. It handles both
quarter labels and shifted date ranges. It never guesses an unpublished URL.
Nominal quarter labels do not become invented filing-date bounds.

`sec-quarterly-source-profile` validates a bound request before enabling its two
runner jobs. The request is currently false. Each source ZIP has a versioned
release binding, its exact download times/hash/bytes and a separate acquisition
receipt. Table schemas, actual row counts, CRCs, member hashes and malformed-row
counts are retained. Exceptional rows have source positions and hashes, without
their prose in the profile. A profile is raw/schema evidence only, with a distinct
status; it is not a completed parquet, historical join or scoring result.

The [insider manual](https://www.sec.gov/files/insider_transactions_readme.pdf)
defines separate transactions and holdings for derivative and non-derivative
securities, with source surrogate keys. The field plan preserves all four tables
and every reporting owner. No first-owner selection or row aggregation is used.
Names, addresses, security-title prose, remarks, signatures and footnote text
are excluded from the fixed-field outputs; original ZIPs remain source evidence.
Source cells, including large numbers and decimal amounts, remain exact strings.
Required missing columns and ragged rows fail; optional absent columns are named.

The [13F manual](https://www.sec.gov/files/form_13f_readme.pdf) identifies the
submission CIK as the filer. It is not an issuer CIK for every holding. Holdings
must retain CUSIP/FIGI identifiers and cannot be filtered to stock issuers by
treating the filing manager as the held issuer. Historical issuer resolution is
separate and remains unproven. Amendment and report metadata stay distinct from
the holdings rows; reporting periods are not availability dates.

The same manual documents a market-value unit change beginning2023-01-03.
The field helper marks pre-boundary filing values `USD_THOUSANDS`, later ones
`USD`, and missing filing dates `UNKNOWN_FILING_DATE`. It preserves the raw value
and never applies a guessed conversion from a report period or ZIP label.
Filing dates accept the documented DD-MON-YYYY form and explicit ISO dates.
The parser rejects invalid or ambiguous forms. The prepared extractor preserves
such raw dates, writes a null normalized date and names the parse failure;
report periods never substitute for filing availability. Orphan child rows stay
in the source outputs with missing-parent status and unknown availability.

The parquet extractor is prepared but has not run on quarterly source archives.
It retains raw surrogate keys and exact numeric strings, both transaction kinds,
all owners and source row positions. Actual parquet row counts, schemas and CIK
sets are checked before publication. A manager CIK is explicitly named as such;
it never becomes a held-issuer key.

Eighteen synthetic tests pass using existing dependencies, including a regression
against every observed archive header. Historical ownership, acceptance-time coverage,
fixed-field parquet coverage and task7 completion remain pending. Scoring CLOSED.

## Actual source profiles

[Run42392401389/attempt1](https://github.com/SRoyaltyy/checklist-engine/actions/runs/42392401389)
succeeded at `ac99f6e230c69eb51bed9d03730f67e2410335a7` for both source kinds.
The public `sec-quarterly-profile-v2-form345-42392401389-1` and corresponding
`form13f` releases each retain83assets:27original ZIPs, acquisition/schema
receipts, the official index and the final profile. Exact final receipts were
independently downloaded/hash-checked:

- [Form345](SEC_QUARTERLY_FORM345_PROFILE_42392401389_V2.json):186,609bytes, SHA256
  `074625032e74e6d8cbf36a53619f5e2875dcb53bf89480095d5fb0af34f1eea8`.
- [Form13F](SEC_QUARTERLY_FORM13F_PROFILE_42392401389_V2.json):127,759bytes, SHA256
  `10adf374b52f2c11128b2bb7b62e38b819c45926d64883620815bfc69d662a59`.

Insider sources span2020Q1 through2026Q3;13F spans2020Q1 through the published
2026-06-01–2026-08-31window. The schema profiles count2,083,620non-derivative
transactions,794,594derivative transactions and77,153,09813Fholding records,
alongside submissions, all owners and holdings/manager metadata. Every required
fixed-field column is present and selected tables have zero malformed rows.
Observed archives use `FORM3_HOLDINGS_REPORTED` and derivative-holdings
`EXERCISE_DATE`; derivative transactions retain their distinct `EXCERCISE_DATE`
spelling. The field plan follows those observed names. Only `AFF10B5ONE` is absent
in the twelve pre-2023insider quarters, explicitly treated as unknown.

The source-profile switch is false. Initial data extraction is bound to these
exact profile roots and uses their cached ZIPs, preserving acquisition times
without additional SEC requests. The monthly schedules remain5th23:29UTC for
Form345 and6th23:41UTC for13F; their updated collector fetches fresh sources.

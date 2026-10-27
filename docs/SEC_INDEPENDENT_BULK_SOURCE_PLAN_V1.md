# Independent SEC bulk source acquisition

James's 2026-10-27 12:20 HKT instruction starts these sources alongside price
recovery. Existing fullscan/theme-radar/checklist sources were reviewed first
(EXISTING_SOURCE_AUDIT_v2.md); the published companyfacts proof already covers
60,921,993 numeric rows / 4,034 verified CIKs. Preserve that evidence. The bulk
sources below broaden acquisition beyond the previously resolved identities.

The legacy workflows pinned `kimi/world-snapshot`, used old direct SEC paths
and invoked a nonfunctional upload CLI on current main. `world_fetch_form4`,
`world_fetch_13f` and `world_fetch_xbrl` now call the current shared bulk fetcher.
Every SEC request goes through PRIMARY_ACTION_RELAY_URL with the established
contact User-Agent, pacing and backoff. The secret is never logged or saved.

Official source indexes:

- [Insider Transactions Data Sets](https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets): flattened structured Forms 3/4/5, retaining filing identifiers. The observed index ends September 2026.
- [Form 13F Data Sets](https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets): structured holdings and submission identifiers. The observed newest window is June–August 2026; newer windows use shifted three-month periods rather than guessed calendar-quarter filenames.
- [Financial Statement Data Sets](https://www.sec.gov/dera/data/financial-statement-data-sets.html): structured statement/submission tables, observed through 2026 Q3.

Fetch actual ZIP links in the official indexes for 2018–2026 (2018–2019 are
history padding). Verify ZIP integrity, inspect table headers/counts without
constructing text features, and publish each original ZIP plus its SHA-256 and
schema receipt. A release remains draft until nonempty verified data uploads.
Only the current bounded ZIP stays on disk; completed assets are immutable.

This is raw source acquisition. No stock join or feature result is claimed.
Preserve accession and filing/acceptance timestamps; a report period is never
an availability date. Current-session incremental filings, historical security
identity, complete entity coverage and prefix leak checks remain open. A blocked
relay response is saved as an explicit source failure, never zero-valued data.
Each workflow emits SEC_BULK_STATUS.json even on failure. No checklist tick or
full-world/scoring approval follows from fetching these files alone.

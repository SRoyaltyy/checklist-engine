# CIK source bindings for the complete archived SEC universe

`SEC_CIK_SOURCE_INDEX_V1.json` binds each eligible company by CIK to its exact
source release, archive, receipt, raw companyfacts member, numeric Parquet member
and official submissions member. No ticker join or dated stock ownership is
inferred. Source hashes come from the already published full integrity proof;
every proof and every archive receipt is downloaded and verified again by
`ci/sec_cik_source_index.py`.

The original source proof contains **4,034 CIK records**, including one explicit
quarantine. Consequently the eligible production input is **4,033 CIKs and
60,915,966 numeric fact rows**. CIK 1790169 and its 6,027 rows remain quarantined,
with its source bindings retained separately. This distinction avoids reading
the older summary's `verified_ciks: 4034` as 4,034 unquarantined companies.

The index requires all sixteen source shards and all 208 original archive
receipts. Each CIK must appear exactly once; both raw and numeric member hashes
must match its previously audited record. Missing official/raw pairings,
unproved companies, duplicate members, changed archives, missing shards and
changed quarantine membership fail construction. The shard-9 repair release is
used only where the source proof selects it.

This is a complete **source index**, not completed native-state production.
Archive payloads were fully reparsed by run 40283469118; this metadata index
inherits that hash-bound evidence and does not claim another local download or
decode of all 208 archives. The existing native-state production proof remains
the separate 20-CIK sample, run 40633006364. Remaining work includes native
production for all eligible CIKs, the complete financial concept/settings tree,
historical stock ownership and eligibility, the full storage budget, and the
comprehensive world leak gate. World acceptance and scoring stay closed.

The corrected submissions review in `SEC_SUBMISSIONS_TICKER_CHECK_V2.json`
includes the six archived older filing pages missed by V1. Neither those pages
nor current undated symbol lists establish historical ticker assignments.
Only GitHub-published source files are read; live SEC access stays held. The
running price world 40621517496 is not restarted, cancelled or reseeded.

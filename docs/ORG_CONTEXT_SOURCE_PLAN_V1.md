# Existing org theme and peer captures

The request pins source commits and each selected file's path, byte size and Git blob SHA-1. Acquisition verifies those bytes and records SHA-256 before producing Parquet projections. It imports all 56 processed theme snapshots and 53 peer-RS filenames at the pinned commits, static correlations, and source hash/restatement metadata. Identical blobs are recorded as aliases with their original paths; a daily filename is not proof of a fresh observation.

Theme projections keep fixed identifiers/categories and an explicit numeric whitelist. News titles, digests, URLs, company descriptions and other unregistered columns are excluded. Percent signs are scaled by 100 and K/M/B/T multipliers expanded; bare numbers retain source units. Missing and unrecognized values stay blank, with distinct parse-failure counts. Peer membership remains a captured fixed list and is not presented as a reconstructed rolling historical peer selection.

Checkpoint packs contain at most five projected/metadata files, individual SHA-256 values, raw source fingerprints, URLs, original capture paths and profiles. The release remains source evidence only. The captures begin August 2026 and cannot supply 2020 history or prove historical first-observation timestamps. Source hash/restatement records are preserved for later availability auditing. No join, question facet, world acceptance, or checklist tick is claimed.

Validation: 24 local parser/transport tests passed. The runner repeats them before acquisition. No local dependency installation was performed. This source lane does not overlap Kimi's comparison-facet implementation or the native recovery computation files.

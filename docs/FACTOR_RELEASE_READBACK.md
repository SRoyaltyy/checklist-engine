# Published native factor readback

`python -m ci.audit_factor_assets` checks every binding in a
`FACTORED_NATIVE_WORLD_CONTEXT_V1` manifest against saved public GitHub release
inventories and the exact downloaded files. Stage files at
`DIRECTORY/RELEASE_TAG/ASSET_NAME`. Supply each inventory as the original release
JSON with `tag_name`, `draft`, and `assets` (including uploaded state, byte size
and SHA-256 digest).

Example for the existing CBOE term release:

```sh
python -m ci.audit_factor_assets \
  --manifest docs/VOLATILITY_TERM_FACTOR_STORE_V1.json \
  --directory downloaded-releases \
  --inventory volatility-release.json \
  --declared-factor-bytes 1107247 \
  --output factor-readback.json
```

The audit authenticates the actual bytes before reading Parquet, then checks
native availability keys, exact feature names and dtypes, row counts, unique
attached columns, and all 22 timeframes for each family/symbol. It rejects a
binding to a producer's local subdirectory or to an original source release
that does not contain the transformed asset. A producer must publish the
transformed files and bind their actual release asset names and hashes.

The total counts each unique bound `(release, asset)` once. An optional declared
factor total must match it exactly. This measures only the factor files named by
the manifest; it does not include raw-source dependencies, code, registries,
question answers, eligibility or missing world types. Every report retains
`world_gate=NOT_PROVEN`, `full_world_storage_gate=NOT_PROVEN`, and
`scoring_gate=CLOSED`, including a successful factor readback. Binding readback
failures write a failure report and exit nonzero.

## Actual immutable-source review, 2026-10-28

`VOLATILITY_FACTOR_RELEASE_READBACK_V1.json` records successful readback of all
22 original published CBOE term factors, exactly 1,107,247 bytes. The public
manifest, files and release inventory were independently checked locally; this
is not a new production run or a full-world acceptance.

`FOLLOWON85_RELEASE_READBACK_REVIEW_V2.json` reviews PR85 at
`bbd3714c8c0f9b51724c600a20b614d6d4a6d849` using all 28 previously published
ETF/CBOE assets, reauthenticated before review. It supersedes the earlier
head's warmup-loss finding: all 441 monthly rows now remain, all five numeric
columns on all 22 CBOE grids retain their exact bits, and the January 2020
three-bar VIX/VIX3M mean is restored to 0.8352165304365041. The candidate's eight
local tests also pass.

Its 418 locally persisted industry/CBOE frames have readable native keys and
declared dimensions. Their bindings still name paths within the original
source releases; those assets are absent there. The candidate's
`ci/factored_world_context.py` publishes only the manifest, coverage and status,
so it does not publish these transformed files. The existing native subdirectory
adds 10,662,815 actual bytes, while `measure_directory` returns only the
5,251,065 bytes of top-level source Parquets. Retaining both requires accounting
for both. The revision therefore remains unsuitable for published-reader
integration until publication, binding and byte accounting are corrected and
the corrected producer is measured on Actions. This review does not edit or
run Cursor's lane. Venice's calendar and breadth are outside this readback.

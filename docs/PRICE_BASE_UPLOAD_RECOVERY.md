# Price-base publication recovery — 2026-10-27 HKT

The compact native-price base builder was present on
`codex/native-world-blocks-v1` at `7a9df7671790d58b2a8f42071a79f988d3a7e112`,
but was not yet on main. This change brings that builder and its tests forward
without reverting newer source-coverage documents on main.

## Failure evidence

[Run 40337725992](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40337725992)
failed in source shards 4, 5, 6 and 7. Shards 0–3 and 8–15 succeeded.
[Shard 4](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40337725992/job/121623977043)
logged HTTP 500 while uploading `base_0005.tar`. Its attempt to publish
`BASE_FAILED.json` also failed, masking the first exception. The
[merge job](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40337725992/job/121644376379)
then stopped at the missing shard-4 completion manifest.

## Recovery behavior

- Upload one asset at a time, with a maximum of five attempts for transient
  HTTP/network errors and delays of 2, 4, 8 and 16 seconds.
- Verify the published size and SHA-256 digest. Reuse an already uploaded asset
  only when both match; never replace a completed asset. Remove only an empty
  `starter` left by an interrupted upload.
- Publish a part's JSON manifest last. Keep local source and part files until
  every asset verifies. A repeated flush can reuse the verified partial upload.
- Preserve the original failure and CLI stderr if publishing its failure report
  also fails. The local report remains available to the workflow artifact step.
- Preflight all 16 completion manifests and report every failed shard with its
  upstream report in `BASE_BUILD_INCOMPLETE.json` before aggregating coverage.

The frozen preparation recipe and indicator calculations are unchanged. No old
release or coverage result is rewritten. This does not add cross-run resume to
the compact base builder; a new run still uses a new release prefix.

The native indicator build also hit the same HTTP 500 upload failure in
[shard 0](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40336250454/job/121619361068).
`ci.native_price_run` now applies the verified transport to that builder's
release uploads without changing its fingerprinted computation file. Its
existing checkpoint recovery can therefore reuse the original frozen inputs
and durable parts. A failed failure-report upload preserves the original cause.

## Validation and outstanding work

Local validation uses the existing Python 3.12 runtime and existing packages;
no dependencies were installed. **44 tests passed, 1 skipped** across
`test_world_release_assets.py`, `test_world_native_transport.py`, `test_world_price_base.py`,
`test_world_native_blocks.py` and `test_price_bridge_basis.py`.
`git diff --check` also passed. Regression coverage includes partial upload,
lost response, immutable conflict, empty starter, permanent error, retry
exhaustion, local data retention, and complete/mixed/missing shard reports.

The exchange-calendar test cannot run locally because `exchange_calendars` is
not installed. A full 8,447-name runner build and real upload smoke have not been
rerun for this change. The full native indicator build's completion, context
joins, historical tradeability, world coverage, v3 questions and full leak gates
remain unverified. No checklist box is claimed by this transport fix.

# Targeted native price recovery

Original full build: [40336250454](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40336250454),
head `3140fa6fdf8a091dbdeddc2a8168179bbd698e40`, attempt 1.

Seven early shards failed on HTTP 500 uploads. Shards 36–63 subsequently failed
when the repository installation exhausted GitHub's API quota. Shard 18 was
still live when the 35-shard recovery request was prepared; it is not restarted.
The compact base build also lost three final shards to that quota, so its full
coverage gate remains incomplete.

The uploader now reads one inventory per batch and verifies each successful
upload using the response's size and SHA-256, avoiding two paginated inventory
reads per asset. Ambiguous/lost responses still reconcile against a fresh
inventory. Explicit primary/secondary rate errors wait according to response
reset/retry headers, in logged chunks of at most 60 seconds; ordinary permission
errors are not retried. Published assets are never overwritten.

Artifact readers cache one authenticated inventory per source release, then use
GitHub's documented public binary-download URL. Every downloaded file must match
that inventory's size and SHA-256 before its temporary file is promoted. This
avoids repeated REST lookups for every checkpoint member without changing the
source bytes or rotating credentials.

The workflow verifies the actual uploader on a small immutable fixture release
before launching recovery. `ci.native_price_recovery plan` checks the source
head/attempt and complete job listing, refusing any live, successful, missing or
ambiguous source shard. At most two recovery jobs run concurrently, using the
original prepared inputs and durable parts with the unchanged computation file.

Inspected original inventories showed orphan trailing manifests in shard 2
(`part_0009.json`), shard 4 (`part_0012.json`) and shard 6 (`part_0007.json`). Such
incomplete parts are skipped and their entities rebuilt in a new release.
Every reused complete part must match the remote SHA-256 of its manifest,
archive and coverage and pass recipe/input/entity validation. Old assets are
preserved. Skipped parts are retained in `RECOVERY_SKIPPED_PARTS.json`.

Recovery completion reports name both reused original parts and new parts.
They are not a full-universe pass. The final merge must combine successful
original shards and recovered replacements only after all required shards have
complete, consistent evidence. Full-world and scoring gates remain closed.

References: [GitHub rate-limit rules](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api),
[release asset upload response](https://docs.github.com/en/rest/releases/assets#upload-a-release-asset).

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

## 2026-10-27 recovery audit

Run 40370285123 is terminal: transport and planner passed, 12 build shards
succeeded, 22 failed and one was cancelled. The successful shards are preserved.
Missing prior releases were a second blocker: an original shard that never
published a release caused recovery to stop on HTTP 404. That case now returns
an explicit zero-checkpoint scratch-build path. A 403 permission error does not.

New price releases are not created for a request alone. The first nonempty
completed part is verified in a draft before the release becomes public. An
all-resumed completion must reference real nonempty data. Old request-only
shells 043–063 are marked incomplete drafts only after their terminal source run
and absence of data/diagnostic assets are verified. No price assets are deleted.

Leg 41's GitHub check annotation reports that the hosted runner lost
communication with the server. Its build step and post-job steps were not
finalized, job log retrieval returns BlobNotFound, and no normal shard artifact
exists. This is an observed infrastructure disconnect; its underlying CPU,
memory or network cause cannot be inferred. Six completed parts remain in the
recovery release, alongside earlier complete original parts. Recovery chains
can reuse disjoint complete parts from both attempts; overlapping older parts
are skipped and their uncovered entities rebuilt.

Request v2's planner rejected successful shard 42 before any build started.
The continuation summary had transposed recovery shards 40 and 42; a fresh
complete job listing confirmed 40 cancelled and 42 successful. Request v3 in
run 40446419246 preserves 42 and targets only 18, 40, 41 and 43–63 (24 total).
Its transport smoke and source-job plan passed. All 21 request-only shells
were marked incomplete drafts in run 40445518486, artifact 12707644293; no
assets were deleted.

## Compact checkpoint recovery

The compact source run 40360947486 has 13 successful shards and three terminal
failures (13–15). Recovery validates the exact source head/attempt and each
failed job. A complete part requires its JSON manifest, archive, coverage CSV
and stock-day weights, all with uploaded state and matching remote SHA-256.
Input identity, recipe fingerprint, entity membership, query counts and the
complete native timeframe grid must agree. Orphan trailing uploads stay intact.
Completed entities are skipped; an entirely checkpointed shard emits its
completion without fetching price archives or recomputing entities.

New compact releases start as drafts. The first fully verified nonempty part
or all-resumed completion publishes the release. The stitch uses explicit
routes: successful original shards 0–12 plus new completion reports 13–15,
whose parts may still refer to their original immutable releases. It verifies
the remote archive/coverage/date-weight digests and full accepted membership
before producing measured OHLCV coverage. Export code SHA-256 and source
routes remain explicit. No indicator formula, accepted universe or frozen
recipe file changes here; full-world and historical tradeability gates remain
closed. This preparation does not complete the separately versioned PR13 math
review or count a checklist box.

The workflow waits for successful completion of native recovery run
40446419246 at its exact pinned head before scheduling compact builds. An
independent planner checks that prerequisite again and refuses live, failed or
different-head runs. The completion event can start the compact recovery after
this workflow lands on main; a review-only branch push cannot start builds.

`COMPACT_PRICE_RESUME_PROOF_V1.json` records validation against released JSON
manifests: 527/527 entities reusable in shard 13, 450/524 in 14 and 350/531 in
15 (1,327 reusable, 255 remaining; 615,137,280 archive bytes preserved). No
large archives were downloaded for that check. Canonical Git object bytes
match frozen recipe fingerprint `0738f12902e29f1272d06f30fdd56d6f80e200bc25f825cf9a737404acdffcc4`.
Windows CRLF working-copy bytes differ, so this is not a local full-build pass;
the production guard remains unchanged and runs against the Linux checkout.

## Final native stitch

`NATIVE_PRICE_STITCH_REQUEST.json` routes each shard exactly once: 28 successful
original shards, 12 successful first-recovery shards (including 42), and 24
replacements in run 40446419246 (including 18/40). The planner verifies every
source run head, attempt and successful terminal job. The frozen merge recipe
receives these explicit completion routes while retaining each part's actual
immutable release. Remote archive/coverage digests must match the part
manifest; coverage bytes are downloaded and verified before aggregation.

The stitch starts after successful compact recovery, refuses a review-only
run, verifies its released status/coverage/stock-day weights, and compares its
accepted ticker count, stock-day denominator, recipe and timeframe grid against
the native result. Publication stays draft until all evidence uploads verify.
The result includes all 64 source-job proofs, compact evidence reference and
unique archive bytes. `recipe_review_gate` remains
`CLOSED_PENDING_PR13_MATH_REVIEW`; full-world, historical tradeability and
scoring gates remain closed. This transports and measures the existing recipe;
it does not accept its known math issues or silently replace any old result.

## Draft transport regression and real acceptance probe

The six-way run 40450227376 exposed a publication regression: all 22 new draft
releases had zero uploaded assets because the uploader queried them by tag.
GitHub's [tag lookup](https://docs.github.com/en/rest/releases/releases#get-a-release-by-tag-name)
returns published releases. Authenticated release listings expose drafts; the
transport now discovers their IDs and reads fresh inventories by release ID.
It caches the draft scan and invalidates it after creating another draft.
Draft downloads use authenticated asset IDs with the same size/SHA-256 checks;
published data retains the verified public binary reader.

The old smoke created an already published fixture and missed this path. Its
replacement must upload into a real draft, reuse identical bytes, read them
while still draft, publish, then verify fresh public downloads. A main-only
controller dispatches the 22 confirmed failed shards only after that smoke
passes. It does not cancel or duplicate live 18/40. Its stable request-hash
identity reuses an existing dispatch across controller reruns. The request ID
also separates the nonoverlapping matrix from the two preserved live jobs.
All old completed shards and assets stay immutable; no recipe file changes.

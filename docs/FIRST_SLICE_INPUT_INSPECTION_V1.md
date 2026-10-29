# First-slice input inspection

The approved FIRST_SLICE_PRICE_ONLY run remains authorized by James/Cyrus
`9e545e9`; it does not wait for full-world coverage. Inspection of its named
input, `world-2020-26-v2`, found these concrete binding gaps:

- All eight Parquet schemas have194 fields and no raw stock OHLCV columns.
- No emitted TA-Lib function columns occur in any schema. The sidecars'95
  discovered function names do not establish emitted values.
- Every shard's recorded date extent is2018-01-02 through2024-12-31.
  This release contains no2025–26 held-out rows.
- Footer row counts total7,590,875. This is a metadata total, not a scan proving
  unique ticker/date keys or the claimed tradeable population.

`FIRST_SLICE_INPUT_INSPECTION_V1.json` records every immutable asset identity,
expected whole-file digest, sidecar digest, footer digest, schema and date extent.
The inspection read751,711 footer bytes plus eight small sidecars. Sidecars
were authenticated against GitHub asset digests. Parquet whole-file digests
were **not** independently verified; no market rows, returns or indicator
statistics were read. Only administrative date minima/maxima were inspected.
Ranges required HTTP206 and exact Content-Range; a full-file fallback was refused.

The source checkout is independently visible in
[build job123441800100](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40872191574/job/123441800100):
`f202302906d968b574b8d43939f809b7a85c75b5`,95 discovered functions,0 patterns.
Its `ci/world_fetch.sh` fetches `bars_all_le2024.parquet` and
`universe_2020_survivors_le2024.parquet` from `data-2020-24-v1`; `datapaths.D`
maps the loader names to those assets. Requested WORLD_END2026 does not extend
an input that ends in2024.

A64-bar synthetic diagnostic extracted only that source's `_feed`, `discover`
and `compute_talib` functions. Under local TA-Lib0.8.2 it discovers76 functions
and emits0 columns: it passes the abstract input label `price` instead of the
required array key `close`. A control using `close` succeeds.76 is the local
discovery count; the actual runner logged95. The observed artifact schemas
establish absence independently of this environment difference.

## Binding work, not a new full-world prerequisite

Use the already-approved compact daily/execution/native price inputs explicitly,
authenticate their manifests and join them to the required cohort keys. Version
additive price/indicator outputs; preserve the existing world-v2 assets and all
published numeric values. The compact source routes are recorded in
`ci/NATIVE_PRICE_BASE_REQUEST.json`, `ci/NATIVE_PRICE_BASE_RECOVERY_REQUEST.json`
and `ci/COMPACT_BASE_ADDON_REQUEST.json`. Actual key membership and numeric
compatibility still require runner measurement; this inspection does not prove
them. A2025–26 cohort extension must have its own explicit identity and remain
held out from discovery. Do not invent absent dates or map missing fields to NO.

James's subsequent `659b203` correction requires binary definitions for **all258**
inventory items, grouped by source, including items awaiting downloads. The
2,680 rows in BINARY_LADDERS_V1 are supplied templates for review, not an
executable-answer proof. Literal thresholds, exact setting/component bindings,
missing rules and drawings must be verified against each dictionary definition.
DEFINE→CHART→DERIVE YES/NO→MINE remains sequential per item. Neither this input
audit nor a raw field count advances an unreviewed item through those gates.

## I201 scope correction

The coverage builder now recognizes the explicit owner exclusions I200 andI201.
I201's22 dictionary/timeframe rows and source status become DROPPED_BY_OWNER,
with the9e545e9 authority/reason. James's map values I201=DROPPED and I195=PROVEN
are retained. I178 VIX and other measured volatility data stay in scope.
`I201_OWNER_DROP_V1.json` binds the two changed CSVs to their original Git blobs;
all other records retain identical bytes. No unavailable source is relabelled as
downloaded, no inventory identity is deleted and no checklist data-completion
tick is claimed.

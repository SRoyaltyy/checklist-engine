# Explicit availability for produced price columns

Every one of the 1,044 produced price fields on each of 22 native timeframes
has an explicit binding in
[`PRICE_COLUMN_AVAILABILITY_V1.csv`](../dictionary/PRICE_COLUMN_AVAILABILITY_V1.csv):
**22,968 registered columns**. The [contract metadata](../dictionary/PRICE_COLUMN_AVAILABILITY_V1.json)
binds this complete grid to the frozen #203 recipe, calendar and the full-cohort
[PIT measurement](PRICE_FULL_COHORT_PIT_V1.md). Definitions and question predicates
are outside this contract.

Each binding identifies the numeric native field, its shared
`features.available_from` clock, and its `candles.date` source-candle end.
The shared clock avoids copying an identical date vector 1,044 times. A column
read masks that clock by the column's own known-value mask: **NaN means unknown
value and NaT availability**, while infinity and signed zero retain their frozen
numeric meanings. A missing latest value is not replaced by an older known value.

The [frozen TA-Lib adapter](https://github.com/SRoyaltyy/checklist-engine/blob/7dcaa48680daeac9a6025c09f9e4d138f5fcbda5/facets_world.py)
intentionally transports its 61 `CDL*` pattern-code arrays as float32. The view
promotes those values exactly to float64, matching the existing PIT matrix
interpretation. This introduces no rounding or tolerance. Other numeric fields
still require float64 storage.

## Guarded reads

Use `world_price_availability.PriceColumnView` with native output from the
bound float64 recipe and its verified session calendar:

```python
view = PriceColumnView(native_candles, native_features, timeframe, session_calendar)
column = view.read("close", setup_dates)
# date, value, available_from, source_candle_end
```

The caller authenticates source bytes against the contract's input/recipe/calendar
bindings; the runner proof does this before constructing a view. The view copies
its inputs and rejects incomplete schemas, duplicate/unknown/unordered date keys,
different feature and candle clocks, incomplete global-session buckets, partial
months, and candles that have not ended before availability. It uses the bound
calendar, including holidays, rather than guessing weekdays.

The frozen `available_from` is a date key. A value may be selected at setup session
D only when its key is no later than D and its source candle ended strictly before
D. This session-level convention does not assert a vendor publication timestamp
or prove historical provider revisions. A read outside the bound trading calendar
is rejected.

`view.align(setup_dates)` returns an `AlignedPriceColumns` pair of numeric values
and shared source clocks, together with the column-contract fingerprint. Its
`column(field)` method exposes the field's masked dates. Bulk consumers must retain
the paired clocks and binding fingerprint. A legacy unstamped alignment frame is
not an explicit price-column record.

## Proof scope

Local tests use synthetic data only. They exercise each registered column on all
22 timeframes, future-row perturbations, malformed/backdated clocks, holiday gaps,
partial IPO/month buckets, unknown fields, missing warmups, infinities and signed
zero. Real-market work is guarded to run only in GitHub Actions.

The `price-column-availability` workflow first reauthenticates the actual complete
PIT bundle and all retained proof fingerprints/receipts. Its source-clock evidence
covers 8,439 names and 12,547,288 setup-day rows. It then runs new frozen-recipe
probes on the predeclared BPOP, DJCO and KGRN controls, comparing all produced
columns on all setup rows, rebuilding at 2023-01-03 and 2025-01-02, and perturbing
future OHLCV at each cut. Every column's public value/clock pair is also checked.
The new runtime probes are those three controls; the complete-cohort source
measurement is reused explicitly rather than relabelled as a new full rebuild.

Actual [run 42249025598, attempt 1](https://github.com/SRoyaltyy/checklist-engine/actions/runs/42249025598)
succeeded on source `af4424c848817c62491905c73ae35831fdc4792c`.
The exact [runner receipt](PRICE_COLUMN_AVAILABILITY_PROOF_V1.json) and
[independent public readback](PRICE_COLUMN_AVAILABILITY_PUBLIC_READBACK_V1.json)
are committed here. All four [public release assets](https://github.com/SRoyaltyy/checklist-engine/releases/tag/price-column-availability-v1-42249025598-1)
were downloaded and checked against their published sizes and SHA256 digests.
The receipt SHA256 is `5a18cca9e7f610fb991ad7128307e22c4538e76ee324d5c147edb735f5bbdcce`.

The three controls each cover 1,712 setup rows and all 22 native timeframes:
**117,963,648 exact alignment cells, 137,808 prefix cells, 137,808 future-perturbation
cells and 206,712 sampled value/clock pairs**, with zero reported differences.
The independent metadata audit checks every declared control, field, timeframe,
cut, source hash and count; it does not rerun market calculations locally.
Its source-cohort readback exactly matches the independently authenticated
full PIT bundle, retaining the packet replay FAIL for 1,308 stocks.
The one-shot execution request is disabled before merge.
The historical PIT report is preserved unchanged.
Diagnostic replay failures and unresolved world prerequisites remain explicit;
**scoring stays CLOSED**.

Initial [run 42246625717](https://github.com/SRoyaltyy/checklist-engine/actions/runs/42246625717)
reauthenticated the full retained-source bundle successfully, then correctly
published a [FAIL receipt](https://github.com/SRoyaltyy/checklist-engine/releases/tag/price-column-availability-v1-42246625717-1)
because the first reader implementation rejected the frozen float32 pattern
transport. Its three failed controls and source reference remain available.
The transport correction preserves those fields, their values, and the declared
controls; the corrected successful run above supersedes that reader failure.

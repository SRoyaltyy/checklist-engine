# Full retained-cohort price PIT measurement

Run [41844079765, attempt 1](https://github.com/SRoyaltyy/checklist-engine/actions/runs/41844079765)
completed successfully on 2026-11-04. The [exact published report](PRICE_FULL_COHORT_PIT_MEASURED_V1.json)
records **MEASURED: 8,439 / 8,439 retained names and 12,547,288 / 12,547,288
setup-day rows**, with no unmeasured names. It covers 1,044 produced price fields
across 22 native timeframes (1d–21d and monthly), or 22,968 field/timeframe rows.
**Scoring remains CLOSED.**

| Check | Measured result |
| --- | --- |
| Prefix rebuilds at 2023-01-03 and 2025-01-02 | PASS; zero failing stocks |
| Past-only setup-day alignment | PASS; zero failing stocks |
| Published diagnostic packet replay | FAIL; 1,308 failing stocks, all named in the report |
| Historical eligibility | NOT_PROVEN; the diagnostic all-true encoding mask does not establish tradeability |
| Historical provider revisions | NOT_MEASURED |
| Canonical binary world | NOT_PROVEN |
| Explicit per-column `available_from` | NOT_PROVEN; the next GPT task |

These are results for the declared cuts and produced-field diagnostic replay.
They do not establish acceptance of the canonical definition world. Observed
failures, missing-value rules and exact float64 comparisons are preserved.
No tolerance, exclusion, definition or held ruling changed.

## Provenance and retained-proof recovery

The original measurement input is
[`price-full-cohort-pit-v1-41578885310-1-inputs`](https://github.com/SRoyaltyy/checklist-engine/releases/tag/price-full-cohort-pit-v1-41578885310-1-inputs),
plan SHA256 `18e12eed42099647d598931868547c85f99731b14b6f6138fece0fd87a43043d`.
Its original worker commit is `8003fb7906c3bf86d88612495664e597de1c65ae`;
the worker's LF SHA256 remains
`d48f918fe27bbdab5df56d4408d74284deba47406b323a138dfd459fa3cddbc2`.

The successful recovery controller is commit
`92f2d4ab6cb4cf9cac2f6218085851b24f759456`, with
[sealed recovery inputs](https://github.com/SRoyaltyy/checklist-engine/releases/tag/price-full-cohort-pit-v1-41844079765-1-recovery-inputs)
SHA256 `dc4c72c9ec98ced17ff7e0d71acb5deee20be84899e89e0c63b0ebd6766b408a`.
It validated 6,799 names in the original 142 failed parts: **6,798 reused proofs
and only one new measurement, KGRN**. The other 1,640 original names were read
by the finalizer. The [recovery summary](PRICE_FULL_COHORT_PIT_RECOVERY_SUMMARY_V1.json)
binds every actual-run receipt to the full report. Proof assets retain their
original `price-full-cohort-pit-v1-41578885310-1-*` namespaces.

The [independent public readback](PRICE_FULL_COHORT_PIT_PUBLIC_READBACK_V1.json)
passed full-cohort membership, field-grid and comparison counters, all 8,439
public proof fingerprints, 142 receipt bodies and execution lineage. It
authenticated 148 aggregate/plan/receipt bodies against a fresh inventory of
180 public releases. Stock proof bodies were validated by the successful GHA
finalizer; the local readback did not run a second market calculation.
The [separate preservation check](PRICE_FULL_COHORT_PIT_RETAINED_PRESERVATION_V1.json)
confirms all 8,438 retained fingerprints and failure vectors are unchanged.
KGRN passes prefix, alignment and packet replay.

## Public evidence

The [measured release](https://github.com/SRoyaltyy/checklist-engine/releases/tag/price-full-cohort-pit-v1-41844079765-1-measured)
contains the report, recovery summary, compressed field coverage and compressed
per-stock evidence manifest. Report SHA256:
`a40b5279a017f5d08af7e32577e6663ac3d295067525ef3480dfaec6648b3734`.
Summary SHA256:
`7846682fe8297ed0e77218e487ef064a2e2cc6efa37ada4de0520e055f09ccc2`.
Both JSON files here preserve the exact published bytes.

With those aggregate files, the sealed plans, the summary's receipt files under
`receipts/{index}/`, and authenticated release inventories downloaded, the
repository's read-only audit can be repeated:

```sh
python -m ci.price_pit_recovery_readback --directory READBACK_DIR --inventories RELEASE_INVENTORIES.json
```

All execution requests added by this PR are disabled after completion. Stable
worker/controller source references remain available for publication lineage.

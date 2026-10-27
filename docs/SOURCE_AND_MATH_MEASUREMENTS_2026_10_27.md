# Source and math measurements — 27 October 2026

## Completed source-byte audit

[Event audit 40480548598](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40480548598) verified all 688 released Parquet parts and receipts against all 8,447 canonical attempts per source. The original released audit SHA-256 is `6b000e12b1f309cd6a0460af2a85b8267c3e597421017d68f77152c7fba07b64`. [EVENT_SOURCE_MEASUREMENTS_V1.json](EVENT_SOURCE_MEASUREMENTS_V1.json) preserves its yearly row/ticker and field counts, with a further classification summary read from the immutable attempt statuses.

| Source | Rows | Tickers with rows | No-row attempts | Non-ETF no-row attempts |
|---|---:|---:|---:|---:|
| Analyst | 350,374 | 4,041 | 4,406 | 1,028 |
| Earnings | 112,760 | 4,195 | 4,252 | 878 |

Each source has 3,372 no-row ETF attempts under the current accepted listing classification. Unknown classifications remain explicit. This current classification does not prove historical eligibility or justify dropping missing entities. A no-row response is not proof of zero historical events. Event dates do not establish original publication/first-observation timing or revision history. The audit's field non-null counters use pandas missingness; blank categorical strings require a separate semantic-missingness check and are not proof of meaningful field coverage. No world/PIT/earnings-completeness claim follows.

## Separately versioned math sample

[Runner 40483350076](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40483350076) passed the corrected math tests and completed the bounded budget comparison. The [immutable proof release](https://github.com/SRoyaltyy/checklist-engine/releases/tag/price-math-budget-v2-40483350076-1) contains both worker results and fixtures. [PRICE_MATH_BUDGET_MEASURED_V2.json](PRICE_MATH_BUDGET_MEASURED_V2.json) is the unchanged released report, SHA-256 `b4eb68c1edf6ce6ebc128d0db2137c0303db70a85d54c90e79bc571c8c807ab8`.

| Measure | Result |
|---|---|
| Status | PASS_SAMPLE_BUDGET_ONLY |
| Corrected recipe fingerprint | `89efd6100f26c998148c7742b7900104618f02adfca0b535ae31baf5092d1e16` |
| Sample | MAN 9,271 input bars; MNTS 1,712; EYE 2,259 |
| Native width | 1,044 numeric columns per timeframe; 22 timeframes; one schema observed per timeframe across all three entities |
| Corrected elapsed seconds | MAN 27.60; MNTS 7.64; EYE 9.20 |
| Corrected compressed bytes | MAN 237,056,770; MNTS 48,192,618; EYE 63,487,546 |
| Combined corrected/baseline bytes | 1.5312× |
| Peak process memory | 474,533,888 corrected / 342,769,664 baseline bytes; runner RAM 16,765,378,560 bytes |
| Projected largest existing shard | 6,492.06 seconds (108.2 minutes), including 25% compute margin and 30-minute I/O allowance |
| Scratch including reserve | 10,886,113,540 bytes, against 90,444,578,816 bytes free |
| Full-universe compressed projection | 2,503,023,170,237.5 bytes (2.50 TB), using the largest sample × all entities × 1.25 |

These are measured sample projections, not proven full-universe bounds. One source part may miss longer histories or other extremes; API quota waits and external upload throughput can exceed the assumed I/O allowance. Main's old frozen recipe and active recovery are unchanged. The corrected recipe stays in draft PR #35 until the old native/compact/stitch work and further review permit a versioned transition.

[GitHub's release documentation](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases#storage-and-bandwidth-quotas) specifies at most 1,000 assets per release, individual assets under 2 GiB, and no total-release-size/bandwidth limit. The existing sharded publication retains a 1.9 GB asset bound. At most one part per entity would give a conservative 547-asset bound for a 136-entity shard (four assets/part plus three fixed assets), below the per-release cap. This storage shape fits those documented limits; the sample does not prove full-run duration or throughput.

## ETF daily source preservation

The previous successful ETF release has all 25 requested native baselines and 44 zero-mismatch prefix checks, but a completed-candle context does not expose the final source session without a next query date. Request v3 adds daily bar assets through the stock cutoff with a per-symbol hash/date/gap manifest. Its actual acquisition and self-verification must complete before source-located/fetched boxes are claimed. Native stock-day joins and the full indicator grid remain separate work.

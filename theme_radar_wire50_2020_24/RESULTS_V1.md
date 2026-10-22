# WIRE50 results V1 (2020-24 only, survivors-only universe)
Rules are in RULES_V1.md (dd7ab2c) and RULES_V1_ADDENDUM_A.md (74c142c). Both were committed before this run. Scorer: wire50_score.py. Full table: WIRE50_RESULTS_V1.csv.

To pass, a row needs >=30 trades, win >55% and mean excess vs the buyable control >0 in BOTH the discovery period (2020-22) and the confirmation period (2023-24). Results are after 0.6% round-trip fees. A run of the same stock counts as one trade.

**Result: 0 of 110 tests pass (55 rows x 2 exits).**
- OWN-TR-00830-BUT-C never fired YES in 2020-24 (0 trades), so it fails automatically. That covers 2 tests; the CSV has the other 108.
- Best near-miss: tr-attn-10-LOUD10K E1. Confirmation 60.4% win on 308 trades, but discovery was only 52.5% with negative excess.
- No row reaches 55% wins in either period except that one confirmation slice.

## Options verdict
- NOT blocked. DoltHub IV v2 (Drive README 1YIraOFc…) covers 2020-01-02..2024-12-31 for 5,423 tickers.
- Caveats: survivors-only, and readings are Mon/Wed/Fri. About 22% of stock-days have a ready (non-NOT_READY) OPT reading.
- All 6 map OPT rows were tested. All fail.
- Master list PV-TF-411..429: 9 testable, all fail.
  - 411-416 map onto the GK-OPX rows.
  - 417 -> TR-OPX-IVCHG1M, 421 -> TR-OPX-IVUP-PXUP, 428 -> TR-OPX-IMPMV.
- 10 are BLOCKED:
  - 418 term structure: one tenor only.
  - 419/420 skew: needs per-strike IV.
  - 422-427 volume, OI and unusual activity: no free 2020-24 history.
  - 429: needs paid data.

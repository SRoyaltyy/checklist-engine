# MCAP100 CLEAN addendum v1 — share-count impossibility rule

Add-only. Written and committed BEFORE any cleaned result is computed. The rule is fixed without looking at trade outcomes. Frozen files and MCAP100_ADDENDUM_V1.md / TRAJECTORY_MCAP100_RESULTS_V1.md are not edited.

Everything is as in MCAP100_ADDENDUM_V1.md (F1 DIV3_PDOWN, 2020–24 only, same exits, 0.6% round-trip fee = 30bp per side, same unfiltered same-day benchmark, same pass bar), except for share-count cleaning:

1. Filing-level rule, applied to sec_shares_out_filed_le_2024.parquet before matching. A share-count row is invalid if any of these hold:
   - val <= 0
   - val > 1e11
   - val > 50 x or < 1/50 x the median val of all rows for that ticker in the file
   Invalid rows are removed. The trade then uses the latest VALID count filed strictly before the entry day. If there is none, the trade has no count (missing).
2. Trade-level rule: if prior close x matched count > $5T, the count is treated as missing for that trade.

Versions (decided by Manager Bot):
- MAIN = keep trades with no count; drop only trades with a known mcap < $100M.
- WARNING = drop trades with no count too.

The report gives the number of filing rows removed, the number of trades whose count changed or became missing, and both versions per period.

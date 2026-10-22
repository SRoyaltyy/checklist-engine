# UNBLOCK_V2 addendum 2 (pre-registration, written before any wave-2 result)
Registered 2026-10-23 ~03:47 HKT, after UNBLOCK_V2.md (24e45c9) and UNBLOCK_V2_ADDENDUM.md (7c7b49e). No wave-2 result has been computed yet.

## $100M market-cap filter (BUYABLE_FILTER_V1 rule 5), applied to the population AND the benchmark
Market cap on D = SEC shares outstanding (New Bot file, filed <= D-1, cleaned: <=0, >1e11, >50x ticker median set missing) x close(D-1).
Stock-days with known market cap < $100M are dropped from the tested population before anything else, so the same-date mean (benchmark for excess) is also computed on the filtered population.
Stock-days with no usable share count are kept (dropping them would remove names with no SEC tag, not small names); their share of the population is reported.
Consequence fixed in advance: MICROCAP (FND-NB-001, < $300M) now means $100M-$300M.

## Scope
Unchanged from the addendum: 48 buildable + PV-TF-452/455/458 mcap versions + PV-TF-159 + 12 v1.2 rewritten timing ideas (PV-TF-082..089, PV-TF-446..449). None of the 40 ideas v1.2 moved to BLOCKED is in scope (overlap checked: empty).
Luck-correction base: 13,851 + every wave-2 p-value (features x 2 exits x 2 periods).

# Inherited ETF/index panel adoption

PR #49 is adopted under James/Cyrus's Tier1 priority. Its historical V1 proof
and candidate Parquets remain available; they are not rewritten as V2 results.
The new measurement consumes only `light-daily-box-v1-20261028`, the existing
25-ETF daily release, and the frozen market-session source. It fetches no live
vendor or Stooq data and introduces no data type or question.

Two inherited blockers are fixed before acceptance. First, prices within
0.0001 of a cent were rounded, and fractional volume could be truncated.
Integer encoding now requires every input bit to reconstruct exactly; other
values remain float64. Vendor volume is tested independently of main volume.
Writers reopen every file and check all fields, signed zeros and NaN bits.
Second, the proposed global monthly availability change is removed. New ETF
panels use a local next-session adapter; `world_timeframes.py` and all running
snapshots retain their existing grid. The producer verifies that extending the
NYSE calendar preserves the entire frozen prefix and original bucket anchor.

The real measurement retains all 43 existing ETF series and raw `adj_close`
separately from raw OHLCV. It checks all five OHLCV fields against all 25 native
ETF sources on every overlapping session, rather than checking close alone.
Every completed 1d–21d/monthly candle is produced from the frozen anchor, with
two independent historical cutoff rebuilds over all rows and fields. Missing
pre-listing history remains unavailable, especially IBIT before January 2024.
Actual source coverage, byte counts, package versions, field mismatch counts
and all source/report hashes are published with versioned V2 artifacts. A source
or prefix mismatch fails the job and cannot produce a world acceptance claim.

Local validation: 80 focused tests passed, including precision, fractional
volume, >2^53 integer preservation, source hash substitution, complete OHLCV
overlap checks, cutoff rebuilds and existing context readers. No dependency
installation was performed locally. The real frozen calendar extension requires
the runner's existing workflow dependency specification (`exchange_calendars`
4.13.2); it has not been claimed as a local check.

Stock-day factor integration, pre-2020 indicator warmups for the new industry
series, historical stock-to-sector/industry membership, all comparison families,
nominal/PIT price eligibility, question quality and full-world budget/leak gates
remain open. No checklist box is ticked before real evidence. World run
40621517496 is never restarted, cancelled or reseeded.

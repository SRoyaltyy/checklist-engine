# Item 5 — forward daily collectors, CBOE indices, spec

2026-11-04T18:33Z. Row [1 Data / Options + money-flow #165]. Non-SEC.

## Sources, already located

cdn.cboe.com/api/global/us_indices/daily_prices/<SERIES>_History.csv

- VIX9D — first 2011-01-04
- VIX3M — first 2009-09-18
- VVIX — first 2006-03-06
- all three last 2026-10-23 as of docs/CBOE_SOURCE_LOCATIONS_V1.json

Same host, same no-auth behaviour as the delayed-quote endpoint proven today. Full history already
exists, so this item needs no backfill problem: fetch once, then append daily.

## Shape

One CSV per series, columns are date and close. Append-only by date, dedupe on date, never
rewrite sealed rows. Release asset per series, or one combined parquet with a series column.

## Collector

- daily cron, after US close
- for each series: fetch, parse, keep rows newer than the max date already stored
- append, commit or upload to release assets
- exit non-zero on a fetch failure so the run is visibly red rather than silently empty

## Pacing

Three requests per day total. No rate risk. Sequential is fine.

## Open questions

- whether cdn.cboe.com rate-limits a daily pattern at all (unlikely, one-shot)
- whether to keep indices in the same asset as the OI rollup from item 4 or separate; separate is
  cleaner because their schedules and failure modes differ

## Why this is worth doing before item 4 resolves

It is independent, small, and finishes on its own. It also exercises the daily-append pattern that
item 4 will reuse, so the second collector is mostly a copy of the first.

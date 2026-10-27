# Independent earnings and analyst acquisition

James's 12:20 and 13:00 HKT instructions keep these non-SEC fetches running
while price recovery proceeds and SEC awaits the Worker change. Existing
sources were checked first: frozen `nasdaq_earn_2020-24.tar`, the earlier
analyst-action release, and theme-radar's October ratings captures. Originals
stay untouched. The earnings job fingerprints the frozen archive as a baseline.

The restored `world_fetch_analyst` and new `world_fetch_earnings` workflows
request dated provider records across all 8,447 accepted names in eight shards
each, with two workers per source. Use the documented
[rating-change API](https://ranaroussi.github.io/yfinance/reference/yfinance.analysis.html)
and [dated earnings API](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.get_earnings_dates.html)
(100-row request cap). Preserve canonical ticker, original timestamp/timezone,
fixed rating action and numeric EPS/surprise fields. SDK version and code SHA
are recorded. An unknown action is missing direction, not neutral.

Save per-name attempts and publish immutable Parquet/receipt batches. A
missing/empty provider response does not prove zero events or complete history.
Repeated provider errors or an initial batch with no usable rows stop the shard
with explicit evidence. Empty initial responses create no remote release.
The last batch and status remain available on failure.

These are additional source rows, not a replacement for verified old data or a
PIT join. A historical event date alone does not establish first-observation or
revision availability. Unknown naive timezones remain flagged. Measure actual
date/entity coverage before any checklist claim. No stock join, leak, world or
scoring gate is approved here. No local dependencies are installed.

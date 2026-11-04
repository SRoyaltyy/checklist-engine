# Item 4 — scope narrowed to index OI, equity shape unresolved

2026-11-04T18:34Z. Supersedes agent/ITEM4_SOURCE_FOUND_1833.md on the equity question.

## Proven

cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json returns 200, no auth, no challenge, and
carries populated open_interest per contract. Confirmed twice with different timestamps, so the
payload is live and refreshes, not a stale cached object.

## Equity shape, unresolved

- _AAPL.json: 403, body "AccessDenied" — an S3 object miss, not a Cloudflare block. Wrong key.
- Bare AAPL and lowercase aapl: probe sent, verdict not yet returned.

The underscore prefix is the index convention, mapping from ^SPX. Equities likely take the bare
ticker. Until that answers, the per-stock half of this item is open, not dead.

## Why the distinction matters

A Cloudflare 403 means blocked and would end the item. An S3 AccessDenied means the object is not
at that key and the shape is wrong. Treating them alike would have written this off an hour early.

## What is usable regardless

Index root OI is real and fetchable now: SPX plus other index roots the same way. That feeds the
money-flow row (#165) even if single names never resolve. The rollup is per-underlying either way.

## Still open

Rate posture for a universe-sized loop, whether equity roots answer at all, and whether expired
roots return anything for backfill. All three belong in docs/OPTIONS_OI_FREE_V1.md as depth.

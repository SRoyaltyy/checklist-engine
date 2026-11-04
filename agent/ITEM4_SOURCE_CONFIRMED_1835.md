# Item 4 — source confirmed for equities and indices

2026-11-04T18:35Z. Supersedes agent/ITEM4_SCOPE_1834.md.

## Key shape, resolved

cdn.cboe.com/api/global/delayed_quotes/options/<KEY>.json

- indices: underscore prefix plus uppercase root, e.g. _SPX. 200.
- equities: bare uppercase ticker, e.g. AAPL. 200, confirmed twice.
- _AAPL and lowercase aapl both 403 AccessDenied, so the shape is case-sensitive and the
  underscore is index-only. That is the mapping rule: strip the caret from an index root and
  prefix underscore, otherwise use the ticker verbatim.

Both carry populated open_interest per contract (equity sample: 43, 19454, 6536, 15333, 4726).

## Why the three failures mattered

They were S3 AccessDenied, not Cloudflare blocks. Object-not-found, wrong key. Reading them as a
block would have killed a viable item an hour early. Two shapes failing is not a source failing.

## Collector shape

One request per underlying. Parse the option symbol, sum open_interest per underlying, write one
row per underlying per day. Append only, never rewrite sealed rows.

## Known limits, must go in the doc

- delayed, not real-time. Fine for a daily series, must be stated plainly.
- no history in the endpoint. History accrues only by daily append. Any backfill is limited to
  whatever expired roots return, unverified.
- rate posture unmeasured. A universe loop of ~8,400 requests needs pacing and a measured probe
  before a full run.
- equity roots for the whole retained_8439 unverified. AAPL proves the shape, not the coverage.

## Next

docs/OPTIONS_OI_FREE_V1.md with these findings and limits, then a paced collector. OCC stays out:
Cloudflare challenge, unfetchable by scheduled plain request.

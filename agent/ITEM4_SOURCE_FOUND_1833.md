# Item 4 — source FOUND, shape workable

2026-11-04T18:32Z. Supersedes agent/ITEM4_PROBE_1832.md.

## Result

cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json returns 200 with no auth and no bot
challenge. Every contract carries a populated open_interest field. Verified live: values 2509,
11321, 1471, 8555, 4071, 7566 across strikes, plus volume and iv alongside.

Same host as the VIX9D / VIX3M / VVIX CSVs already located, so the egress that reaches one
reaches all. cdn.cboe.com is the sanctioned egress for this lane item; OCC is not.

## Why OCC is out

www.theocc.com/market-data answers 403 with Cloudflare's interactive challenge. marketdata
subdomain root 404s. Neither is fetchable by a scheduled plain request.

## Shape

One call per root symbol. Response is per-contract, live snapshot. Contract symbol encodes
root, expiry and strike, e.g. SPX261120C00400000. Per-stock open interest is a rollup: parse
the root, sum open_interest per underlying, write one row per underlying per day.

No history in the endpoint. History accrues only by appending daily, so backfill beyond today
is limited to whatever the same endpoint returns for expired roots, if anything.

## Consequences

- Collector: iterate the retained universe, one request per symbol, sum OI, append daily.
- Rate: unknown. Needs pacing and a measured probe before a full-universe run.
- Delayed quotes: values are delayed, not real-time. Fine for a daily series, must be stated.
- Root symbol form differs from ticker for some underlyings (index vs equity). Needs a mapping
  check against retained_8439 before any full run.

## Not yet proven

Rate limits, whether equity roots answer at all, whether expired-root history exists, and the
daily append under a cron. All four belong in docs/OPTIONS_OI_FREE_V1.md as the honest depth.

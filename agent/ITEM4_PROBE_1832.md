# Item 4 — options open interest, probe log

Started 2026-11-04T18:32Z. Non-SEC lane item, row [1 Data / Options + money-flow #165].

## Tried

- marketdata.theocc.com root: 404. Host resolves, path does not.
- www.theocc.com/market-data: 403, body is Cloudflare's "Just a moment... Enable JavaScript
  and cookies". OCC is behind a bot challenge, so a plain scheduled fetch does not get in.
  That is the same wall as SEC but a different vendor, and unlike SEC it is not a rate
  threshold that decays — it is an interactive check.

- cdn.cboe.com is clean by contrast. The VIX9D / VIX3M / VVIX daily CSVs already located in
  docs/CBOE_SOURCE_LOCATIONS_V1.json return without auth, first dates 2006-2011, last date
  2026-10-23. Same host is the candidate for per-stock open interest.

## In flight

cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json — delayed-quote endpoint, same host,
expected to carry per-contract open_interest. Probe sent 18:32Z, verdict pending.

## What decides this item

If that endpoint carries populated open_interest keyed by contract, item 4 is viable: the
collector parses contract symbols, rolls OI up to the underlying, and appends a daily file.
Per-contract is a parsing job, not a sourcing problem.

If it is empty, gated, or per-root only with no history, then no free daily per-stock OI exists
inside the sanctioned routes and docs/OPTIONS_OI_FREE_V1.md records the honest negative with
these URLs and statuses.

## Note on item 5

Item 5 shares this host and is already half-solved: the index CSVs are located with usable
history. Its collector is the same shape as item 4's, so whichever lands first sets the pattern.

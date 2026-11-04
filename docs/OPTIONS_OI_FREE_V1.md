# Free options open interest — depth and limits

Status: SOURCE FOUND, collector not yet built. 2026-11-04.

## The source

cdn.cboe.com/api/global/delayed_quotes/options/<KEY>.json

No auth, no bot challenge, 200. Every contract carries open_interest, volume and iv alongside.

Key shape, verified both ways:

- index roots: underscore prefix plus uppercase, e.g. _SPX
- equities: bare uppercase ticker, e.g. AAPL

_ prefixed equity tickers and lowercase tickers both return 403 AccessDenied. The shape is
case-sensitive and the underscore is index-only.

Sample equity OI values from one pull: 43, 19454, 6536, 15333, 4726, 4416, 4191. Populated, not
placeholder.

## What is NOT free here

OCC. www.theocc.com/market-data answers 403 with Cloudflare's interactive challenge, and
marketdata.theocc.com root 404s. A scheduled plain request does not get in. OCC volume and OI
reports are therefore out unless a headless browser or a proxy is added later.

## Limits that matter

- **Delayed.** Not real time. Acceptable for a daily series, must be labelled as delayed wherever
  it is used.
- **No history.** The endpoint is a snapshot. A backfill is only possible if expired roots still
  answer, which is unverified. Assume the series starts the day the collector starts.
- **Per contract, not per stock.** OI must be summed per underlying. The rollup is ours to do and
  ours to get wrong.
- **Rate posture unmeasured.** The retained universe is ~8,400 underlyings. One request each needs
  pacing and a measured probe before a full run, or the first run will be throttled or banned.
- **Coverage unproven.** AAPL proves the shape, not that every retained ticker answers. Expect gaps
  for illiquid names and for tickers whose option root differs from the equity symbol.

## Collector shape, when built

One request per underlying, sequential with pacing. Parse the option symbol for the root, sum
open_interest per underlying, write one row per underlying per day. Append only, dedupe on
underlying plus date, never rewrite sealed rows. Release asset per month.

## Honest position

Per-stock OI is available free, delayed, forward-only, from a single vendor with an unmeasured
rate posture. That is enough for a daily money-flow series and not enough for anything
intraday or historical. Anyone needing history before today needs a paid source.

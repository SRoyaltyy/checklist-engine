# New root sources: Grok Bot test (pulled 2026-10-22, 03:00–03:25 HKT)
Proof file: ../src/fetch_proof_grok-bot-newroots.csv. Raw files exactly as received: ./raw/ (ssga_*.xlsx, yahoo_*.json, cboe_*_History.csv, nasdaq_*.json, wiki/<TICKER>.json, wiki_AAPL_allagents.json, wiki_top_20240610.json). Ticker-to-article map: sp500_wiki_map.csv.
Taskforce's handoff folder (inbox/handoff_grok/) didn't exist when I checked, so everything here is my own pull.

## 1. VIX term structure: PASS
- Cboe official CSV (cdn.cboe.com/api/global/us_indices/daily_prices/{VIX,VIX9D,VIX3M,VIX6M}_History.csv): HTTP 200 after a 307 redirect (use curl -L). No key needed.
  History: VIX from 1990-01-02, VIX9D from 2011-01-04, VIX3M from 2009-09-18, VIX6M from 2008-01-02, all through 2026-10-20. Sample: 10/20/2026 VIX close 17.31, VIX3M 18.99.
- Yahoo v8 chart: HTTP 200, no key, but unofficial and undocumented. VIX3M starts earlier on Yahoo (2006-07-17). Data runs through 2026-10-21.
- Cross-check of closes: VIX 11 of 9,266 days differ by more than 0.02, VIX9D 51/3,972, VIX3M 9/4,298, VIX6M 42/4,730 (mostly 2014–2018 half-days). Use Cboe as the main source.
- When it's known: the close prints at 16:15 ET on day T-1, so it's usable at 09:25 ET on day T.
- Future fetch: Cboe's file is official and stable (the path has been the same for years), with no key. Yahoo is the backup.

## 2. ETF shares outstanding: PASS for SPDRs, but QQQ and IWM have no free history
- SSGA NAV-history xlsx (ssga.com/.../navhist-us-en-{ticker}.xlsx): HTTP 200 for SPY and all 11 sector SPDRs. Each file has daily Date, NAV, Shares Outstanding and Total Net Assets.
  History starts 2003-12-01 (XLRE from 2015-10-07, XLC from 2018-06-18) and runs to 2026-10-20. Sample: SPY on 2026-10-20 had 1,064,682,116 shares.
- When it's known: day T-1's value posts overnight. Treat it as usable at 09:25 ET on day T, but confirm SSGA's posting time with a few nightly saves before relying on it.
- Future fetch: it's a public issuer file with no key and no documented API or rate limit, under the site's terms. The URL could change if SSGA redesigns its site; the "State Street®" rebrand already happened.
- QQQ (Invesco download link): HTTP 406. IWM (iShares link): returns an HTML page, not data. Treat both as today's value only and start a nightly save.
- Cross-check: Nasdaq's quote/info endpoint returns HTTP 200 but has no shares-outstanding field, so it doesn't count as a second source. I haven't found an independent free daily history. Fallback check: shares should equal Total Net Assets / NAV inside the same file.

## 3. Wikimedia pageviews: PASS, with caveats
- REST per-article endpoint, user agent only: 489 of 502 S&P 500 articles return HTTP 200. Data runs from 2015-07-01 to 2026-10-20. Sample: Apple Inc. had 5,419 views on 2026-10-20.
- 24 titles redirect, e.g. Cigna → The Cigna Group, Aon (company) → Aon plc. Views count under the title the reader actually lands on, so a renamed article loses its history. 108 articles start after 2015-07, mostly because of renames (CI from 2023-07-30, ADBE from 2018, GOOGL from 2015-08-10). Fix: add up views across the old titles too.
- 13 fails come from a bug in my scraper that left "&amp;" in titles (AJG, BRO, CHD, HST, IFF…). AT&T came back as only 1 day for the same reason. These are fixable, not a problem with the source.
- GOOG and GOOGL share one article, so they're the same signal.
- News-day check: Apple's top days were 2023-09-12/13 (iPhone 15 event) and 2022-09-07/08 (iPhone 14 event), which is what you'd expect. User views were ≤ all-agents views on every day. The second endpoint (top/2024-06-10) agrees: Apple_Inc. had 10,627 views there and 10,627 in the per-article data.
- When it's known: each day is a UTC day and usually appears by early the next day UTC. To be safe, use day D-2 at 09:25 ET on day D, or D-1 once the posting time is confirmed.
- Future fetch: official and documented (Wikimedia REST API, CC0 data). No key, but a User-Agent header is required. The limit is about 100 requests/s, and the endpoint has been stable since 2015. Backup: the dumps.wikimedia.org pageview files (bulk hourly).

Dropped by the scope change: CBOE put/call (the CSVs worked, 2006-11 to 2019-10-04, plus a daily JSON from 2019-10-07), Treasury auctions and S&P index changes. Nothing was posted and no checklist rows were written.

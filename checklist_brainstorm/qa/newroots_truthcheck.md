# Truth check of Grok Bot's new-source test pulls (Manager Bot, 2026-10-22 ~03:30 HKT)
I did not edit Grok's files. I re-pulled live myself and compared. Raw log: /workspace/tc/res.txt

| Source | Values checked | Result |
|---|---|---|
| VIX term structure (Cboe CSVs) | 19 closes (10 VIX, 3 each VIX9D/3M/6M, 1996–2025) | PASS: 19/19 match live Cboe AND live Yahoo |
| ETF shares outstanding (SSGA navhist xlsx) | 10 random (XLI, XLE, XLB, XLRE, XLP, 2012–2026) + SPY 10-20 | PASS: 11/11 match the live SSGA file. SPY 2026-10-20 = 1,064,682,116 confirmed |
| Wikipedia views (Wikimedia REST API) | 10 random ticker-days (CSX, CSGP, CVS, LYB, CME, VTRS, PYPL, CFG, LOW, EXE) | PASS: 10/10 exact match |
| Cboe put/call | Grok saved no raw put/call file, so I pulled it myself: 10 random archive rows | PASS (with note): archive totalpc/equitypc runs 11/1/2006–10/04/2019; 10/10 rows give P/C = puts/calls. Daily JSON feed works for 2019-10-07, 2024-03-15, 2026-10-20 |

Mismatches: none.

Caveats / durability:
- All four are official publisher URLs, no login or key. None is a formal "API with a contract" except Wikimedia (documented REST API, asks for a User-Agent).
- Cboe CDN files and the daily put/call JSON are public but undocumented paths; Cboe has moved URLs before. Daily put/call feed returns 403 for days not yet posted (and non-trading days), so the fetcher must treat 403 as "not ready", not as failure. Index P/C archive stops 2012-06-07; gap to 2019 should be checked before using index P/C.
- SSGA: second source is weak. The Nasdaq raw file Grok saved has no shares field, so the only check is inside SSGA's own file. Old files have rounded share counts (XLRE/XLC end in 00000). SSGA's site blocks some bots; must prove the pull works from GitHub servers.
- QQQ/IWM shares: no free history (confirmed by Grok's 406/HTML results) -> nightly save only.
- Wikipedia: renamed articles and "&" titles need fixing (Grok's own note); a day's views are only safe D+2.
- Put/call earlier "failed" verdict should be re-opened: the data is real and pullable.
- Still needed under the durability rule: two clean nightly pulls from GitHub servers.

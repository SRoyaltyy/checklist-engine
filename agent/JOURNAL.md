Journal - append only, newest last. date UTC | item | action | sha | result.

2026-11-02 | infra | tooling branch created from main; lane staged | n/a | no work yet
2026-11-03T09:41Z | 1 | TODO.md re-read, lane and item 1 confirmed; workflow dir listing scrape emitted | n/a | pending
2026-11-04T16:35Z | infra | scrape result arrived in wake payload via FETCH.md, no web_scrape, no human paste | n/a | proven
2026-11-04T16:35Z | infra | markdown was eating asterisks from directive bodies; bodies now fenced, file restored to 4.5 | n/a | proven
2026-11-04T16:36Z | infra | scrape delivery arrived as its own chat message, capped and wrapped | n/a | proven
2026-11-04T16:37Z | 1 | doorman Worker egress to sec.gov company_tickers.json | n/a | 403, 500 bytes, route two gone
2026-11-04T16:37Z | infra | doorman scrape returns an envelope, not the body; delivery shows a receipt. Resolve path and deliver the file | n/a | fixed in 4.6 and 4.7
2026-11-04T16:41Z | 1 | SEC block page text recovered: Request Rate Threshold Exceeded, Reference ID 0.a10f0317.1793810104.3c4f6fb4 | n/a | not an IP ban; rate or undeclared agent
2026-11-04T16:41Z | 1 | doorman forwards no User-Agent on scrape, so SEC sees an anonymous client | n/a | suspected cause, unverified

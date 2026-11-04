Journal - append only, newest last. date UTC | item | action | sha | result.

2026-11-02 | infra | tooling branch created from main; lane staged | n/a | no work yet
2026-11-03T09:41Z | 1 | TODO.md re-read, lane and item 1 confirmed; workflow dir listing scrape emitted | n/a | pending
2026-11-04T16:35Z | infra | scrape result arrived in wake payload via FETCH.md, no web_scrape, no human paste | n/a | proven
2026-11-04T16:35Z | infra | markdown was eating asterisks from directive bodies; bodies now fenced, file restored to 4.5 | n/a | proven
2026-11-04T16:36Z | infra | scrape delivery arrived as its own chat message, capped and wrapped | n/a | proven
2026-11-04T16:37Z | 1 | doorman Worker egress to sec.gov company_tickers.json | n/a | 403, 500 bytes, route two gone
2026-11-04T16:37Z | infra | doorman scrape returns an envelope, not the body; delivery shows a receipt | n/a | fixed in 4.6 and 4.7
2026-11-04T16:41Z | 1 | SEC block page text recovered: Request Rate Threshold Exceeded, Reference ID 0.a10f0317.1793810104.3c4f6fb4 | n/a | not an IP ban; rate or undeclared agent
2026-11-04T16:41Z | 1 | doorman forwarded no User-Agent on scrape | n/a | fixed, contact UA plus backoff deployed, bindings kept
2026-11-04T16:48Z | infra | deliveries arrived as envelopes, tab still on 4.5 | n/a | reload outstanding
2026-11-04T16:50Z | infra | scrape of api.github.com 403, op fetches unauthenticated and shared IP limits are gone | n/a | fix pending, not blocking
2026-11-04T17:11Z | infra | Copy code line from the chat UI broke eval with a SyntaxError. cleanBody now strips it and fences anywhere; loader sanitises again before eval | n/a | fixed in 4.9 and loader 1.4
2026-11-04T17:12Z | infra | loader 1.5 adds post-swap health check, marks a bad version and rolls back to last good | n/a | written, unproven
2026-11-04T17:12Z | infra | repo state verified clean: bridge 4.9, no Copy code lines, version 4.9.1 | n/a | confirmed by read

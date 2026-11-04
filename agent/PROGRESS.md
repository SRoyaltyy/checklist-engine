Progress - SEC and Options download pipelines

Lane owner: Venice. Branch venice/sec-options-pipelines. Never push main.

Order below is the lane's order. Take the first unticked row.

Items

Item State Evidence

1 Fix SEC 403 on runners BLOCKED, both routes 403 runs 41413529249, 41413535355 direct 403. Worker egress 403 twice: 16:36Z bare UA, 17:17Z with contact UA, Accept, identity encoding, five backoff attempts, new Reference ID 0.5e711102.1793812678.1edce412
2 SEC tickers and bulk gated on item 1 -
3 Form 4 and 13F datasets gated on item 1 -
4 Options open interest source not started, non-SEC -
5 Forward daily collectors not started, non-SEC -
6 Summary doc NO_AI_DATA_PIPELINES_V1 not started -

Blocker, recorded

SEC answers "Request Rate Threshold Exceeded" to both sanctioned routes. The header is not the cause: the runner already sends a contact UA and paces at 0.15s, and the Worker now sends the same contact UA with Accept, Accept-Encoding identity and five backoff attempts. The threshold is on the egress IP, and Cloudflare's pool is shared and permanently hot. Four attempts across both routes, all 403.

Options still inside the sanctioned routes, in order of promise: retry the Worker on a long delay so the threshold decays, since the block is time-based rather than an IP ban. If that fails, item 1 stops and the lane moves to items 4 and 5, which do not touch sec.gov.

Reading order
docs/SEC_INDEPENDENT_BULK_SOURCE_PLAN_V1.md
docs/SEC_RETAINED_IDENTITY_MAP_V1.md — the .md companion, never the 5.3 MB json
docs/CBOE_SOURCE_LOCATIONS_V1.json
docs/NO_AI_DATA_PIPELINES_V1.md
Rules
One item per wake. Tick the row and add evidence before stopping.
METHODOLOGY.md is 587KB: grep it, never read whole.
No markers in committed files. PR to main only.

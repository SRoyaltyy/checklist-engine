Progress - SEC and Options download pipelines

Lane owner: Venice. Branch venice/sec-options-pipelines. Never push main.

Order below is the lane's order. Take the first unticked row.

Items
#	Item	State	Evidence
1	Fix SEC 403 on runners	not started	runs 41413529249, 41413535355 both 403
2	SEC tickers and bulk	not started	-
3	Form 4 and 13F datasets	not started	-
4	Options open interest source	not started	-
5	Forward daily collectors	not started	-
6	Summary doc NO_AI_DATA_PIPELINES_V1	not started	-
Blocker rule

If sec.gov 403s on runners, fix the User-Agent first. If it still 403s through the Cloudflare Worker, journal it with the response headers and stop. Do not try a fourth route.

Reading order
docs/SEC_INDEPENDENT_BULK_SOURCE_PLAN_V1.md
docs/SEC_RETAINED_IDENTITY_MAP_V1.md — the .md companion, never the 5.3 MB json
docs/CBOE_SOURCE_LOCATIONS_V1.json
docs/NO_AI_DATA_PIPELINES_V1.md
Rules
One item per wake. Tick the row and add evidence before stopping.
METHODOLOGY.md is 587KB: grep it, never read it whole.
No markers in committed files. PR to main only.

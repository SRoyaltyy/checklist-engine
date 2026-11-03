State - read first on every wake.

Lane: SEC and Options download pipelines. Branch: venice/sec-options-pipelines.

Infrastructure is complete and proven running as of 2026-11-03. Read agent/CONTEXT.md in full before anything else — it explains the strategic goal, which is to make a Venice chat survive its context ceiling, wake itself, and read without web_scrape.

Next step: item 1, FIX FIRST: SEC 403 on runners. Read docs/SEC_INDEPENDENT_BULK_SOURCE_PLAN_V1.md, docs/SEC_RETAINED_IDENTITY_MAP_V1.md (the .md, not the 5.3 MB JSON) and the existing nai-sec-bulk workflow, then fix the User-Agent and headers.

No markers. Never push main. Never merge without instruction.

State - read first on every wake.

Work on venice/sec-options-pipelines. Ignore venice/calendar-announce-ledger entirely.

Read agent/CONTEXT.md in full, then agent/PROTOCOL.md, then TODO.md on main for the lane.

Lane as of 2026-11-03: SEC and Options no-AI download pipelines. Unchanged.

Infrastructure is finished and autonomous. Bridge 5.0. Loader hot-swaps on a version bump and rolls back to the last good copy if a build fails or never starts. Scrape and dispatch debounce 60s so a URL can be re-fetched. Delivery resolves the doorman envelope and delivers page text.

Item 1 is blocked with evidence. Both sanctioned routes 403 with correct headers. Do not add a third route.

Next step: one long-delay Worker retry, because the block is a rate threshold and may decay. Roughly sixty seconds between attempts, twice. If it still 403s, mark item 1 blocked in TODO terms, stop touching sec.gov, and start item 4 (options open interest) which does not need SEC.

Open defect: concurrent scrapes share agent/FETCH.md, so two deliveries resolve the same file. Give each scrape its own destination path.

No markers. Never push main. Never merge without instruction.

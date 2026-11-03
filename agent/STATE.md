State - read first on every wake.

Work on venice/sec-options-pipelines. Ignore venice/calendar-announce-ledger entirely.

Read agent/CONTEXT.md in full, then agent/PROTOCOL.md, then TODO.md on main for the lane.

Lane as of 2026-11-03: SEC and Options no-AI download pipelines. Confirm it in agent/FETCH.md, written last wake from TODO.md on main.

Infrastructure proven. Rollover proven at gen 4. Writes from inside the loop proven.

Next step: item 1, SEC 403 on runners. If FETCH.md confirms item 1 is still the first unticked row, scrape the workflow directory listing:
https://api.github.com/repos/SRoyaltyy/checklist-engine/contents/.github/workflows?ref=venice%2Fsec-options-pipelines
Take the nai-sec-bulk file name from it. The wake after that, scrape the file, then fix the User-Agent to a Name plus email@domain form with Accept and Accept-Encoding set, and prove with a dispatch run ID in the PR. If it still 403s through the Worker, journal the response headers and stop.

No markers. Never push main. Never merge without instruction.

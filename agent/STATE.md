State - read first on every wake.

Work on venice/sec-options-pipelines. Ignore venice/calendar-announce-ledger entirely.

Read agent/CONTEXT.md in full, then agent/PROTOCOL.md, then TODO.md on main for the lane.

Lane as of 2026-11-03: SEC and Options no-AI download pipelines. Confirmed in TODO.md this wake.

Infrastructure proven. Rollover proven at gen 4. Writes from inside the loop proven.

Next step: item 1, SEC 403 on runners. agent/FETCH.md holds the workflows directory listing written last wake. Take the nai-sec-bulk file name from it and scrape that file raw:
https://raw.githubusercontent.com/SRoyaltyy/checklist-engine/venice%2Fsec-options-pipelines/.github/workflows/<name>
Then, the wake after, fix the request: User-Agent in Name plus email@domain form, Accept and Accept-Encoding set, and a delay keeping under ten requests a second. Prove with a dispatch run ID.

If it still 403s with correct headers, the TODO sanctions one fallback only: route the fetch through the Cloudflare Worker egress instead of the runner, and prove that with a green run. Journal the response headers and stop rather than trying a fourth route.

Do not edit nai-sec-form345 or nai-sec-form13f this wake unless the same one-line header fix is all they need.

No markers. Never push main. Never merge without instruction.

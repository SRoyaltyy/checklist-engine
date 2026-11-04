State - read first on every wake.

Work on venice/sec-options-pipelines. Ignore venice/calendar-announce-ledger entirely.

Read agent/CONTEXT.md in full, then agent/PROTOCOL.md, then TODO.md on main for the lane.

Lane as of 2026-11-03: SEC and Options no-AI download pipelines. Unchanged.

Infrastructure finished and self-driving. Doorman scrape op rebuilt at 2026-11-04T16:41Z: proper contact User-Agent for sec.gov hosts, Accept and Accept-Encoding set, five attempts with backoff, and the UA echoed in the reply for evidence. Deployed through the deployer, all seven bindings kept, op=ops verified.

Next step: item 1. Read the SEC result from the retry. A 200 means the 403 was the undeclared UA and the Worker route is the answer; wire scripts/nai/common.py to call the Worker scrape instead of the runner direct, dispatch nai-sec-bulk, and cite the run ID.

If it is still 403 with the contact UA, both sanctioned routes are genuinely spent. Journal the headers and the UA used, and stop trying routes.

Bridge is at 4.8. Badge shows v48. Busy watchdog clears a stranded flag after a minute and a parked scrape retries for three.

No markers. Never push main. Never merge without instruction.

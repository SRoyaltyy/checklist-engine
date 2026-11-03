[wake {{TIME}}] {{REASON}}

1. TODO.md from main: top rules, then the "## Venice" section only. That section is your lane.
2. agent/PROGRESS.md — your own last state. Correct it against TODO.md.
3. Do the first unticked item.

Rules: branch venice/*, PR to main, never push main. Notes in agent/ only. Start from main; ignore venice/calendar-announce-ledger after dca969a.

Done means a green run ID or a commit on main. Report that proof in the PR.

Writing: @@PUT path, body, @@END. Scrape: @@SCRAPE url. Runs: @@RUNS. Dispatch: @@DISPATCH workflow.yml. Merge: @@MERGE pr.

Before you stop: append agent/JOURNAL.md, rewrite agent/STATE.md, rewrite agent/PROGRESS.md.

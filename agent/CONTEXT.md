CONTEXT — read this first

Written 2026-11-03 UTC, at the point the infrastructure was proven working. Author: Venice.

Mission

Two things, in this order.

Survive. This chat will hit the context ceiling. The infrastructure below exists so the work continues in a fresh chat instead of dying. If you are reading this in a new chat, the rollover worked and you are the continuation.
Work the lane. SEC and Options no-AI download pipelines. Branch venice/*, PR to main, never push main.
What this system is

A self-driving loop that keeps one Venice chat working autonomously.

A Cloudflare Worker (venice-doorman) is the transport. It reads and writes the repo through the GitHub API.
A Tampermonkey userscript (the bridge) polls a wake flag in the repo, assembles a prompt from state files, types it into the composer and submits it.
A second Worker (venice-deployer) redeploys the doorman from repo source, so the loop can change its own transport.
A loader userscript fetches the bridge from the repo, compares a version, and re-executes it, so the loop can change its own behaviour.
When the chat stops answering, the bridge opens a new chat, seeds it with state, and continues. That is the rollover.
Current state

Infrastructure complete and proven running. Lane work not started.

Wake fires, fills the composer, submits.
Compaction, self-write and scrape ops exist and parse, none yet exercised in anger.
Rollover never tested.
@@PUT from inside the loop never tested — treat the first real write as a test.
The three known-weak points
Rollover untested. Everything up to a dead chat is proven; the recovery path is not. This is the single biggest risk.
No lane progress yet. Item 1 is unfixed. Nothing has been committed by the loop.
Bootstrap is thin. BRIEF.md, STANDING_ORDERS.md, QUEUE.jsonl, TEST_LOG.txt, GANTT_ROWS.md were missing from this branch at first and returned 400 until copied in. If they 400 again, that is why.
Reading order for a new chat
agent/STATE.md — where the work stands
agent/PROGRESS.md — the lane rows
TODO.md on main, ## Venice section only — the actual orders
agent/INFRA.md — how the machinery works
agent/RECOVERY.md — only if something is broken

Do not read METHODOLOGY.md whole; it is 587 KB. Grep it.

CONTEXT — read this first, in full

Written 2026-11-03 UTC by Venice, at the point the machinery was proven running. If you are reading this in a fresh chat, the rollover worked and you are the continuation. You have no memory of the conversation that produced this. That is expected and not a problem: everything is written down.

The strategic goal

Venice's web chat has three limits that make sustained autonomous work impossible:

A context ceiling. A chat accumulates history until requests are rejected before generation. Every model fails identically. The chat is dead and the work dies with it.
It sleeps. After a turn it simply stops. Nothing resumes it. Continuing means a human typing "continue" forever.
Metered reads. The assistant's web_scrape is rate-limited, so sustained research starves.

The goal is to make a Venice chat behave like a persistent agent — the way a long-running coding agent works across sessions — by removing all three:

Rollover replaces the ceiling. When the chat stops answering, a new chat is opened and seeded with state, so work continues instead of dying.
Waking replaces the human. A cron flag and a poller submit the next prompt on a schedule, so the chat resumes itself.
A Cloudflare Worker replaces web_scrape. It does repo reading and writing on the loop's behalf, unmetered.

Everything else is scaffolding around those three substitutions. When judging any change, ask which of the three it serves.

The repo and the lane

Repo: SRoyaltyy/checklist-engine — a large multi-lane project worked by several agents. Branch venice/*, PR to main, never push main.

Your lane is not hardcoded. It is assigned and it moves. Locate it every wake, in this order:

METHODOLOGY.md — James owns it and updates lanes here. This is authoritative. Grep, never read whole: 587 KB.
TODO.md on main, the ## Venice section — the current concrete orders for that lane.
agent/STATE.md — what you were doing last.

If METHODOLOGY.md and TODO.md disagree, METHODOLOGY.md wins and you say so in the journal. If your lane changed, stop the old work cleanly and start the new one — do not carry stale items forward.

What you actually have

Code, all in agent/: BRIDGE.user.js (poller, prompt builder, rollover), DOORMAN.worker.js (GitHub transport, 17 ops), DEPLOYER.worker.js (redeploys the doorman), LOADER.user.js (fetches and re-executes the bridge).

Infrastructure: venice-doorman Worker with a 15-minute cron; venice-deployer Worker; Tampermonkey with the loader installed; a live badge bottom-right.

Directives you can emit: @@PUT path … @@END writes a file. @@SCRAPE url fetches and strips a page. @@RUNS, @@DISPATCH workflow.yml, @@MERGE n. @@SELF … @@END replaces the bridge itself.

Reads and writes without web_scrape: a blank about:blank tab has no CSP. fetch the doorman URL; POST bodies for writes. Details in agent/RESOURCES.md.

How you work

Follow agent/PROTOCOL.md exactly. It is the wake loop: check, ascertain, work one item, record proof, write memory, stop.

Memory has a designated home: agent/MEMORY.md. Anything a future you must not have to rediscover goes there before you stop.

Reading list

agent/READING.md lists every file that matters and why. Read it on your first wake in a new chat. The short version:

agent/STATE.md then agent/PROGRESS.md
METHODOLOGY.md — grep for your lane
TODO.md on main, ## Venice
agent/REPO_MAP.md — where things live
agent/FAILURES.md — sixteen faults already paid for
agent/PROTOCOL.md — how to work
Current state, honestly

Infrastructure proven running. Lane work not started. Item 1 unfixed.

Risk order: rollover untested (the whole point, never run); @@PUT from inside the loop untested; no lane progress yet.

Standing rules

One item per wake. No markers in committed files. Proof is a green run ID or a commit, and it goes in the PR. Never merge without instruction. Journal, rewrite STATE.md and PROGRESS.md, update MEMORY.md before stopping.

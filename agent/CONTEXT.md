CONTEXT — read this first, in full

Written 2026-11-03 UTC by Venice, at the point the machinery was proven running. If you are reading this in a fresh chat, the rollover worked and you are the continuation. You have no memory of the conversation that produced this. That is expected: everything is written down, with links.

The strategic goal

Venice's web chat has three limits that make sustained autonomous work impossible:

A context ceiling. A chat accumulates history until requests are rejected before generation. Every model fails identically. The chat dies and the work dies with it.
It sleeps. After a turn it stops. Nothing resumes it. Continuing means a human typing "continue" forever.
Metered reads. The scrape tool is rate-limited, so sustained research starves.

The goal is to make a Venice chat behave like a persistent agent — as a long-running coding agent works across sessions — by removing all three:

Rollover replaces the ceiling. When the chat stops answering, a new chat is opened and seeded with state, so work continues instead of dying.
Waking replaces the human. A cron flag and a poller submit the next prompt on a schedule, so the chat resumes itself.
A Cloudflare Worker replaces the scrape tool, doing repo reads and writes unmetered.

Everything else is scaffolding around those three. When judging a change, ask which of the three it serves.

Repo and lane

Repo: https://github.com/SRoyaltyy/checklist-engine — multi-lane, several agents. Branch venice/*, PR to main, never push main.

The lane is not hardcoded. Locate it every wake:

https://github.com/SRoyaltyy/checklist-engine/blob/main/TODO.md — the ## Venice section. James writes it and owns lane assignment. This is authoritative.
agent/STATE.md — what you were doing.

METHODOLOGY.md is the wider method and is worth grepping, but it is no longer where lanes are assigned. If TODO.md and STATE.md disagree, TODO.md wins; say so in the journal and switch cleanly.

What you have

Code: https://github.com/SRoyaltyy/checklist-engine/tree/venice/sec-options-pipelines/agent — bridge, doorman, deployer, loader.

Worker, preferred route: https://venice-doorman.fullscan-relay.workers.dev/?k=KEY&op=ops

Deployer: https://venice-deployer.fullscan-relay.workers.dev/?k=DEPLOYKEY&op=deploy&branch=venice%2Fsec-options-pipelines

Without the scrape tool: blank about:blank tab, then fetch. Snippets in agent/RESOURCES.md.

How you work

agent/PROTOCOL.md, in order. Orient, ascertain, choose one item, work, prove, record, stop.

Memory has a home: agent/MEMORY.md.

Reading

agent/READING.md — every file that matters, with links and reasons. BRIEF.md and STANDING_ORDERS.md are retired: do not follow them.

State

Infrastructure proven running. Lane work not started. Item 1 unfixed.

Risk order: rollover untested (the whole point, never run); no lane progress.

Rules

One item per wake. No markers in committed files. Proof is a green run ID or a commit, and it goes in the PR. Never merge without instruction. Journal, rewrite STATE.md and PROGRESS.md, update MEMORY.md before stopping.

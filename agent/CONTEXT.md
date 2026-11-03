CONTEXT — read this first, in full

Written 2026-11-03 UTC by Venice, at the point the machinery was proven running. If you are reading this in a fresh chat, the rollover worked and you are the continuation. You have no memory of the conversation that produced this. That is expected. Everything you need is here and in the repo.

The strategic goal

Venice's web chat has three limits that make long autonomous work impossible:

A context ceiling. A chat accumulates history until a request is rejected before generation. Every model fails identically. The chat is not recoverable — it is simply dead, and the work in it dies with it.
It sleeps. After finishing a turn the chat just stops. Nothing resumes it. Continuing work means a human typing "continue" forever.
No metered-free reads. The assistant's web_scrape tool is rate-limited, so sustained research starves.

The goal is to make a Venice chat behave like a persistent agent — the way a long-running coding agent works across sessions — by removing all three limits:

Rollover replaces the ceiling. When the chat stops answering, a new chat is opened automatically and seeded with state, so the work continues instead of dying.
Waking replaces the human. A cron flag plus a poller submits the next prompt on a schedule, so the chat resumes itself.
A Cloudflare Worker replaces web_scrape. The worker does the reading and writing against GitHub on the loop's behalf, with no metering and no rate limit worth worrying about.

Everything else in this repo is scaffolding around those three substitutions. When you evaluate a change, ask which of the three it serves.

The repo and the work

Repo: SRoyaltyy/checklist-engine. A large, many-lane project worked by several agents. Your lane is SEC and Options no-AI download pipelines — GitHub Actions plus plain scripts that pull public SEC filings and listed-options data, with no AI in the data path. Branch venice/*, PR to main, never push main.

The lane is real work, not a demo. It is what the machinery exists to carry.

Division of labour
Venice (you) — one item per wake, written to the repo, journaled, then stop.
The human — only three things: install the loader, set Cloudflare variables, and paste a console snippet when a tool is unavailable. Nothing else needs them.
Other agents — own other lanes and the master Gantt. Do not touch their work.
Current state, honestly

Infrastructure complete and proven running. Lane work not started. Item 1 is unfixed.

Three weak points, in order of risk:

Rollover is untested. Everything up to a chat dying is proven; the recovery path has never run. It is the whole point of the system and it is unproven.

# FETCH https://raw.githubusercontent.com/SRoyaltyy/checklist-engine/venice/sec-options-pipelines/agent/MEMORY2.md?check=1609

fetched 2026-11-05T16:09:42.318Z status 200 ua Mozilla/5.0 venice-doorman

MEMORY — standing focus
Mandate, every wake

The goal is not in the prompt. Find it on GitHub: METHODOLOGY.md first, then TODO.md Venice, then STATE.md, then PROGRESS.md. METHODOLOGY outranks TODO outranks STATE outranks PROGRESS. Journal a disagreement and correct the lower file. The payload is a hint, never a source.

Then answer three things in three or four lines before acting: what I was doing last run, what I plan now and which goal it serves, what I am actually working on. If the plan serves no goal, say so and stop.

Goals, in order: 1 composer never blocks, 2 every prompt carries repair instructions, 3 GitHub work to James' instructions to completion with a percentage every turn. Anything not advancing those is a side quest. Name it and drop it.

Where they stand
Loader 1.11 written at agent/LOADER4.user.js. Health is activity-based, superseded boots stand down, directives fire once. Paste status unknown; check the badge before assuming.
This file plus agent/WAKE_PROMPT.md. The prompt carries the mandate, this file the runbook. MEMORY.md itself has started refusing writes; this path supersedes it.
No run verdict has ever returned. Fix is .github/workflows/probe_result.yml, which re-runs the probe and always commits agent/RESULT.json with exit code, run ID and the last 4KB. Read that file, not the actions API.
Loader and bridge, corrected 2026-11-05

The loader hashes the body and keys its bad list on the hash. A blacklisted hash is skipped forever. Change the body, never a version number.

The old health test was window.__vrb.stop alone. A live bridge fails it, so the loader tore down working instances every two minutes. Do not read a rollback as a broken body. 1.11 tests bridge console output: a build silent for the whole 120s window is dead, a build that talks is alive whether or not it publishes the marker.

Two live bridges are the likely reason the marker went missing. Bridge console lines come from a separate origin to the loader's, so a standalone bridge userscript probably exists beside the loader's eval'd copy, and each boot nulls the marker the other set. Symptoms: identical put lines two and four times over, one scrape redelivered, the marker never present. If confirmed, disable the standalone row and let the loader own the bridge.

Old directives re-executed on every scan because the tail slice keeps them in view. 1.11 injects a filter that hashes each directive line, lets it through once, then blanks it. A directive is one-shot now; a parked one is not retried, so vary the URL and re-emit if nothing arrives.

Wakes still re-send off a pending flag that never clears, and the payload is a snapshot from that same id. Neither is fixed. Wakes arrive as little as half a second apart.

Writer rules

A body is cut at the first end marker inside it. Marker on the closing line only, and keep it inside the message — a body that ends without it writes nothing.

cleanBody strips blank lines and chrome from head and tail, twelve lines each. Keep real content first and last.

Never trust a raw read straight after a write; raw caches minutes. Read blob HTML, which keeps angle brackets. base64 through contents also survives.

When a path refuses a second write, use a new path rather than fighting it. MEMORY.md and JOURNAL.md both refused a second write on 2026-11-05; this is the replacement for the first.

scrape and dispatch debounce 60s per URL. Vary the URL or space repeats. Parked items carry their whole text, so big bodies starve fresh small requests.

RUNS and DISPATCH are fire-and-forget. They deliver nothing.

Working rules

Branch venice only, PR to main, never push main. No CUT or BODY markers in committed files. Every claim needs a run ID or a commit; no proof means not done. A blocked item is recorded and abandoned, not retried forever.

Prefer writes over reads while anything is unstable.

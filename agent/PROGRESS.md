Progress - Venice lane

Lane owner: Venice. Branch venice/sec-options-pipelines. Never push main.

The lane, from TODO.md on main

TODO.md was narrowed and this file had not caught up. The lane is a thin poke: keep the tab and the bridge alive, notice a failed nai-sec-* or nai-occ-oi-daily run, post the run ID and the error in a PR comment or issue, stop. GPT owns the fix. Do not own or rewrite the download pipelines, do not push new collectors, do not burn scrape quota on bulk downloads. Calendar #96 stays parked.

Item State Evidence

L1 Post a failed run's ID and error to a PR comment or issue BLOCKED. Probe written 2026-11-05T17:38Z, not yet dispatched, no verdict has ever returned.

Why L1 is blocked and what was done about it

The actions job log is not readable without sign-in: the logs endpoint answers Must have admin rights to Repository, and the job HTML truncates every step as too large. So a run verdict cannot be read out of the API by an outsider, and no agent has ever been able to see one.

.github/workflows/probe_result.yml now exists on this branch to close that. Dispatch it with a run id; it reads the run and its jobs with the repo token, captures the last 4KB of output, writes agent/RESULT.json and commits it. The verdict then arrives as a file on the branch, which a read can actually see.

Written, unproven. Proof is a green run id plus a landed agent/RESULT.json. Until that exists L1 stays blocked.

Next action, exact

gh workflow run probe_result.yml --ref venice/sec-options-pipelines -f run_id=41413529249

Then read agent/RESULT.json off the branch, never the actions API.

Superseded by the narrowing

Kept as reference, not as work.

A SEC tickers and bulk — gated on the SEC 403
B Form 4 and 13F — gated on the SEC 403
C Options open interest source — sourced and documented, docs/OPTIONS_OI_FREE_V1.md, cdn.cboe.com, bare uppercase ticker, delayed and forward-only
D Forward daily collectors — not built
E Summary doc NO_AI_DATA_PIPELINES_V1 — not written

Why nothing else has moved, 2026-11-05

Three harness faults, each with its own file. The wake payload repeats one id and is stale, so payload state is never proof. Directives re-executed on every scan, so one scrape URL stuck and new ones never ran. The loader rolled a healthy bridge back every two minutes because its health test watched a marker a live bridge does not set.

Loader 1.11 at agent/LOADER4.user.js fixes the second and third and is not yet pasted. The paste is the gate on lane work.

SEC blocker, retained

SEC answers Request Rate Threshold Exceeded to both sanctioned routes. Not the header: the runner already sends a contact UA at 0.15s pacing, and the Worker sends the same contact UA with Accept, identity encoding and five backoff attempts. The threshold is on egress IP and Cloudflare's pool is shared and hot. Four attempts, all 403.

Reading order

docs/OPTIONS_OI_FREE_V1.md
docs/CBOE_SOURCE_LOCATIONS_V1.json
docs/SEC_INDEPENDENT_BULK_SOURCE_PLAN_V1.md
docs/SEC_RETAINED_IDENTITY_MAP_V1.md — the .md companion, never the 5.3 MB json

Rules
One item per wake. Tick the row and add evidence before stopping.
METHODOLOGY.md is 587KB: grep it, never read whole.
No markers in committed files. PR to main only.

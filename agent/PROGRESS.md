Progress - Venice lane

Lane owner: Venice. Branch venice/sec-options-pipelines. Never push main.

Lane, from TODO.md on main: thin poke. Keep the tab and the bridge alive, notice a failed nai-sec-* or nai-occ-oi-daily run, post the run ID and the error in a PR comment or issue, stop. GPT owns the fix. No pipeline ownership, no new collectors, no bulk scrapes. Calendar #96 parked.

Item State Evidence

L1 Post a failed run's ID and error to a PR comment or issue PROVEN. Issue 215 carries run 41413529249 three times and 42240608258 once, each with conclusion, failing job, failing step and log tail, machine-posted. The instrument that does it is scripts/nai/report2.py, green on runs 42370434685, 42370537435 and 42371613132.

How the reporter was broken and how it was fixed

Four wakes went into this, and two of the theories were wrong. Recorded so they are not repeated.

Symptom: every push reddened nai-auto in under a second, first with exit 127, then exit 2. Job logs need admin rights, so the only readable signal was the check-run annotation.

Wrong theory one: a missing jq after the ubuntu-latest image moved to Ubuntu 26. The migration notice was real but irrelevant.
Wrong theory two: a shell or python fault in the script. The script was committed, indented and correct.

Cause: the workflow had no actions/checkout step at all. One step, nothing else. The workspace was empty, so bash answered 127 for a missing .sh and python answered 2 for a missing .py.

Fix: checkout first, python reporter second, fresh workflow path so no directive race could overwrite it. Proven green three times.

Superseded, kept as reference

SEC tickers and bulk, Form 4 and 13F, options OI source, forward collectors, summary doc. All GPT's now.

Reading order for pipeline context

docs/OPTIONS_OI_FREE_V1.md
docs/CBOE_SOURCE_LOCATIONS_V1.json
docs/SEC_INDEPENDENT_BULK_SOURCE_PLAN_V1.md
docs/SEC_RETAINED_IDENTITY_MAP_V1.md

Rules
One item per wake. Proof is a run ID or a commit, never an inference.
METHODOLOGY.md is 587KB: grep it, never read whole.
No markers in committed files. PR to main only.

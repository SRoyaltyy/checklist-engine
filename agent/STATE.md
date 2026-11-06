State - read first on every wake.

Work on venice/sec-options-pipelines. Ignore venice/calendar-announce-ledger entirely.

The lane, from TODO.md on main: thin poke. Keep the tab and the bridge alive, notice a failed nai-sec-* or nai-occ-oi-daily run, post the run ID and the error in a PR comment or issue, stop. GPT owns the fix. Do not own the pipelines, do not push collectors, do not burn scrape quota. Calendar #96 parked.

L1 IS SATISFIED AND PROVEN. Issue 215 carries run 41413529249 three times and run 42240608258 once, each with conclusion, failing job, failing step and log tail, machine-posted.

The live problem is now self-inflicted noise, not the lane: every push fires four reporting workflows, two of them the old broken ones. Runs 42240608258 (nai-verdict) and 42243674978 (nai-post) were the machinery failing, not a pipeline. Both old bodies have been replaced with one-line callers onto working scripts, and post.sh now dedupes by run id so the duplicate flood stops.

Gate: still shut. Badge does not read LOADER v1.11. LOADER4.user.js is at 1.13. The rollback is caused by the loader's liveness test, which needs a [bridge] console line within 120s and gets none from an idle healthy bridge. Fix belongs in the bridge, which is pushable, not the loader.

Next step

Bridge liveness patch: announce on a short timer and set window.__vrb synchronously at boot, so the probe passes under any loader version. Keep the loader patch target strings verbatim. Then verify two minutes of survival and a green run.

Open items, not started

Dedupe is now in post.sh but report.sh and post.sh both post; consolidate to one reporter.
Grep the verdict log for the exception line instead of blind-tailing.
Fix the wake payload pending flag so it clears.
Two bridge instances still erase each other's one-shot marks.

Writer rules that still bite

Leading whitespace is stripped from every line, so YAML must be flow style on one line. Leading hash and dash are stripped from line starts and lone asterisks are eaten, so fence every body and keep no comment lines and no asterisks in code. A path an old directive in this chat already wrote is rewritten by it every scan, so use a fresh filename for those. Paths written in earlier chats are safe to rewrite.

No markers. Never push main. Never merge without instruction.

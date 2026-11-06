State - read first on every wake.

Work on venice/sec-options-pipelines. Ignore venice/calendar-announce-ledger entirely.

The lane, from TODO.md on main: thin poke. Keep the tab and the bridge alive, notice a failed nai-sec-* or nai-occ-oi-daily run, post the run ID and the error in a PR comment or issue, stop. GPT owns the fix. Do not own the pipelines, do not push collectors, do not burn scrape quota. Calendar #96 parked.

L1 IS SATISFIED AND PROVEN. Issue 215 carries run 41413529249 three times and run 42240608258 once, each with conclusion, failing job, failing step and log tail, machine-posted.

Gate: still shut. Badge does not read LOADER v1.11. LOADER4.user.js is at 1.13. Rollback cause is now read out of the 1.13 source, not guessed: healthy() counts only a console line beginning with the bridge tag inside a 120s settle window, so an idle healthy bridge is silent and rolls itself back. window.__vrb is irrelevant to 1.13 but still matters to older bodies.

Fix pushed 2026-11-06T18:12Z as bridge 5.2: window.__vrb set synchronously at boot, a boot line and a ready line logged, and an alive line every 20s. Loader patch target strings left verbatim, so all three loader patches still apply. The loader adopts a new bridge body on its 60s refresh with no paste.

Next step

Confirm two minutes of survival. The badge must stop cycling to UNHEALTHY and ROLLBACK, and agent/BRIDGE_VERSION.json must read 5.2. If it holds, the only thing still gating lane work is the 1.11 paste.

Open items, not started

run 42267379973 (nai-auto) failed on this wake. It is the reporter on push, so diagnose it next.
Dedupe is in post.sh but report.sh and post.sh both post; consolidate to one reporter.
Grep the verdict log for the exception line instead of blind-tailing.
Fix the wake payload pending flag so it clears.
Two bridge instances still erase each other's one-shot marks.

Disagreement journaled

METHODOLOGY.md still says Venice takes a SEC identity sub-slice after the write-path proof. TODO.md on main narrowed to thin poke on 2026-11-05. TODO followed, METHODOLOGY not corrected since James owns it.

Writer rules that still bite

Leading whitespace is stripped from every line, so YAML must be flow style on one line. Leading hash and dash are stripped from line starts and lone asterisks are eaten, so fence every body and keep no comment lines and no asterisks in code. A path an old directive in this chat already wrote is rewritten by it every scan, so use a fresh filename for those. Paths written in earlier chats are safe to rewrite.

No markers. Never push main. Never merge without instruction.

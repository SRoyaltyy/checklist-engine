State - read first on every wake. Supersedes STATE.md, STATE2.md, and the truncated STATE3.md.

Work on venice/sec-options-pipelines. Ignore venice/calendar-announce-ledger entirely.

Lane, from TODO.md: thin poke. Keep the tab and the bridge alive, notice a failed nai-sec-* or nai-occ-oi-daily run, post the run ID and the error in a PR comment or issue, stop. GPT owns the fix. Calendar #96 parked.

Harness, 2026-11-05T17:10Z

Gate: clear, on evidence. put agent/LOADER4.user.js returned 200 with readback 7113/7113 OK, the filter line parses, the build boots with no eval failure, and the loader's own badge is absent. Absence is the proof: hide() is reachable only from the settle timer when healthy() is true. The badge we kept checking was the bridge's green wakeg15 v51, a different element; the loader's is orange LOAD v1.11. Badge gate dropped permanently.

Live fault: three bridge instances in one tab. Root cause is a no-op. Loader 1.11 does call stopOld() on every boot, but the next line installs a placeholder, if (!window.__vrb || !window.__vrb.stop) window.__vrb = { stop: function(){}, sentinel: true }. A live bridge never publishes window.__vrb.stop, so stopOld() finds the placeholder and stops nothing. Three boots, three instances, three wake go per wake, three bail per scan. Trace in DIAG_STOPOLD_NOOP_1700.md.

Damage is the shared mark set, window.__vrbSeen. One instance marks a directive line and another blanks it, so the one-shot filter is defeated even though its code is correct. No directive result is trustworthy while the count is above one.

Fix in flight, loader only, two edits, given at 17:00Z, not yet applied. Key the seen store per boot: set window.__vrbTok in boot, and have the filter read window['_vrbSeen'+window.__vrbTok] instead of the shared object. Duplicates stop erasing each other and a directive fires once per boot.

Not fixed by that: the instance count. Real fix needs the bridge to publish a stop handle. Follow-up, bridge edit; the bridge body only arrives through a channel that strips angle brackets, so delivered text is approximate.

Wake payload: the id does advance (16:40:42Z), but each instance re-arms it, so wakes arrive seconds apart. Expected to slow once the count drops. If it does not, the flag is a second defect.

Files written this session, all with matching readbacks: JOURNAL_LOADER_111.md, JOURNAL_LOADER_111_READBACK.md, DIAG_DOUBLE_INSTANCE_1640.md, DIAG_TRIPLE_INSTANCE_1650.md, DIAG_SCRAPE_CHANNEL_1652.md, DIAG_WAKE_ID_ADVANCED_1655.md, DIAG_STOPOLD_NOOP_1700.md, PATCH_SINGLE_INSTANCE_1640.md, STATE2.md, STATE3.md, this file.

Next step

Two editor edits, waiting on a human, and nothing else is useful until they land. After that: check the console shows one directive firing once, then rewrite PROGRESS which still says 1.11 is unpasted.

Do not chase the badge again. Do not reinstall. Do not start lane items while the instance count is above one.

No markers. Never push main. Never merge without instruction.

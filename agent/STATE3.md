State - read first on every wake. Supersedes STATE.md and STATE2.md.

Work on venice/sec-options-pipelines. Ignore venice/calendar-announce-ledger entirely.

Lane, from TODO.md: thin poke. Keep the tab and the bridge alive, notice a failed nai-sec-* or nai-occ-oi-daily run, post the run ID and the error in a PR comment or issue, stop. GPT owns the fix. Calendar #96 parked.

Harness, 2026-11-05T17:05Z

Gate: clear. Evidence, not hope. put agent/LOADER4.user.js returned 200 with readback 7113/7113 OK, the filter line parses, the build boots with no eval failure, and the loader's own badge is absent from the screen. Absence is the proof: hide() is only reachable from the settle timer when healthy() is true. The badge we kept checking was the bridge's green wakeg15 v51, a different element, and the loader's is orange LOAD v1.11. Badge gate dropped for good.

Live fault: three bridge instances in one tab. Root cause is a no-op. Loader 1.11 does call stopOld() on every boot, but the next line installs a placeholder, if (!window.__vrb || !window.__vrb.stop) window.__vrb = { stop: function(){}, sentinel: true }. A live bridge never publishes window.__vrb.stop, so stopOld() finds the placeholder and stops nothing. Three boots, three instances, three wake go per wake, three bail per scan. Full trace in DIAG_STOPOLD_NOOP_1700.md.

Damage is the shared mark set, window

Ask anything privately...

Agent

Sub-agent
wakeg15 v51
wakeg15 v51
wakeg15 v51
wakeg15 v51

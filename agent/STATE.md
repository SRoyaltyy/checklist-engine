State - read first on every wake.

Work on venice/sec-options-pipelines. Ignore venice/calendar-announce-ledger entirely.

Lane as of 2026-11-03: SEC and Options no-AI download pipelines. Unchanged. Item 1 is blocked, so the lane sits behind harness repair.

Bridge is 5.3 logic under a 5.1 header; the loader patches the header to 5.4 and bumps the badge. That is cosmetic, not a fault.

Where the harness stands, 2026-11-05T11:44Z

Three coupled faults, each hiding the next. All three are recorded as files.

One. The wake payload is frozen. Six wakes have carried the same WAKE.json id, 11:34:42.774Z, and identical bodies, so every payload predates the work. Treat payload state as stale by minutes and never as proof.

Two. Directives re-execute. The loader's tail slice keeps the scan to the last 20000 characters, which stopped the rewrite storm, but old directives inside that window are re-issued on every scan. A LOADER2 scrape has now been delivered six times about every 15 seconds while a different URL never ran. A directive is a standing subscription, not a one-shot. See agent/DIAG_DIRECTIVE_REPLAY_1143.md.

Three. The loader was rolling back a healthy bridge. Its health test was window.__vrb.stop alone and a live bridge failed it, so it tore down working instances every two minutes forever. Loader 1.9 at agent/LOADER3.user.js replaces the test with console activity, stamps a boot sequence so a superseded timer exits, and installs a tagged placeholder stop handle. See agent/DIAG_LOADER_ROLLBACK_1140.md.

Next step

Loader 1.9 is written but not pasted. The paste is a human step and it is the gate on everything.

Ask for two things, in this order. Whether the Tampermonkey dashboard holds a second entry with "Bridge" in its name and no "Loader" — if yes, disable it so the loader owns the bridge alone. Then the paste of agent/LOADER3.user.js, from the raw URL, after deleting the 1.8 row rather than overwriting it.

Do not start lane items until the rollback stops. A bridge that is killed every two minutes cannot hold a wake.

While the faults stand

Prefer writes over reads; a write lands, a read may never arrive. Do not re-emit a URL inside 60s. Keep the closing marker inside the message — a body that ends without it writes nothing. When a read is genuinely needed, make the URL unique so the queue cannot collapse onto the old one.

No markers. Never push main. Never merge without instruction.

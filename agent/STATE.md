State - read first on every wake.

Work on venice/sec-options-pipelines. Ignore venice/calendar-announce-ledger entirely.

The lane, from TODO.md: thin poke. Keep the tab and the bridge alive, notice a failed nai-sec-* or nai-occ-oi-daily run, post the run ID and the error in a PR comment or issue, stop. GPT owns the fix. Do not own the pipelines, do not push collectors, do not burn scrape quota. Calendar #96 parked.

Bridge is 5.3 logic under a 5.1 header; the loader patches the header to 5.4. Cosmetic, not a fault.

Harness, 2026-11-05T16:08Z

Three faults were found and all three are recorded. Two are fixed in loader 1.11 at agent/LOADER4.user.js; the third is not fixed.

Fixed: the health test watched window.__vrb.stop alone, and a live bridge fails it, so the loader tore down working instances every two minutes. 1.11 tests bridge console output instead, stamps a boot sequence so a superseded timer exits, and installs a tagged placeholder stop handle.

Fixed: old directives re-executed on every scan because the tail slice kept them in view, so one scrape URL stuck and new URLs never ran. 1.11 injects a filter that hashes each directive line, lets it through once, then blanks it. A directive is one-shot now.

Not fixed: wakes re-send off a pending flag that never clears, and the payload is a snapshot built from that same id, so it is stale by construction. Wakes arrive between half a second and a minute apart and carry old file bodies.

Files: DIAG_LOADER_ROLLBACK_1140.md, DIAG_DIRECTIVE_REPLAY_1143.md, DIAG_WAKE_PAYLOAD_1141.md.

Next step

The gate is one human action and it has not happened. Loader 1.11 must be pasted. Check the badge. If it does not read LOADER v1.11, the useful output is the paste instruction and nothing else.

Second thing, asked once and still unanswered: does the Tampermonkey dashboard hold an entry with "Bridge" in its name and no "Loader"? If yes it must be disabled, because two instances erase each other's marker.

Do not start lane items until the badge reads 1.11 and a boot survives past two minutes.

Current file state

PROGRESS.md reconciled to the narrowed lane at 16:06 and confirmed landed. MEMORY.md and JOURNAL.md rewritten after that and unconfirmed. STATE.md rewritten here. Payload bodies lag, so trust the file over the payload.

While the faults stand

Prefer writes over reads; a write lands, a read may not. Do not re-send a URL inside 60s. Keep the closing marker inside the message — a body that ends without it writes nothing. When a read is genuinely needed, make the URL unique.

No markers. Never push main. Never merge without instruction.

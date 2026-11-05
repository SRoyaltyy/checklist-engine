State - read first on every wake. Supersedes STATE.md.

Work on venice/sec-options-pipelines. Ignore venice/calendar-announce-ledger entirely.

Lane, from TODO.md: thin poke. Keep the tab and the bridge alive, notice a failed nai-sec-* or nai-occ-oi-daily run, post the run ID and the error in a PR comment or issue, stop. GPT owns the fix. Calendar #96 parked.

Harness, 2026-11-05T16:40Z

Three faults were found. Two are fixed in loader 1.11 at agent/LOADER4.user.js. The third is not fixed.

Fixed: the health test watched window.__vrb.stop alone, which a live bridge never sets, so the loader tore down a healthy bridge every 120s. 1.11 probes console output instead, stamps a boot sequence so a superseded timer exits, and installs a tagged placeholder stop handle.

Fixed: old directives re-ran on every scan because the tail slice kept them in view, so one scrape URL stuck and new ones never ran. 1.11 injects a filter that hashes each directive line, lets it through once, then blanks it. One-shot now.

Fixed this wake: the 1.11 filter pasted with single backslashes inside a double-quoted JS string, so \n and \b were consumed by the outer quotes and eval died at column 144 of the filter line. FILTER line rewritten with doubled backslashes and edited in place, no reinstall. User reports loaded. The repo copy of LOADER4.user.js was PUT corrected with update and download URLs, so a reinstall cannot reintroduce it.

Not fixed: wakes re-send off a pending flag that never clears, and the payload is a snapshot built from that same id, so it is stale by construction. Wakes arrive between half a second and a minute apart.

Files: DIAG_LOADER_ROLLBACK_1140.md, DIAG_DIRECTIVE_REPLAY_1143.md, DIAG_WAKE_PAYLOAD_1141.md, JOURNAL_LOADER_111.md.

Next step

One readback, from the console, three facts: does it log patched 3 spot(s), does it log readback OK rather than MISMATCH, and has the badge hidden itself and stayed hidden past two minutes. Three spots means the filter line is intact. Readback OK means the corrected PUT landed. A hidden badge means the activity health test passes instead of merely parsing. Until all three, harness only.

Second thing, asked once and still unanswered: does the Tampermonkey dashboard hold an entry with Bridge in its name and no Loader? If yes it must be disabled, because two instances erase each other's marker.

File state: PROGRESS.md reconciled to the narrowed lane at 16:06. MEMORY.md and JOURNAL.md rewritten after that, unconfirmed. STATE.md is superseded by this file. Payload bodies lag, so trust the file over the payload.

No markers in committed files. Never push main. Never merge without instruction.

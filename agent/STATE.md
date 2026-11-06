State - read first on every wake.

Work on venice/sec-options-pipelines. Ignore venice/calendar-announce-ledger entirely.

The lane, from TODO.md: thin poke. Keep the tab and the bridge alive, notice a failed nai-sec-* or nai-occ-oi-daily run, post the run ID and the error in a PR comment or issue, stop. GPT owns the fix. Do not own the pipelines, do not push collectors, do not burn scrape quota. Calendar #96 parked.

Gate: still shut. Badge does not read LOADER v1.11. Loader 1.11 at agent/LOADER4.user.js must be pasted by a human. Until it is, harness work only.

Two writer defects, both confirmed, both worked around

The writer strips leading whitespace from every line, so indented YAML arrives flat and invalid. Workaround: write YAML in flow style, braces, one line, zero indentation.
A path that an old directive already wrote gets rewritten by that directive on every scan, so a second write to the same path is silently clobbered. Workaround: never reuse a filename. nai-probe.yml is permanently flat for this reason and should be abandoned, not fixed.

Proof both ways: nai-probe2.yml written flow style to a fresh path landed byte-exact and ran green twice, runs 42216183221 and 42214233882.

Paste instruction, still owed to the human

Open agent/LOADER4.user.js on the branch, copy the whole file, edit the Tampermonkey Loader entry, replace the body, save, reload the Venice tab. Badge must read LOADER v1.11 and a boot must survive past two minutes.

Also unanswered, ask once: does the Tampermonkey dashboard hold a second entry with "Bridge" in its name and no "Loader"? If yes disable it; two instances erase each other's marker.

Next step

Build the verdict collector on the proven pattern: a NEW filename, flow style, one line. It takes a run id, reads the run and its jobs with the repo token, takes the last 4KB of output, commits agent/RESULT.json, then reads back.

Simplest that satisfies that: put the logic in a python file committed to scripts/, since a script file can carry newlines and indentation freely, and let the workflow be a three-key flow line calling it. The indentation problem only exists inside the workflow YAML, not in .py.

So: write scripts/nai/probe_result.py first, then a workflow that runs it. Both to fresh paths. Then dispatch against run 41413529249 and read agent/RESULT.json.

Progress against the gate

Gate 0 of 1, blocked on the human paste. L1 unblocking 60 percent: probe pattern proven, collector not written.

Do not restart nai-probe.yml. Do not write two files in one wake if the first has not landed.

No markers. Never push main. Never merge without instruction.

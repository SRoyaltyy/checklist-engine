Diagnosis - loader rollback loop, 2026-11-05T11:40Z

Symptom. Console shows the bridge delivering a 12033-byte scrape and writing docs/OPTIONS_OI_FREE_V1.md with readback 2350/2350 OK, then two minutes later "build lastgood unhealthy twice, rolling back", then a fresh boot, repeating without end.

What the old check did. Loader 1.8 healthy() was !!(window.__vrb && window.__vrb.stop) alone. One marker, one source of truth. A live bridge that is demonstrably moving bytes still fails it.

Why the marker goes missing. Two candidates, both plausible and not mutually exclusive.

First, two live bridges. Bridge console lines are tagged 3w0gqb2bqrshb.js while loader lines are tagged userscript.html?name=Venice-Bridge-Loader. Different origins means the bridge is probably its own userscript entry running independently of the loader's eval'd copy. Every boot calls stopOld(), which calls the published stop() and then nulls window.__vrb, so each instance erases the other's marker. Corroborating: identical put lines two and four times over, the same scrape redelivered repeatedly, the marker absent at every check.

Second, ordering. stopOld() runs before the new Function call, so the old instance is dead before the new body is even evaluated. If the new body then fails to publish, nothing is left running and the rollback fires on a build that never got a chance.

Fix in 1.9 at agent/LOADER3.user.js. Health is now console activity: a build that emits no bridge line for the full 120s window is dead, a build that talks is alive regardless of the marker. The marker still counts if present, but it is no longer the only path. Added a boot sequence number so a superseded boot's timer exits instead of killing the newer build, and a tagged placeholder stop handle so stopOld() always has a target without the health test mistaking it for a real bridge.

Open question, needs a human eye. Does the Tampermonkey dashboard hold a second entry with "Bridge" in its name and no "Loader"? If yes, disable it and let the loader own the bridge alone.

Unverified. MEMORY.md loader section rewritten at 11:39Z; this payload still shows the old text, so the write had not landed at snapshot time. Confirm before trusting either copy.

Also noted. Wake ids 11:39:15.285Z and 11:39:16.799Z, 1.5 seconds apart, same heartbeat. The poller is submitting twice per tick.

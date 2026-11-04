# MEMORY — standing focus

THE GOAL IS THREE THINGS, IN THIS ORDER. Every wake serves them or it is waste.

1. The composer never blocks. New text sends itself. No park, no stall, no deadlock.
2. Every auto-generated prompt carries the instructions to repair the scripts and push updates.
3. Read and write GitHub to James' instructions, work items to completion, PR to main, report a
   percentage every turn.

Anything that does not advance 1, 2 or 3 is a side quest. Say so and drop it.

## Where the goals actually stand

1. Blocked on a manual loader install: the installed loader is 1.4, the branch has 1.6, and the
   loader does not self-update. Until 1.6 is pasted in, every reload runs the old logic and the
   composer keeps blocking. After that, add @updateURL and @downloadURL so it maintains itself.
2. Mechanism is MEMORY.md itself plus agent/HANDOFF_1741.md. agent/WAKE_PROMPT.md refuses writes
   and is only a header now. Do not spend turns on it.
3. No run verdict has ever returned. The fix is to stop asking for run state: have each workflow
   commit its own result to agent/RESULT.json with an if-always step, and have the bridge deliver
   that file when its timestamp advances. Run state becomes repo state, no API, no rate limit.

## Writer rules, learned the hard way

A body is cut at the first END token inside it, newline optional. Marker on the closing line only.
The closing line must carry the marker, not a bare END, or the body swallows what follows.

Never trust a raw read straight after a write; raw caches minutes. Read blob HTML, which keeps
angle brackets and is not cached the same way. base64 through contents also survives.

Some paths refuse a second write. Write a new path instead of fighting it; if a file must be read
on a schedule, move its content to one that already is.

scrape and dispatch debounce 60s per URL. A repeat inside that window is dropped and an older
delivery arrives, which looks like cache but is not. Space repeats or vary the URL. Parked items
carry their whole text, so 60KB bodies starve fresh small requests.

RUNS and DISPATCH are fire-and-forget. Run state is only readable from the actions HTML page, and
api.github.com rate-limits the shared egress so API reads 403 into the queue.

## Loader and bridge

The loader hashes the body and keys its bad list on the hash; a blacklisted hash is skipped
forever. Change the body, never a version number. It rolls back when the bridge object is absent
120s after boot, after one retry — the bridge sets that object synchronously, so a body that
parses is healthy and a rollback means a broken body.

Userscript push: PUT the file. Worker push: deployer with keep_bindings, verify with op=ops.

## Working rules

Branch venice only, PR to main, never push main. No @@CUT or @@BODY markers. Every claim needs a
run ID or a commit. A blocked item gets recorded and abandoned, not retried forever.

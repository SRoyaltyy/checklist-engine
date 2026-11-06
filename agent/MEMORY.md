MEMORY — standing focus
Reporting format, required by the human, 2026-11-06

Every wake response carries three labelled blocks, in this order, before any tool call:

Strategic goal — the goal this wake serves, named from the three: composer never blocks, every prompt carries repair instructions, GitHub work to James' instructions. If the work serves none, say so in one line and stop.

Operational goal — the concrete action this wake takes, and which item or defect it moves.

Percentage to completion — three numbers, always: lane rows proven, gate cleared, harness reliability. Never a single blended figure.

Then the three mandate answers, then work. The format is not optional and does not lapse.

Percentages are stated honestly even when they are embarrassing. A wake that adds nothing says so and says why.

Mandate, every wake

Open with three answers before any action: what was I doing last run, what is my plan now and
which goal does it serve, and what am I actually working on — harness code, James' lane
instructions, or something else. If the plan serves none of the goals, say so in a line or stop.

The goals, in order: 1 composer never blocks, 2 every prompt carries repair instructions,
3 GitHub work to James' instructions to completion with a percentage every turn.

Anything not advancing 1, 2 or 3 is a side quest. Name it and drop it.

Where they stand
Installed loader is 1.6 and the gate is live. Next: add @updateURL and @downloadURL so the
loader maintains itself instead of needing a paste.
Mechanism is this file plus agent/HANDOFF_1741.md. agent/WAKE_PROMPT.md has refused writes;
if it takes now, it carries the mandate directly and this section is the fallback.
No run verdict has ever returned. Fix is a probe workflow that commits agent/RESULT.json with
the run id, conclusion, failing step and last 4KB. Read that file, not the actions API.
Writer rules

A body is cut at the first end marker inside it, newline optional. Marker on the closing line only.
A bare END as the closer makes the body swallow what follows.

cleanBody strips blank lines and chrome words (fences, Copy code, language tags) from head and
tail, twelve lines each. A short body can strip to nothing; keep real content first and last.

The writer strips leading whitespace from every line. Indented YAML is impossible; write YAML in
flow style, all on one line, braces for mappings and lists, zero indentation. Proven failure:
nai-probe.yml committed flat, run 42210301200 died in the same second with no job.

The writer also strips leading markdown: a leading hash or hash-hash or dash goes from line
starts, and lone asterisks get eaten. So fence every body, keep no comment lines in scripts, and
use no asterisks in executable code. Proven failure: open_pr.sh arrived with its comment line
gutted and its parameter expansion mangled.

Never trust a raw read straight after a write; raw caches minutes. Read blob HTML, which keeps
angle brackets and is not cached the same way. base64 through contents also survives.

When a path refuses a second write, use a new path rather than fighting it.

scrape and dispatch debounce 60s per URL. A repeat inside that window is dropped and an older
delivery arrives, which looks like cache but is not. Vary the URL or space repeats. Parked items
carry their whole text, so 60KB bodies starve fresh small requests.

RUNS and DISPATCH are fire-and-forget: they log a status and deliver nothing.

Loader and bridge

The loader hashes the body and keys its bad list on the hash; a blacklisted hash is skipped
forever. Change the body, never a version number. It rolls back when the bridge object is absent
120s after boot, after one retry — the bridge sets that object synchronously, so a body that
parses is healthy and a rollback means a broken body.

The loader is the bootstrapper and only a paste changes it. The bridge is not: the loader
re-fetches agent/BRIDGE.user.js every 60s and evals it, so a PUT to the bridge is live within a
minute with no human. Workers are equally autonomous through the deployer with keep_bindings.
Enhance the bridge and the Workers freely; the loader only by paste.

Userscript push: PUT the file. Worker push: deployer with keep_bindings, verify with op=ops.

Working rules

Branch venice only, PR to main, never push main. No @@CUT or @@BODY markers. Every claim needs a
run ID or a commit; no proof means not done. A blocked item is recorded and abandoned, not
retried forever.

A block that is only a block because of an assumption gets re-examined. The loader paste was
carried for days as the gate while the actual rollback cause sat in the bridge's liveness and was
pushable the whole time.

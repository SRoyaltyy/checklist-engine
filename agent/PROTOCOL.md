PROTOCOL — the wake loop

Standard. Follow in order, every wake.

0. Reading without a tool

web_scrape is metered and shared, so assume it is exhausted. The loop reads by scraping through the page:

Emit a line: two at-signs, SCRAPE, space, the URL.
Stop the wake there. Do not wait, do not poll.
The page fetches it, strips the HTML, writes agent/FETCH.md.
The next wake inlines agent/FETCH.md. Read it, then act.

One URL per wake. For several, scrape the most important and note the rest in STATE.md.

The worker itself is not readable without a fetch. op=ops is only a health check, and only if something can fetch.

1. Orient (no writing yet)
agent/STATE.md
agent/PROGRESS.md
TODO.md on main, ## Venice only — the lane, authoritative
agent/MEMORY.md
agent/FETCH.md — whatever was scraped last wake
2. Ascertain

Compare PROGRESS.md against TODO.md. Correct it where reality moved: done without proof becomes unproven. Lane changed? Journal it, reset STATE.md. Half-done item? Finish or abandon it first.

3. Choose one item

First unticked row matching the lane. One only. Too large means split it.

4. Work

Branch venice/<slug>. Never main. Read the docs the item names before writing code. Keep committed files marker-free.

5. Prove

Run it. A green run ID or a commit is the only proof, and it goes in the PR body. No proof, the row stays unproven.

6. Record
JOURNAL.md — one line: date UTC | item | action | sha | result
STATE.md — rewrite: lane, exact next step
PROGRESS.md — tick or mark unproven, with evidence
MEMORY.md — anything durable
7. Stop

When proven, or when compaction is due. No second item.

Hard rules
Never push main. Never merge without instruction.
No CUT or BODY markers in committed files.
Blocked? Journal it, set STATE.md to it, stop. Do not thrash.

[wake {{TIME}}] {{REASON}}

Read in this order. Stop when you have what you need.

1. Gantt audit. Read agent/GANTT_ROWS.md and score every row: overall percent, per-section percent, counts of done / caveated / in progress / gate / not started. This is the whole-repo view, not your lane.

2. Ascertain your goal. Grep METHODOLOGY.md for "§0d" and "James → Venice", read the newest hits. James overrides everything else. If there is no §0d, say so and work QUEUE.

3. Read agent/PROGRESS.md: your lane, your last percent, problems, to-do. Compare against step 2 and correct it.

4. Continue toward the goal. Next QUEUE item. Verify before claiming done. Stay in your lanes. Note out-of-lane work, do not start it.

5. Before you stop: rewrite PROGRESS.md with new percentages and blockers, journal, rewrite STATE. Then @@DISPATCH outside-event-calendar and stop. Never dispatch in the same turn as a write.

Every @@PUT body starts with a line "@@BODY:x". Write files with @@PUT blocks, not tool calls.

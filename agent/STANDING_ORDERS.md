# Standing orders

Fires on every automated wake. Read in full before acting. The wake text points here.

## 1. Audit first, every wake
1. Read the watermark and skip anything already reported.
2. Pull both agents' activity since it: Kimi's commits and PRs, GPT's commits and PRs, and any new §0c lines.
3. For each item name the exact Gantt v3.1 row. If it matches none, name the nearest and say it matches none.
4. Report current finished % for every row in the table, not a verdict word. Chart figure in brackets. An unmoved row is `level`.
5. Flag any hard gate or decision row that moved, or should have moved and has not.
6. Flag any row running ahead of its own prerequisite.

Never write "stale" alone. A verdict is a number and a delta.

## 2. Units
Row 4 reports OAT variants as primary with question count in brackets. Every other row uses the chart's own denominator. Say so when a denominator changes.

## 3. Then the queue
7. After the audit, work my own queue head. A James ruling beats the queue.
8. Work to the stop condition, not to a time limit. Batch edits, keep commits small, run the test file after each.
9. Three queue items per wake maximum. Park the rest explicitly.
10. Read agent/STATE.md before touching the queue and rewrite it before stopping. Assume the next wake remembers nothing.
11. Never stop mid-edit. Finish the unit or revert to a clean boundary.
12. One journal line in the same turn as every action. The journal, not the chat, is the memory.

## 4. Guardrails
10. Never merge. Never commit to main. Never force push. 40621517496 stays untouched.
11. Do not touch GPT's price gate or rebuild lane, or Kimi's master/ladder lane, without a §0b line allowing it.
12. Edits are fail-closed: on a failed anchor, re-read and lengthen. Never shorten to force a match.
13. One logical change per commit. Green tests are the bar for done, not for correct.

## 5. Log
14. One agent/JOURNAL.md line per action: item, action, sha, test result.
15. §0c only for James-facing proof, opening with the Gantt row tag, or naming the nearest row and saying it matches none.

## 6. Stop
16. Report and stop. Three failed attempts on one edit is blocked, not a fourth.
17. Doorman down or branch mid-migration: report and stop.

## 7. Effort
Non-premium model only. Take the full turn. Do not stop early to look tidy.

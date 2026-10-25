# Answers to Kimi's 4 UNSURE items (§0c READ-ACK, commit 929e001b)
Drafted by James (box) 2026-10-25 ~14:15 HKT. Sources: docs/WAR_ROOM_CONTEXT_FOR_KIMI.md, CYRUS_REQUESTS_LEDGER.md, Cyrus's 4 ground rules, engine code in checklist_brainstorm/engine/universe/.

## 1. LT (long_trend, default 60 bars) test grid — ANSWER (no Cyrus needed)
Use the ratio grid, same convention as every other dial (S_leg_atr is 0.5/0.75/1/1.5/2 x default):
**LT ∈ {30, 45, 60, 90, 120} bars.** Default 60 stays the Step A value. Reason: Cyrus's rule "timeframes and numbers are variables X that the code tests" + ground rule 2 (all conceivable questions) -> wider span beats the narrow {40..120} set; 30 also overlaps the 1-month (~21 bar) "how it got here" history horizon. Log the choice in §0c; no dial-table rewrite of frozen rows — add as new rows/groups 034+.

## 2. W0-EVT scope — ANSWER (from code, no Cyrus needed)
The brief's gloss "event fires on every bar in the window" is WRONG. In the engine (nb_year_sealed.py L219, nbx_year.py L75, nb_spot.py L58) **W0-EVT = window of 0 extra bars: YES if the event fired on the latest known bar (D-1, or a calendar event dated D that is known pre-open), else NO; answer blank if the event feed is invalid that day.** Its "BUT" twin is always NO at the open (move since event is 0). Sibling lenses: T20-CNT (count in last 20 bars: >=2 YES / ==0 for BUT), T20-EXT (20-bar count vs own p95/p05).
Applies to the **New Bot event indicators** (the `E` dict / CAL_EV families: e.g. halts nb4-PDS-NB-039, Reg SHO threshold nb4-BRW-NB-056, calendar/earnings events, candle/price events from ev_at). For the world build: apply W0/T20-CNT/T20-EXT to every boolean event column (blocks A candle patterns, D earnings, E Form 4, G halts/RegSHO, J div/split, L analyst actions).
Action: fix the glossary line in WAR_ROOM_CONTEXT_FOR_KIMI.md.

## 3. Older folders = archive? — ANSWER (mostly yes, one caveat)
Yes: untested_v1/v2, nb32, nb193, map_v5, coverage_v1_x, fix2023, trajectory, unblock are earlier experiments; treat as archive, no runs. Do NOT delete (back-up-before-delete rule). Caveat: use them as **inputs to mine for missing questions** (ground rule 2): e.g. map_v5 six-bucket map and nb193/nb32 New Bot question IDs (DIL-/PDS-/BRW-NB-xxx) — any question there not in QUESTION_TREE v2.7.1 should be listed for groups 034+. Code there (engine/universe/*.py) is the reference for lens semantics (see answer 2).

## 4. Pre-open data — ANSWER (needs Cyrus confirm for future feeds)
Correct today: the only D-day input is the **D open = buy price** (and calendar facts dated D that are published before the open, e.g. a BMO earnings date already on the calendar — but report CONTENTS released D-morning stay excluded, per the strict report_date < D rule already used). Everything else is <= D-1 close; filings by filed/publish date < D; FINRA SI by publication_date < D; FRED by ALFRED vintage.
No premarket/gap feed is wired or planned. Gap-at-open questions (open vs D-1 close) are allowed since the buy happens at the open — **NEEDS CYRUS**: whether questions may condition on the D open gap itself (it is knowable at buy time but means buying after seeing the gap). Default until he answers: do NOT use the D open as a question input; use it only as the buy price.

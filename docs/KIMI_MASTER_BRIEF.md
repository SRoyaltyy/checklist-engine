# KIMI MASTER BRIEF (Cyrus-approved, 2026-10-25 ~22:45 HKT). Read this first.

## ROLE
You build the checklist engine in SRoyaltyy/checklist-engine for repo owner Cyrus. METHODOLOGY.md on main is the source of truth: §0b = instructions to you, §0c = your change log (reply with run IDs + counts). You have no other context; everything needed is here and in the repo.

## GOAL
Find profitable buy/sell setups for US stocks. A setup = a combination of checklist answers + an exit rule. For every setup publish: win %, average win, average loss, expected profit after fees (win% × avg win − loss% × avg loss), sample size, significance stat. Counts only if expected profit > 0 and win rate ≥ 40% (test floors 35/40/45/50). Train 2020–2022, confirm 2023–24, final check 2025–26 (2025–26 is unlocked).

## FRAMEWORK (levers 1–4 + history)
Every question is yes/no or fixed-outcome about one stock on one day D, built from the world state.
- Lever 1 — Where price is: chart picture (trend, range position, distance from highs/lows, Bollinger %B, moving averages).
- Lever 2 — How it got there: the recent leg (run size in ATR, swing lows, drawdown since high, days since high, pump-fade cycles, gap given back).
- Lever 3 — Pressure & participation: volume, green vs red bodies/volume, momentum and oscillators, breadth.
- Lever 4 — Outside context: sector/market moves, peers, earnings dates, short interest/volume, halts, Reg SHO, insider Form 4, 13F, analyst up/downgrades, XBRL financials, GDELT news volume, FRED/ALFRED macro.
- History lever: how this stock behaved last time in the same state (retest counts, past reactions, bucketed).
Every number in a definition is a test variable with a range and default (window lengths, number of highs, indicator lengths, thresholds). Test every value.

## ABSOLUTE PREREQUISITES (all must pass with proof from real files before any shortlist, combine or probability run)
- **P1 Full world state.** One snapshot row per stock per day with every master-list item (~296: TradingView M001–M293 + every non-price source). Proof: docs/WORLD_COVERAGE.csv MEASURED from released shards, one row per item × timeframe: column(s), non-null %, first date, status. Non-WIRED only with stated reason (BLOCKED_SECRET, NOT_AVAILABLE_FREE with tested source + error, EXCLUDED_FREE_TEXT). CI FAILS on a missing row or a WIRED row at 0% filled. A claimed list does not count.
- **P2 Multiple timeframes.** Every item computed on 1d, 5d, 10d, 20d and monthly (~21d) candles, built only from bars < D. Columns named item__tf. Daily indicators relabelled "weekly" do not count.
- **P3 Every possible question.** ~26,000 questions per stock per day from every world column × timeframe under levers 1–4 + history, not just price/volume. Publish counts by data kind and timeframe.
- **P4 No leaks.** Everything knowable before day D's open. All bars/windows end at D−1; day-D open is buy price only. Filings/insider/13F/analyst join on filed/acceptance date < D, never period end. FRED via ALFRED vintages. Adjusted prices only for ratios/returns/indicators; price, market-cap and size cutoffs use raw D−1 close and shares outstanding known that day. Leak test over every column, timeframe and question (rebuild with future cut off, zero mismatches); post columns covered.
- **P5 Combine everything.** Combination search crosses all questions and data kinds (pairs, triples, beyond), never within isolated groups. Each setup scored jointly with its buy/sell rule (Amendment A1, approved).

## FIXED RULES
- Heavy compute only on GitHub runners; run in parallel within the 20-job account cap; never cancel shortlist runs in cleanups.
- Yes/no or fixed outcomes only; if free text must be read to get the answer, don't use it.
- Drop untradeable and < $100M market cap names as of D. Delisted skipped (survivors-only, labelled).
- Score vs same-day market baseline.
- Ratio rule: zero denominator with positive numerator = infinite; both zero = blank. Built tags `_inf`; Taskforce blank-on-zero variant `_blank`. cp_* definitions pinned in §0b (11a0117); use exactly.
- No secrets/keys/passwords in the repo.
- Never silently rewrite published results; version them.
- Partial-data results don't count; label provisional.

## CURRENT STATE (James audit, 2026-10-25 22:36 HKT)
- World snapshot: 114 columns, 0 TA-Lib (fix 8fd25c1 never rebuilt), daily only.
- 13F, Form 4, analyst fetched but not joined; XBRL failed on 404 for unpublished quarters (skip, don't fail); GDELT running; FRED blocked until FRED_API_KEY secret added.
- WORLD_COVERAGE.csv: 39 WIRED / 192 PENDING, never refreshed.
- Question tree 14,643, price/volume only.
- World leak test covered only 89 columns; ARQT cut_errors open.

## ORDER OF WORK
1. Rebuild world snapshot with every block joined point-in-time + all timeframes.
2. Pass coverage gate.
3. Expand question tree to ~26k.
4. Full leak test.
5. Rerun Step A → exit grid.
6. Shortlist (sharded by chunk + merge job).
7. Combine.
8. Confirm 2023–24, then 2025–26.
9. Publish per-setup probabilities.
Post run IDs + counts in §0c after each step.

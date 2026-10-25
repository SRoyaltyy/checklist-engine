# Methodology: the checklist scanner

## 0. Start here if you have no context (e.g. you are Kimi)
**Who and why.** Cyrus Fung, based in Hong Kong, trades US stocks. A team of AI assistants works on this for him ("the War room": James, New Bot, Theme Radar, Grok Bot, Trading Bot Taskforce, Manager Bot). He wants a **scanner**: code that asks thousands of fixed yes/no questions about every US stock each day, and learns which answers have been followed by profitable trades.

**The repos.**
- `SRoyaltyy/checklist-engine` (this repo) holds the question tree, the results, and this doc. The scanner engine code is on branch [`engine/v2.7.2.2`](https://github.com/SRoyaltyy/checklist-engine/tree/engine/v2.7.2.2) (use commit `487387f` or later).
- `SRoyaltyy/fullscan` is a separate, live daily stock-picking pipeline. It supplies the tradeable-stock filter. Don't merge the two.
- `SRoyaltyy/theme-radar` is a separate theme and sector scorer. Don't merge it either.

**Words used below.**
- *Question + answer*: one checklist item and one of its fixed answers, e.g. "route over last 20 days = up_down".
- *Case*: one stock on one day D where an answer was true. *Trade*: buy at D's open, then apply exit rule v1.
- *Cutoff*: a number inside a question's definition (e.g. a "leg" is at least 3 ATR). We test many versions of each.
- *ATR*: average true range, meaning a stock's typical daily move. *SMA, RSI, MACD, RVOL, Bollinger*: standard chart indicators.
- *Practice data* is 2020–24. *2025–26* was sealed until after Fri 2026-10-23 23:00 HKT. Cyrus unlocked it on 2026-10-25 for a live / out-of-sample check once the list exists. Not for discovery or fitting.
- *Luck bar*: with this many tries, some answers will look good by chance. The bar is how strong a result has to be to count.
- *bp*: basis point, 0.01%.

**What we're doing right now.** We're running every checklist question on 2020–24 practice data (Steps A to C in §6) to find question + answer pairs whose trades make money on average after fees and beat the market on the same days. Nothing has passed yet.

**What to look for (your job, Kimi).**
1. Any answer whose expected profit beats the same-day market and clears the luck bar (§7) on 2020–22, and then holds unchanged on 2023–24.
2. Mistakes in our method: peeking at future data, untradeable stocks slipping in, or a few huge trades carrying a result.
3. Which cutoff definitions give an edge, and under what conditions (Cyrus: "try all definitions").

**Where things are.**
| What | Where |
|---|---|
| Method (this file) | `METHODOLOGY.md` |
| Scanner engine code | branch [`engine/v2.7.2.2`](https://github.com/SRoyaltyy/checklist-engine/tree/engine/v2.7.2.2) |
| Question tree and cutoff grid | `dials/` (v2.7.1, v2.7.2.2) |
| Ideas tried and their status | [`dials/TAKEAWAYS.csv`](dials/TAKEAWAYS.csv) |
| Big data files and their sha256 | [`DATA_INDEX.md`](DATA_INDEX.md) |
| Price history (only valid file sha `fb9bbe69…`) | Cyrus's Google Drive, folder `pricehist-backup` |
| Locked question/answer files and run output parts (~1GB each) | Cyrus's Google Drive, folder `checklist_engine_chunks` |
| Tradeable-stock filter | [`buyable_filter_v1/`](buyable_filter_v1/BUYABLE_FILTER_V1.md) |
| Old practice results | `practice_results/` |
| Older experiments | `lookalike/`, `combo/`, `path_bank*/`, `chart_picture_pack/`, `checklist_brainstorm/` |
| Theme Radar research shorts (daily plans and scorecard) | repo [`SRoyaltyy/theme-radar`](https://github.com/SRoyaltyy/theme-radar), `research/shadow_log/` |
| F4TR insider tags 2020–24 | Drive file id `19PtFPKG4O6wBnR5IaEUP0d9PxL0w83cq` |
| F4TR insider tar 2025–26 | Drive file id `1WAKjsY9SWnKFw61fFAuprs-7Mpy0gEWh`. **Unlocked 2026-10-25 (Cyrus):** live / out-of-sample check once the list exists. Not for discovery or fitting. |
| F4TR casebook | theme-radar PR #17; Drive file id `12uJhWTLllB2djHY2BqEsbzxlHeVTc6fm` |
| Nasdaq earnings answers 2020–24 (tags sha `08f15079…ebe42cc`) | Drive file id `1iE6J8sJlGWJLIYKY7iDTyJQ8hrrA5bjr` |
| Earnings calendar 2025-01→2026-06 (manifest sha `ee6e836a…915d`) | Drive `15whNbyvIE8Q_3QV_B92EuyadbRnEcP-N`. **Unlocked 2026-10-25 (Cyrus):** live / out-of-sample check once the list exists. Not for discovery or fitting. |
| New Bot chunks 2025-01→2026-06 (manifest sha `784e00ac…6e45`) | Drive `14XOz6w9QgNKHoSKC_mTD4xhKWie8FuiA`. **Unlocked 2026-10-25 (Cyrus):** live / out-of-sample check once the list exists. Not for discovery or fitting. |
| Chart-picture v2 formulas (sha `0badaa4a…0c05`) | Drive `1pSFAIKcP2EWjieXbG01yVJj6pt-3EeOo` |
| Lock index v3 | Drive `14vtWrL3tfPvXUuFP781BQ9sqEwbI-1uH` |
| Daily stock-picking pipeline | repo `SRoyaltyy/fullscan` (separate) |

**Data access.** The 2020–24 inputs the engine reads (11 files plus a checksum list, survivors only, nothing after 2024-12-31) are on the release page [data-2020-24-v1](https://github.com/SRoyaltyy/checklist-engine/releases/tag/data-2020-24-v1). The engine expects fixed folder paths, so point them at wherever you save the files; the release page says which file goes where. The Drive folders above are the master copies.

**House rules.**
- 2025–26 stock-split dates are used as metadata in `mcap_fix.py` to fix share counts. 2025–26 prices and outcomes may be used for a live / out-of-sample check once the list exists (unlocked, Cyrus 2026-10-25). Not for discovery or fitting.
- No secrets in the repo.
- 2025–26 is unlocked (Cyrus 2026-10-25). Use it for the live / out-of-sample check once the list exists. See the top §0b entry.
- The only valid price file is sha `fb9bbe69…` (see [DATA_INDEX.md](DATA_INDEX.md)).
- Frozen question files are add-only.
- Rules get committed before any results are computed.
- Sealed buy/sell records in fullscan are never rewritten.

This file explains, in plain English, what the scanner is for, how it works, and what we tried before. It replaces the older version of this file (see git history). Related docs: [README.md](README.md), [DATA_INDEX.md](DATA_INDEX.md), [buyable filter](buyable_filter_v1/BUYABLE_FILTER_V1.md), [lookalike](lookalike/LOOKALIKE_V1.md), [combo model](combo/COMBO_MODEL_V1.md), [path bank](path_bank/README.md), [takeaways](dials/TAKEAWAYS.csv).

### 0b. Live updates for Kimi (newest first; the War room adds here)
This file is the single source of truth. The newest entry overrides any pasted prompt and any older house rule it conflicts with.
- **2026-10-25 ~08:35 HKT (Cyrus via James): Kimi, do these next, in this order. This entry overrides older "2025-26 sealed / do not open" lines.**
  - Already done: Step A answers for 2020-22 are finished, all 34/34 chunks. The chunk-1 identity proof passed. Release `data-2020-24-v1` has `answers_000` through `answers_033`.
  - Already done: exit-grid workflows exist. Release `grid-2020-22-v1` has raw tables only (~42 assets as of this writing). Release `combine-2020-22-v1` is still empty (0 assets).
  - 1. Clear the leak-sweep FAIL: https://github.com/SRoyaltyy/checklist-engine/actions/runs/40099037308. Cutting price at day D changed 0 answer values (good). The FAIL is missing question columns at early cut dates: `breakout`, `range_max_position`, `segment_compare`, `fail_shape`, `vol_direction_link`. Prove those are "not enough history yet" gaps, or fix real lookahead. No number counts until this is resolved and logged in the Kimi change log with the verifying run link.
  - 2. Unblock the Actions queue. Cancel duplicate schedule/cron runs waiting on `main` that are not needed while grid-chunk is finishing — especially queued combiner, combiner-predict, grid-backfill, step-a, and exit-grid cron copies holding slots. Keep the in-progress and queued grid-chunk runs on `kimi/exit-grid`. Prefer parallel grid work. Don't serialize.
  - 3. Finish the exit grid for all chunks into release `grid-2020-22-v1`. Raw tables first, then the workflow's shortlist job after grid and gridyearly. Need counts of setups that pass the 2020-21 screen and their 2022 check numbers, not only raw trade/win/sum tables.
  - 4. Publish the finished list to `combine-2020-22-v1` (0 assets now). The combiner does not auto-start when the grid finishes — only `workflow_dispatch` and the hourly schedule. Make fit and predict actually publish. Scoring rules (binding):
    - Probability / ranking metric = expected profit after fees: win% × avg win − loss% × avg loss. Not raw win rate.
    - Minimum win-rate floor defaults to about 40%. Keep the ability to report 35/40/45/50.
    - Drop untradeable names, and names under $100M on day D, from cases and from controls.
    - Score against the same-day market baseline.
    - Grade each independent checklist setup separately under every buy/sell rule (hold 1-30 days, take-profit 2-30%, stop 2-30% or none, early sell when the target is hit). One setup can have many scores.
  - 5. Data windows. This overrides older "2025-26 sealed" lines:
    - 2020-22: discovery and fitting only.
    - 2023-24: one confirmation test after the shortlist.
    - 2025-26: unlocked as of Cyrus 2026-10-25. It may be used for a live / out-of-sample check once the list exists.
    - Still in force: no passwords or keys in the public repo; survivors-only build; questions are yes/no or a fixed set only (no free-text reading).
  - 6. Operating rules stay:
    - Heavy crunching only on GitHub Actions runners. Bots and models write code and workflows and check outputs. They never crunch the grid themselves.
    - Keep the current working code. Only speed it up or fix blockers, without breaking Step A or the identity proof.
    - Every real change: append a dated line to the "Kimi change log" section with what changed and the commit, run, or release link, so James can verify it on GitHub.
    - Commits on `main` are fine. The public repo is fine.
- **2026-10-24 ~22:50 HKT (Cyrus via James): Kimi, make the runs parallel. Keep all the math code as it is.**
  - Rule 1: all heavy compute runs on GitHub runners only. Never on the box, and never by a frontier model. Models only write workflow changes and check outputs.
  - Rule 2: the current engine, questions, scoring and exit-grid code stay as they are. Change only how jobs are launched, unless a fix is truly needed. Then explain why.
  - Step A: change the workflow to a matrix that runs many chunks at once (one or two chunks per job, about 20 at a time, the free-plan limit). Each job adds only its own chunk files, so jobs never overwrite each other. Use the same checkpoint and skip rules.
  - Proof it didn't break: rebuild chunk 1 in a matrix job and show it is identical to the existing `scores_001.parquet` / `answers_001.npz` (compare sha or exact equality).
  - Exit grid: start each chunk's grid job as soon as that chunk's answers land. Don't wait for all 34.
  - Combining model: write and test the code from docs/COMBINING_PREREG.md now, while Step A runs, so the per-setup, per-rule probabilities come out the moment the answers finish.
  - Report: add a "Kimi change log" section to this file. List what changed in each step (files, commit shas, run ids, what was proven, what is still open), newest first. James reads it and checks it against GitHub.
- **2026-10-24 ~13:30 HKT (Cyrus via James): Kimi, build the full exit-rule grid code next.**
  - Your pre-registration (`kimi/pre-register` @ `240cc7b`, docs/COMBINING_PREREG.md) is approved as the spec. Step A today only scores the legacy +20% / 15-day rule, and no grid code exists yet. Write it now.
  - Grid: take-profit 2-30% (every integer), max hold 1-30 sessions (every value), stop-loss 2-30% (every integer) or none. That's 29 x 30 x 30 = 26,100 rules. Early sell when the target is hit. Stop counts first if both are hit on the same day. A gap through the target or stop fills at the open. Fees are 30bp each way. NOT_READY applies per rule.
  - Reuse Step A's saved answers (`answers_NNN.npz` + `trade_base_rows.parquet`). Don't recompute the questions. Use the per-trade first-hit-day method so the whole grid is a few passes over the data, not 26k separate runs.
  - Output: for every setup x rule, report n, win%, avg win, avg loss, expected profit after fees, and the same-day benchmark. Keep the 40% win-rate floor (also show 35/45/50).
  - Splits and luck bar: tune and pick on 2020-21, check once on 2022 with nothing tweaked afterwards, and test the state-to-rule map once on 2023-24. The grid is exempt from per-rule luck counting ONLY under that single 2023-24 test. Any claim that one specific rule works counts every rule tried toward the bar.
  - Add a test that rule (20%, 15d, no stop) reproduces `scoring/trades.py` exit_v1 exactly. Push to a `kimi/exit-grid` branch and open a PR.
- **2026-10-24 ~13:25 HKT (Cyrus via James): exit-rule grid is separate from the question combinations.**
  - A *setup* is a combination of question answers. The *trade rule* (buy/sell strategy) is a separate axis and has nothing to do with the questions.
  - Score every setup under every trade rule: all hold times, all take-profit levels, with early profit-taking enabled. One setup therefore has several win probabilities / expected profits, one per trade rule. The +20% / day-15 rule is only one point on this grid.
  - Luck bar: every (setup x trade rule) pair tried counts as a try. Pick the trade rule on 2020-21 only, confirm on 2022, and use 2023-24 once. Same fees (30bp each way), the same 40% win-rate floor, and the same NOT_READY rule (the window must cover the longest hold).
- **2026-10-24 ~08:50 HKT (Cyrus via Grok Bot): combining rules and reminders.**
  - Combining rules: see "Single questions vs combinations" and §7b. Shortlist on 2020-21, test pairs and the combining model on 2022, and use 2023-24 once for the final test. Failing alone doesn't drop a question.
  - Don't store `answers_*.npz` on the shared bot computer (only about 8.8GB free). All the answers files together are 3-8GB.
  - Hard rules then: 2020-22 only for scoring, nothing from 2025 on, yes/no or fixed-set answers only, no free text. The "nothing from 2025 on" ban is overridden by the 2026-10-25 entry above: 2025-26 may be used for a live / out-of-sample check once the list exists. Yes/no or fixed-set only, and no free text, still stand.
- **2026-10-24 08:45 HKT (Taskforce): Step A handoff.**
  - Engine: branch `engine/v2.7.2.2` @ `487387f`. Run `python3 step_a.py --workers N --chunk 400` with `CHECKLIST_DATA_DIR` and `OUT_DIR` set. Bars are cut at 2022-12-31 inside the script.
  - `487387f` saves every stock-day's answer to every question: `chunks/answers_NNN.npz` (int8, -1 = blank, 0/1 = answer) plus `chunks/trade_base_rows.parquet` (the ticker and date of each row). Saving is on by default (`SAVE_ANSWERS=1`). Pieces that have scores but no answers file get re-run automatically, so pieces 0–8 from `results/step-a-2020-22` will be redone.
  - Push `scores_NNN.parquet` and `errors_NNN.json` to `results/step-a-2020-22`. Upload `answers_*.npz` (about 100–250MB each) as **release assets**, never git (GitHub rejects files over 100MB).
  - Already fixed, don't redo: the calendar_context leak (`tests/test_leak.py`, 20 cut points, 0 differences), the multi_year_position and pump_fade_cycles crashes (`032c6e3`), mcap-unknown stocks (`bd36a24`), and the 120s per-question timeout plus 5-minute heartbeat (`7371812`).
  - Still open: about 300–550 "can't answer" errors per piece on stocks with short histories (`errors_NNN.json`); a code fix only.
  - Universe: 7,238 stocks, 2,845,186 trades that are filtered and ready, and 208,497 set aside as not ready. 34 pieces of 400 questions each, plus `scores_cp_v2.parquet` (8 chart-picture tags, none pass).
  - Taskforce stops its local copy as soon as Kimi posts "Kimi started Step A".

## 0c. Kimi change log (newest first; Kimi maintains this, James checks it against GitHub)

- **2026-10-24 ~23:15 HKT — Parallel Step A live; combiner code written; two infra bugs found and fixed.**
  - **What changed**
    - `step_a.py` gained `--only` (run a subset of chunks; launch plumbing only, no math change). Commit `e8f9402` on `kimi/step-a-wincompat`.
    - `ci/run_step_a_piece.sh` (new): one matrix leg = one chunk. Seeds only its own piece from `results/step-a-2020-22` + the release, runs the engine for that chunk, checkpoints scores+errors to the results branch and answers to the release, then dispatches that chunk's `grid_chunk.yml` jobs. Same `e8f9402`.
    - `ci/push_loop.py`: push retries with fetch+rebase (up to 20 legs push the results branch concurrently). `e8f9402`.
    - `.github/workflows/step_a.yml`: 34-leg matrix, `max-parallel: 20`, `fail-fast: false`, no concurrency group (legs must not cancel each other); optional `verify` dispatch input runs only the identity proof. `e8f9402` (branch) + `0aebb69` (registered on `main` — workflows only run from the default branch).
    - `.github/workflows/grid_chunk.yml` (new, registered on `main` in `0aebb69`): per-chunk exit grid (full window + 2020/2021/2022), prep is idempotent, legs skip cleanly if answers aren't up yet.
    - `ci/push_loop.py` (`beb393b` on `kimi/step-a-wincompat`): also pushes `trade_base_rows.parquet` — the engine writes it on every start but it was never pushed, and `ci/exit_grid_prep.sh` needs it.
    - `ci/exit_grid_prep.sh` (`05b85b3` on `kimi/exit-grid`): robust base-rows fetch (results branch, else single-asset release download, else a clear message).
    - `scoring/combine.py` (`d726c38` on `kimi/exit-grid`): the combining model per `docs/COMBINING_PREREG.md` — one-hot per fixed-set answer level (junk = >95% blank or a level on >95%/<0.5% of days), rule params (m, h, stop) as features, logistic p(win) + ridge E[profit] in a joint trade-score + rule-score form so the 26,100-cell surface is an outer sum. numpy/pandas only. Smoke-tested end-to-end on the local 800-trade sample: losses decrease, 2022 check (Brier + calibration deciles + EV vs benchmark) and per-year strategy maps are produced.
  - **Run ids**
    - Old serial Step A run `40096584458`: cancelled (replaced by the matrix).
    - Matrix run `40105028128` (34 legs, one chunk each, dispatched 2026-10-24 23:00 HKT): in progress.
    - Verify run `40105030811` (rebuilds chunk 1 in a matrix-style job, sha + content comparison vs existing `scores_001.parquet` / `answers_001.npz`): queued behind the matrix; **result pending**.
    - Leak sweep run `40099037308` (60 tickers x 12 stress cut dates): still in progress; verdict to PR #5.
  - **What is proven**: matrix + per-chunk grid workflows are registered and dispatching; the combiner runs end-to-end on sample data; the serial run's checkpoint format is untouched (only launch plumbing changed).
  - **What is still open**: the chunk-1 identity proof (verify run) has not reported yet; first grid legs depend on `trade_base_rows.parquet` landing via `beb393b` (first queued leg that pushes); the combiner has no runner workflow yet (code + smoke test done); Step A pieces 9/34 done at dispatch time.

- **2026-10-25 ~00:05 HKT — combiner runner workflow live; three bugs found in first live legs and fixed.**
  - **What changed**
    - `scoring/combine.py` v2 (`cb80b8a` on `kimi/exit-grid`): answers streamed per chunk (~43GB concat would not fit a runner); smoke-tested end-to-end again on the local sample.
    - `ci/combine_run.sh` + `.github/workflows/combiner.yml` (`cb80b8a`, registered on `main` in `78cd10f`; YAML colon-in-step-name parse fix `b42e86e`/`5866590`; name-only gate `c49ce3e`): hourly gate checks all 34 answers chunks + grid precompute, fits on 2020-21 (one 2022 check), publishes to release `combine-2020-22-v1`.
    - `.github/workflows/step_a.yml` (`26c700c` on branch and main): added `actions: write` — the first finished leg's grid dispatch failed 403 (GITHUB_TOKEN denies cross-workflow dispatch without it).
  - **Run ids**: combiner gate run `40107225696` completed SUCCESS (listed 31 missing chunks, no-opped cleanly). Matrix run `40105028128`: first leg done — piece (3) finished in 31 min with 0 errors, `scores_003.parquet` + `answers_003.npz` published; 13 legs concurrent at last check.
  - **What is still open**: `trade_base_rows.parquet` push pending (first leg ran pre-`beb393b` code); grid dispatches for chunks 0/1/3 need backfill once base rows land; verify proof and leak verdict still pending.

## 1. Goal
- Find checklist question + answer pairs that make money on average per trade.
- **Expected profit** = win% × average win − loss% × average loss. Fees of 30bp each way are taken off first.
- Every trade uses **exit rule v1**: sell at +20% if it gets there, otherwise sell on day 15.
- A result only counts if it beats what the market did on the same days.
- There is a **minimum win rate**. It starts at 40%, and we also test 35, 40, 45 and 50%.
- Later, the good answers get combined into one model that estimates expected profit.
- Code scans every stock. Nobody reads charts by eye.

## 2. Data
- **Survivors only.** Stocks that were delisted are skipped. Prices come from a Stooq backfill ([history10y/build_stooq.py](history10y/build_stooq.py)) plus the history we already had.
- **Tradeable stocks only.** On each day D, a stock is dropped if it fails the fullscan liquidity filter or is worth under $100M, using split-fixed share counts. Peer groups get the same filter.
- For 553 tickers whose market cap looks wrong, only the dollar-volume filter is used. `integrity/quarantine.csv` is always honored.
- Every question is yes/no or picks from a fixed list of labels. No reading of free text.
- **No peeking.** Answers for day D use data up to the close of D−1, plus pre-open data. A leak test for this is planned but **not built yet**.

## 3. Question tree
- The tree is built from **dials 1–4 plus the history lever**: (1) data type, (2) timeframe, (3) derivative, (4) facets, plus "how it got here" history questions. The locked breakdown is in `dials/v2.7.1/README.md`. Step A covers about 2,023 daily columns, not the whole tree.
- Questions are nested like folders: data type → timeframe → derivative → how it's analysed.
- **v2.7.1** has **15,093 questions**: 6,654 base and 8,439 history. Answer file sha `d8adbb46…`.
- **Cutoff grid v2.7.2.2** has **232 cutoffs** and **154,667 versions**, swept one at a time (commit `67844a6`).
- The cutoffs are the thing being tested. Cyrus's rule: try every definition.

## 4. Outcomes
- For every case: the 30-day close, the best and worst point within 30 days, and the exit rule v1 result.
- For each question + answer, the tallies keep: n, wins, average win, average loss, total profit, the share of profit from the top 5% of trades, and the market's result over the same days.

- **Censoring.** A case whose 15-day exit or 30-day outcome runs past the end of the data is NOT_READY and is left out. This applies the same way at every boundary, including the 2025–26 exam. Each question keeps a NOT_READY tally.
- **Benchmark (frozen).** The equal-weight average return of the same filtered tradeable stocks over the same days and the same exit rule. SPY is reported alongside but isn't the bar.
- **Execution realism.** A +20% exit fills at the open if the stock gaps through it. Results are also reported with an extra 20bp of slippage. Passing cases are reported by market-cap band, because survivor-only edge in $100–300M names may fade live.

## 5. Time splits
- **Discover** on 2020–22.
- **Confirm** on 2023–24, with nothing changed.
- **2025–26 is unlocked** (Cyrus 2026-10-25). Use it for a live / out-of-sample check once the list exists. Not for discovery or fitting.

## 6. Plan
- **Status (2026-10-23):** Step A has **not started**. It waits for Cyrus to say "start Step A" to Taskforce. The scanner engine code is on branch [`engine/v2.7.2.2`](https://github.com/SRoyaltyy/checklist-engine/tree/engine/v2.7.2.2) (use commit `487387f` or later). It isn't merged.
- **Step A:** full 2020–24 run at default cutoffs, keeping full rows. Output goes to Drive in parts of about 1GB.
- **Step B:** sweep the cutoff grid on 2020–22, tallies only.
- **Step C:** confirm the winners on 2023–24.
- **Then:** build the combining model.

## 7. Luck bar (James)
- 650,660 tries means a result must be about 5.4 standard errors out. That is roughly 2,500–2,900 setups.
- Measure the gap over the market, not over 50%. Cap how much any single trade can move the average.
- Also run a softer check, and label each result by which check it passed.

- **Not independent (Kimi review #1).** The same stock on nearby days and same-day market shocks shrink the real sample size. Standard errors are grouped by day and by stock, and a block bootstrap is run as well. The bar must pass on those, not on the raw count.
- Near-duplicate cutoffs make the bar conservative. This is stated, and no action is needed.

## 7b. Combining model (pre-registered)
- Fit a logistic or tally model on 2020–22 using every question that isn't junk (see "Single questions vs combinations" below): shortlist and tune on 2020–21, check on 2022. Test the final combined model once on 2023–24 and show its calibration table there. Freeze it before the 2025–26 live / out-of-sample check (unlocked, Cyrus 2026-10-25, once the list exists).
- **Later study, Cyrus's idea:** the day-to-day change in model probability (e.g. 45% → 60%) as an input. Take out the stock's own recent return first so it isn't just momentum. The probability only exists after the combining model is fitted, so this is tested on 2023–24 only. The flip counts (questions turning bullish vs bearish since yesterday) and yesterday's price move come straight from the saved answers, so they go into Step A as ordinary questions. Both add tries to the luck bar.

### Single questions vs combinations (Cyrus 2026-10-24)
- The 5.4 luck bar applies only to claiming that ONE question works alone.
- Step A is not a filter for the combiner. Every question goes into the pre-registered combining model, except junk ones: more than 95% blank, or answering "yes" on more than 95% or fewer than 0.5% of days.
- Step A must save every question's daily yes/no answers, not just summary scores, so the combiner gets the full pool.
- We don't brute-force test pairs or triples. There are about 113M pairs, and the luck bar would explode. Instead, one combining model is trained on 2020-22 and gets a single test on 2023-24, so no huge luck bar applies.
- Selection split: shortlist and tune on 2020-21, check any named pairs and the combining model on 2022, and touch 2023-24 only for the single final test. Every pair we could have tried counts toward the luck bar.
- "Nothing passes alone" is not the verdict. The verdict is the combined score on 2023-24.

## 8. Disk and resources
- Keep 7GB free between 17:00 and 21:00 HKT, and 2GB at other times. If free space is below that, pause between parts.

## 9. What we tried before
- **YES/NO miner pilot.** An AAPL + NVDA smoke test found 0 clears.
- **2020–24 PRELOCK result.** Top-bull fifth plus a stock's own QW spike z≥1.5 gave −0.29% over 5 days (CI −0.46 to −0.11). See `PRELOCK_2025_26.md`, sha `8f1940e3…`.
- **Lookalike / twin matching.** Match the whole 20–30 day picture, the green:red body ratio, Bollinger position and dip depth. See [lookalike/](lookalike/LOOKALIKE_V1.md) and [chart picture formulas](drive_docs/CHART_PICTURE_V2_FORMULAS.md).
- **Rally "tug of war" and probability cloud.** Ways of framing a rally as buyers vs sellers, with a spread of possible outcomes.
- **Theme Radar F4TR insider casebook.** 2,154 cases, no edge found. See [theme-radar PR #17](https://github.com/SRoyaltyy/theme-radar/pull/17) and [practice_results/2020_24_f4tr_score.md](practice_results/2020_24_f4tr_score.md).
- **Short interest and options.** 110 tests, 0 passed.
- **Old smoke test was invalid.** It used made-up history labels. That is now fixed.
- **Old pass bar dropped.** The earlier rule (win rate over 55%, n ≥ 30, 5/10/21-day holds, matched-stock controls) was replaced by expected profit vs the same-day market, using exit rule v1.
- **Dead stocks.** We didn't buy Polygon data and stopped hunting free delisted data, so results are survivors-only.
- **Bots reading charts by eye** was replaced by code, because eye-reading used up too much Grok usage.
- **Cutoff clean-up.** v2.7.2 had 441 cutoffs (208,837 versions). These were cut to 232 (154,667).
- **Chart-picture questions** are on hold. The v2 rebuild starts after 23:00 HKT on 2020–24 only.
- **Grok Bot up/down calls.** Rounds 1–3 found no reliable pre-open direction call. v4 predicted *how big* a move would be, not its direction. The D8 ranker is paper-tracked only. The six-bucket map v1–v5 builders were lost in a disk wipe.
- **Manager's list.** NFLX-lane packs found nothing usable. Combos v1/v2 found no edge. The lookalike pass cleared 0 of 156.
- **7-stock smoke test.** 12,285 columns in 192s. It was a pipe test only, with no win/loss results.

## 10. Known gaps
- About 1,262 columns have no data source yet: sector/theme peers, anchored VWAP, volume profile, Fib swing, events and score path.
- `pump_fade_cycles` and `multi_year_position` crash.
- About 200 base cutoffs are not wired up.
- "Last 2 pivots" is not a cutoff yet.

## 11. Takeaways and luck check (James)
- The ledger is [dials/TAKEAWAYS.csv](dials/TAKEAWAYS.csv), with one row per idea tried. Status is one of: hint, fluke, holding, resolved, note or on_hold. As of 2026-10-23 it has 27 rows: 22 hint, 2 fluke, 0 holding, 1 resolved, 1 note and 1 on_hold.
- Number of tries: 650,660 question × version × answer cells across the full grid, or 58,977 at the default cutoffs. Combining questions later adds more tries, and the luck bar is recomputed when that happens.
- At the full grid the bar is about 5.4 standard errors (about 2,900 setups at a 55% win rate). At the default cutoffs it is about 5.0 (about 2,500). The try count is updated from Taskforce's real column numbers once Step A runs.
- A ledger row moves to "holding" only if it clears the bar on 2020–22, holds unchanged on 2023–24, and then survives the single 2025–26 shot.

# War room context for Kimi (self-contained brief)

Written 2026-10-25 (HKT) by James for Kimi. You are not in Cyrus's "War room" chat, so this file gives you everything that was agreed there. If anything here conflicts with the pinned **GROUND RULES** at the top of `METHODOLOGY.md` §0b, the GROUND RULES win. Items marked **UNSURE** are things James could not confirm from the repo; ask in §0c instead of guessing.

---

## 1. The goal in one paragraph

Cyrus trades US stocks. He wants **profitable buy/sell strategies**, and for each **independent checklist setup** an honest **win probability** and **expected profit after fees**. A "setup" is a combination of fixed-answer checklist questions true on day D (e.g. "RSI14 route over last 20 bars = down_up" AND "earnings in last 5 days = yes"). Code scans every stock, every day. Nobody reads charts by eye.

## 2. The four GROUND RULES (Cyrus, 2026-10-25, override everything)

1. **Use all the data.** Every conceivable source that can be used: every item in `dictionary/WORLD_SNAPSHOT_DICTIONARY.*`, every source in `dictionary/DATA_SOURCES.csv`, and anything else fetchable. Think of a TradingView chart with *every* indicator and *every* data overlay ticked.
2. **Ask all the questions.** Every conceivable question built from levers 1–4 plus the history lever (section 4), applied to every world-state item.
3. **Combine across everything.** The combination search mixes questions in every way possible across all groups and all data blocks. The 34+ groups (`grid_000`… `grid_033`, `034+`) are only a compute split, never a boundary for combining.
4. **No leaks.** Every value must be knowable at buy time (point-in-time, PIT). The leak-proof test must pass before any result counts.

One-line restatement: **build a world state for every item, for every stock, for every trading day 2020–2026, using only data known before that day; then ask every lever question of it; then combine across everything.**

## 3. The world state (what you build first)

For each (ticker, day D) you build one row = the "world snapshot": a value for every dictionary item (233 rows, blocks A–P). Rules:
- Prices: only up to the **D−1 close** (plus genuine pre-open data). The engine shifts answers down one row (`A.shift(1)`), so day D's own OHLCV is never read.
- Events/filings: keyed on **publication/filing date < D** (not period date). FINRA short interest by publication date. FRED via **ALFRED vintages** (the value as it was known then).
- Missing / not enough history → **blank (-1, "n_a")**. Blank is never "no" and never an answer bucket.
- Blocks: A TA-Lib indicators + all 61 candle patterns; B sector/style ETFs (sector as of D−1); C theme peers (correlation clusters); D earnings; E SEC Form 4; F FINRA short interest; G halts + Reg SHO; H SEC XBRL fundamentals; I FRED macro; J dividends/splits; K market breadth; L analyst actions; M 13F; N single-stock options (**gap**, no history beyond DoltHub IV 2020–Oct 2024 M/W/F survivors-only); O GDELT news counts/tone; P Finviz snapshot (**live-only from 2026-08, never scored**).

### Zero-ambiguity definitions
Every item and sub-concept has one fixed definition in the dictionary. **Only the named numbers (X) vary**, and the code sweeps them over a test range. Example: "High" = highest **wick** in a rolling window of N bars through D−1 (C03), N swept 5..252. Do not invent alternative wording; if code differs from the dictionary (14 `differs` rows), fix the code.

## 4. The question framework: levers 1–4 + history ("1234 + history")

Every question is a path down a folder tree: **(1) data type → (2) timeframe → (3) derivative/variant → (4) facet (how it's analysed) → fixed answer set**. History questions add a fifth step: **how it got here**.

### Lever 1 — data type (17 families in v2.7.1)
candles, volume, moving_averages, range_position, extremes, overbought_oversold, momentum, volatility, relative_strength, support_resistance, return_path, liquidity_float, calendar, market_condition, setup_score, events, phase_list. Ground rule 1 extends this to every new world-state block (fundamentals, short interest, macro, news, breadth, 13F, …).

### Lever 2 — timeframe ("k x N")
`k x N` = N composite bars, each k trading days long (k ∈ {1,2,3,5,10,20}). `1x20` = last 20 daily bars; `5x20` = last 20 weekly-ish (5-day) bars ≈ 100 days. Valid pairs per variant are listed in `DIAL_TABLE_v2.7.1.csv` column `valid_lookbacks` (e.g. 1x3, 1x5, 1x10, 1x20, 1x60, 1x120, 2x10 … 20x10). Longer windows (100, 252, 504, 756) where the tree asks.

### Lever 3 — derivative / variant (the actual series)
The concrete indicator or series inside the type, e.g. OHLC, RSI6/12/14/24, MACD12_26_9, SMA20/50/200, EMA21, Bollinger20_2, ATR14, RVOL20, OBV, MFI14, ADX14, Stoch14_3, WilliamsR14, Ichimoku, Donchian20, 52w_range, 3ATR_legs, SPY_VIX, vs_SPY, vs_sector_peers, vs_theme_peers, earnings, form4, analyst_actions, halts, reg_sho, short_interest … (full list: column `variant` of the dial table).

### Lever 4 — facet (how it's analysed) + fixed answer set
E.g. intraday_change {up>1%, down<-1%, flat}; interday_change {up>5%, flat, down>5%}; gap_up {filled, open, none}; speed; route; zone_route; cross_event; price_divergence; time_in_zone; vs_own_past {above_usual, usual, below_usual}; breakout; capitulation_bar … Each facet has a `facet_kind` (directional, momentum, event, decomposition, …) and a leak rule.

### Lever 5 — history ("how it got here")
Applies a history value to a series X (the variant) over window W. 16 locked history values (`dials/v2.7.1/HISTORY_BUCKETS_v2.7.1.csv`), first matching rule wins, sizes in ATR14 for price series, else sX = std of 1-bar changes over 250 bars before W:
| history value | answers |
|---|---|
| route | up_down, down_up, straight_up, straight_down, flat (net move < 1 unit) |
| speed | up/down × speeding/slowing/steady, flat |
| order_of_events | high_first, low_first, none |
| divergence_sync | bull_div, bear_div, none (last 2 pivots of price vs X) |
| change_of_state | moved_up, moved_down, stayed_high/mid/low (terciles) |
| time_since | up/down × recent/mid/old |
| character_change | wilder, calmer, same (std ratio vs prior 250 bars, band 1.5/0.67) |
| retests / retest_count | held, failed, none / 0, 1, 2+ |
| squeeze_release | released_up, released_down, still_squeezed, none |
| stage | advance, decline, top, bottom, base |
| vs_own_past | above_usual, usual, below_usual (percentile 80/20) |
| lead_lag | leads, lags, together, none (vs benchmark, corr ≥ 0.2) |
| timeframe_agreement | agree_up, agree_down, disagree |
| shock_recovery | up_shock_held, up_shock_faded, down_shock_held, down_shock_recovered, partial, none (shock = latest bar with |dX| > 3 units) |

Count in v2.7.1: **15,093 questions = 6,654 base + 8,439 history**. Today Step A only answers ~2,023 daily columns, and ~94% of what runs is own price/volume. Ground rule 2 means the full tree **and** the same levers over every new world-state block.

### Worked examples

**Example 1 (base question).** L1 candles → L2 `1x5` → L3 OHLC → L4 intraday_change. Question: "Over the last 5 daily bars ending D−1, is mean((C−O)/O) > +1%, < −1%, or between?" Answers {up>1%, down<-1%, flat}. Question id `B|candles|OHLC|intraday_change|1x5`. On day D for AAPL you compute 5 numbers from D−5..D−1, average, bucket. Exactly one answer is true.

**Example 2 (history question).** L1 overbought_oversold → L2 `1x20` → L3 RSI14 → history `route`. Question: "How did RSI14 travel over the last 20 bars?" Rule: find the window extreme between start and end; if RSI rose ≥1 unit to a peak then fell ≥1 unit → up_down, etc.; net |move| < 1 unit → flat. Answers {up_down, down_up, straight_up, straight_down, flat}.

**Example 3 (new block, same levers).** L1 events (block F short interest) → L2 `1x60` → L3 short_interest_pct_float → history `change_of_state`. "Did short interest % of float move between terciles of its own 250-bar distribution from the first to the last published value in the window?" Answers {moved_up, moved_down, stayed_high, stayed_mid, stayed_low}. Value used on D = last FINRA publication dated < D. (This question is illustrative of the pattern; it is not yet in the tree.)

### How one world-state item expands into many questions
Take dictionary item **RSI14** (one column per stock-day, plus its history).
- Timeframes: say 10 valid `k x N` pairs.
- Base facets: zone_route, cross_event, price_divergence, time_in_zone, speed, vs_own_past … (~8).
- History values that apply to overbought_oversold: ~10.
- So ≈ 10 × (8 + 10) = **~180 questions**, each with 2–7 fixed answers.
- Then each number inside a definition (e.g. zone high 80, zone low 20, baseline 250 bars) is a cutoff X swept over its grid (e.g. 70|75|80|85|90), one at a time → ×~5 versions per cutoff.
Do this for all 233 items and you get the "all conceivable questions" set.

## 5. Cutoffs (the numbers X inside definitions)

- Cyrus: "try all definitions to see which give an edge under what conditions." Every fixed number is a dial.
- v2.7.2.2: **232 cutoffs**, swept one-at-a-time = **154,667 question-versions** (full cross would be 31M). File `dials/v2.7.2.2/CUTOFF_GRID_v2.7.2.2.csv`.
- Key defaults: **leg ≥ 3 ATR** (`S_leg_atr`, grid 1.5|2.25|3|4.5|6; dictionary C19 says 2..5); **long trend = leg lasting ≥ 60 bars** (`LT=long_trend=60`, grid UNSURE — dictionary only says "(grid)"); baseline 250 bars; oscillator zones 80/20; RSI extremes 70/30; retest tolerance 0.5 ATR; volume spike 3×.
- Grid rules: ATR/%/multiples × {0.5, 0.75, 1, 1.5, 2}; small integers d−1..d+2; oscillator levels ±5, ±10. Directional cutoffs mirror for bull/bear.
- Indicator periods (RSI6 vs RSI14) are **variants (lever 3)**, not cutoffs.

## 6. Answers must be fixed
Every question is **yes/no or one of a fixed set of labels**. No free text, no LLM reading of news/filings. News enters only as counts/tone numbers (GDELT) bucketed into fixed answers.

## 7. Universe and data hygiene
- On each day D drop untradeable names: fails the fullscan liquidity filter, or market cap < **$100M** (split-fixed shares). Unknown market cap = excluded. Peer groups get the same filter. Honor `integrity/quarantine.csv`.
- **Survivors only**: delisted stocks are skipped. Label every result "survivors-only".
- **Score vs the same-day market baseline**: the equal-weight return of the same filtered tradeable stocks on the same days with the same exit rule. SPY is shown but is not the bar.
- Only valid price file: sha `fb9bbe69…` (`DATA_INDEX.md`).

## 8. Scoring (what "good" means)
- **Expected profit after fees** = win% × avg win − loss% × avg loss, fees 30bp each way, plus a 20bp extra-slippage report. Not raw win rate.
- **Minimum win-rate floor**: default 40%; also test 35/40/45/50.
- Must beat the same-day market and clear the **luck bar** (~5.4 standard errors at 650,660 tries; SEs clustered by day and stock + block bootstrap; cap single-trade influence; report top-5% profit share).
- **Sell rules**: 26,100 = take-profit 2–30% (29) × max hold 1–30 sessions (30) × stop 2–30% or none (30). Stop counts first if both hit same day; gaps fill at open. Original reference rule "exit rule v1" = +20% target else sell on day 15.
- Censoring: a case whose exit/outcome runs past the end of data is **NOT_READY**, excluded, tallied.

## 9. Time splits
- Per Cyrus 2026-10-25 ~08:33 HKT the 2025-26 seal is lifted: 2025-26 price/outcome data may be used for mining. Keep the 2020-22 fit / 2023-24 confirm / 2025-26 check order as the default validation design unless §0b says otherwise. Finviz block P (from 2026-08) stays live-only, never scored.

## 10. Combining (ground rule 3)
- Pre-registered combiner: one-hot every fixed answer level of every non-junk question (junk = >95% blank, or a level on >95% / <0.5% of days), sell-rule params as features, logistic p(win) + ridge E[profit]. Fit 2020–21, check 2022, one-shot test 2023–24, freeze before 2025–26.
- It must take inputs from **all** groups and blocks at once. Per-group grids are fine for compute; per-group *combining* violates rule 3.
- Output per setup: win probability + expected profit, per sell rule.

## 11. How you work (binding process)
- Heavy math only on **GitHub Actions runners**; run jobs **concurrently** (matrix), don't serialize by habit.
- Repo is **public**: no secrets, tokens, passwords, emails.
- Rules are committed before results are computed; frozen question files are add-only; never rewrite sealed buy/sell records in fullscan.
- Don't merge `fullscan` or `theme-radar` into this repo.
- Channel: James writes in **§0b** (newest wins); you write in **§0c** (HKT-timestamped lines with commit/run/release links). ACK each §0b within ~10 min, report the phase number every update.
- Phase map: (1) Step A answers → (2) leak proof → (3) exit grid all chunks → (4) shortlist → (5) combine → `combine-2020-22-v1` → (6) 2023–24 confirm → (7) 2025–26 live check.
- Don't restart `grid_000`–`grid_033` or the shortlist; only rerun question IDs whose definitions change; new data enters as groups 034+.

## 12. Glossary (War room terms found in the repo)
- **War room**: Cyrus's group chat of bots (James, New Bot, Theme Radar, Grok Bot, Trading Bot Taskforce, Manager Bot). Kimi is outside it.
- **James**: chief of staff; writes §0b, monitors Kimi. **New Bot**: FRED, earnings dates, FINRA SI, Cboe put/call, CFTC, `cp_*` tags; owns path bank. **Theme Radar**: theme/sector scorer (repo `theme-radar`), Wikipedia views, GDELT. **Grok Bot**: six-bucket map, options IV. **Trading Bot Taskforce / Taskforce**: chart-picture gate, story questions, owns `fullscan`. **Manager Bot**: lock index, coordination.
- **fullscan**: separate live daily stock-picking pipeline; supplies the tradeable filter. **sealed records**: fullscan buy/sell logs, never rewritten.
- **Lever / dial**: one of the 5 axes of question building (§4). **Dial table**: `DIAL_TABLE_v2.7.1.csv`. **Question tree**: `QUESTION_TREE_v2.7.1.csv`.
- **Base question** vs **history question**: plain facet vs "how it got here".
- **Facet / facet_kind**: lever 4 / its category. **Variant**: lever 3.
- **k x N**: N bars each k days long.
- **Cutoff / X**: a number in a definition that is swept. **S_ cutoff**: shared cutoff used by many rows.
- **Bull/bear mirror**: same rule applied in the up and down direction.
- **ATR / ATR14**: average true range (14 bars), the unit for price sizes. **sX**: std of 1-bar changes of a non-price series. **unit**: ATR14 or sX.
- **Leg / 3ATR_legs / phase_list**: moves between zigzag pivots of ≥3 ATR; the list of recent legs. **Long trend**: leg ≥ 60 bars.
- **Pivot / PIV**: strict fractal swing high/low, confirmed by D−1.
- **World state / world snapshot**: one row per stock-day with every dictionary item. **Blocks A–P**: data groups (§3).
- **Dictionary**: `dictionary/WORLD_SNAPSHOT_DICTIONARY.*`, zero-ambiguity spec. **differs**: code disagrees with dictionary — fix code.
- **TradingView master (M001–M296)**: source checklist of every chart item (have / n/a / missing-fetchable / needs-new-data).
- **PIT / leak / leak_verify**: point-in-time rule and its test.
- **Case**: one stock-day where an answer was true. **Trade**: buy D open, apply sell rule.
- **NOT_READY**: case whose outcome isn't fully in the data yet.
- **Blank / n_a / -1**: missing value; not an answer.
- **Survivors-only**: delisted stocks absent.
- **Tradeable / buyable filter**: `buyable_filter_v1` + ≥$100M.
- **Same-day market baseline**: equal-weight tradeable universe, same days, same rule.
- **Expected profit / EV**: §8. **Win-rate floor**: §8. **Luck bar**: §8. **bp**: 0.01%.
- **Exit rule v1 (EXIT_RULE_V1)**: +20% target else day 15. **Exit grid / sell rules (26,100)**: §8.
- **Step A / B / C**: answer all questions at default cutoffs 2020–24 / sweep cutoffs 2020–22 / confirm 2023–24.
- **Chunks / groups `grid_000`…**: compute split of questions (34 existing, 034+ new). **Shortlist**: candidate answers passing 2020–21 + 2022 check. **Combiner**: §10. **Junk**: §10.
- **Practice data** (2020–24) vs **exam** (2025–26, now unlocked for live check only).
- **Lock / lock index**: frozen file versions with sha256 (Manager Bot). **Frozen**: add-only.
- **HINT scan**: early quick 2020–24 OHLC search (Taskforce). **path bank**: New Bot's "how it got here" questions (v1/v2). **casebook / case cards**: example setups with charts. **lookalike**: look-alike setup search. **FINDINGS_FREEZE_V1, STACKS_V1, SCORE_V1**: earlier frozen findings / confluence stacks / scores (none found an edge). **chart picture / cp_***: Taskforce's chart-picture gate and tags. **F4TR**: Form 4 insider tags (Theme Radar). **DIL-NB-xxx / PDS-NB-xxx**: New Bot question ids. **W0-EVT**: window variant meaning "event fires on every bar in the window" (UNSURE exact scope). **TAKEAWAYS.csv**: ideas tried and their status (hint / confirmed); **TFxx**: its ids. **eye readers / blind charts / rounds**: earlier human-style chart-reading rounds that fed v2.6/v2.7 (hints only, never confirmed until engine test). **HLAB**: engine history-label map in `facets_v26`. **SECADD**: missing sector add-on. **untested_v1/v2, nb32, nb193, map_v5, coverage_v1_x, fix2023, trajectory, unblock**: older experiment folders (UNSURE details; treat as archive).
- **HOT4, Lane, Webull**: fullscan-side terms, not part of this repo's method (UNSURE if you meet them).

## 13. UNSURE items (ask in §0c, don't guess)
1. Test grid for long_trend LT (default 60).
2. Exact meaning/scope of `W0-EVT`.
3. Purpose of older folders listed above.
4. Whether "pre-open data" includes any specific feeds beyond D−1 close (none currently wired).

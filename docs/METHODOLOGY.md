# Checklist Scanner: Goals, Method, and What We Tried

Written in plain English. Short translations of trading words are in *(brackets)*.

## Changelog
- **2026-10-23 (HKT):** First version. Replaces the old pass bar (win rate > 50–55% on ≥30 trades) with expected profit vs the market plus a multiple-testing luck check. The older root `METHODOLOGY.md` is kept for history.

---

## 1. Goals
- **A code-only scanner.** Code answers the questions, not bots looking at charts. Bot chart reading was dropped because it cost too much (Grok usage) and wasn't repeatable.
- **A frozen checklist.** Every stock, every trading day, gets the same list of questions. Each answer is yes/no or one label from a fixed list, like ticking boxes on a form.
- **Find what predicts profit.** Count which answers, and later which *combinations* of answers, were followed by **expected profit** *(the average money made per trade, wins and losses together)*.
- **Use the winners live later.** Holding period is up to about 1 month. Multi-week trades are fine.

## 2. Methodology

### 2.1 Which stocks (universe)
- About **11,600 US stocks**, 2020 to mid-2026. Prices come from a Stooq backfill plus our existing history.
- **Survivors only:** stocks that were later delisted are skipped *(survivorship bias: results may look a bit too good)*. Delisted data from Polygon was not bought.
- **Each day D**, drop any stock that fails fullscan's liquidity filter *(too hard to buy/sell)* or is under **$100M market cap** *(company size)*, using split-fixed share counts. This applies to the setups **and** to the comparison group.

### 2.2 The questions
- Checklist **v2.7.1** (commit `0339367`, folder `dials/v2.7.1/`): **15,093 questions** = 6,654 base + 8,439 history.
- Organised as a tree: L1 data type → L2 timeframe → L3 variant → L4 facet or history value.
- **Locked answer lists**, for example:
  - `divergence_sync`: bull_div / bear_div / none *(price and momentum disagree)*
  - `order_of_events`: high_first / low_first / none
  - `route`: up_down / down_up / straight_up / straight_down / flat (moved < 1 ATR)
  - `retests`: held / failed / none, plus `retest_count` 0 / 1 / 2+
  - `squeeze_release`: released_up / released_down / still_squeezed / none *(price was squeezed into a tight range, then broke out)*
  - `shock_recovery`
- Sizes are measured in **ATR** *(average true range = a stock's normal daily move)*, so big and small stocks compare fairly. Bull and bear versions mirror each other.
- **Data rule:** SEC or other data is used only if the answer is yes/no or a fixed set. Never free text.

### 2.3 No peeking (no-leak rule)
The answer for day D may only use data from **before D's open**: the previous close plus anything known pre-open. A test fails the whole run if any question touches D's open or later.

### 2.4 Cutoffs ("dials")
- Version **v2.7.2.2** (commits `c5e980f`, `67844a6`): **232 cutoffs** (35 shared, prefix `S_`), **154,667** question-versions when tested one at a time.
- Every cutoff *(e.g. how big a move counts as "big")* is a dial. The aim: **try all definitions to see which give an edge, and under what conditions.**
- Dials are tested **one at a time**, with all others left at their defaults.

### 2.5 What happened next (outcomes)
For every case we record: the 30-day close, the best and worst points within 30 days, and **exit rule v1** = take profit at +20%, otherwise sell on day 15, with 30bp *(0.30%)* fees each way. **Exit rule v1 is what gets scored.**

### 2.6 Score
- **Expected profit per trade after fees** = win% × average win − loss% × average loss.
  Example: win 4 out of 10, +15% per win, −5% per loss → about +3% per trade. That counts as winning even with a low win rate.
- It is compared against the **same-day market baseline** (what all tradeable stocks did over the same days), not against zero.
- **Minimum win-rate floor:** 40% by default. The floor is itself a dial, tested at 35/40/45/50%.
- **Big-trade guard:** each result shows what share of profit came from its top 5% of trades (flagged if large), and any single trade's effect on the average is capped.
- **Saved for every answer:** count, wins, average win, average loss, total profit, top-5% share, market result. So everything can be re-scored without re-running.

### 2.7 Luck check
With this many questions, some look good by pure chance.
- A **Benjamini–Hochberg-style** correction *(adjusts for testing many things at once)*.
- **James's bar:** about **5 standard errors** on the gap over the market. That's roughly **2,500 setups at 55%** at default cutoffs, or **~2,900** for the full grid (58,977 / 650,660 tries respectively).
- A softer check is also reported, clearly labelled as softer.

### 2.8 Time splits
| Period | Use |
|---|---|
| 2020–22 | **Discover** patterns |
| 2023–24 | **Confirm** them, unchanged |
| 2025-01-01 → 2026-06-30 | **Sealed exam**, opened once only. Sealed buy/sell records are never rewritten. |

### 2.9 Steps
- **Step A:** 2020–24 at default cutoffs, full rows. ~18GB, ~13–14 hours on 4 workers. Saved per year in ~1GB parts to Drive. Disk floors: ≥2GB free always, ≥7GB between 17:00–21:00 HKT. Pauses between years.
- **Step B:** cutoff grid on 2020–22, tallies only (full rows would be ~117–140GB / 100–112h). A "best" cutoff value only counts if its **neighbouring values also work** (so it isn't a lucky spike).
- **Step C:** take the winners to 2023–24, unchanged.
- **Combining step:** a model that combines several answers into one expected-profit number. Same discover / confirm / luck bar, then one sealed test.

### 2.10 Known gaps
- 7-stock smoke test: 12,285 columns, 192s, 18MB; built 5,087 of 6,654 base questions.
- `pump_fade_cycles` and `multi_year_position` crash on 5-day bars.
- ~1,262 history columns have no data source yet (sector peers, volume profile, events). Left **blank, not guessed**.
- 854 blank on long lookbacks (pre-2020 history too short; expected).
- Takeaway ledger: currently `dials/TAKEAWAYS.csv` (planned `dials/ledger/`). "Confirmed" = seen in ≥3 charts.

## 3. What we tried before
(All on 2020–24 unless noted.)
- **Taskforce pilot** mining NFLX-shaped packs:
  - Nasdaq earnings calendar + EPS beat/miss tags (P1/P2/BEAT-MISS): **dropped**.
  - Form 4 insider clusters: industry clusters 166–169 won ~42–50%, matched edge negative; F4-182 ~53% raw at 60 days but <50% matched: **dropped**.
  - Attention spike × earnings: positive but not a dump signal.
  - Short-interest short-ratio: 0 passed.
  - F4TR: unscored.
  - Warnings kept as warnings: trading halts, Reg SHO threshold list, short interest.
- **Theme Radar F4TR insider casebook:** 2,154 cases, no edge ([theme-radar PR #17](https://github.com/SRoyaltyy/theme-radar/pull/17)).
- **Theme Radar short-interest and options tests:** 110 tests, 0 passed.
- **Delisted-stock purchase (Polygon):** skipped.
- **Chart-picture `cp_*` tags:** v1 lost in a box wipe; v2 rebuild pending from `CHART_PICTURE_V2_FORMULAS.md`.
- **Manual chart reading by bots:** replaced by code because of Grok usage cost.
- **Earlier excel_bot A–JL mine:** cuts were thin (N≈25 trades), not trustworthy.
- **Pass bar evolution:** from ">55% on ≥30 trades" → expected profit vs market with a multiple-testing bar (this doc).

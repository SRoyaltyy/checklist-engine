# Checklist Scanner — Methodology, Goals, and What We Tried Before

_Last updated 2026-10-23 (HKT). This replaces the earlier methodology note; that note is kept in full in section 8e so nothing is lost._

## 1. Goal (in one breath)
Plain code (no AI and no eyeballing charts, which burns Grok usage) answers a **fixed checklist** for **every tradeable stock, every day**. Then we find which answers, alone and combined, predict **expected profit**, so they can feed buy decisions.

Cyrus's requests are **cumulative**: a new request adds to the earlier ones, it doesn't replace them.

## 2. The question tree
Think of it like a choose-your-path book. Every question is picked by 4 levers, plus a "history" lever.

| Lever | What it picks | Example |
|---|---|---|
| 1. Type of data | price, volume, etc. | price |
| 2. Timeframe | how far back | 20 bars |
| 3. Derivative | what's built from it | Bollinger band, trend |
| 4. How it's analysed | at least 6 facets | level, slope, cross… |
| History | how the stock **got to** the setup day | "down run, then base, then break up" |

**History lever.** The road to the setup day is cut into phases. A phase ends on a 3-ATR reversal, and a base is 10+ bars. Labels: up run, down run, up shock, down shock, base, retest, break up, break down. All sizes are measured in the stock's own ATR (its normal daily swing), so a sleepy stock and a wild one are judged fairly.

| Version | Questions | Notes |
|---|---|---|
| v2.6 | 14,588 | |
| v2.7 (`0e1ddc5`) | 14,643 | added gap_given_back, pump_fade_cycles, range_box |
| v2.7.1 (`0339367`) | **15,093** = 6,654 base + 8,439 history | answer file `HISTORY_BUCKETS_v2.7.1_FINAL.csv` (sha `d8adbb46…9f69`); added retest_count; shock_recovery gains "partial"; route = up_down / down_up / straight_up / straight_down / flat (<1 ATR) |

## 3. Cutoff grid ("try every definition")
How big does a leg have to be to count as "big"? Instead of guessing, Cyrus wants **every reasonable definition tested**, to see which ones give an edge and under what conditions.

| Version | Cutoffs | Note |
|---|---|---|
| v2.7.2 (`0a4b1e0`) | 441 | first grid |
| v2.7.2.1 (`1248537`) | 231 | trimmed after review |
| v2.7.2.2 (`67844a6`) | **232** | adds S_squeeze_width_pct |

Changing one cutoff at a time gives **154,667 question-versions**, which is **650,660** question × version × answer cells (58,977 at the default cutoffs). Defaults: a leg is ≥ 3 ATR, a long trend is ≥ 60 bars.

## 4. Which stocks, and what we measure afterwards
- **Stocks:** survivors only, about 11.6k stocks, 2020–24. On each day D we drop any name that fails fullscan's liquidity filter or is under **$100M market cap** (using split-fixed SEC share counts). This applies to both the setups and the comparison group. 33 bad tickers are excluded.
- **No peeking:** answers use only data up to the **previous close**. A test fails the whole run if any question touches day D's open or later.
- **Outcomes per case:** 30-day close, best and worst point within 30 days, and **exit rule v1**: take profit at +20%, otherwise sell on day 15, 30bp fee each way. **v1 is what gets scored.**
- **Caveat:** survivors-only means long results are probably too rosy.

## 5. Scoring: expected profit, not win rate
**Expected profit per trade** = win% × average win − loss% × average loss, after fees.
Example: winning 4 times in 10 at +15%, losing 6 at −5%, averages +3% a trade. That counts as winning.

- It's compared with **all tradeable stocks over the same days**, not with zero.
- **Minimum win rate floor:** 40% by default, also tested at 35/40/45/50%.
- **One-trade carry:** the share of profit from the top 5% of trades is flagged, and any single trade's influence is capped.
- **Tallies kept per answer:** count, wins, avg win, avg loss, total profit, top-5% share, market result on the same days. That way everything can be re-scored without rerunning.

## 6. Luck check
With hundreds of thousands of tries, some will look great by pure chance. Every cutoff version and every later combination **counts as a try**.

| Check | Bar |
|---|---|
| Strict (all 650,660 tries) | ~5.4 standard errors ≈ ~2,900 setups at 55% vs coin-flip |
| Default cutoffs only | ~5.0 SE ≈ ~2,500 setups |
| Softer, correlation-aware | also reported |

The bar applies to the **gap over the market**, not over 50%. Each result is labelled with which check it passed.

## 7. Steps and status
| Step | What | Data |
|---|---|---|
| A | Full run at default cutoffs (~13–14 h, ~18GB compressed, saved to Drive in ~1GB parts; disk floors 2GB / 7GB during 17:00–21:00 HKT; pauses for trading jobs) | 2020–24 |
| B | Cutoff grid, tallies only (raw would be ~117–140GB, too big); keep best value + neighbours | 2020–22 only |
| C | Step B winners checked unchanged | 2023–24 |
| Combine | Model that turns several answers into one expected-profit number, with the same discover / check / luck bar | 2020–22 → 2023–24 |
| Exam | One shot | sealed 2025–26 |

**Status (2026-10-23):** the 7-stock test passed (12,285 columns, 192 s, 18MB). It was a **pipe test only, with no edge measured**. Still to fix: 2 crashes and year mode. About 1,262 history columns have no data yet (sector peers, anchored VWAP, volume profile, Fib swing, events, score path) and are left blank, not guessed. Step A waits for Cyrus to send "start Step A" in the Taskforce 1:1.

## 8. What we tried before
### 8a. Takeaways ledger (`dials/TAKEAWAYS.csv`, 27 rows)
Rule: an idea is a **hint** until it's **holding**. Holding needs ≥ 5 charts **and** the engine agreeing on 2020–22, then again on 2023–24. If it doesn't line up, it's a **fluke**.

| Status | Count |
|---|---|
| hint | 22 |
| fluke | 2 (TF03 RSI higher second low; TF06 gap overhead as a wall) |
| holding | 0 |
| resolved / note / on_hold | 1 / 1 / 1 |

Eyeball ideas that **failed** once outcomes came in: new high on drying volume (JA04), gap fully given back (JA05), gap down through old base (JA06), shrinking bounces (JA08), RSI higher second low (TF03, fluke). Base rate (JA15): calm charts hit +20% in 15 days **0/30**, jumpy charts **4/10**.

### 8b. James v5.5f sheet
7,780 rows, after cutting 14 calendar rows. It fed the question bank.

### 8c. Theme Radar
| Test | Result |
|---|---|
| F4TR insider casebook (Form 4 buys by theme rank, 2020–24) | 2,154 cases, **no edge**. [theme-radar PR #17](https://github.com/SRoyaltyy/theme-radar/pull/17) (unmerged); sealed 2025–26 chunks unopened |
| Short-interest / attention / options | 110 tests of 44 SI/ATTN rows plus options rows, **0 passed** (checklist-engine PR #2, `281434e`). Options IV covers only 2020–24; 10 options ideas are blocked for lack of data |
| Finviz pilot | ~1,075 map rows, to be tested on live days after the lock |
| shadow_log locked plans (since 2026-10-06) | EP CLEAN+LOCKED: 40 trades, 77.5% win, +4.20%. Avoid-after-hours CLEAN+LOCKED: 36 trades, 69.4%, +4.72%. FPE LOCKED **fails**: 319 trades, 27.9%, −1.69% |

### 8d. New Bot and Trading Bot Taskforce
- **New Bot** (dial-table versions, model plan): _pending from owner_.
- **Trading Bot Taskforce** (fullscan backtests): _pending from owner_. Engine test: see section 7.

### 8e. Earlier methodology (superseded, kept for the record)
Older plan: yes/no snapshot bank, forward 5/10/21-day returns vs matched controls, win rate > 50%, n ≥ 30, Benjamini–Hochberg. It was replaced by sections 4–6 above.

### Methodology

#### 1. Questions
- **Snapshot bank (~10,000 yes/no questions):** each asks something about a stock on day D ("is RSI14 < 30?", "is the stock on the Reg SHO list?"). Answers can only be YES, NO or NOT_READY (data missing or too short).
- **Path bank ("how it got here", in progress):** the same yes/no form, but about the route to today over 5/10/20/60-day lookbacks: trend of the middle band, pullback depth in ATR, distance from the 20-day high, volume pattern, the swing-low structure. It was inspired by the ALDX (pass) vs AAPL 2022-09-01 (lookalike fail) case: two charts can look the same today but have got there differently.
- **Macro state:** the same idea applied to market regime (FRED rates, copper/yields, VIX, put/call, CFTC).
- **SEC rule:** only binary or fixed-set structured fields (e.g. Form 4 transaction codes, filing present yes/no). No free text and no LLM reading of filings.

#### 2. Point-in-time (PIT) rule
The answer for day D uses only data available before D. Price questions use the last bar before D, at most 7 days old. (The gate's one-off selftest reads D's own bar; the bulk `cp_*` build uses the strict before-D rule.) The Taskforce truncation test (210/210 passed) cuts the history at D and checks the answer doesn't change.

#### 3. Scoring
- Forward returns at **5, 10 and 21 trading days**. 21 is the cap, because Cyrus trades at most 1-month horizons.
- Each YES is compared against **matched controls** (similar stocks on the same date), not the raw market.
- **Fees:** 30 bp per side (60 bp round trip) deducted.
- **Pass bar:** win rate > 50% after fees vs controls (Theme Radar packs use >55%), n ≥ 30, and surviving the **Benjamini–Hochberg** false-discovery correction across all questions tested.
- Negative results are kept as **warnings** (a sign to avoid or short), not discarded.

#### 4. Practice vs exam
- **2020–24 = practice.** It's open, and you may iterate on it.
- **2025–26 = sealed exam.** It's opened once, only after the **Fri 2026-10-23 23:00 HKT lock** (FRIDAY_LOCK_INDEX v5). Every question, formula, file fingerprint and cutoff is frozen first, so rules can't be tuned after seeing results.

#### 5. Chart-picture gate
`chart_picture_pack/gate/chart_picture_gate.py` (sha `2059efb6…`) with `feats.py` (`687db55f…`), `feats2.py` (`d54ce721…`) and `match2.py` (`bea4bf15…`). The selftest must give **AAPL 2022-09-01 = FAIL** (on 4 hard rules: mid_slope_up, gr_body20, pctB, dip_atr) and **ALDX 2021-11-18 = PASS**. The reference case ARQT.csv `e239c454…b9ca` is a copy restored after the wipe and can't be verified against an original. The v2 formulas (drive_docs) are a spare and are not built.

#### 6. Caveats
- **Survivors-only universe:** the price file contains stocks that survived to 2020+. That means survivorship bias, and long-side results are likely optimistic.
- The SECADD sector add-on is a known gap.
- Map v4 was lost in the box wipe; use map v5.1.

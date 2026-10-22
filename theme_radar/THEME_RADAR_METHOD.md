# Theme Radar method (handoff for Kimi)

Theme Radar is Cyrus's companion to `SRoyaltyy/fullscan`. Every US trading day it takes a Finviz Elite snapshot of about 11,600 tickers and scores every one of them with fixed rules (no AI in the daily loop). This file explains the two pieces of Theme Radar work that feed the checklist engine: the **shadow-short log** and the **F4TR insider tags**. Source of truth: `SRoyaltyy/theme-radar`, folder `research/shadow_log/` (README, `rules_frozen.json`, `scorecard.md`).

Everything here is **research only**. Nothing is ever sent to Webull or put on James's buy/sell list.

## 1. The shadow-short log (three frozen research shorts)

### The three strategies ("cells")
Frozen in `research/shadow_log/rules_frozen.json` (sha256 `e66cac9b7208117611466f5606e1ba218a9540b64756629ea8cfe21f64402ba6`). They must never change.

| cell | rule in plain words | hold |
|---|---|---|
| `fpe_delta_t3_earn_today_3d` | Forward P/E went up versus 3 snapshots ago (T-3), and the stock reports earnings today, tomorrow or this week. Short it. | 3 days |
| `fresh_dcp_t1_ep_ge03_2d` | The "data-center-power" theme tag newly appears (0 yesterday, 1 today), the stock is in that day's Excel CLEAR-letter rows, and its earnings yield (EP) is at least 3%. Short it. | 2 days |
| `fresh_dcp_t1_avoid_ah_3d` | Same fresh data-center-power appearance, plus the CLEAR open feature AH >= 1. Short it. | 3 days |

Costs: every trade pays a **15bp fee plus 0.3% borrow**. Results use `short_ret_fee_borrow` (after-close price on entry day to after-close price on exit day).

### How a day's plan is built and locked
1. About **04:45 ET** on the entry day, once the inputs have landed (last evening's theme-radar snapshot and Yahoo closes, plus fullscan's pre-market universe file from ~04:30 ET), `plan_build.py` builds the day's shorts with the frozen rules.
2. The plan is committed to git as `plans/plan_<entry date>.csv`. A backstop run at 09:00 ET (`plan_run.sh`) builds it if missing. A day with no shorts still gets a file marked `# status=no_fires`, so "no fires" is different from "no plan".
3. A plan whose **first git commit is before 09:30 ET** on the entry date is **LOCKED**. Only log rows that match a LOCKED plan (same cell, ticker, entry date, hold) count as LOCKED. Plans are append-only and never overwritten.
4. In the evening the trades are appended to `log.csv` and scored once their exit day arrives.

### The lock script `shadow_log_lock.py` (Python stdlib only)
- `check`: every pinned fingerprint (sha256 of a row's signal fields, then later its outcome fields) must still match, no rows deleted or duplicated, and the rules hash unchanged. CI runs it on every push touching `research/shadow_log/**`.
- `pin`: records new fingerprints. It is append-only and refuses to change an existing pin.
- `plan-pin` / `plan-status`: pin and inspect the pre-open plan.
- `audit` (with `--seal`): checks that no sealed plan or closed LOCKED/CLEAN row moved since its first seal. Weekday CI runs it at 18:30 ET.
- `scorecard`: writes `scorecard.md` and the verdict keys in `summary.json`. Never edit the scorecard by hand.

### Buckets
- **LOCKED**: fingerprinted when appended, and matches a pre-09:30 plan (entry dates from 2026-10-06, the day the lock started).
- **CLEAN pre-lock**: live shadow rows from 2026-09-28 up to the lock. Not fingerprinted; git history is the record.
- **CLEAN+LOCKED**: both of the above, i.e. every forward shadow row since 2026-09-28.
- **MIXED**: includes reconstructed history. Context only. It can never pass the bar.

### Cyrus's bar
Win rate **> 55% over >= 30 closed trades**, after fee and borrow, counted on LOCKED or CLEAN rows only. The mean return is always shown next to the win rate, and a cell that wins often but loses money is flagged **LOSES MONEY**. A stricter extra check (n >= 60 over >= 12 signal dates, win > 55%, mean > 0) is also reported.

### Current results (CLEAN+LOCKED, from `scorecard.md`, log through signal date 2026-10-21, lock check PASS)
| cell | closed n | win | mean after fee+borrow | Cyrus bar | 60/12 check |
|---|---|---|---|---|---|
| `fresh_dcp_t1_ep_ge03_2d` | 39 | 76.9% | +4.26% | MEETS | not yet (n<60) |
| `fresh_dcp_t1_avoid_ah_3d` | 36 | 69.4% | +4.72% | MEETS | not yet (n<60) |
| `fpe_delta_t3_earn_today_3d` | 310 | 35.2% | -1.18% | FAILS | not cleared |

Note: `milestones_posted.json` wrongly records an FPE milestone (n=122, 57.3%) from MIXED totals. The FPE cell has **not** passed.

## 2. F4TR insider tags (Form 4)
- Source: SEC **DERA Form 4 structured data sets** (insider transactions). Only coded fields with fixed values are used (transaction codes, share counts, prices), never free text. That is the general SEC data rule of the checklist engine.
- Tag definitions: tags file sha256 `201f39f300f39428fe44a1e7cce5af17f1bb9f52523b8efc3ee7a75c78a2fe02`. Each tag is a fixed yes/no question about net insider buying in dollars (`form4_net_ps_usd`), written down by meaning before any result was seen.
- Answers are stored 2-bit packed per stock-day: 0 = NR (not ready), 1 = NO, 2 = YES.
- **Insider ownership % tags are all NR**, because there is no point-in-time shares-outstanding figure. "Rank vs theme" tags are NR too.
- **COVER_END = 2026-03-31.** DERA has not published 2026 Q2, so everything after that date is NR. The blind judging window for F4TR is therefore cut to signal dates 2025-01-01 to 2026-03-31 (see `PRELOCK_ADDENDUM_00051.md`).
- Chunks: 2020–24 at `engine/universe/chunks/{y}__F4TR__<sector>.parquet` (tar sha `7735d47d…`). The 2025–26 chunks are a **SEALED** tar (sha256 `d8ed17c3da40680831ea24e2a67d655e1e94e11e588a09550ed02c64f099b628`). Do not open it before the joint lock (Fri 2026-10-23 23:00 HKT).
- 2020–24 practice score (Taskforce, `2020_24_f4tr_score.md`): 666 of 720 cells tested, 236 survived the multiple-testing (BH) filter at 30bp, and **12 cells across 10 row ids passed the Manager bar** (30bp, matched win rate > 50%, matched CI clears 0). These are hints only until the 2025–26 blind check.

## 3. Packs dropped on 2020–24
- **ATTN** (unusual-attention pack) and **SI** (short-interest / squeeze pack) both missed the bar on 2020–24 and are dropped. They are not in the lock and should not come back without a new written hypothesis.

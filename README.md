# checklist-engine — handoff archive

**Private.** This is a handoff archive so another AI (e.g. Kimi) can continue Cyrus Fung's "War room" checklist / probabilistic-model work from cold.

## What it is
A big bank of **yes/no checklist questions** about US stocks (snapshot state, plus "how it got here" path questions and macro state). Each is scored against forward returns (up to 1 month, which is Cyrus's max horizon), against matched controls, after 30 bp/side fees, with BH correction. It passes only if win rate > 50% after fees and n ≥ 30. **2020–24 is practice; 2025–26 is the sealed exam**, opened only after the Fri 2026-10-23 23:00 HKT lock. SEC data: only binary/fixed-set fields, no free text. Details: [METHODOLOGY.md](METHODOLOGY.md).

## Who owned what
| Bot | Data / job |
|---|---|
| James | Form 4 EDGAR (insider filings) |
| New Bot | FRED, earnings dates, FINRA short interest, Cboe put/call, CFTC, `cp_*` tags |
| Theme Radar | Wikipedia page views, GDELT (repo SRoyaltyy/theme-radar — separate, don't merge) |
| Grok Bot | six-bucket map / bucket counts, options IV |
| Trading Bot Taskforce | chart-picture gate, story yes/no questions (owns SRoyaltyy/fullscan — separate) |
| Manager Bot | lock index, task coordination |

## Status (2026-10-22)
- Chart-picture gate restored; selftest **AAPL FAIL / ALDX PASS**. Back in Friday's lock (lock index v5).
- `cp_*` 2020–24 tags built (tags `54a731b2…0d64`, manifest `5f0c3c43…7e2a`, Drive tar `1UAGlXkq0rCdbXtwuGuuUiyImQBf8PfHm`). Taskforce spot-check passed (210/210 PIT; ~22% NOT_READY expected).
- **Findings (practice only):** trading halts (~−3% vs market) and Reg SHO threshold list (~−2.6%) are strong **negative warnings**. Top-bullish stocks plus a sudden warning burst: −0.29% over 5d (CI −0.46 to −0.11%). Thin buy signals: Fed hold, and copper up with yields down (FRED). Most squeeze packs failed (earnings timing, beat/miss, Form 4, short interest, attention spikes ≈ coin flip).
- Known gap: SECADD sector add-on.

## Next steps
1. After the lock, score everything once on 2025–26 and report what survives.
2. Build the path/"how it got here" question bank (5/10/20/60-day lookbacks, ≤21-day horizon), test on 2020–24 only, and lock it before any exam use.
3. Macro-state bank similarly.
4. Fill the SECADD gap.

## Layout
- `checklist_brainstorm/`: engine code, readers, question sheets (`v8src/`, `merge/`…), specs, qa scripts (bulk outputs removed).
- `chart_picture_pack/`: byte-exact copies of the gate files, with `SHA256SUMS`.
- `drive_docs/`: lock index v5 (current) and v4, the v2 formulas, the options IV README.
- `map_v5_1/`: six-bucket map v5.1.
- `practice_results/`: practice-only score notes.
- `theme-radar.md`: Theme Radar's inventory notes.
- `DATA_INDEX.md`: where the big data lives, with sha256. **The only valid price file is `fb9bbe69…`.**

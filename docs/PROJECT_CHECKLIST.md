# Project checklist

Master progress list for Codex and Kimi. The rules live in METHODOLOGY.md on main: §00, P1–P5, P3b, and §0b, including the entries of 2026-10-25 23:35, 2026-10-25 23:40, 2026-10-26 00:30, and the dual sign-off of 2026-10-26 10:40. This file is the box list. Tick a box in the same commit as the work.

**Verified by both: 17/303. Claimed awaiting James: 20.**

## Rules

- Tick a box only when Evidence is filled with a commit SHA or a run URL, and the Done when proof is on main (a file, a column, a run, or a CSV row James can open). Before ticking, the contributor self-verifies: rerun or inspect the proof, not only cite it.
- Never tick partial-data work. A six-stock smoke, a claimed list with no fill rate, and a provisional release do not count.
- One checkbox is one commit-able unit.
- Update this file in the same commit as the work, and add one §0c line per tick with the item id and the run id. Update the summary counts in that same commit.
- No boxes were pre-ticked when this file was created. Later ticks require the evidence below.
- **DUAL SIGN-OFF (Cyrus 2026-10-26 10:36 HKT).** A box counts as DONE only when both signatures are present on its line: `GPT ✓ <date/SHA>` (the contributor ticks `[x]` with Evidence) and `James ✓ <date HKT>` (James independently verified the Evidence on GitHub). A box with only the contributor tick is claimed, awaiting James. Progress counts report both numbers: claimed, and verified. Phase N+1 may start only when every box in phase N is verified by both. James may reject a claim by adding `James ✗ <reason>` and unticking.

## Already on main, and why it is not a tick

- `docs/TV_COVERAGE.csv` has 296 items, M001–M296: 207 WIRED, 78 EXCLUDED_FREE_TEXT, 11 NOT_AVAILABLE_FREE. WIRED rows name snapshot columns and carry no non-null percent. That is not P1.
- `docs/WORLD_COVERAGE.csv` is now on main, explicitly marked SIX_STOCK_PROVISIONAL_NOT_FULL_UNIVERSE. It provides SEC blocked-source evidence for Phase 0 and does not complete Phase 1, 2 or 4.
- `docs/WORLD_COVERAGE_STATUS.md` records run [40209615520](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40209615520) and release [world-smoke-v2-40209615520-1](https://github.com/SRoyaltyy/checklist-engine/releases/tag/world-smoke-v2-40209615520-1). Six stocks. Snapshot prices end 2024-12-31. Coverage FAIL: WIRED 1,367, PENDING 8,269, BLOCKED_SECRET 22, EXCLUDED_LIVE_ONLY 22, EXCLUDED_FREE_TEXT 1,716, NOT_AVAILABLE_FREE 242, over 11,638 item-by-timeframe rows. The leak PASS in that note is the six-stock smoke after the Kagi fix. It does not tick phase 2 or phase 4.
- `docs/EXISTING_SOURCE_AUDIT_v2.md` (commit 05ef8d7) is the org-source inventory for prices, Form 4, 13F, analyst captures, companyfacts, FRED, earnings, Stooq, and options. It says itself that it is not full historical coverage. Use it when writing Evidence for a source-located box. It does not tick one.
- `FRED_API_KEY` is a repository Actions secret. Phase 0.08 is now proved by the merged implementation and green main run 40257553448: 38,038 ALFRED observations across five series, with the value excluded from code and logs.
- The question tree on record is QUESTION_TREE_v2.7: 14,643 questions, 17 price/volume families. The v3 tree and `docs/QUESTION_QUALITY.csv` are not on main.

## Shape of a line

Each box starts with its id, then the task, then `Done when:` and the proof James can verify, then `Evidence:`. Leave Evidence blank until the proof exists. Then set it to a commit SHA or a run URL, tick `[x]`, and add `GPT ✓ <date/SHA>`. James adds `James ✓ <date HKT>` after he checks that proof on GitHub. Both signatures are required before the box is DONE.

## Item counts

| Phase | Title | Boxes |
|---|---|---|
| 0 | Infra (crash fixes and the FRED secret) | 8 |
| 1 | World rebuild | 206 |
| 2 | Coverage gate | 10 |
| 3 | Question tree v3 and the P3b quality gate | 28 |
| 4 | Full leak test | 10 |
| 5 | Step A full rerun | 6 |
| 6 | Exit grid | 5 |
| 7 | Shortlist, sharded | 7 |
| 8 | Combine (Amendment A1) | 8 |
| 9 | 2023–24 check | 4 |
| 10 | 2025–26 check | 5 |
| 11 | Publish probabilities | 6 |
|  | Total | 303 |

## Phase 0 — Infra (crash fixes and the FRED secret)

Each crash James read from runs 40207164333 through 40209615520 needs a test on main. A fix that exists only on codex/world-state-v2 does not tick.

- [x] **0.01** Date-key helper for merge dtypes. Done when: One load-time helper casts every date key to datetime64[ns], and a test merges the MSFT and NVDA keys that raised MergeError datetime64[ns] vs datetime64[us] in runs 40207164333–40209615520 on codex/world-state-v2. The test is on main and passes in CI. Evidence: [merge 38fb6d6](https://github.com/SRoyaltyy/checklist-engine/commit/38fb6d626f2bb6e830d72eb925afec8648099d42) + [green main CI 40257553448](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40257553448). GPT ✓ 38fb6d6. James ✓ 2026-10-26 10:25 HKT (merge 38fb6d6 + CI 40257553448 checked).
- [x] **0.02** world_timeframes import path. Done when: The coverage gate imports world_timeframes on ubuntu-latest with no ModuleNotFoundError. The fix is a real package import or an explicit PYTHONPATH, and the passing CI log is linked. Evidence: [merge 38fb6d6](https://github.com/SRoyaltyy/checklist-engine/commit/38fb6d626f2bb6e830d72eb925afec8648099d42) + [green main CI 40257553448](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40257553448). GPT ✓ 38fb6d6. James ✓ 2026-10-26 10:25 HKT (merge 38fb6d6 + CI 40257553448 checked).
- [x] **0.03** Import smoke before heavy steps. Done when: The world workflow runs an import smoke of the build, leak, and coverage modules and stops before fetch, build, leak, or publish if any import fails. A forced bad import fails that step in CI. Evidence: [merge 38fb6d6](https://github.com/SRoyaltyy/checklist-engine/commit/38fb6d626f2bb6e830d72eb925afec8648099d42) + [green main CI 40257553448](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40257553448). GPT ✓ 38fb6d6. James ✓ 2026-10-26 10:25 HKT (merge 38fb6d6 + CI 40257553448 checked).
- [x] **0.04** SEC fair-access client. Done when: companyfacts requests send User-Agent `checklist-engine research cyrus-checklist@users.noreply.github.com`, Accept-Encoding gzip, at most 10 requests per second, and retry with backoff. A logged MSFT fetch no longer returns 403 for a missing header. Evidence: [merge 38fb6d6](https://github.com/SRoyaltyy/checklist-engine/commit/38fb6d626f2bb6e830d72eb925afec8648099d42) + [green main CI 40257553448](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40257553448). See [SEC_SOURCE_STATUS.json](SEC_SOURCE_STATUS.json) and [WORLD_COVERAGE.csv](WORLD_COVERAGE.csv). GPT ✓ 38fb6d6. James ✓ 2026-10-26 10:25 HKT (merge 38fb6d6 + CI 40257553448 checked). James note: header/throttle/retry client verified; SEC still 403 so data comes via 0.05 BLOCKED path, source still needed in Phase 1.
- [x] **0.05** Persistent SEC 403 is BLOCKED, not a zero column. Done when: If companyfacts is still HTTP 403 after the fair-access client, WORLD_COVERAGE marks that source BLOCKED with the status code, URL, and response excerpt, and the column is absent rather than filled with zeros. Evidence: [merge 38fb6d6](https://github.com/SRoyaltyy/checklist-engine/commit/38fb6d626f2bb6e830d72eb925afec8648099d42) + [green main CI 40257553448](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40257553448). See [SEC_SOURCE_STATUS.json](SEC_SOURCE_STATUS.json) and [WORLD_COVERAGE.csv](WORLD_COVERAGE.csv). GPT ✓ 38fb6d6. James ✓ 2026-10-26 10:25 HKT (merge 38fb6d6 + CI 40257553448 checked).
- [x] **0.06** Publish fails when the asset list is empty. Done when: A test fails the publish step on an empty asset list. The failure mode of release world-smoke-v2-40207938044-1 (published with zero assets) is the regression case. Evidence: [merge 38fb6d6](https://github.com/SRoyaltyy/checklist-engine/commit/38fb6d626f2bb6e830d72eb925afec8648099d42) + [green main CI 40257553448](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40257553448). GPT ✓ 38fb6d6. James ✓ 2026-10-26 10:25 HKT (merge 38fb6d6 + CI 40257553448 checked).
- [x] **0.07** Downstream steps name the upstream failure. Done when: Leak rebuild, the coverage gate, and publish each stop with the upstream step's command, exit code, and log excerpt. They do not continue into a second traceback that hides the first cause. A CI test breaks an upstream step and checks the downstream message. Evidence: [merge 38fb6d6](https://github.com/SRoyaltyy/checklist-engine/commit/38fb6d626f2bb6e830d72eb925afec8648099d42) + [green main CI 40257553448](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40257553448). GPT ✓ 38fb6d6. James ✓ 2026-10-26 10:25 HKT (merge 38fb6d6 + CI 40257553448 checked).
- [x] **0.08** FRED_API_KEY wired, value never shown. Done when: The workflow passes ${{ secrets.FRED_API_KEY }} into the FRED fetch environment. The secret was set 2026-10-25 23:37 HKT. A run writes macro rows, the log does not contain the key, and git has no key. BLOCKED_SECRET is cleared only for series the fetch returned. Evidence: [merge 38fb6d6](https://github.com/SRoyaltyy/checklist-engine/commit/38fb6d626f2bb6e830d72eb925afec8648099d42) + [green main CI 40257553448](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40257553448). GPT ✓ 38fb6d6. James ✓ 2026-10-26 10:25 HKT (merge 38fb6d6 + CI 40257553448 checked).

## Phase 1 — World rebuild

Phase 1 starts only after every Phase 0 box is verified by both signatures. Twenty-six blocks from dictionary/DATA_SOURCES.csv (blocks A–P, 233 items) and docs/TV_COVERAGE.csv (M001–M296). Each block is five boxes: source (check fullscan and theme-radar first), fetch, point-in-time join, candle sizes 1 through 21, and a measured fill. Free public sources only. No paid purchases.

### OHLC and volume bars, including 2025–26

- [x] **1.01** OHLC and volume bars, including 2025–26: source located. Items: C01 daily OHLCV for the tradeable universe. Done when: Check SRoyaltyy/fullscan and SRoyaltyy/theme-radar releases, then checklist-engine release data-2020-24-v1 asset bars_all_le2024.parquet, before any new download. Stooq previously failed TLS; use a free public daily source. Evidence names the repo, release, and asset, or the public URL that was checked. Evidence: [docs/PHASE1_PRICE_SOURCE_INVENTORY.json](https://github.com/SRoyaltyy/checklist-engine/blob/main/docs/PHASE1_PRICE_SOURCE_INVENTORY.json), [org-source audit 05ef8d7](https://github.com/SRoyaltyy/checklist-engine/commit/05ef8d7), and [source collection 40259691137](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40259691137). GPT ✓ 2026-10-26 HKT. James ✓ 2026-10-26.
- [x] **1.02** OHLC and volume bars, including 2025–26: fetched onto a checklist-engine release. Done when: A checklist-engine release holds daily OHLCV for the full universe through the latest completed session, with a checksum. The six-pilot pull through 2026-10-23 inside run 40209615520 does not pass. Evidence: [PRICE_SOURCE_ACCEPTANCE_V6.json](PRICE_SOURCE_ACCEPTANCE_V6.json), [8,447-name accepted inventory](ACCEPTED_PRICE_INVENTORY_V6.csv), immutable [price source release](https://github.com/SRoyaltyy/checklist-engine/releases/tag/world-prices-v3-40259691137-1), and [acceptance run 40292775611](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40292775611). GPT ✓ 2026-10-26 HKT; awaiting James. 280 named exclusions remain in the single EXCLUDED.csv. Historical liquidity/size and full-world context gates are not claimed.
- [ ] **1.03** OHLC and volume bars, including 2025–26: joined point-in-time. Done when: Snapshot features read bars dated < D only. Day-D open is stored as the buy price and is not an input to any question column. Evidence:
- [ ] **1.04** OHLC and volume bars, including 2025–26: built at candle sizes 1 through 21. Done when: The build emits a true OHLC aggregate for every integer candle size from 1 through 21 trading days. A daily series renamed to another timeframe does not pass. The manifest lists the 21 sizes that were built. Evidence:
- [ ] **1.05** OHLC and volume bars, including 2025–26: column count and fill rate measured. Done when: WORLD_COVERAGE reports column count > 0, non-null percent over 2020–2026, and first date for the daily bar columns and for one column of each candle size, on the full universe. Evidence:

### Moving averages and trend

- [x] **1.06** Moving averages and trend: source located. Items: dictionary I001–I023, plus TradingView trend items on the same formulas (ALMA, ADX, Aroon, Ichimoku, supertrend, Kagi, and the rest of that family in docs/TV_COVERAGE.csv). Done when: Source is the phase-1 bar file. No second vendor. The coverage row names the bar asset. Evidence: [source-location proof](PRICE_SOURCE_CLAIM_1_06.json), [source coverage rows](PRICE_DERIVED_SOURCE_COVERAGE.csv), and [approved stitch 40494479693](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40494479693). Source is the same released OHLCV, with all 411 exclusions explicit against 8,727. GPT ✓ 2026-10-28; awaiting James. Source only; derived storage, parameter completeness, fill and PIT gates are separate.
- [ ] **1.07** Moving averages and trend: fetched onto a checklist-engine release. Done when: The world build stores each named length as its own columns (registered defaults plus the other lengths in the variable grid). The shard manifest shows a column count > 0 for this family. Evidence:
- [ ] **1.08** Moving averages and trend: joined point-in-time. Done when: Every average uses bars < D. A test compares one SMA on a cutoff date with a hand calculation that drops the day-D bar. Evidence:
- [ ] **1.09** Moving averages and trend: built at candle sizes 1 through 21. Done when: Each average exists as item__tf for every candle size 1..21. A daily SMA labelled weekly fails. That is the old facets.py _weekly failure. Evidence:
- [ ] **1.10** Moving averages and trend: column count and fill rate measured. Done when: WORLD_COVERAGE has one measured row per item in this family per candle size, with non-null percent and first date. A row at 0 percent cannot be WIRED. Evidence:

### Momentum and oscillators

- [x] **1.11** Momentum and oscillators: source located. Items: dictionary I024–I078 (RSI, MACD including signal and histogram, Stochastic, CMO, Awesome Oscillator, and the rest of section 2). Done when: Source is the phase-1 bar file. The coverage row names it. Evidence: [source-location proof](PRICE_SOURCE_CLAIM_1_11.json), [source coverage rows](PRICE_DERIVED_SOURCE_COVERAGE.csv), and [approved stitch 40494479693](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40494479693). Source is the same released OHLCV, with all 411 exclusions explicit against 8,727. GPT ✓ 2026-10-28; awaiting James. Source only; derived storage, parameter completeness, fill and PIT gates are separate.
- [ ] **1.12** Momentum and oscillators: fetched onto a checklist-engine release. Done when: Each oscillator's lengths are columns: RSI period, MACD fast/slow/signal, Stochastic 14/3/3 where that is the named setting, plus the other registered settings. A TA-Lib default does not replace a named setting that differs. Column count > 0. Evidence:
- [ ] **1.13** Momentum and oscillators: joined point-in-time. Done when: Values use bars < D. MACD signal and histogram are both present. Evidence:
- [ ] **1.14** Momentum and oscillators: built at candle sizes 1 through 21. Done when: Each oscillator is built from that candle's OHLC at sizes 1..21, not copied from the daily series. Evidence:
- [ ] **1.15** Momentum and oscillators: column count and fill rate measured. Done when: WORLD_COVERAGE non-null percent and first date are filled for every item in this family at every candle size. Evidence:

### Volume indicators

- [x] **1.16** Volume indicators: source located. Items: dictionary I079–I096 (OBV, accumulation/distribution, Chaikin money flow, MFI, RVOL, and the rest of section 3). Done when: Source is the phase-1 volume column. The coverage row names it. Evidence: [source-location proof](PRICE_SOURCE_CLAIM_1_16.json), [source coverage rows](PRICE_DERIVED_SOURCE_COVERAGE.csv), and [approved stitch 40494479693](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40494479693). Source is the same released OHLCV, with all 411 exclusions explicit against 8,727. GPT ✓ 2026-10-28; awaiting James. Source only; derived storage, parameter completeness, fill and PIT gates are separate.
- [ ] **1.17** Volume indicators: fetched onto a checklist-engine release. Done when: Raw OBV and accumulation/distribution are stored, plus the percentile form where the dictionary asks for both. RVOL windows are explicit columns. Column count > 0. Evidence:
- [ ] **1.18** Volume indicators: joined point-in-time. Done when: Volume indicators use bars < D, including volume. Evidence:
- [ ] **1.19** Volume indicators: built at candle sizes 1 through 21. Done when: Each volume item exists at candle sizes 1..21 from that candle's volume. Evidence:
- [ ] **1.20** Volume indicators: column count and fill rate measured. Done when: WORLD_COVERAGE non-null percent and first date are filled for every item at every candle size. Intraday-only TV items M046, M145, M169, M199, M273, M280, and M281 stay NOT_AVAILABLE_FREE with the tested-source error, and are not filled with a daily proxy. Evidence:

### Volatility and bands

- [x] **1.21** Volatility and bands: source located. Items: dictionary I097–I105 (ATR, Bollinger, Keltner, bandwidth, and the rest of section 4). Done when: Source is the phase-1 bar file. The coverage row names it. Evidence: [source-location proof](PRICE_SOURCE_CLAIM_1_21.json), [source coverage rows](PRICE_DERIVED_SOURCE_COVERAGE.csv), and [approved stitch 40494479693](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40494479693). Source is the same released OHLCV, with all 411 exclusions explicit against 8,727. GPT ✓ 2026-10-28; awaiting James. Source only; derived storage, parameter completeness, fill and PIT gates are separate.
- [ ] **1.22** Volatility and bands: fetched onto a checklist-engine release. Done when: Bollinger(N, k) uses population standard deviation (ddof=0); defaults N=20, k=2, and percent-B is blank when upper equals lower. ATR(N) is Wilder, seed is the SMA of the first N true ranges, default 14. Keltner matches the dictionary. Column count > 0. Evidence:
- [ ] **1.23** Volatility and bands: joined point-in-time. Done when: Bands use bars < D. A unit test locks cp_pctB and cp_dip_atr to the §0b pin in commit 11a0117. Evidence:
- [ ] **1.24** Volatility and bands: built at candle sizes 1 through 21. Done when: Each band item exists at candle sizes 1..21. Evidence:
- [ ] **1.25** Volatility and bands: column count and fill rate measured. Done when: WORLD_COVERAGE non-null percent and first date are filled for every item at every candle size. Evidence:

### Price structure, extremes, and positional tools

- [x] **1.26** Price structure, extremes, and positional tools: source located. Items: dictionary I106–I117 and swing tools C03–C08 (window high/low, strict fractal pivot, Fibonacci, pivots, pitchfork, distance to high or low). Done when: Source is the phase-1 bar file. The coverage row names it. Evidence: [source-location proof](PRICE_SOURCE_CLAIM_1_26.json), [source coverage rows](PRICE_DERIVED_SOURCE_COVERAGE.csv), and [approved stitch 40494479693](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40494479693). Source is the same released OHLCV, with all 411 exclusions explicit against 8,727. GPT ✓ 2026-10-28; awaiting James. Source only; derived storage, parameter completeness, fill and PIT gates are separate.
- [ ] **1.27** Price structure, extremes, and positional tools: fetched onto a checklist-engine release. Done when: Pivot confirmation is one strict left/right confirmed by D−1. Divergence uses the last K confirmed pivots, K in {2, 3}, against the oscillator on those same bars. Column count > 0. Evidence:
- [ ] **1.28** Price structure, extremes, and positional tools: joined point-in-time. Done when: Highs, lows, and pivots are computed only on bars < D. A pivot that needs the day-D bar is not confirmed. Evidence:
- [ ] **1.29** Price structure, extremes, and positional tools: built at candle sizes 1 through 21. Done when: Each structure item exists at candle sizes 1..21. Evidence:
- [ ] **1.30** Price structure, extremes, and positional tools: column count and fill rate measured. Done when: WORLD_COVERAGE non-null percent and first date are filled for every item at every candle size. Evidence:

### Candle patterns and cp_* tags

- [x] **1.31** Candle patterns and cp_* tags: source located. Items: dictionary I118–I161, all 61 TA-Lib candle patterns, and the pinned cp_* tags (cp_mid_slope_up, cp_gr_body20, cp_pctB, cp_dip_atr, cp_days_since_h20, cp_dd_vs_run, cp_redgreen_vol10, cp_hard_all, lower_highs10). Done when: Source is the phase-1 bar file. The six-stock smoke that found 61 patterns does not by itself pass this block. Evidence: [source-location proof](PRICE_SOURCE_CLAIM_1_31.json), [source coverage rows](PRICE_DERIVED_SOURCE_COVERAGE.csv), and [approved stitch 40494479693](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40494479693). Source is the same released OHLCV, with all 411 exclusions explicit against 8,727. GPT ✓ 2026-10-28; awaiting James. Source only; derived storage, parameter completeness, fill and PIT gates are separate.
- [ ] **1.32** Candle patterns and cp_* tags: fetched onto a checklist-engine release. Done when: All 61 patterns are columns. Dictionary patterns that were only partly specified are built. cp_* matches the §0b pin in commit 11a0117, including the warmup of at least 60 bars (blank fails the hard gate). Column count > 0. Evidence:
- [ ] **1.33** Candle patterns and cp_* tags: joined point-in-time. Done when: Patterns and cp_* read bars ending at D−1. Green is close above open, red is close below open, doji is neither. Evidence:
- [ ] **1.34** Candle patterns and cp_* tags: built at candle sizes 1 through 21. Done when: Patterns are evaluated on each candle size 1..21. A pattern column that exists only on the daily frame fails. Evidence:
- [ ] **1.35** Candle patterns and cp_* tags: column count and fill rate measured. Done when: WORLD_COVERAGE non-null percent and first date are filled for every pattern and every cp_* tag at every candle size. Warmup blanks stay blank, not zero. Evidence:

### Market breadth

Note (2026-10-26 ~14:52 HKT, do not tick): Breadth is a context block on every stock-day row, at every timeframe in the union of 1d, 5d, 10d, and 20d/monthly with candle sizes 1 through 21, point-in-time as of buy time (bars ending D−1). A stock row with no breadth block fails box 2.10.

- [x] **1.36** Market breadth: source located. Items: dictionary I179 and I180, plus TradingView advance/decline items M007, M008, and M009. Done when: Check fullscan and theme-radar, then data-2020-24-v1 asset breadth_2020_24.parquet. Extend the same free construction through 2026. Evidence: [source/readback inventory](BREADTH_RELEASE_READBACK_V1.json) independently rechecks fullscan/theme-radar (no releases), and hash-checks `data-2020-24-v1/breadth_2020_24.parquet` (1,258 sessions through 2024-12-31). The existing SMA50 construction is rebuilt from approved stitch-v2 OHLCV through 2026-10-23 by actual [Actions40689026569](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40689026569), 8,316/8,316 names and seven Linux tests passed; [exact runner proof](BREADTH_ACTIONS_REBUILD_PROOF_V1.json). The new accepted-universe series is separately versioned; its 2024-12-31 value0.246993746993747 differs from old0.2482394366197183. No historical file is rewritten. GPT ✓ 2026-10-28 HKT; awaiting James. Source location only; native partial buckets and warmup remain open.
- [x] **1.37** Market breadth: fetched onto a checklist-engine release. Done when: The release contains percent above SMA50, the advance/decline line, the advance/decline ratio, and new highs minus new lows, checksummed. Evidence: Public [outside-breadth-stitch-v1](https://github.com/SRoyaltyy/checklist-engine/releases/tag/outside-breadth-stitch-v1) daily file143,426 bytes / SHA256 `22dfcd51f88d898a7bc156efa9d79677c769d207604f3a68aec065623d65b2c0`; all four required columns are present. Independently downloaded/hashed and read every row; the exact [Actions40689026569 proof](BREADTH_ACTIONS_REBUILD_PROOF_V1.json) matches both published daily/native hashes. [Readback](BREADTH_RELEASE_READBACK_V1.json) verifies all1,712 daily arithmetic rows and retains source/universe limitations. The runner's separately named draft is not used as public-release evidence. GPT ✓ 2026-10-28 HKT; awaiting James. Download only; partial opening candles, pre2020 aggregate warmup and world PIT/eligibility remain open.
- [ ] **1.38** Market breadth: joined point-in-time. Done when: Breadth on day D uses the universe as of D−1. Survivors-only is written on the column and on the WORLD_COVERAGE row. Evidence:
- [ ] **1.39** Market breadth: built at candle sizes 1 through 21. Done when: The breadth series is aggregated at candle sizes 1..21. Evidence:
- [ ] **1.40** Market breadth: column count and fill rate measured. Done when: WORLD_COVERAGE non-null percent and first date are filled, and the survivors-only label is on the row. Evidence:

### Sector and market baselines

Note (2026-10-26 ~14:52 HKT, do not tick): Sector-ETF features sit on every stock-day row, at every timeframe in the union of 1d, 5d, 10d, and 20d/monthly with candle sizes 1 through 21, point-in-time (bars ending D−1), with relative-to-sector facets. The index set on the stock row is SPY, QQQ, IWM, DIA, and VIX. DIA is not in boxes 1.41–1.45; it is boxes 1.136–1.140. The per-stock industry ETF map is boxes 1.131–1.135. A stock row that lacks these context blocks fails box 2.10.

Note (2026-10-26 ~15:33 HKT, do not tick): Index membership history is skipped. No clean free source. Not a box.

- [x] **1.41** Sector and market baselines: source located. Items: I162 relative strength vs SPY, I163–I175 vs QQQ, IWM, and the 11 SPDRs, I181 SPY trend, I182 beta. Done when: Check fullscan and theme-radar, then data-2020-24-v1 asset etf_2015_le2024.parquet. Extend those ETF daily files through 2026 from the same free source as the stock bars. Evidence: [source-location proof](ETF_BASELINE_SOURCE_LOCATION_V1.json), [complete ETF source run 40484930003](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40484930003), and source collector on main at 1434de9. All 14 required ETF histories self-verified through the stock cutoff 2026-10-23, with org/original-source review recorded. GPT ✓ 2026-10-27 / 1434de9. Awaiting James.
- [x] **1.42** Sector and market baselines: fetched onto a checklist-engine release. Done when: The release contains SPY, QQQ, IWM, and all 11 SPDRs through the same last date as the stock bars. Evidence: [released-byte proof](ETF_BASELINE_SOURCE_FETCHED_V1.json), [run 40484930003](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40484930003), [immutable daily ETF release](https://github.com/SRoyaltyy/checklist-engine/releases/tag/etf-native-context-v1-40484930003-1). All 25 requested daily files were read and hash/date/OHLCV-checked; SPY/QQQ/IWM and all 11 SPDRs have no missing 2020-through-cutoff sessions and end on the stock cutoff 2026-10-23. GPT ✓ 2026-10-27 / 1434de9. Awaiting James.
- [ ] **1.43** Sector and market baselines: joined point-in-time. Done when: Relative strength and beta use ETF closes dated < D, aligned by date. The sector benchmark is the stock's own sector as of D−1. Evidence:
- [x] **1.44** Sector and market baselines: built at candle sizes 1 through 21. Done when: Each baseline exists at candle sizes 1..21. Evidence: SPY, QQQ, IWM, and the 11 SPDRs each have candle sizes 1d through 21d in [outside-market-released-v3-40667431231-1](https://github.com/SRoyaltyy/checklist-engine/releases/tag/outside-market-released-v3-40667431231-1). Monthly candles are in that release too. Cursor ✓ / James ✓ 2026-10-28 (run 40667431231).
- [ ] **1.45** Sector and market baselines: column count and fill rate measured. Done when: WORLD_COVERAGE non-null percent and first date are filled for every baseline at every candle size. A build that only reads SPY fails the SPDR rows. Evidence:

### Sector peers

- [ ] **1.46** Sector peers: source located. Items: I177 relative strength vs sector peers. Done when: Check theme-radar and fullscan for a peer map before building a new one. Prices come from the phase-1 bar file. data-2020-24-v1 has the ETF file and does not ship the peer map as a release asset. Evidence:
- [ ] **1.47** Sector peers: fetched onto a checklist-engine release. Done when: The peer map is a versioned release asset, keyed by the industry code known on each date. Evidence:
- [ ] **1.48** Sector peers: joined point-in-time. Done when: Peer statistics for day D use peers and prices dated < D. Theme Radar raw Finviz fields are not the source. Evidence:
- [ ] **1.49** Sector peers: built at candle sizes 1 through 21. Done when: Peer relative values are computed at candle sizes 1..21. Evidence:
- [ ] **1.50** Sector peers: column count and fill rate measured. Done when: WORLD_COVERAGE non-null percent and first date are filled. An unknown industry is blank, not zero. Evidence:

### Theme peers

- [ ] **1.51** Theme peers: source located. Items: I176 relative strength vs theme peers. Done when: Check theme-radar for the cluster file first. Prices come from the phase-1 bar file. DATA_SOURCES marks this item partly in-repo (prices yes, cluster file no) and untested. Evidence:
- [ ] **1.52** Theme peers: fetched onto a checklist-engine release. Done when: A point-in-time cluster file is a release asset, or the row is NOT_AVAILABLE_FREE or BLOCKED with the path that was tested and the error. A price-only column does not pass as theme peers. Evidence:
- [ ] **1.53** Theme peers: joined point-in-time. Done when: Membership and prices are dated < D. Evidence:
- [ ] **1.54** Theme peers: built at candle sizes 1 through 21. Done when: If the cluster file exists, theme-peer stats are built at candle sizes 1..21. If it does not, every candle-size row carries the same written blocker. Evidence:
- [ ] **1.55** Theme peers: column count and fill rate measured. Done when: WORLD_COVERAGE has a measured row per candle size with either a non-null percent or that blocker. No silent PENDING. Evidence:

### Earnings

Note (2026-10-26 ~15:33 HKT, do not tick): The 2025–26 dates and surprise source is boxes 1.161–1.165. Boxes 1.56–1.60 stay as they are.

- [ ] **1.56** Earnings: source located. Items: I184 date and timing, I185 surprise, I186 gap reaction and drift. Done when: Check fullscan, theme-radar, and checklist-engine release data-2020-24-v1 asset nasdaq_earn_2020-24.tar. 2025–26 files that exist only on the box are uploaded, or refetched from the Nasdaq public calendar. Evidence:
- [ ] **1.57** Earnings: fetched onto a checklist-engine release. Done when: The release holds the calendar and the surprise fields through 2026, checksummed. A before-open / after-close flag that is unknown is labelled unknown. Evidence:
- [ ] **1.58** Earnings: joined point-in-time. Done when: An earnings row joins when its publication time is before the open of D. report_date < D. A report released on the morning of D is excluded. Gap and drift use the bar file after that join. Evidence:
- [ ] **1.59** Earnings: built at candle sizes 1 through 21. Done when: Days since, days until, and count inside the window are evaluated at candle sizes 1..21. Evidence:
- [ ] **1.60** Earnings: column count and fill rate measured. Done when: WORLD_COVERAGE non-null percent and first date are filled for I184, I185, and I186. A column that is constantly 'unknown' does not count as a filled surprise. Evidence:

### Form 4 insider trades

- [ ] **1.61** Form 4 insider trades: source located. Items: I187. Done when: Check SRoyaltyy/fullscan and SRoyaltyy/theme-radar for Form 4, then data-2020-24-v1 asset f4tr_insider_tags_2020_24.csv. Tags alone are not the open-market tape. If the org copies lack open-market buy and sell, shares, and price, pull SEC EDGAR Form 4 bulk with the fair-access User-Agent. Evidence:
- [ ] **1.62** Form 4 insider trades: fetched onto a checklist-engine release. Done when: The release holds open-market purchase and sale rows (transaction code, shares, price, filing date) for 2020–2026, checksummed. A filing-count column does not pass. Evidence:
- [ ] **1.63** Form 4 insider trades: joined point-in-time. Done when: Join on filing or acceptance date < D, never the transaction period. Evidence:
- [ ] **1.64** Form 4 insider trades: built at candle sizes 1 through 21. Done when: Days since the last buy, days since the last sell, and counts inside the window exist at candle sizes 1..21. Evidence:
- [ ] **1.65** Form 4 insider trades: column count and fill rate measured. Done when: WORLD_COVERAGE non-null percent and first date are filled, and the row names the EDGAR asset rather than a count proxy. Evidence:

### 13F holdings

- [ ] **1.66** 13F holdings: source located. Items: I199. Done when: Check fullscan and theme-radar for 13F-HR, then checklist-engine releases. An empty parquet does not count. Use SEC EDGAR bulk with the fair-access User-Agent. Evidence:
- [ ] **1.67** 13F holdings: fetched onto a checklist-engine release. Done when: The release holds holdings quantities and the filer, dated by filing date, checksummed. Evidence:
- [ ] **1.68** 13F holdings: joined point-in-time. Done when: Join on filing date < D, never the quarter end. Evidence:
- [ ] **1.69** 13F holdings: built at candle sizes 1 through 21. Done when: Holding level, change versus the prior filing, and the count of filers are sampled at candle sizes 1..21. Evidence:
- [ ] **1.70** 13F holdings: column count and fill rate measured. Done when: WORLD_COVERAGE non-null percent and first date are filled. A mention count or an empty file fails. Evidence:

### Analyst ratings and targets

- [ ] **1.71** Analyst ratings and targets: source located. Items: I197. Done when: Check fullscan and theme-radar for historical ratings and price targets, then checklist-engine releases. Finviz live fields are not this source. Yahoo upgrades_downgrades is the free dated source DATA_SOURCES already marks proven. Evidence:
- [ ] **1.72** Analyst ratings and targets: fetched onto a checklist-engine release. Done when: The release holds dated actions (upgrade, downgrade, initiation) and the target price for 2020–2026, checksummed. Evidence:
- [ ] **1.73** Analyst ratings and targets: joined point-in-time. Done when: Join on the action date < D. Evidence:
- [ ] **1.74** Analyst ratings and targets: built at candle sizes 1 through 21. Done when: Days since the last upgrade, days since the last downgrade, distance to the target, and counts inside the window exist at candle sizes 1..21. Evidence:
- [ ] **1.75** Analyst ratings and targets: column count and fill rate measured. Done when: WORLD_COVERAGE non-null percent and first date are filled. An action count with no direction fails. Evidence:

### XBRL companyfacts, every filing version

- [ ] **1.76** XBRL companyfacts, every filing version: source located. Items: I192 SEC fundamentals and I194 Altman Z, Piotroski F, and Beneish M. Done when: Source is SEC EDGAR companyfacts through the phase-0 fair-access client. The latest-only frames endpoint is not the source. M290 in docs/TV_COVERAGE.csv is NOT_AVAILABLE_FREE with an intraday reason; that reason is wrong for this fundamental and is replaced. Evidence:
- [ ] **1.77** XBRL companyfacts, every filing version: fetched onto a checklist-engine release. Done when: The release stores every filed version with filed date, accession, unit, and period, checksummed. A 404 for an unpublished future quarter is a logged skip, not a job failure. Evidence:
- [ ] **1.78** XBRL companyfacts, every filing version: joined point-in-time. Done when: Join on filed date < D, never the period end. A fact filed on D is excluded. Evidence:
- [ ] **1.79** XBRL companyfacts, every filing version: built at candle sizes 1 through 21. Done when: Levels and changes are sampled at candle sizes 1..21. Evidence:
- [ ] **1.80** XBRL companyfacts, every filing version: column count and fill rate measured. Done when: WORLD_COVERAGE non-null percent and first date are filled for I192 and I194, or the row is BLOCKED with the 403 evidence from phase 0. A zero-filled fundamental fails. Evidence:

### Shares outstanding, float, and the size filter

- [ ] **1.81** Shares outstanding, float, and the size filter: source located. Items: I193, plus the raw D−1 close used for price-level tests and the $100M market-cap cutoff. Done when: Source is SEC dei:EntityCommonStockSharesOutstanding by filed date. data-2020-24-v1 asset sec_shares_out_filed_le_2024.parquet ends in 2024 and is extended. Finviz float fields tested empty and are not the source. Evidence:
- [ ] **1.82** Shares outstanding, float, and the size filter: fetched onto a checklist-engine release. Done when: The release holds shares outstanding by filed date through 2026. Evidence:
- [ ] **1.83** Shares outstanding, float, and the size filter: joined point-in-time. Done when: Shares used on D are the latest filing with filed date < D. Market cap is raw D−1 close times those shares. Adjusted close is not used for the $100M cutoff or for any price-level test. Unknown market cap is excluded. Evidence:
- [ ] **1.84** Shares outstanding, float, and the size filter: built at candle sizes 1 through 21. Done when: Shares outstanding is sampled at candle sizes 1..21. The size filter is one point-in-time flag, documented once, not repeated as 21 fake candles. Evidence:
- [ ] **1.85** Shares outstanding, float, and the size filter: column count and fill rate measured. Done when: WORLD_COVERAGE reports non-null percent for shares outstanding and for the raw-close column used in the filter, and states how many names the filter drops. Evidence:

### GDELT news counts and tone

**Superseding scope decision — 2026-10-28 ~16:30/16:40 HKT:** all news is excluded. Items 1.86–1.90 are **dropped by Cyrus 2026-10-28: tone is evaluated after the fact, so it is not usable live**. The earlier numeric-tone permission is withdrawn. Existing evidence is historical only; these are dropped requirements, not completed boxes or James sign-offs.

- [ ] **1.86** GDELT news counts and tone: source located. Items: I200. Done when: Source is GDELT 2.0 public events and GKG. Check fullscan and theme-radar first. Store counts and tone only. Free text is excluded. Evidence: **Dropped by Cyrus 2026-10-28: tone is evaluated after the fact, so it is not usable live.**
- [ ] **1.87** GDELT news counts and tone: fetched onto a checklist-engine release. Done when: The release holds daily article counts and tone by ticker for 2020–2026, checksummed. Evidence: **Dropped by Cyrus 2026-10-28: tone is evaluated after the fact, so it is not usable live.**
- [ ] **1.88** GDELT news counts and tone: joined point-in-time. Done when: A story counts on D only when its GDELT timestamp is before the open. Evidence: **Dropped by Cyrus 2026-10-28: tone is evaluated after the fact, so it is not usable live.**
- [ ] **1.89** GDELT news counts and tone: built at candle sizes 1 through 21. Done when: Count and tone are aggregated at candle sizes 1..21. Evidence: **Dropped by Cyrus 2026-10-28: tone is evaluated after the fact, so it is not usable live.**
- [ ] **1.90** GDELT news counts and tone: column count and fill rate measured. Done when: WORLD_COVERAGE non-null percent and first date are filled. A column that required reading article text is EXCLUDED_FREE_TEXT with that reason. Evidence: **Dropped by Cyrus 2026-10-28: tone is evaluated after the fact, so it is not usable live.**

### FRED and ALFRED macro

Note (2026-10-26 ~14:52 HKT, do not tick): Macro is a context block on every stock-day row, at every timeframe in the union of 1d, 5d, 10d, and 20d/monthly with candle sizes 1 through 21, using the ALFRED vintage known as of buy time. Boxes 1.91 and 1.92 stay as already signed. A stock row with no macro block fails box 2.10.

- [x] **1.91** FRED and ALFRED macro: source located. Items: I195 FRED macro and I178 VIX. Done when: Source is the FRED API using the phase-0 secret. ALFRED vintage dates are the point-in-time values. The VIXCLS file in data-2020-24-v1 is not a vintage series and does not pass on its own. Evidence: [merge 2f3eaaa](https://github.com/SRoyaltyy/checklist-engine/commit/2f3eaaa2df798ce0febb93c870dcccef2060a39e) + [real vintage source run 40266650669](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40266650669) + [MACRO_SOURCE_STATUS_V3.json](MACRO_SOURCE_STATUS_V3.json). GPT ✓ 2026-10-26/2f3eaaa. James ✓ (2026-10-26 12:36 HKT: release fred-structured-v3-40266650669-1 exists with checksum, run 40266650669 green, no secret in log).
- [x] **1.92** FRED and ALFRED macro: fetched onto a checklist-engine release. Done when: The release holds each required series as vintage rows (observation date, realtime start, value), checksummed. The log does not contain the API key. Evidence: [checksummed 13-series release](https://github.com/SRoyaltyy/checklist-engine/releases/tag/fred-structured-v3-40266650669-1), [source run 40266650669](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40266650669), [source manifest](MACRO_SOURCE_STATUS_V3.json); 900,986 vintage rows, complete available source ranges with the earlier credit-spread archive gap explicit. GPT ✓ 2026-10-26/2f3eaaa. James ✓ (2026-10-26 12:36 HKT: release fred-structured-v3-40266650669-1 exists with checksum, run 40266650669 green, no secret in log).
- [ ] **1.93** FRED and ALFRED macro: joined point-in-time. Done when: The value on D is the vintage whose realtime period contains the morning of D and whose observation date is < D. Evidence:
- [ ] **1.94** FRED and ALFRED macro: built at candle sizes 1 through 21. Done when: Each macro series is sampled at candle sizes 1..21. Evidence:
- [ ] **1.95** FRED and ALFRED macro: column count and fill rate measured. Done when: WORLD_COVERAGE non-null percent and first date are filled, and BLOCKED_SECRET is gone for every series the fetch returned. Evidence:

### Finviz snapshot, live only

- [ ] **1.96** Finviz snapshot, live only: source located. Items: I198, block P. Done when: The source is the theme-radar nightly snapshots from 2026-08-06. Record that path. Do not copy a Finviz token into the repo, and do not buy a feed. Evidence:
- [ ] **1.97** Finviz snapshot, live only: fetched onto a checklist-engine release. Done when: No scored world column is fetched from Finviz. Raw ratings, targets, short float, and earnings dates stay in theme-radar. Evidence:
- [ ] **1.98** Finviz snapshot, live only: joined point-in-time. Done when: The snapshot is not joined into the backtest table. Evidence:
- [ ] **1.99** Finviz snapshot, live only: built at candle sizes 1 through 21. Done when: Candle sizes 1..21 are not built for Finviz. The coverage rows say EXCLUDED_LIVE_ONLY and say why a candle grid does not apply. Evidence:
- [ ] **1.100** Finviz snapshot, live only: column count and fill rate measured. Done when: WORLD_COVERAGE has an EXCLUDED_LIVE_ONLY row for I198. A WIRED Finviz column fails this box. Evidence:

### FINRA short interest and daily short volume

Note (2026-10-26 ~15:33 HKT, do not tick): Daily short volume is already this block (I189), with short interest (I188). No second block.

- [ ] **1.101** FINRA short interest and daily short volume: source located. Items: I188 and I189. Done when: Check fullscan, theme-radar, and checklist-engine releases. DATA_SOURCES marks both box-only. CDN 403s on old short-volume files stay a tested error. Evidence names the asset actually used. Evidence:
- [ ] **1.102** FINRA short interest and daily short volume: fetched onto a checklist-engine release. Done when: The release holds short interest by FINRA publication date and daily short volume for 2020–2026, checksummed. Evidence:
- [ ] **1.103** FINRA short interest and daily short volume: joined point-in-time. Done when: Short interest joins on publication date < D, never the settlement date. A short-volume print counts only after its file is published. Evidence:
- [ ] **1.104** FINRA short interest and daily short volume: built at candle sizes 1 through 21. Done when: Both series are aggregated at candle sizes 1..21. Evidence:
- [ ] **1.105** FINRA short interest and daily short volume: column count and fill rate measured. Done when: WORLD_COVERAGE non-null percent and first date are filled for I188 and I189, and the publication-date rule is written on the row. Evidence:

### Trading halts

- [ ] **1.106** Trading halts: source located. Items: I191. Done when: Check fullscan and theme-radar, then the Nasdaq Trader public halts feed. The repo folder halts/ is old results, not the raw tape. Evidence:
- [ ] **1.107** Trading halts: fetched onto a checklist-engine release. Done when: The release holds halt start, halt end, and reason code, checksummed, including 2025–26. Evidence:
- [ ] **1.108** Trading halts: joined point-in-time. Done when: A halt is visible on D only when its timestamp is before the open. Halt duration is not stored as a price gap. Evidence:
- [ ] **1.109** Trading halts: built at candle sizes 1 through 21. Done when: Days since the last halt, and the halt count inside the window, exist at candle sizes 1..21. Evidence:
- [ ] **1.110** Trading halts: column count and fill rate measured. Done when: WORLD_COVERAGE non-null percent and first date are filled. Halt category ids are stable across runs. Evidence:

### Reg SHO threshold list

- [ ] **1.111** Reg SHO threshold list: source located. Items: I190. Done when: The Nasdaq list for 2020–24 is data-2020-24-v1 asset regsho_nasdaq_th_2020_24.csv. The NYSE list is still outside the release until it is uploaded. Extend both through 2026 from the public lists. Evidence:
- [ ] **1.112** Reg SHO threshold list: fetched onto a checklist-engine release. Done when: The release holds Nasdaq and NYSE threshold membership by date through 2026. Evidence:
- [ ] **1.113** Reg SHO threshold list: joined point-in-time. Done when: Membership on D uses the list publication date < D. Evidence:
- [ ] **1.114** Reg SHO threshold list: built at candle sizes 1 through 21. Done when: The on-list flag and days on the list exist at candle sizes 1..21. Evidence:
- [ ] **1.115** Reg SHO threshold list: column count and fill rate measured. Done when: WORLD_COVERAGE non-null percent and first date are filled for both venues. A Nasdaq-only file fails the NYSE half. Evidence:

### Dividends and splits

- [ ] **1.116** Dividends and splits: source located. Items: I196. This is the item that was marked WIRED at 0 percent fill. A split baked into the adjusted bar does not satisfy the row.. Done when: Nasdaq dividend and split calendars, cross-checked to Yahoo chart events. DATA_SOURCES marks the fetch proven and the release asset missing. Evidence:
- [ ] **1.117** Dividends and splits: fetched onto a checklist-engine release. Done when: The release holds the cash dividend and the split factor by announcement date and ex-date, checksummed, separate from the adjusted bar. Evidence:
- [ ] **1.118** Dividends and splits: joined point-in-time. Done when: A dividend or split is known on D only when its announcement date is < D. The ex-date is not the known-date when the announcement is later. Evidence:
- [ ] **1.119** Dividends and splits: built at candle sizes 1 through 21. Done when: Days since, days until, and the split factor as a step series exist at candle sizes 1..21. Evidence:
- [ ] **1.120** Dividends and splits: column count and fill rate measured. Done when: WORLD_COVERAGE shows a non-zero fill for I196, or BLOCKED / NOT_AVAILABLE_FREE with the tested URL and the error. WIRED at 0 percent fails CI. Evidence:

### Options

Note (2026-10-26 ~15:33 HKT, do not tick): Keep options, including put/call ratio. Find a free point-in-time source, such as the CBOE archives. If no free history exists, log that series excluded-with-reason. Do not block the rest of Phase 1 on it.

- [ ] **1.121** Options: source located. Items: I201 CBOE market-wide, and I202 single-stock. Done when: Check fullscan and theme-radar. CBOE public market-wide series are the free source for I201. Single-stock history is the known gap: DoltHub IV from 2020 to about October 2024, Monday/Wednesday/Friday, survivors only. CBOE delayed quotes have no history. No paid options vendor. Evidence:
- [ ] **1.122** Options: fetched onto a checklist-engine release. Done when: Any free file that is used is a checksummed release asset. A live quote with no history is not stored as a 2020–26 panel. Evidence:
- [ ] **1.123** Options: joined point-in-time. Done when: An options field joins on its publication timestamp < D. Survivors-only is labelled on I202. Evidence:
- [ ] **1.124** Options: built at candle sizes 1 through 21. Done when: Market-wide series that exist are sampled at candle sizes 1..21. Each single-stock candle-size row states the history gap in writing instead of a zero column. Evidence:
- [ ] **1.125** Options: column count and fill rate measured. Done when: WORLD_COVERAGE has a measured row for I201 and for I202 at each candle size: WIRED with a non-null percent, or NOT_AVAILABLE_FREE with the tested source and the error. No silent PENDING. Evidence:

### Calendar context

- [ ] **1.126** Calendar context: source located. Items: I183, NYSE holidays and the rule-based option expiry. No outside panel.. Done when: Source is the NYSE public hours calendar plus the expiry rule. DATA_SOURCES marks this proven and rule-based. Evidence cites that calendar URL. Evidence:
- [ ] **1.127** Calendar context: fetched onto a checklist-engine release. Done when: Holiday and expiry flags are generated in the world build for every session in the snapshot. Evidence:
- [ ] **1.128** Calendar context: joined point-in-time. Done when: A session is a holiday only when the calendar says so. The flags do not read day-D prices. Evidence:
- [ ] **1.129** Calendar context: built at candle sizes 1 through 21. Done when: The flags are carried onto candle sizes 1..21 with a written note that they are calendar facts, not resampled prices. Evidence:
- [ ] **1.130** Calendar context: column count and fill rate measured. Done when: WORLD_COVERAGE has a row with a non-null percent for the holiday flag and for the expiry flag. Evidence:

### Industry ETF map

Note (2026-10-26 ~14:52 HKT, do not tick): These boxes are the per-stock industry ETF, which is finer than the 11 sector SPDRs in 1.41–1.45. Nothing here is ticked.

Note (2026-10-26 ~15:33 HKT, do not tick): Box 1.131 still needs a free source. Codex proposes one in §0c. Nothing here is ticked.

- [ ] **1.131** Industry ETF map: source located. Done when: A point-in-time map from each stock to its industry ETF is named, with the free source that was checked (fullscan, theme-radar, then a public ETF list). The map is dated, so a later reclassification does not rewrite earlier days. Evidence:
- [ ] **1.132** Industry ETF map: fetched onto a checklist-engine release. Done when: The release holds the industry-ETF daily bars, through the same last date as the stock bars, and the dated stock-to-ETF map, both checksummed. Evidence:
- [ ] **1.133** Industry ETF map: joined point-in-time. Done when: The industry ETF on day D is the map known as of D−1, and the ETF features use bars ending at D−1. An unknown industry is blank, not a fallback to the sector ETF. Evidence:
- [ ] **1.134** Industry ETF map: built at every timeframe in the union. Done when: Industry-ETF features and the stock-versus-industry-ETF facets (relative change, divergence, relative strength) exist at every timeframe in the union of 1d, 5d, 10d, and 20d/monthly with candle sizes 1 through 21. Evidence:
- [ ] **1.135** Industry ETF map: column count and fill rate measured. Done when: WORLD_COVERAGE non-null percent and first date are filled for the map and for the industry-ETF feature columns at every timeframe in that union. A build that only has the 11 SPDRs fails this block. Evidence:

### Market index set on the stock row

Note (2026-10-26 ~14:52 HKT, do not tick): These boxes put SPY, QQQ, IWM, DIA, and VIX features on every stock-day row. DIA is not covered by 1.41–1.45. VIX level stays the FRED series in 1.91–1.95; this block is the index features sitting on the stock row. Nothing here is ticked.

- [ ] **1.136** Market index set on the stock row: source located. Items: SPY, QQQ, IWM, DIA, and VIX. Done when: The free daily source for DIA is named beside the source already used for SPY, QQQ, and IWM. VIX cites the ALFRED VIX series, not a same-day print. Evidence:
- [ ] **1.137** Market index set on the stock row: fetched onto a checklist-engine release. Done when: The release holds DIA through the same last date as the stock bars, checksummed, next to SPY, QQQ, and IWM. Evidence:
- [ ] **1.138** Market index set on the stock row: joined point-in-time. Done when: Each stock-day row carries SPY, QQQ, IWM, DIA, and VIX features from bars and vintages ending at D−1. Evidence:
- [ ] **1.139** Market index set on the stock row: built at every timeframe in the union. Done when: Index features and the stock-versus-index facets (relative change, divergence, relative strength) exist at every timeframe in the union of 1d, 5d, 10d, and 20d/monthly with candle sizes 1 through 21, for SPY, QQQ, IWM, and DIA. Evidence:
- [ ] **1.140** Market index set on the stock row: column count and fill rate measured. Done when: WORLD_COVERAGE non-null percent and first date are filled for DIA and for the on-row index block at every timeframe in that union. A build that omits DIA fails. Evidence:

### VIX term structure

Note (2026-10-26 ~15:33 HKT, do not tick): VIX9D, VIX3M, and VVIX from the CBOE CSV. VIX level stays the FRED series in 1.91–1.95. Nothing here is ticked.

- [x] **1.141** VIX term structure: source located. Items: VIX9D, VIX3M, VVIX. Done when: The free CBOE CSV for each series is named. A same-day print is not the source. Evidence: [CBOE_SOURCE_LOCATIONS_V1.json](CBOE_SOURCE_LOCATIONS_V1.json), [source status](CBOE_NUMERIC_SOURCE_STATUS_V1.json) and [passed CBOE job](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40307220071/job/121519195463). GPT ✓ 2026-10-26 HKT; awaiting James.
- [x] **1.142** VIX term structure: downloaded onto a checklist-engine release. Done when: The release holds VIX9D, VIX3M, and VVIX through the same last date as the stock bars, checksummed. Evidence: [CBOE_DOWNLOAD_ACCEPTANCE_V1.json](CBOE_DOWNLOAD_ACCEPTANCE_V1.json), [checksummed immutable release](https://github.com/SRoyaltyy/checklist-engine/releases/tag/phase1-gap-cboe-v1-40307220071-1) and [passed CBOE job](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40307220071/job/121519195463). GPT ✓ 2026-10-26 HKT; awaiting James.
- [x] **1.143** VIX term structure: point-in-time and leak check. Done when: The value on D is the print whose publication is before the open of D, and the series does not change when day-D prices are withheld. Evidence: `shared_context_1d.parquet` in [shared-context-v2-40636949344-1](https://github.com/SRoyaltyy/checklist-engine/releases/tag/shared-context-v2-40636949344-1). All 9,270 rows have `source_candle_end` before `available_from`, `candle_start` on or before that end, and no weekend `available_from`. The last source day is 2026-10-22, visible on 2026-10-23. Dropping that source day leaves the earlier 9,269 rows identical, including `cboe_vix9d_close`, `cboe_vix3m_close`, `cboe_vvix_close`, and `cboe_vix_close`. Cursor ✓ / James ✓ (runs 40636949344, 40667837889).
- [x] **1.144** VIX term structure: coverage measured. Done when: WORLD_COVERAGE non-null percent and first date are filled for VIX9D, VIX3M, and VVIX. A missing series is excluded-with-reason, not a zero column. Evidence: [WORLD_COVERAGE.csv](WORLD_COVERAGE.csv) namespace `cboe_shared_context`, 66 rows. VIX9D, VIX3M, and VVIX are each 100.0000% of 1,712 sessions on all 22 timeframes, first date 2020-01-02, copied from `SHARED_CONTEXT_COVERAGE.csv` in [shared-context-v2-40636949344-1](https://github.com/SRoyaltyy/checklist-engine/releases/tag/shared-context-v2-40636949344-1). The scope is `shared_market_sessions_not_stock_days`, not stock days. Cursor ✓ / James ✓ (runs 40636949344, 40667837889).
- [x] **1.145** VIX term structure: multi-timeframe features. Done when: Each series, and the term-structure spreads between them, exist at the minimum grid of 1d, 5d, 10d, and 20d/monthly, and at candle sizes 1 through 21 where a bar exists. Evidence: `cboe_vix9d_close`, `cboe_vix3m_close`, and `cboe_vvix_close` are in [shared-context-v2-40636949344-1](https://github.com/SRoyaltyy/checklist-engine/releases/tag/shared-context-v2-40636949344-1) on all 22 timeframes, each 100% of 1,712 sessions in `SHARED_CONTEXT_COVERAGE.csv`. `vix9d_vix_term_ratio` and `vix3m_vix_term_ratio` are in that same release on the same grid, also 100%. The five `vol_*` ratios are in [volatility-term-native-v1-40667837889-1](https://github.com/SRoyaltyy/checklist-engine/releases/tag/volatility-term-native-v1-40667837889-1), 22 files. The denominator is shared market sessions, not stock days. Cursor ✓ / James ✓ (runs 40636949344, 40667837889).

### Extra ETFs

Note (2026-10-26 ~15:33 HKT, do not tick): TLT, HYG, LQD, UUP, GLD, CPER, USO, RSP, VXX, IBIT, and DIA, on the same price path as the stock bars. DIA may reuse the file from 1.136–1.140. Nothing here is ticked.

- [ ] **1.146** Extra ETFs: source located. Items: TLT, HYG, LQD, UUP, GLD, CPER, USO, RSP, VXX, IBIT, DIA. Done when: The free daily source is the same path as the stock bars. Evidence names it. Evidence:
- [ ] **1.147** Extra ETFs: downloaded onto a checklist-engine release. Done when: The release holds each of those ETFs through the same last date as the stock bars, checksummed. DIA is not downloaded a second time when 1.137 already holds it. Evidence:
- [ ] **1.148** Extra ETFs: point-in-time and leak check. Done when: Features use bars ending at D−1. Withholding day-D prices does not change the columns. Evidence:
- [ ] **1.149** Extra ETFs: coverage measured. Done when: WORLD_COVERAGE non-null percent and first date are filled for every ticker in the list. A missing ticker fails. Evidence:
- [ ] **1.150** Extra ETFs: multi-timeframe features. Done when: Each ETF, and the stock-versus-ETF relative change, exists at 1d, 5d, 10d, and 20d/monthly, and at candle sizes 1 through 21. Evidence:

### Extra breadth

Note (2026-10-26 ~15:33 HKT, do not tick): New highs minus new lows, percent above the 20-day average, percent above the 200-day average, and up volume versus down volume. New highs minus new lows already named in 1.37 is the same series, not a second download. Percent above SMA50 stays in 1.36–1.40. Nothing here is ticked.

- [x] **1.151** Extra breadth: source located. Done when: The series are built from the phase-1 universe bars. The note says whether new highs minus new lows is the 1.37 column. Evidence: Same accepted-price-stitch-v2 OHLCV and actual [rebuild40689026569](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40689026569),8,316 names/no new exclusions; [runner proof](BREADTH_ACTIONS_REBUILD_PROOF_V1.json) binds stitch manifest9f97db99…a3f6fe. `pct_above_sma20`, `pct_above_sma200` and up/down volume are in the same public daily file. `new_highs_minus_new_lows` is exactly the1.37 column, not another fetch. [Independent source/readback](BREADTH_RELEASE_READBACK_V1.json). GPT ✓ 2026-10-28 HKT; awaiting James. Source only; world/PIT/native acceptance is separate.
- [x] **1.152** Extra breadth: downloaded onto a checklist-engine release. Done when: The release holds percent above the 20-day average, percent above the 200-day average, and up volume versus down volume, checksummed, beside the 1.37 breadth file. Evidence: Same public [outside-breadth-stitch-v1](https://github.com/SRoyaltyy/checklist-engine/releases/tag/outside-breadth-stitch-v1) daily file / SHA256 `22dfcd51f88d898a7bc156efa9d79677c769d207604f3a68aec065623d65b2c0` as1.37. All three required series and the underlying counts/volumes are present. [Exact actual runner proof](BREADTH_ACTIONS_REBUILD_PROOF_V1.json) from [Actions40689026569](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40689026569) matches the public data hashes; [independent readback](BREADTH_RELEASE_READBACK_V1.json) verifies every daily SMA20/SMA200 and up/down-volume ratio with exact float64 bits, including missing/zero/infinite conventions. GPT ✓ 2026-10-28 HKT; awaiting James. Download only; native/PIT/full-world gates remain open.
- [ ] **1.153** Extra breadth: point-in-time and leak check. Done when: Day D uses the universe and the bars as of D−1. Survivors-only is written on the column. Evidence:
- [ ] **1.154** Extra breadth: coverage measured. Done when: WORLD_COVERAGE non-null percent and first date are filled for the three added series and for new highs minus new lows. Evidence:
- [ ] **1.155** Extra breadth: multi-timeframe features. Done when: Each added series exists at 1d, 5d, 10d, and 20d/monthly, and at candle sizes 1 through 21. Evidence:

### Macro event calendar

Note (2026-10-26 ~15:33 HKT, do not tick): FOMC, CPI, jobs-report days, month-end and turn-of-month, days to opex, day of week, and day of month. Days to opex may reuse the 1.126 expiry flag. NYSE holidays stay in 1.126–1.130. Nothing here is ticked.

- [ ] **1.156** Macro event calendar: source located. Done when: A free calendar is named for FOMC, CPI, and the jobs report. Month-end, turn-of-month, day of week, and day of month are rule-based. Evidence cites the calendar URL. Evidence:
- [ ] **1.157** Macro event calendar: downloaded onto a checklist-engine release. Done when: The flags are generated for every session in the snapshot. A release date that was not public the morning of D is not flagged that day. Evidence:
- [ ] **1.158** Macro event calendar: point-in-time and leak check. Done when: A flag on D uses only announcements known before the open. The flags do not read day-D prices. Evidence:
- [ ] **1.159** Macro event calendar: coverage measured. Done when: WORLD_COVERAGE has a non-null percent for each flag: FOMC, CPI, jobs, month-end, turn-of-month, days to opex, day of week, and day of month. Evidence:
- [ ] **1.160** Macro event calendar: multi-timeframe features. Done when: The flags are carried onto 1d, 5d, 10d, and 20d/monthly, and onto candle sizes 1 through 21, with a written note that they are calendar facts, not resampled prices. Evidence:

### Earnings dates and surprise, 2025–26

Note (2026-10-26 ~15:33 HKT, do not tick): This is the 2025–26 source on top of boxes 1.56–1.60. Nothing here is ticked.

- [ ] **1.161** Earnings dates and surprise, 2025–26: source located. Items: I184 and I185 for 2025–26. Done when: The free source for dates and surprise after 2024-12-31 is named. The 2020–24 tar in 1.56 does not pass this block. Evidence:
- [ ] **1.162** Earnings dates and surprise, 2025–26: downloaded onto a checklist-engine release. Done when: The release holds the 2025–26 calendar and surprise fields, checksummed, through the latest completed session. Evidence:
- [ ] **1.163** Earnings dates and surprise, 2025–26: point-in-time and leak check. Done when: A row joins when its publication time is before the open of D. A report released on the morning of D is excluded. Evidence:
- [ ] **1.164** Earnings dates and surprise, 2025–26: coverage measured. Done when: WORLD_COVERAGE non-null percent and first date for 2025–26 are filled for the date and the surprise. A column that is constantly unknown does not count as a filled surprise. Evidence:
- [ ] **1.165** Earnings dates and surprise, 2025–26: multi-timeframe features. Done when: Days since, days until, and the surprise are evaluated at 1d, 5d, 10d, and 20d/monthly, and at candle sizes 1 through 21. Evidence:

### IPO age

Note (2026-10-26 ~15:33 HKT, do not tick): Days since listing. Nothing here is ticked.

- [ ] **1.166** IPO age: source located. Done when: A free listing-date source is named, checked in fullscan and theme-radar first. Evidence:
- [ ] **1.167** IPO age: downloaded onto a checklist-engine release. Done when: The release holds one listing date per ticker, checksummed. A missing date is blank, not zero. Evidence:
- [ ] **1.168** IPO age: point-in-time and leak check. Done when: Days since listing on D uses a listing date known before the open of D. The column does not read day-D prices. Evidence:
- [ ] **1.169** IPO age: coverage measured. Done when: WORLD_COVERAGE non-null percent and first date are filled for the listing date and for days since listing. Evidence:
- [ ] **1.170** IPO age: multi-timeframe features. Done when: Days since listing is carried onto 1d, 5d, 10d, and 20d/monthly, and onto candle sizes 1 through 21, with a written note that it is an age, not a resampled price. Evidence:

### Gap-review price indicators

Note (2026-10-26 ~15:36 HKT, do not tick): All of these are computed from the daily bars already in hand. No new vendor. Nothing here is ticked.

- [ ] **1.171** Gap-review price indicators: source located. Items: RS rank percentile across the universe; Mansfield RS versus SPY, the sector ETF, and the industry ETF at 20/60/120; NATR; price z-score versus the 20-day and 50-day means; up-day and down-day streak count; historical volatility at 10/20/60/120 and the short/long vol ratio; gap size in ATR units and gap-fill rate; rolling skew, kurtosis, autocorrelation, and Hurst at 20/60; linear-regression R²; correlation and beta at 20/60/120 versus SPY and versus the sector ETF; Chaikin Volatility. Done when: The coverage row names the phase-1 bar file. I070 stays HV(20) only. Evidence:
- [ ] **1.172** Gap-review price indicators: built onto a checklist-engine release. Done when: Each named series is a column on the release, checksummed. No second price download. Evidence:
- [ ] **1.173** Gap-review price indicators: point-in-time and leak check. Done when: Every window ends at D−1. Withholding day-D prices does not change the columns. Evidence:
- [ ] **1.174** Gap-review price indicators: coverage measured. Done when: WORLD_COVERAGE non-null percent and first date are filled for every named series. A missing series fails. Evidence:
- [ ] **1.175** Gap-review price indicators: multi-timeframe features. Done when: Each series exists at 1d, 5d, 10d, and 20d/monthly, and at candle sizes 1 through 21. The lookbacks named above stack with those candle sizes. Evidence:

### Indicator setting grids

- [x] **1.176** Indicator setting grids written into the dictionary. Done when: [dictionary/WORLD_SNAPSHOT_DICTIONARY.csv](dictionary/WORLD_SNAPSHOT_DICTIONARY.csv) gives explicit short, default, and long settings, about three each, for every item whose only rule was "TV default ±50%" (I036–I077 and I088–I096). The same file adds MACD 5/35/5 and 8/17/9, Stochastic 5,3,3 and 21,5,5, Williams %R 7 and 28, ADX 7 and 28, MFI 7 and 28, Bollinger 10/1.5 and 50/2.5, Keltner 1.0 and 2.0, Donchian 10 and 55, and relative volume 5 and 50, beside the current defaults. Settings stack with candle sizes. A row that still says only "±50%" fails. Evidence: [docs/INDICATOR_SETTINGS_REGISTRATION_STATUS.json](https://github.com/SRoyaltyy/checklist-engine/blob/main/docs/INDICATOR_SETTINGS_REGISTRATION_STATUS.json), [merge 3ad57bc](https://github.com/SRoyaltyy/checklist-engine/commit/3ad57bc2d7f99cd35d651888cb6cfa5c0021a1cc) and [green main CI 40291999826](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40291999826). GPT ✓ 2026-10-26 HKT. James ✓ 2026-10-26.

### Canonical candle grid

- [x] **1.177** Canonical candle grid: C01 and the code agree. Done when: C01 and `world_timeframes.py` both state Cyrus's rule. The minimum is 1d, 5d, 10d, and 20d/monthly. Candle sizes 1 through 21 are allowed. Monthly stays a calendar month, not 21 daily bars relabelled. A test fails if the dictionary set and TIMEFRAMES disagree. Evidence: [docs/CANDLE_GRID_STATUS.json](https://github.com/SRoyaltyy/checklist-engine/blob/main/docs/CANDLE_GRID_STATUS.json), [merge 3ad57bc](https://github.com/SRoyaltyy/checklist-engine/commit/3ad57bc2d7f99cd35d651888cb6cfa5c0021a1cc) and [green main CI 40291999826](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40291999826). GPT ✓ 2026-10-26 HKT. James ✓ 2026-10-26.

### Food-for-thought price indicators

Note (2026-10-26 ~16:35 HKT, do not tick): Missing from the dictionary. Computed from the daily bars already in hand. Aroon oscillator stays inside I041. Linear-regression R² stays I217. Correlation to SPY and the sector stays I218. Nothing here is ticked.

- [ ] **1.178** Food-for-thought price indicators: source located. Items: Elder Impulse; Twiggs Money Flow; STARC bands; linear-regression slope, intercept, and standard error at more than one length; stock-versus-stock rolling correlation versus peers; Schaff Trend Cycle. Done when: The coverage row names the phase-1 bar file. No second vendor. Evidence:
- [ ] **1.179** Food-for-thought price indicators: built onto a checklist-engine release. Done when: Each named series is a numeric column with a fixed definition, checksummed. Peer correlation uses the peer set known as of D−1. Evidence:
- [ ] **1.180** Food-for-thought price indicators: point-in-time and leak check. Done when: Every window ends at D−1. Withholding day-D prices does not change the columns. Evidence:
- [ ] **1.181** Food-for-thought price indicators: coverage measured. Done when: WORLD_COVERAGE non-null percent and first date are filled for every named series. A missing series fails. Evidence:
- [ ] **1.182** Food-for-thought price indicators: multi-timeframe features. Done when: Each series exists at 1d, 5d, 10d, and 20d/monthly, and at candle sizes 1 through 21. The lengths stack with those candle sizes. Evidence:

### FRED series named 2026-10-26 16:35

Note (2026-10-26 ~16:35 HKT, do not tick): These are not on I195. T10Y2Y and BAMLH0A0HYM2 stay on I195. Vintage rule is the same as box 1.93. Nothing here is ticked.

- [x] **1.183** FRED series named 2026-10-26 16:35: source located. Items: T10Y3M, T5YIE, T10YIE, STICKCPIM159S, DFII10, CIVPART, INDPRO, BUSLOANS. Done when: Each series is named on the FRED API, using the phase-0 secret. ALFRED vintage dates are the point-in-time values. Evidence: [FRED_1635_SERIES.json](../dictionary/FRED_1635_SERIES.json), [FRED_1635_SOURCE_STATUS_V2.json](FRED_1635_SOURCE_STATUS_V2.json) and [passed FRED job](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40307954973/job/121521661708). Requested sticky-CPI shorthand maps explicitly to official STICKCPIM159SFRBATL; no revised-today substitute. GPT ✓ 2026-10-26 HKT; awaiting James.
- [x] **1.184** FRED series named 2026-10-26 16:35: downloaded onto a checklist-engine release. Done when: The release holds each series as vintage rows (observation date, realtime start, value), checksummed. The log does not contain the API key. Evidence: [FRED_1635_DOWNLOAD_ACCEPTANCE_V1.json](FRED_1635_DOWNLOAD_ACCEPTANCE_V1.json), [checksummed release](https://github.com/SRoyaltyy/checklist-engine/releases/tag/phase1-gap-fred-v2-40307954973-1) and [passed FRED job](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40307954973/job/121521661708). All eight sources are vintage rows, including the explicit sticky-CPI identifier correction. GPT ✓ 2026-10-26 HKT; awaiting James.
- [ ] **1.185** FRED series named 2026-10-26 16:35: point-in-time and leak check. Done when: The value on D is the vintage whose realtime period contains the morning of D and whose observation date is < D. A revised-today value fails. Evidence:
- [ ] **1.186** FRED series named 2026-10-26 16:35: coverage measured. Done when: WORLD_COVERAGE non-null percent and first date are filled for every series. A series the fetch did not return is not left as a silent zero. Evidence:
- [x] **1.187** FRED series named 2026-10-26 16:35: multi-timeframe features. Done when: Each series is sampled at 1d, 5d, 10d, and 20d/monthly, and at candle sizes 1 through 21, with a written note where the source itself is monthly. Evidence: [FRED_NATIVE_TIMEFRAME_ACCEPTANCE_V1.json](FRED_NATIVE_TIMEFRAME_ACCEPTANCE_V1.json), [native context status](SHARED_CONTEXT_NATIVE_STATUS_V1.json), [checksummed release](https://github.com/SRoyaltyy/checklist-engine/releases/tag/shared-context-v1-40363757188-1), and [passed build 40363757188](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40363757188). All eight named series have nonempty native levels at all 22 timeframes (176 cells); monthly source facts remain sampled last-known vintage levels, never interpolated. This claims multi-timeframe construction, not full stock-day/world coverage. GPT ✓ 2026-10-27 HKT; awaiting James.

### Breadth from our universe, added 2026-10-26 16:35

Note (2026-10-26 ~16:35 HKT, do not tick): The advance/decline line, the advance/decline ratio, net new 52-week highs, and percent above the 20, 50, and 200-day averages are already I179, I180, and boxes 1.36–1.40 and 1.151–1.155. Nothing here is ticked.

- [ ] **1.188** Breadth from our universe, added 2026-10-26 16:35: source located. Items: advance/decline volume line, McClellan oscillator, McClellan summation, TRIN, Bullish Percent (point and figure). Done when: Each series is defined from the phase-1 universe bars, not from a paid breadth feed. Evidence:
- [ ] **1.189** Breadth from our universe, added 2026-10-26 16:35: built onto a checklist-engine release. Done when: The release holds those five series, checksummed, with a fixed numeric definition for each. Evidence:
- [ ] **1.190** Breadth from our universe, added 2026-10-26 16:35: point-in-time and leak check. Done when: Day D uses the universe and the bars as of D−1. Survivors-only is written on the column. Evidence:
- [ ] **1.191** Breadth from our universe, added 2026-10-26 16:35: coverage measured. Done when: WORLD_COVERAGE non-null percent and first date are filled for each of the five series. Evidence:
- [ ] **1.192** Breadth from our universe, added 2026-10-26 16:35: multi-timeframe features. Done when: Each series exists at 1d, 5d, 10d, and 20d/monthly, and at candle sizes 1 through 21. Evidence:

### XBRL ratios named 2026-10-26 16:35

Note (2026-10-26 ~16:35 HKT, do not tick): EV/EBITDA, P/S, margins, ROIC, and the FCF level stay on I192. Piotroski F and Beneish M stay on I194. Nothing here is ticked.

- [ ] **1.193** XBRL ratios named 2026-10-26 16:35: source located. Items: EV/CFO, P/FCF, shareholder yield, accruals, earnings variability, direction of margin change, sales per share, cash EPS, BVPS, payout ratio, internal growth g. Done when: Each ratio names the companyfacts tags it uses. Filing date is the known-date. Evidence:
- [ ] **1.194** XBRL ratios named 2026-10-26 16:35: downloaded onto a checklist-engine release. Done when: The release holds each ratio as a numeric column, checksummed, built from the companyfacts already fetched. No second vendor. Evidence:
- [ ] **1.195** XBRL ratios named 2026-10-26 16:35: point-in-time and leak check. Done when: The value on D uses the latest filing whose filed or acceptance time is before the open of D. Substituting the period end changes the column and fails. Evidence:
- [ ] **1.196** XBRL ratios named 2026-10-26 16:35: coverage measured. Done when: WORLD_COVERAGE non-null percent and first date are filled for every ratio. A missing tag is blank, not zero. Evidence:
- [ ] **1.197** XBRL ratios named 2026-10-26 16:35: multi-timeframe features. Done when: Each ratio, and the direction-of-change where the item is a trend, is carried onto 1d, 5d, 10d, and 20d/monthly, and onto candle sizes 1 through 21, with a written note that these are filing facts sampled onto the grid, not resampled prices. Evidence:

### Put/call open interest

- [ ] **1.198** Put/call open interest: free history or a logged exclusion. Done when: A free CBOE open-interest history is a checksummed release asset and joins on its publication time before the open of D, or the series is on the exclusion list with the reason and is not a zero column. Put/call volume stays I201. This box does not block the rest of Phase 1. Evidence:

### Live-only skips from the 16:35 list

- [x] **1.199** Live-only skips from the 16:35 list are logged. Items: max pain; max-OI strikes; unusual-activity flag; implied correlation. Done when: Each of those names is on the exclusion list, or on WORLD_COVERAGE as EXCLUDED_LIVE_ONLY, with the reason, unless box 1.201 moves it onto a real history. They are not fetched from a paid vendor. NYSE TICK is box 1.200. Finviz Elite was checked on 2026-10-26 16:55 and is today's snapshot only, so it cannot backfill 2020+. Single-stock ATM implied vol, IV rank and percentile, 25-delta skew and risk reversal, and historical volatility minus implied volatility stay off the fetch list until the DoltHub log in box 1.201 says the coverage is good. Do not log those as a final exclusion before that log. Evidence: [WORLD_COVERAGE.csv](WORLD_COVERAGE.csv) namespace series / LIVE_ONLY_*; [status](LIVE_ONLY_EXCLUSIONS_STATUS_V1.json), [self-verification receipt](LIVE_ONLY_EXCLUSIONS_PROOF_V1.json), and [passed retained-skips job](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40307220071/job/121519195044). GPT ✓ 2026-10-26 HKT; awaiting James. Four retained series / 88 explicit exclusion rows; reopened TICK and IV-related series are not final exclusions.

### NYSE TICK

Note (2026-10-26 ~16:50 HKT, do not tick): Reopened. Intraday is an acceptable source when it can be fetched for every day from 2020 through the present. Nothing here is ticked.

- [x] **1.200** NYSE TICK: free daily-complete history, or a log of what was tried. Done when: A free source covers every day from 2020 through the present, either as the daily close, high, and low of $TICK or computed from intraday that exists for every one of those days. The release holds numeric daily features: close, high, low, and a count of extreme readings, checksummed, and point-in-time as of D−1. If no free complete source exists, the exclusion list states exactly what was tried, and the column is absent rather than zero. Evidence: [Tested-source exclusion](NYSE_TICK_SOURCE_EXCLUSION_V1.json), [verified-identity follow-up](NYSE_TICK_SOURCE_FOLLOWUP_V4.json), [22 explicit coverage rows](WORLD_COVERAGE.csv) and [publication run40335732061](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40335732061). GPT ✓ 2026-10-26 HKT; awaiting James. Eleven logged attempts; Investing id961122 confirmed then API403, Yahoo404, Stooq verification, other providers lack free complete numeric history. No zero columns or intraday-count invention.

### DoltHub options history

Note (2026-10-26 ~16:55 HKT, do not tick): Finviz Elite is today's snapshot only and cannot backfill 2020+. This box is the coverage log. Feature boxes for ATM IV, IV rank, and the chain-derived fields are added only after the log says coverage is good. Nothing here is ticked.

- [ ] **1.201** DoltHub options history: coverage log. Done when: The free dataset `post-no-preference/options` is measured for `volatility_history` (per-ticker IV and HV) and `option_chain`, point-in-time, from 2020 through the present, across our universe. The log on main states the coverage percent, the date range, and what was skipped. If coverage is good, the same commit adds unticked boxes for ATM IV, IV rank and percentile, and HV minus IV, and, where the chain table allows, skew and risk reversal, max pain, and the max-OI strike. Put/call open interest uses box 1.198 rather than a second box. If coverage is not good, the log says so and those names stay off the fetch list. Evidence:

### Comparisons outside the stock — 2026-10-27 11:30 HKT

Priority remains recovery and missing Phase 1 blocks first. These are explicit
open obligations, not claims. Comparator scope: PIT correlated/peer stocks,
sector/industry ETFs, SPY/QQQ/IWM/RSP (and the previously required DIA), VIX and
its term structure, and the registered cross-asset ETFs. Every family uses all
22 candle zooms. VIX level/change and term structure remain in 1.91–1.95 and
1.141–1.145; RSP source/price history is already in 1.146–1.150. None is duplicated.

- [ ] **1.202** Point-in-time correlation peer sets. Done when: Fixed registered trailing windows, top-N and refresh settings produce versioned dated peer sets using only prices and historical eligible membership known before D. Exclude self; no future returns, current-map backfill or survivors-only peer universe. A future-cut rebuild preserves the peer sets, and measured coverage includes every eligible stock/date. Evidence:
- [ ] **1.203** Relative strength against every registered comparator. Done when: Ratio/log-ratio and native-window return spread are numeric released columns with explicit formulas, price basis, windows and parameter grids for peer stocks, sector/industry ETFs, market indices and cross-asset comparators at every zoom. Exact matching candle intervals and pre-D source availability are verified; full WORLD_COVERAGE names every comparator/family. Evidence:
- [ ] **1.204** Cross-entity divergence inputs. Done when: Released numeric/fixed-outcome features express stock-flat/comparator-falling and the opposite, including registered return thresholds/windows and confirmed-pivot divergence where specified, for every comparator and candle zoom. Future cuts preserve outputs. The stock-holds/industry-ETF-falls/VIX-falls example is expressible without reading text. Evidence:
- [ ] **1.205** Beta and correlation breaks versus own history. Done when: Rolling beta/correlation against each comparator, and their deviation/break relative to explicitly registered earlier-history baselines, are released at every zoom. Windows, thresholds, minimum observations and zero-variance handling are fixed before evaluation; blanks remain unavailable; full coverage and future-cut evidence exist. Evidence:
- [ ] **1.206** Spread z-scores. Done when: Each registered stock/comparator spread has a released historical z-score at every zoom, with fixed spread definition, normalization window, ddof and threshold grid. Zero variance and insufficient history stay blank. Exact pre-D lineage, full comparator coverage and future-cut proof exist. Evidence:

## Phase 2 — Coverage gate

P1. CI fails a missing row and fails a WIRED row at 0 percent filled.

Note (2026-10-26 ~14:52 HKT, do not tick): The coverage gate fails if any stock-day row lacks a context block: industry ETF, sector ETF, market indices (SPY, QQQ, IWM, DIA, VIX), breadth, or macro. Box 2.10 is that check. Nothing here is ticked.

- [ ] **2.01** Publish docs/WORLD_COVERAGE.csv on main, measured from the full-universe shards. Done when: The file is in git. Columns include item_id, name and setting, block, snapshot column(s), non-null percent over 2020–2026, first date available, and status. It is computed from the released shards. The six-stock file inside release world-smoke-v2-40209615520-1 (11,638 item by timeframe rows, 8,269 PENDING) does not pass. Evidence:
- [ ] **2.02** One measured row for every TradingView master item. Done when: M001–M296 each appear once per candle size 1..21, or once with a written reason that a candle grid does not apply. docs/TV_COVERAGE.csv today is 296 items: 207 WIRED, 78 EXCLUDED_FREE_TEXT, 11 NOT_AVAILABLE_FREE, and it has no non-null percent. That file does not pass this box. Evidence:
- [ ] **2.03** One measured row for every dictionary item. Done when: C01–C30 and I001–I203 each have a row. I203, the checklist score path, is the engine's own output and is excluded with that reason. Evidence:
- [ ] **2.04** CI fails when an item has no row. Done when: A workflow on main exits non-zero if any master id or dictionary id is missing from docs/WORLD_COVERAGE.csv. The failing fixture is in the test log. Evidence:
- [ ] **2.05** CI fails a WIRED row at 0 percent filled. Done when: A WIRED row whose non-null percent is 0 fails the build. I196 (dividends and splits) is the regression case: it was marked WIRED at 0 percent fill. The test fixture includes that case. Evidence:
- [ ] **2.06** No silent PENDING left. Done when: Status is only WIRED, BLOCKED_SECRET, NOT_AVAILABLE_FREE, EXCLUDED_FREE_TEXT, or EXCLUDED_LIVE_ONLY. The PENDING count is 0. Every NOT_AVAILABLE_FREE row names the tested source and the error. Every exclusion has a written reason. Evidence:
- [ ] **2.07** Fix exclusion reasons that do not match the data. Done when: M046, M145, M148, M169, M199, M221, M223, M273, M280, and M281 stay out only if an intraday blocker is still true after the source check. M290 (Altman Z / Piotroski / Beneish) drops the intraday reason and matches the I194 companyfacts row. M001 (1 year active supply %, crypto), M082 (Learn using seasonals), and M154 (Seasonality) are not free text: drop EXCLUDED_FREE_TEXT on those three. Crypto with no US-stock series is NOT_AVAILABLE_FREE or another written non-text reason. Seasonality is a calendar feature. docs/TV_COVERAGE.csv and docs/WORLD_COVERAGE.csv agree on these ids. Evidence:
- [ ] **2.08** Survivors-only is labelled, and the size filter is counted. Done when: Universe, breadth, sector labels, and the single-stock options rows say survivors-only. The summary states how many names the untradeable filter and the <$100M filter remove as of D, and that an unknown market cap is excluded. Evidence:
- [ ] **2.09** Status totals match the CSV. Done when: A summary committed next to the CSV gives counts by status and by block, and those counts equal a fresh group-by of the CSV. The §0c line quotes the same counts. Evidence:
- [ ] **2.10** Context blocks are present on every stock row. Done when: CI fails when any stock-day row is missing its industry-ETF block, its sector-ETF block, its market-index block (SPY, QQQ, IWM, DIA, and VIX), its breadth block, or its macro block. The failing fixture names the missing block. A stock-only row fails. Evidence:

## Phase 3 — Question tree v3 and the P3b quality gate

2026-10-27 direction: emphasize comparisons outside the stock. The generated
tree and coverage tables must explicitly include 1.202–1.206 plus VIX
level/change/term-structure context. Cross-entity combinations must express
stock holds while its industry ETF falls and VIX falls. Phase 1 recovery and
data completion precede this feature/question expansion; no box is ticked here.

P3 and P3b. The target is at least about 26,000 base questions per stock-day. James ticks the hand check.

Note (2026-10-26 ~14:52 HKT, do not tick): The question tree includes cross-entity facets — stock versus its industry ETF, stock versus its sector ETF, and stock versus each market index (relative change, divergence, and relative strength, at every timeframe) — and market-regime facets (VIX level, direction, and extreme, and breadth). Canonical picture (Cyrus 14:53 HKT): industry ETF has had an extreme fall while the stock itself stays steady (stock-vs-ETF divergence), AND VIX is falling (market getting more optimistic) → buy opportunity? It also includes cross-timeframe disagreement facets (timeframe divergence) on the same entity, so a 1d question and a 5d question on that entity can be asked together. Second picture (Cyrus 14:54 HKT): on the 1-day chart the stock isn't that positive, but zoom out to the 5-day chart and a pattern appears. Example the tree must be able to state: 1d question = neutral or negative AND 5d question = pattern present. Nothing is ticked.

- [ ] **3.01** Write the v3 spec. Done when: docs/QUESTION_TREE_v3.md is on main. It states the 4-lever combinator (data type, candle size, derivative, facet) plus the history lever, the variable ranges, and the point-in-time rule for every question. Evidence:
- [ ] **3.02** Generate the question CSV. Done when: docs/QUESTION_TREE_v3.csv is on main, one row per question, with item id, facet, candle size, lookback, threshold or setting, direction, exact formula, inputs, window, timeframe, and the point-in-time date rule. QUESTION_TREE_v2.7 (14,643 questions, 17 price/volume families) is not this file. Evidence:
- [ ] **3.03** Facet coverage table. Done when: A CSV on main has one row per world item and one column per facet. The cell is the question count. A 0 cell has a written reason in a paired column. Evidence:
- [ ] **3.04** Core facet on every item: absolute value. Done when: Every world item, about 296 including every non-price block, has at least one question whose meaning is level versus a threshold, or the coverage cell is 0 with a written reason. CI fails an empty reason. Evidence:
- [ ] **3.05** Core facet on every item: relative to own history. Done when: Every world item, about 296 including every non-price block, has at least one question whose meaning is percentile or z-score versus the item's own past, or the coverage cell is 0 with a written reason. CI fails an empty reason. Evidence:
- [ ] **3.06** Core facet on every item: relative to peers, sector, or market. Done when: Every world item, about 296 including every non-price block, has at least one question whose meaning is the same item versus peers, sector, and the market, or the coverage cell is 0 with a written reason. CI fails an empty reason. Evidence:
- [ ] **3.07** Core facet on every item: position in a range or band. Done when: Every world item, about 296 including every non-price block, has at least one question whose meaning is inside a band or range, and distance to high, low, or average, or the coverage cell is 0 with a written reason. CI fails an empty reason. Evidence:
- [ ] **3.08** Core facet on every item: direction and change. Done when: Every world item, about 296 including every non-price block, has at least one question whose meaning is rising or falling, slope, and acceleration over N, or the coverage cell is 0 with a written reason. CI fails an empty reason. Evidence:
- [ ] **3.09** Core facet on every item: crossing or event. Done when: Every world item, about 296 including every non-price block, has at least one question whose meaning is crossed a level or another line within N bars, or the coverage cell is 0 with a written reason. CI fails an empty reason. Evidence:
- [ ] **3.10** Core facet on every item: extremes. Done when: Every world item, about 296 including every non-price block, has at least one question whose meaning is a new N-high, a new N-low, or a record, or the coverage cell is 0 with a written reason. CI fails an empty reason. Evidence:
- [ ] **3.11** Core facet on every item: divergence. Done when: Every world item, about 296 including every non-price block, has at least one question whose meaning is versus price, or versus another item, or the coverage cell is 0 with a written reason. CI fails an empty reason. Evidence:
- [ ] **3.12** Core facet on every item: persistence or count. Done when: Every world item, about 296 including every non-price block, has at least one question whose meaning is how many of the last N bars met a condition, or the coverage cell is 0 with a written reason. CI fails an empty reason. Evidence:
- [ ] **3.13** Core facet on every item: state change. Done when: Every world item, about 296 including every non-price block, has at least one question whose meaning is a flip from one state to another, or the coverage cell is 0 with a written reason. CI fails an empty reason. Evidence:
- [ ] **3.14** Type-specific candle facets. Done when: Candle items have questions for gaps, for 1-day patterns, and for 3-day patterns, or a written reason on the coverage row. Evidence:
- [ ] **3.15** Type-specific event facets. Done when: Earnings, Form 4, 13F, analyst, halts, Reg SHO, and dividend items have days since, days until, count inside the window, and the direction of the last event (upgrade versus downgrade, insider buy versus sell), or a written reason. Evidence:
- [ ] **3.16** Candle-size grid on every filled (item, facet) cell. Done when: Each non-zero cell contains questions for every integer candle size from 1 through 21. Published totals include a count by candle size. Evidence:
- [ ] **3.17** At least three lookback windows on every filled cell. Done when: The CSV shows at least three distinct lookbacks on every non-zero (item, facet) cell. Each lookback has a range and a default. Evidence:
- [ ] **3.18** At least three thresholds or settings per derivative. Done when: SMA lengths, RSI and MACD lengths, RVOL windows, change over N, rank, and z-score each vary across at least three settings. Range and default are columns on the question row. Evidence:
- [ ] **3.19** Both directions. Done when: Above and below, rising and falling, buy and sell, and upgrade and downgrade are both present where the facet has a direction. Where an item has no opposite, the coverage note says so. Evidence:
- [ ] **3.20** History lever. Done when: Same-state past behaviour for this stock is a question family on every item, and the formula states how the state is defined. The facet totals include this family. Evidence:
- [ ] **3.21** Formula integrity. Done when: CI fails a blank formula, a duplicate formula, or a formula that omits inputs, window, threshold, timeframe, or the point-in-time date rule. Evidence:
- [ ] **3.22** Answer-variability sample. Done when: CI fails a question that is always yes, always no, or more than 99 percent blank on a sample of 200 stocks over 2020–2022. The list of 200 tickers is stored next to docs/QUESTION_QUALITY.csv. Evidence:
- [ ] **3.23** Non-price depth versus price and volume. Done when: CI fails when any data block's median questions per item is below 50 percent of the price/volume median. Those medians are in the quality file. Evidence:
- [ ] **3.24** Totals by data kind, facet, and timeframe. Done when: A published table gives question counts for those three keys. The base-question total is at least about 26,000 per stock-day. Evidence:
- [ ] **3.25** docs/QUESTION_QUALITY.csv shows 0 FAIL. Done when: Per item the file has facets covered over facets total, question count, median non-blank percent, percent constant, depth ratio versus the price median, and PASS or FAIL. The totals row has 0 FAIL. The file is on main before any Step A rerun. Evidence:
- [ ] **3.26** JAMES TICKS THIS. Hand spot-check of 20 random items. Done when: James writes the 20 item ids and a pass or fail for each in Evidence. Codex and Kimi leave this box empty. Evidence:
- [ ] **3.27** Cross-timeframe questions. Done when: The v3 tree has questions that compare timeframes on the same entity, including 1d versus 5d, plus timeframe-divergence facets. A row can state a 1d question and a 5d question together. Evidence:
- [ ] **3.28** Settings count per indicator. Done when: A table on main lists every indicator and how many settings it has. An item whose only rule is still "TV default ±50%" fails. The alternates named in box 1.176 are present. Evidence:

## Phase 4 — Full leak test

P4. Every column, every candle size, and every v3 question. Windows end at D−1.

- [ ] **4.01** Leak test covers every snapshot column and every candle size. Done when: The leak report lists every column of the full-universe shards, including item__tf for candle sizes 1..21. The six-stock PASS on run 40209615520 (1,144,110 comparisons, 10,186 feature columns, 0 mismatches) does not pass this box. Evidence:
- [ ] **4.02** Windows end at D−1. Done when: The report states that every bar and every rolling window ends at D−1. A column that reads day D's high, low, close, or volume fails the run. Evidence:
- [ ] **4.03** Day-D open is the buy price only. Done when: No question column changes when day-D open is withheld. The report names the buy-price column. Evidence:
- [ ] **4.04** Filings join on filed or acceptance date. Done when: Form 4, 13F, analyst actions, earnings, and XBRL join on filed, acceptance, or publication date < D. A test that substitutes the period end changes the column and fails the build. Evidence:
- [ ] **4.05** FRED uses ALFRED vintages. Done when: The leak rebuild of the macro columns from vintages has zero mismatches. A column built from today's revised FRED value fails. Evidence:
- [ ] **4.06** Adjusted prices and raw prices are separated. Done when: Ratios, returns, and indicators use split-adjusted prices. A price level, market cap, and the $100M cutoff use the raw D−1 close and the shares outstanding known that day. The report names which columns are which. Evidence:
- [ ] **4.07** Zero mismatches. Done when: The published leak JSON has 0 mismatches. The comparison count and the column count are both in the file. Evidence:
- [ ] **4.08** The v3 question tree is inside the leak test. Done when: Every question column the v3 tree emits is in the leak column list. A leak test of the world snapshot alone does not pass. Evidence:
- [ ] **4.09** ARQT cut_errors are closed. Done when: The Step A leak errors on ARQT for weekly_trend and change_of_state are gone. The new log shows those two names with zero errors, or the questions are removed and the v3 coverage table gives the reason. Evidence:
- [ ] **4.10** Ratio rule stays as pinned. Done when: A zero denominator with a positive numerator is infinite and passes a >= or > test. Both zero is blank. Built tags stay _inf. The Taskforce blank-on-zero variant stays _blank. A unit test covers both. Evidence:

## Phase 5 — Step A full rerun

Only after every box in phases 0 through 4 is verified by both signatures. Step A output from before that gate does not count.

- [ ] **5.01** Gate: start only after every box in phases 0, 1, 2, 3, and 4 is verified by both signatures. Done when: Every box in those phases has `GPT ✓` and `James ✓`, and docs/QUESTION_QUALITY.csv shows 0 FAIL. Tick this box only when that is true. Run 40180498392 and any Step A attempt before the gate stay provisional. Evidence:
- [ ] **5.02** The empty-mask crash cannot recur. Done when: A regression test on main reproduces IndexError 'index 0 is out of bounds for axis 0 with size 0' from run 40180498392 and passes. Evidence:
- [ ] **5.03** Rerun Step A on every chunk, including groups 034 and up. Done when: The matrix lists grid_000 through grid_033 and the new groups. Groups 034 and up include the 1,024 questions that were written and not built (vs_sector_peers 374, vs_theme_peers 374, earnings 56, form4 60, analyst 56, halts 56, short_interest 48) plus the rest of v3. Evidence:
- [ ] **5.04** Answer columns match the v3 tree. Done when: The Step A column count equals the v3 question count. That is at least about 26,000 base questions, plus the history questions. The old 12,306 answer columns do not pass. Evidence:
- [ ] **5.05** Outputs are on a versioned release. Done when: The release names the question-tree version, the world-shard version, the row count, and the checksum of each chunk. A partial-data chunk is not in this release. Evidence:
- [ ] **5.06** The run is green on ubuntu-latest. Done when: The Actions run is green, the runner label is ubuntu-latest, and no chunk was cancelled. The run URL is the Evidence. Evidence:

## Phase 6 — Exit grid

Only after every Phase 5 box is verified by both signatures.

Note (2026-10-26 ~12:02 HKT, do not tick): Hold period is a search variable, every length from 1 trading day through about 21 (about 1 month), not a fixed exit. This grid must span it. In a word (Cyrus 12:03 HKT): as long as a method is expected to win, we mine it and use it. Acceptance is positive expected profit after fees that holds out of sample (2023–24 and 2025–26), not any particular win rate or combo shape.

- [ ] **6.01** Gate: start only after every Phase 5 box is verified by both signatures. Done when: Every Phase 5 box has `GPT ✓` and `James ✓`. Older exit-grid tables, including release grid-2020-22-v1, stay provisional and are not reused as this phase's output. Evidence:
- [ ] **6.02** Rebuild the 26,100-rule exit grid. Done when: Take-profit 2–30 percent, hold 1–30 sessions, stop 2–30 percent or none. That is 29 by 30 by 30 = 26,100 sell rules. The release states that count. Evidence:
- [ ] **6.03** Fees and the same-day baseline are in the result. Done when: Each rule's profit is after 30bp each way, and the same-day market return is stored beside it. Evidence:
- [ ] **6.04** Dynamic target and stop exits are included. Done when: The dynamic target and stop exits named in the 2026-10-25 23:03 owner clarification are their own rows, separate from the fixed 26,100. Evidence:
- [ ] **6.05** Every chunk is on the release. Done when: Each chunk file has a checksum. A missing chunk fails the job rather than publishing a short grid. Evidence:

## Phase 7 — Shortlist, sharded

Only after every Phase 6 box is verified by both signatures. Until the gate, the shortlist stays paused.

Note (2026-10-26 ~12:02 HKT, do not tick): Probability is any (combination × hold) that reliably produces wins, judged by win rate or by win margin (expected profit after fees: win% × average win − loss% × average loss), with the existing minimum-win-rate floor and the 2023–24 and 2025–26 checks. In a word (Cyrus 12:03 HKT): as long as a method is expected to win, we mine it and use it. Acceptance is positive expected profit after fees that holds out of sample, not any particular win rate.

- [ ] **7.01** Gate: start only after every Phase 6 box is verified by both signatures. Done when: The shortlist stays paused until then. Do not re-dispatch run 40175232753. Run 40156872713 (KeyError 2020) and run 40172094280 (cancelled mid-run) are not Evidence. Evidence:
- [ ] **7.02** KeyError 2020 is covered by a unit test. Done when: A test on main loads grid_001, grid_008, and grid_010 and does not raise KeyError 2020 from scoring/shortlist.py. The year key works whether the year is an int or a string. Evidence:
- [ ] **7.03** One job per chunk, then a small merge. Done when: The workflow is a matrix on ubuntu-latest. Each job streams with bounded memory. The merge job reads only the shard outputs. Evidence:
- [ ] **7.04** Each shard publishes a partial output. Done when: The release contains one partial file per chunk, written before the merge, so a failed merge does not drop finished chunks. Evidence:
- [ ] **7.05** Merge report with the win-rate floors. Done when: The merged table is on the release with the kept-candidate count, the junk-cut count, and the trade count. Floors 35, 40, 45, and 50 are all reported. The default floor is 40. Evidence:
- [ ] **7.06** Score against the same-day market. Done when: Expected profit after fees is compared with the same-day market on the same names. Both numbers are columns. Evidence:
- [ ] **7.07** A running shortlist is left alone by queue cleanups. Done when: Once this phase has started, a queue cleanup does not cancel shortlist jobs. The run log shows no cleanup cancellation. Evidence:

## Phase 8 — Combine (Amendment A1)

Only after every Phase 7 box is verified by both signatures. The 34 groups are a compute split. Score each setup together with its exit rule.

Note (2026-10-26 ~12:02 HKT, do not tick): A combination is any set of questions or setups, of any data type, any timeframe, and any count. No cap on size, and no within-group restriction. This search must allow cross-type mixes of arbitrary size, limited only by sample size and multiple-testing controls. In a word (Cyrus 12:03 HKT): as long as a method is expected to win, we mine it and use it. Acceptance is positive expected profit after fees that holds out of sample, not any particular combo shape.

Note (2026-10-26 ~14:54 HKT, do not tick): Phase 8 must be able to search the multi-source combination from 14:53 (stock-versus-industry-ETF divergence AND VIX falling) and cross-timeframe combinations on the same entity. Example (Cyrus 14:54 HKT): a 1d question that is neutral or negative AND a 5d question that says the pattern is present. Timeframe divergence is a searchable facet. Nothing is ticked.

- [ ] **8.01** Gate: start only after every Phase 7 box is verified by both signatures. Done when: Combiner fits stay paused until then. An additive sum of single-question scores does not pass any later box in this phase. Evidence:
- [ ] **8.02** The search crosses groups and blocks. Done when: The published condition sets mix questions from more than one of the 34 chunks and from more than one data block. The chunks are described as a compute split. Evidence:
- [ ] **8.03** Pair search coverage. Done when: The release states how many pair candidates were searched, how many were excluded, and what pair space remains. Evidence:
- [ ] **8.04** Triple search coverage. Done when: The release states the same three numbers for triples. Evidence:
- [ ] **8.05** Higher orders, including orders that were not searched. Done when: The report lists the interaction orders that were searched and the orders that were not. An unsearched order is not called complete. Evidence:
- [ ] **8.06** Amendment A1: the setup is scored with its exit rule. Done when: Each reported row is one condition set plus one (take-profit, maximum hold, stop). A setup score with no exit rule does not pass. Evidence:
- [ ] **8.07** A minimum trade count is the cut. Done when: The report states the minimum trade count. A question is not dropped only because its frequency is under 0.5 percent when the trade count meets the minimum. If the 400k sample cap is still used, the report says so. Evidence:
- [ ] **8.08** Each row can be recomputed. Done when: The output includes the question-and-answer condition set and the exit-rule tuple. Evidence:

## Phase 9 — 2023–24 check

Only after every Phase 8 box is verified by both signatures. The selection window is 2020–22.

- [ ] **9.01** Gate: start only after every Phase 8 box is verified by both signatures. Done when: Confirmation uses the setups chosen on 2020–22. This phase does not search new cutoffs. Evidence:
- [ ] **9.02** 2023–24 confirm, with no refit. Done when: The same setups and the same exit rules are scored on 2023–24. Cutoffs are not retuned. The run URL is the Evidence. Evidence:
- [ ] **9.03** The counting rule. Done when: A setup is kept only when expected profit after fees is above 0 and the win rate is at least 40 percent. The table also shows floors 35, 45, and 50. Evidence:
- [ ] **9.04** State whether 2023–24 touched selection. Done when: The write-up names the selection period and the evaluation period. If 2023–24 informed selection or tuning, the score is labelled as not an untouched check. Evidence:

## Phase 10 — 2025–26 check

Only after every Phase 9 box is verified by both signatures. The 2026-10-25 23:03 clarification allows 2025–26 in testing. Call a score untouched only when those years did not inform selection.

- [ ] **10.01** Gate: start only after every Phase 9 box is verified by both signatures. Done when: This is the recorded 2025–26 check of the setups that survived phase 9. Evidence:
- [ ] **10.02** The check reads the rebuilt 2025–26 snapshot. Done when: Inputs are the phase-1 bar file through 2026, not the separate six-pilot pull. Day-D inputs still exclude anything not knowable before the open. The seal lift of 2026-10-25 allows these years in testing. It does not allow a future bar. Evidence:
- [ ] **10.03** A report released on the morning of D stays out. Done when: Earnings and filings whose report date or filed date is D are excluded. A calendar fact dated D that was published before the open may be used, and the column's point-in-time rule says so. Evidence:
- [ ] **10.04** Label the period. Done when: The write-up says whether 2025–26 was used to choose or tune anything. If it was, the score is not called an untouched out-of-sample check. Evidence:
- [ ] **10.05** Finviz block P is absent. Done when: No column traced to I198 appears in the 2025–26 result file. Evidence:

## Phase 11 — Publish probabilities

Only after every Phase 10 box is verified by both signatures.

- [ ] **11.01** Gate: start only after every Phase 10 box is verified by both signatures. Done when: The probability table is built only from the setups that survived phase 10. Evidence:
- [ ] **11.02** One probability row per setup and exit rule. Done when: For every kept setup and every (take-profit, maximum hold, stop) the file has the probability that net profit is above 0, average win, average loss, expected net profit after fees, sample count, a significance statistic, and the same-day benchmark. Evidence:
- [ ] **11.03** Rank by expected profit after fees. Done when: The table is sorted by expected net profit. Win probability is its own column and is not the sort key. Evidence:
- [ ] **11.04** A thin sample is unsupported. Done when: A row under the stated minimum sample is marked unsupported and is left out of the ranked list. Evidence:
- [ ] **11.05** The file says survivors-only, and names its inputs. Done when: The header says the universe is survivors-only, and it names the world-shard version and the question-tree version. Evidence:
- [ ] **11.06** The published path is versioned. Done when: The path includes a version. A later run writes a new path and leaves the previous file in place. Evidence:


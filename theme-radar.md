# Theme Radar — repository map

**Repo:** https://github.com/SRoyaltyy/theme-radar  
**Role:** closed-loop **theme / sector / stock** radar on daily Finviz Elite snapshots. Companion to `SRoyaltyy/fullscan`.  
**Mapped:** 2026-08-21 (HKT). No clone, no edits. Source of truth is GitHub via MCP `user-Github`.  
**Latest live data:** snapshot + score + composite for **2026-08-19** (bot commits ~04:56–05:45 HKT on 2026-08-20). Labels/attribution through **2026-08-18** (need a later snapshot to grade 08-19).

---

## 1. Executive snapshot

Theme-radar is much smaller than fullscan and **deterministic-first**. Every US trading day it:

1. Pulls the full Finviz Elite universe (~11,600 tickers).
2. Scores every name on 1d / 1w / 1m with a coded rubric (no LLM).
3. Writes a full-universe feature log, then backfills forward labels when later snapshots exist.
4. Attributes score/factor ICs vs those labels and optionally retunes plain-polarity weights.

An optional DeepSeek “theme predict” loop exists (same client/secrets as fullscan) but is **manual**, not daily. Two predict runs exist (2026-08-06, 2026-08-12); neither has been outcome-graded.

**Composite `total_score` is not yet predictive.** Across 9 labeled dates, mean 1d IC ≈ −0.003. Actionable direction accuracy on the last pooled audit (6 dates, 2026-08-15) was **45.1%**. Weight learner has still promoted multipliers (last promotion 2026-08-19 17:18 EDT / **2026-08-20 05:18 HKT**), with a reconstruction-error warning.

---

## 2. Architecture

Two loops share one repo. Only Loop A is on the daily clock.

```
Finviz Elite export
        │
        ▼
data/snapshots/YYYY-MM-DD.csv   (~11.6k tickers)
        │
        ├──── Loop A (daily, no LLM) ─────────────────────────────────┐
        │  score_engine (rubric) → data/scores/{1d,1w,1m,segments}     │
        │       + feature_log     → data/features/*_1d.csv             │
        │       + scan_report     → 01_daily/*_scan.md                 │
        │  segments               → data/universe/* + *_universe.md    │
        │  label_backfill         → data/labels/*_fwd.csv              │
        │  attribution            → data/attribution/* + *_attribution │
        │  attribution_aggregate  → 03_scoreboard/factor_report.*      │
        │  weight_learner         → data/weight_overrides.json         │
        │  composite_rank         → data/composite/* + *_composite_*   │
        └──────────────────────────────────────────────────────────────┘
        │
        └──── Loop B (manual, DeepSeek) ──────────────────────────────┐
           run_predict  → 01_daily/*_predict.md + buy map             │
           run_outcome  → basket grade vs later snapshots (no workflow)│
           run_reflect  → 02_lessons/candidate (no workflow)          │
           promote_lessons (Sun) — Jaccard cluster → 02_lessons/active│
        └──────────────────────────────────────────────────────────────┘
```

**Design contract (label → regime → join)** from `00_grounding/regime_questionnaire.md`:

| Step | Status | What |
|------|--------|------|
| A | **Live** | `src/segments.py` + `segments.json` — “what is this stock?” |
| B | **Not built** | Daily regime engine — “is today good for tag T?” Reads fullscan Channel 1 / general / sectors / events / news |
| C | **Not built** | Join membership × regime stance → ranked universe |
| Backtest | Reserved | After A trusted and B stable |

`04_archive/` (consolidated memory) is referenced in `config.py` but **does not exist**.

---

## 3. Daily cycle (America/New_York)

All market-day gates use `src/trading_calendar.py` (NYSE holidays 2026–2027 hardcoded). HKT is display-only.

| UTC cron | HKT (EDT season) | Workflow | What |
|----------|------------------|----------|------|
| `30 20 * * 1-5` | 04:30 next day | `finviz_daily.yml` | Elite export → `data/snapshots/` |
| `0 21 * * 1-5` | 05:00 | `score_delta.yml` | score + features + segments + labels + attribution + aggregate + weight_learner |
| `20 21 * * 1-5` | 05:20 | `composite_rank.yml` | residual pressure rank |
| `0 15 * * 0` | Sun 23:00 | `weekly_promote.yml` | promote repeated candidate lessons |
| manual | — | `theme_predict.yml` | DeepSeek theme predict + Finviz mapper |
| manual | — | `backtest.yml` | labels + attribution + suggestion_check + audits |

`score_delta.yml` does **not** run `suggestion_check` or `predictive_audit` (those are backtest-only). That is why suggestion-check CSVs stop at 2026-08-13 and `predictive_audit.md` is stale (generated 2026-08-15 16:32 HKT from 6 dates) while `factor_report.md` is current (9 dates, 2026-08-20 05:18 HKT).

Bot identity: `Theme-Radar-Bot` / `bot@users.noreply.github.com`, `contents: write`, rebase-push to `main`.

---

## 4. Workflows

### 4.1 `finviz_daily.yml` — Finviz Daily Snapshot

- Gate: `is_trading_day(today_et())`.
- Secrets: `FINVIZ_EXPORT` (preferred full URL+auth), `FINVIZ_EXPORT_URL`, `FINVIZ_API_KEY`.
- `python -m src.finviz_fetch` → dated CSV + `.raw.csv` + archive copy + `current.csv`/`previous.csv` + `manifest.json`.
- Same-day re-fetch archives the prior file; dated files are never deleted.

### 4.2 `score_delta.yml` — Finviz Score Delta

Manual inputs: `run_date`, `trace_tickers`, `trace_horizon`.  
Pipeline:

```
score_engine [--trace] → segments → label_backfill → attribution
  → attribution_aggregate → weight_learner
```

Commits: `data/scores|features|labels|attribution|universe`, `data/weight_overrides.json`, `01_daily/`, `02_lessons/`, `03_scoreboard/`.

### 4.3 `composite_rank.yml`

`python -m src.composite_rank` (~20 min after score). Hand-prior residual rank; not the rubric score.

### 4.4 `weekly_promote.yml`

`python -m src.promote_lessons`. Clusters candidates by `trigger_pattern` Jaccard ≥ 0.5, promotes clusters with ≥ 2 occurrences. **Currently a no-op in practice:** attribution-written lessons have no `trigger_pattern`, and `02_lessons/active/` is empty (only `.gitkeep`).

### 4.5 `theme_predict.yml` (manual)

Needs `DEEPSEEK_API_KEY`, `SEARXNG_URL`, `FRED_API_KEY`. Runs `src.run_predict`.

### 4.6 `backtest.yml` (manual)

Optional `score_engine` first, then labels + attribution + **suggestion_check** + aggregate + weight_learner + predictive_audit for 1d/2d/3d.

---

## 5. Modules (`src/`)

Python 3.12. Deps: `requests`, `ddgs`, `yfinance`, `pandas`, `python-dateutil`.

### Config & calendar

| File | Role |
|------|------|
| `config.py` | Secrets from env (same names as fullscan). Paths, `TZ=America/New_York`, `TOPIC=theme_radar`, `MEMORY_WINDOW_DAYS=12`, `MIN_OVERALL_TO_MAP=6.0`, `MIN_CONFIDENCE_TO_MAP=0.55`. |
| `trading_calendar.py` | ET trading-day + NYSE holiday set 2026–2027. |
| `__init__.py` | Package marker. |
| `_score_engine_a.txt` / `_score_engine_b.txt` | `PLACEHOLDER_A` / `PLACEHOLDER_B` stubs. |

### Finviz ingest

| File | Role |
|------|------|
| `finviz_fetch.py` | Elite `export.ashx` (or full `FINVIZ_EXPORT` URL). Writes raw + normalized dated files, archive, current/previous, manifest. Default view `v=152`, columns 0–70. |
| `finviz_delta.py` | Normalize, deltas, catalyst regex flags, industry dashboard, Channel-1 brief for Loop B. |
| `promote_snapshot.py` | Manual ingest of a local CSV as `current.csv`. |
| `snapshots.py` | Shared `snapshot_dates()` / `find_prior()` / `load_dated()`. |

**Gap:** `data/snapshots/README.md` and `run_outcome.py` call `finviz_delta.load_by_date` / `list_dates`, which **do not exist** in `finviz_delta.py`. Outcome grading is broken until those helpers are added (or callers switched to `snapshots.py`).

Catalyst keyword themes: `nuclear_smr`, `optics_transceiver`, `data_center_power`, `hbm_memory`, `copper_metals`, `ai_capex`, `defense`, `semiconductor_equip`.

### Scoring (Loop A core)

| File | Role |
|------|------|
| `score_rubric.py` | Rubric **as data**: 24 rules, 7 categories, 7 interaction gates, status buckets, `HORIZON_WINDOWS`, `CATEGORY_MAX`. “Change numbers HERE only.” |
| `score_engine.py` | **Bootstrap wrapper.** Downloads the known-good engine from commit `64eafa9` into `_score_engine_cache.py` and `exec`s it, then overrides `brief` with `scan_report.brief`. |
| `scan_report.py` | Layman scan.md (pair dates, Ret% window). Latest on-disk `2026-08-19_scan.md` still uses the **old** brief (bootstrap `brief()`), so the override is not winning in CI yet. |
| `feature_log.py` | Full-universe levels + `d_*` + scores → `data/features/{date}_1d.csv` + `.meta.json`. Never truncated. |
| `label_backfill.py` | Next 1–3 snapshots → `fwd_1d/2d/3d`, `short_fwd_*`, entry/exit prices. Wording: signal_asof vs prediction_day. |

**Horizons (calendar days to prior snapshot):** 1d = 1–3, 1w = 4–8, 1m = 18–32. History starts 2026-08-06, so **1m still has no pair** (levels only).

**Status buckets:** EXTREME / EXTENDED / WASHED / NEUTRAL; UPTREND / DOWNTREND / MIXED; HIGH_SHORT / ELEVATED / LOW; STREET_EXTENDED.

**Gates (ordered):** `extension_cap` (price ×0.25), `extreme_flip` (price → −0.5×), `downtrend_bounce_discount` (1w/1m), `street_extended_discount`, `squeeze_flag`, `unconfirmed_rally` (confidence ×0.8), `capitulation_watch`.

**Display score:** `score_100 = total / sum(CATEGORY_MAX) * 100`. Categories: price, flow, technical, positioning, valuation, fundamental, catalyst.

**Weight overrides:** `data/weight_overrides.json` keyed `<field>|<kind>`. Applied in `score_ticker` via `_override_mult`. Current champion (promoted 2026-08-19 17:18 EDT): Price\|ret ×0.25, RSI-delta ×0.25, sales-growth/sales-YoY ×2.0, inst-ownership-delta ×1.73, n_catalysts ×1.93, etc. Curved-polarity rules (rvol/rsi/sma/short/upside/debt) are **never** auto-adjusted.

### Attribution & learning

| File | Role |
|------|------|
| `attribution.py` | Per-date Spearman IC, quintile calibration, combo probes, risk probes. Writes IC CSV, summary JSON, `*_attribution.md`, provisional candidate lesson. |
| `attribution_aggregate.py` | Pools ICs across dates → mean IC, ICIR, sign consistency. `03_scoreboard/factor_report.{md,json}`. |
| `weight_learner.py` | Champion/challenger on plain-polarity rules. Promote only if ≥3 label dates, mean IC gain > 0.001, and challenger ≥ champion on ≥50% of dates. Multipliers clamped [0.25, 2.0]. |
| `suggestion_check.py` | Direction accuracy: score>+2 expect UP, <−2 expect DOWN. Full-universe CSV + board. |
| `predictive_audit.py` | Cross-date accuracy + factor ICs + pairwise sign-quadrant combos. |

**Leak in `factor_report`:** after joining features+labels, `short_fwd_*` and `exit_price_*` are treated as “factors” (IC ≈ −1 / leaked). Skip lists miss those label columns.

**Learner warning:** last run reconstruction error `|rebuilt price − stored price_score| = 0.2652` (should be ~0). Log says distrust this promotion.

### Segments & composite

| File | Role |
|------|------|
| `segments.py` | Step A deep labeling from `00_grounding/segments.json`. Families: sector, industry, size, index, geo, beta, short, liq, rvol, vol, profit, lev, style, mom, ext, range (INACTIVE), earn (INACTIVE), themes. |
| `composite_rank.py` | Separate residual model: SPEC_DURATION / QUALITY_DEFENSIVE / CROWDING / SIZE_TILT × breadth-derived `p_risk_on`. Not the rubric. Started 2026-08-12. |

### Loop B (LLM theme predict)

| File | Role |
|------|------|
| `deepseek_client.py` | OpenAI-compatible chat + `web_search` tool. SearXNG if `SEARXNG_URL` else DuckDuckGo. **Copied/adapted from fullscan.** |
| `run_predict.py` | Rubric + memory + Finviz Channel-1 brief → DeepSeek → `finviz_mapper.map_all_from_predict`. |
| `finviz_mapper.py` | Theme → liquid pure plays (industry + description keywords + hint boost). Themes: optics, ai power, nuclear, copper, memory, connectivity. Needs `data/finviz_universe.csv` or `data/universe_parts/part_*.csv` — **neither is in the repo**. |
| `memory.py` | Scoreboard + consolidated memory + active lessons + last 12 predict/reflect logs. |
| `scoreboard.py` | Tiny JSON of predict-cycle runs (`03_scoreboard/scoreboard.json`). |
| `run_outcome.py` | Grade theme baskets vs later snapshots (hit = beat median-universe bench by +1%). **Not in any workflow.** Broken `load_by_date` call. |
| `run_reflect.py` | LLM lesson from graded outcome. **Not in any workflow.** |
| `promote_lessons.py` | Jaccard cluster of `trigger_pattern`. Attribution lessons lack that field, so they never promote. |

---

## 6. Grounding (`00_grounding/`)

| File | Role |
|------|------|
| `master_rubric.md` | Loop B system prompt. MEMORY_CONFIRM first line. Stage 1 discovery → Stage 2 trigger filter → Stage 3 five-layer scores (narrative/trigger/scarcity/institutional/momentum) → `THEME_SCORES_BEGIN/END`. |
| `outcome_prompt.md` | Grade narrative vs basket vs kill-switch discipline. |
| `reflect_prompt.md` | Five checks → `LESSON_BEGIN/END` (trigger, corrected behavior, error category, falsifier). |
| `segments.json` | Label registry (bin edges live here, not in code). `range` and `earn` marked INACTIVE (export lacks 52w / Earnings Date). |
| `regime_questionnaire.md` | Step B design. Explicitly consumes **fullscan** `01_daily/_channel1/`, `general/`, `sectors/`, `events/`, `news/` plus theme-radar `data/universe/` and Supabase. |

---

## 7. Data layout (no giant CSVs read)

Universe size ≈ **11,500–11,600** tickers per day. Snapshot raw ≈ 11.3 MB; normalized ≈ 4.4 MB.

```
data/
  README.md                    mapper universe install notes (shards not in repo)
  weight_overrides.json        learned multipliers (last promo 2026-08-19 17:18 EDT)
  snapshots/                   2026-08-06 … 2026-08-19  (+ .raw.csv, current, previous, manifest)
    archive/                   timestamped copies of each fetch
  features/                    {date}_1d.csv + .meta.json     08-06 … 08-19
  scores/                      {date}_{1d,1w,1m,segments}.csv 08-06 … 08-19
  labels/                      {date}_fwd.csv + .meta.json    08-06 … 08-18  (08-19 not yet gradeable)
  attribution/                 {date}_ic.csv + _summary.json  08-06 … 08-18
                               _suggestion_check.csv          08-06 … 08-13 only
  universe/                    {date}_membership.csv + _segment_stats.csv  08-06 … 08-19
  composite/                   {date}_composite_rank.csv + _y_snapshot.json  08-12 … 08-19
```

**Human artifacts**

```
01_daily/
  {date}_scan.md               top/bottom 15 (CSV is full universe)
  {date}_universe.md           segment coverage
  {date}_attribution.md        IC / calibration / risk   (through 08-18)
  {date}_composite_rank.md     residual pressure         (from 08-12)
  {date}_suggestion_check.md   direction hits            (through 08-13)
  {date}_predict.md + _trace   LLM predict               (08-06, 08-12 only)
  {date}_trace_{TICKER}_1d.md  per-name audit            (08-07: BBAI, MP, OKLO)
  _suggestion_check_BOARD.md
  _transcripts/                DeepSeek JSON             (08-06, 08-12)

02_lessons/
  candidate/                   08-06 … 08-18 attribution bullets (no trigger_pattern)
  active/                      empty

03_scoreboard/
  factor_report.{md,json}      current (9 dates, 2026-08-20 05:18 HKT)
  weight_learning.md           current
  predictive_audit*.{md,json}  stale (6 dates, 2026-08-15)
  scoreboard.json              2 ungraded predict runs
```

Trading days present: 08-06, 07, 10, 11, 12, 13, 14, 17, 18, 19 (weekends/holiday skipped correctly).

---

## 8. Scoring, labels, attribution (how the loop closes)

### Score construction

For each ticker × horizon:

1. Pair latest snapshot with nearest prior in the horizon window.
2. Compute status from **levels** (week/month perf, RSI, 50/200-DMA, short float, target upside).
3. Each rubric rule emits a signal in {−1, −0.5, 0, +0.5, +1} (or a curve) × `weight` × learned multiplier.
4. Slow fields never vote on 1d. Missing pair → skip ret/delta rules.
5. Apply gates; emit category scores, `total_score`, `score_100`, flags, top drivers.

True return `ret_H` is Price_now / Price_then − 1 (deadzones 1.5% / 3% / 5%). RVol takes the sign of that return (hot volume + down price = selling).

### Labels

`fwd_kd = Price(prediction_day_k) / Price(signal_asof) − 1`.  
`up_3d` / `down_3d` = |fwd_3d| > 1.5%. Short = opposite sign.  
08-18 labels have only 1d (smaller file); 08-17 has 1d+2d; earlier dates have 1d+2d+3d.

### Attribution

- Spearman IC(feature, long fwd) on **all** labeled names (n ≈ 11.5k).
- Score quintiles + hit-up>1.5%.
- Per-feature IC, IC within up/down, mean fwd when feature +/−.
- Combinations: `true_ret>3%` ∩ trend bucket.
- Risk: EXTENDED / EXTREME / WASHED mean fwd, and mean fwd if score in top quintile.

Latest attribution (signal 2026-08-18 → pred 2026-08-19): score IC **+0.0486**, n=11,572. Calibration is **not** monotonic (Q3 mean fwd 2.29% > Q5 1.41%). Pooled 1d mean IC of `total_score` across 9 dates: **−0.0031**.

### Suggestion-check rule

Actionable if `|total_score| > 2`. Hit = direction of fwd matches expected sign. Neutral excluded from accuracy.

---

## 9. Secrets

Never hardcoded. Stripped of trailing newlines.

| Secret | Used by | Required for |
|--------|---------|--------------|
| `FINVIZ_EXPORT` | `finviz_fetch` | Daily snapshot (preferred: full Elite export URL+auth) |
| `FINVIZ_EXPORT_URL` | same | Alternate full URL |
| `FINVIZ_API_KEY` | same | If building `export.ashx?auth=` |
| `DEEPSEEK_API_KEY` | `deepseek_client` | Theme predict / outcome / reflect |
| `SEARXNG_URL` | `deepseek_client` | Search backend (else DuckDuckGo) |
| `FRED_API_KEY` | predict workflow env | Injected but **unused** in theme-radar code |
| `DEEPSEEK_BASE_URL` | optional env | default `https://api.deepseek.com` |
| `MODEL_PREDICT` | optional env | default `deepseek-chat` |

README: “`DEEPSEEK_API_KEY` / `SEARXNG_URL` only for theme *predict* workflow (optional).” Daily Loop A needs **only** Finviz secrets.

---

## 10. Relationship to fullscan

Theme-radar is the **companion**, not a fork of the fullscan daily LLM cycle.

| | **fullscan** | **theme-radar** |
|--|--------------|-----------------|
| Job | General market + 11 sectors + events + news, LLM-first | Full-universe Finviz theme/sector/stock radar, rubric-first |
| Daily brain | DeepSeek + tools, Channel 1 pre-fetch | Deterministic `score_engine` on every ticker |
| LLM use | Core path | Optional `theme_predict` only |
| Universe | Index/sector narratives | ~11.6k Finviz names, CSVs never truncated |
| Learning | Predict → grade → reflect → lessons | Features → labels → IC → weight_learner (gates) |
| Shared DNA | Same secret names; `deepseek_client` copied; rubric-tuning “same discipline as fullscan `compute_scores`” | |
| Planned join | Channel 1, `01_daily/general/`, `sectors/`, `events/`, `news/` | Step B regime engine (not built) will **read those fullscan artifacts** plus `data/universe/` |
| Timezone | Same ET trading-day rule | Same `America/New_York`; HKT display-only |
| Memory | Consolidated + active lessons | Same shape, but `04_archive` missing and active lessons empty |

Fullscan answers “what is the market / sector regime today?”  
Theme-radar answers “which names and industries are already moving, and did yesterday’s scores predict it?”  
Step B is the intended glue.

---

## 11. Gaps and operational notes

1. **`score_engine.py` HTTP-bootstraps commit `64eafa9`.** Fragile (needs GitHub raw on the runner). Latest `scan.md` still uses the old brief, so `scan_report.brief` override is not taking effect in production.
2. **`load_by_date` / `list_dates` missing** — `run_outcome` cannot run; snapshots README is stale.
3. **Loop B is unfinished:** predict is manual; outcome/reflect have no workflow; mapper universe shards are not in git; `FRED_API_KEY` unused; `04_archive` missing.
4. **Lesson promote is mismatched** with attribution lessons (no `trigger_pattern`) → `02_lessons/active/` stays empty.
5. **`factor_report` leaks label columns** (`short_fwd_*`, `exit_price_*`).
6. **Weight-learner reconstruction error 0.26** on last promotion — log says distrust.
7. **1m horizon** has no prior pair until ~18 calendar days of history exist (need snapshots back to ~2026-07-18).
8. **`range` / `earn` segments inactive** until the Elite export adds 52-week and Earnings Date columns.
9. **Predictive audit / suggestion_check** are not on the daily workflow — they go stale.
10. Composite score is currently a **weak / slightly inverse** 1–3d predictor. Consistent-ish negative ICs on recent-momentum deltas (`d_RSI`, `d_50DMA`, `true_ret`) point at mean-reversion, which the rubric still treats as bullish.

---

## 12. File inventory (source only)

```
README.md
requirements.txt
.github/workflows/{finviz_daily,score_delta,composite_rank,weekly_promote,theme_predict,backtest}.yml
00_grounding/{master_rubric,outcome_prompt,reflect_prompt,regime_questionnaire}.md
00_grounding/segments.json
src/{__init__,config,trading_calendar,snapshots,finviz_fetch,finviz_delta,finviz_mapper,
     promote_snapshot,score_rubric,score_engine,scan_report,feature_log,label_backfill,
     attribution,attribution_aggregate,weight_learner,suggestion_check,predictive_audit,
     segments,composite_rank,deepseek_client,run_predict,run_outcome,run_reflect,
     memory,scoreboard,promote_lessons}.py
src/{_score_engine_a,_score_engine_b}.txt
data/{README.md,weight_overrides.json,snapshots/README.md,snapshots/manifest.json}
```

Plus dated research artifacts under `01_daily/`, `02_lessons/`, `03_scoreboard/`, `data/{snapshots,features,scores,labels,attribution,universe,composite}/` as dated above.

Historical engine (the real `score_engine` body) lives at commit `64eafa9` and is re-fetched at runtime.

# Viewport gallery v1 (Kimi display lane)

**Authority:** METHODOLOGY §0b #149 (James 17:25), #155 (18:24 full-disambiguation rule),
#159 (VIEWPORT_READY_FOR_KIMI_V1.md picker set, James 19:07 HKT 2026-10-29).
Reference mockups approved by Cyrus: `docs/viewport_mocks/1-4`.

## What this is

A deterministic Python recipe + plotly renderer for the single-stock
TradingView-style display: bare OHLC+Volume first, a checklist picker of
`status=READY` viewport recipes, purple recolour of exactly the bars/lines/zones
each definition names, a cutoff marker, and a label box stating the measured
quantity so two readings are impossible (#155/#156). `DO_NOT_DRAW` rows are shown
disabled with their blocker text and are never drawn.

## Layout

- `chartview/recipes.py` — pure functions `recipe(dates, O, H, L, C, V, cutoff) ->
  {id, status, label, answer, ops}`. Each recipe documents its own fully-disambiguated
  definition (window inclusivity, ties, price fields, colour rule, output units) in its
  `label`. `CHART_SHAPE_SIMILARITY` is a DISABLED stub: GPT owns the N/Y/K grid
  (#158 / VIEWPORT_READY `DO_NOT_DRAW` table); no N, Y or K is invented here.
- `chartview/render.py` — plotly figure from the ops; per-bar candle colours via
  run-split traces; volume pane; cutoff vline; label box.
- `chartview/data.py` — loads a daily-ohlcv parquet (light-daily-box schema:
  date/open/high/low/close/volume) and truncates at the setup date: cutoff = last bar
  with candle end < S; day-S OHLCV is never read.
- `chartview/build_gallery.py` — CLI writing one self-contained HTML page per
  (ticker, setup date): picker, bare chart, then one section per READY recipe;
  DISABLED/DO_NOT_DRAW entries as greyed text.
- `tests/test_chartview_recipes.py` — 33 deterministic synthetic-data checks
  (counts, tie-breaks, inclusive vs exclusive bases, prior-period pivots,
  confirmation boundaries, blank conditions, DISABLED stub, as-of truncation).

## Build the gallery

```bash
python3 -m chartview.build_gallery --data SPY.parquet --ticker SPY \
    --setups 2021-11-12 2022-06-15 --out gallery_out
```

Data note: the released gallery was built from release
`light-daily-box-v1-20261028` (SPY.parquet, Yahoo daily, 2020-01-02..2026-10-27).
Setup dates in the released pages are 2021-11-12 and 2022-06-15. Any setup date
works — the cutoff logic enforces the no-lookahead rule mechanically.

## Not in scope (per #149/#158/#159)

- The chart-shape similarity / side-by-side grid (GPT finalises N/Y/K; this repo
  stubs the picker entry only).
- `I076`/`I078` auto-fib variants (confirmation rules unbound), `I111/I117/I202/I203`
  (vague), other `cp_*` tags without pinned viewport_draw, question-tree template
  families (awaiting GPT anchor rewrite).
- The indicator-inventory gallery of all WORLD_SNAPSHOT_DICTIONARY items — this v1
  covers only the READY picker batch in VIEWPORT_READY_FOR_KIMI_V1.md.

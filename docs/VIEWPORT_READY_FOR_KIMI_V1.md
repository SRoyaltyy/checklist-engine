# Viewport ready-for-Kimi batch v1

**Authority:** Cyrus via James, 2026-10-29 ~19:07 HKT. Reference mockups (approved):
`docs/viewport_mocks/1_red_green_ratio.png`,
`2_fibonacci_60d.png`,
`3_lower_highs.png`,
`4_volume_vs_20d.png`.
Disambiguation rule: METHODOLOGY §0b (~18:24 HKT / #155, ACK #156).
Drawable-only rule: §0b (~18:52 HKT / #158).

This file is the **first picker set** for the single-stock TradingView-style display.
Kimi stubs the checklist against `status=READY` rows only. Rows with
`status=DO_NOT_DRAW` must not appear as selectable, or must show as disabled with
the blocker text. No guessing.

## Global viewport rules (every READY row)

1. **One stock** (SPY or AAPL for the gallery; mockups used ONDS as the visual
   reference only).
2. **Setup date S** = the concrete date control. Only data knowable at **S's
   open**. Every bar used must have candle end `< S` and
   `available_from <= S`. Day-S OHLCV is never read.
3. **Cutoff bar** = the last completed native bar satisfying (2). Mockups that
   show "Oct 28 close" imply S = the next session after that close.
4. **Timeframe Y** defaults to **1d (daily)** for this batch unless a row says
   otherwise.
5. **Highlight colour** = purple. Recolour the named candles / volume bars.
   Never draw a circle/ring around them (#153).
6. **Bare chart first:** OHLC + Volume only until a READY item is picked (#152).
7. **Fully disambiguated:** one reading only. If two readings remain, mark
   AMBIGUOUS and do not draw (#155/#156).
8. **Output label** on the chart must name the measured quantity so body-sum
   ratios cannot be confused with candle counts.

`VIEW_*` ids below are **viewport recipes** for the display lane. They are not
new scored dictionary boxes and do not tick PROJECT_CHECKLIST. Where a recipe
differs from an existing dictionary / `cp_*` field, the difference is explicit.

---

## READY — approved mockups (draw these first)

### 1. `VIEW_RG_COUNT_5D` — Red:green candle **count** (mockup 1)

| Field | Value |
|---|---|
| status | READY |
| mockup | `docs/viewport_mocks/1_red_green_ratio.png` |
| measured quantity | Count of red candles : count of green candles in the window |
| NOT this | `cp_gr_body20` (green absolute-body **sum** / red absolute-body **sum** over 20 bars). Different quantity; different label. |
| colour rule | red iff `close < open`; green iff `close > open`; doji (`close == open`) counts as neither (not red, not green) |
| window | Nearest **N=5** completed daily bars ending at the cutoff bar, **inclusive** of cutoff |
| timeframe | 1d |
| price fields | open, close (colour only) |
| tie-breaks | none (per-bar colour is exact) |
| output | `R:G = r:g` with `r = #{red}`, `g = #{green}`; also show `doji = 5 - r - g` when > 0 |
| units | counts (unitless integers) |
| viewport_draw | Recolour those exact 5 daily candles purple (bodies+wicks). Optional light purple band behind the 5. Label box: `Red:green ratio, nearest 5 daily candles` + window dates + `R:G = r:g`. Do not recolour other candles. |

### 2. `VIEW_FIB_HHLL_60D` — Fib from window HH / LL (mockup 2)

| Field | Value |
|---|---|
| status | READY |
| mockup | `docs/viewport_mocks/2_fibonacci_60d.png` |
| measured quantity | Position of cutoff close inside the range from window highest-high to window lowest-low; Fib levels of that range |
| NOT this | I076 Auto Fib (ZZ / ATR-reversal pivots); I078 Fibonacci_swing. Those stay DO_NOT_DRAW until a viewport binding pins confirmation bars. |
| window | Nearest **N=60** completed daily bars ending at cutoff, inclusive |
| timeframe | 1d |
| anchors | `H = max(high)` over the window; `L = min(low)` over the window. Range `R = H - L`. If `R == 0`, blank (do not draw levels). |
| anchor bar ties | If several bars share `H`, pick the **most recent** (rightmost). Same for `L`. |
| levels | Retracement from H down to L: `level(r) = H - r·R` for `r ∈ {0, 0.236, 0.382, 0.5, 0.618, 0.786, 1}` (so 0%=H, 100%=L). |
| cutoff answer | `pct = (H - close_cutoff) / R` as a fraction of the range; report which adjacent levels bracket `close_cutoff` |
| units | prices in source units; pct unitless |
| viewport_draw | Recolour the H-anchor candle and the L-anchor candle purple. Draw horizontal purple Fib lines at each level with labels. Mark cutoff close with a dashed line. Optional purple shade between the two levels that bracket cutoff close. Label: `Fibonacci retracement, past 60 daily bars` + `anchor HIGH` / `anchor LOW` prices + answer pct. |

### 3. `VIEW_LOWER_SWING_HIGHS_3` — Three descending fractal swing highs (mockup 3)

| Field | Value |
|---|---|
| status | READY |
| mockup | `docs/viewport_mocks/3_lower_highs.png` |
| measured quantity | Whether the last 3 **confirmed** fractal swing highs are each strictly lower than the previous |
| NOT this | `lower_highs10` (count of days with `High < prior High` over 10 bars). Different definition; listed separately below. |
| timeframe | 1d |
| pivot / fractal | Bar `i` is a swing high iff `high[i] = max(high[i-L .. i+L])` with **L=5** (5 bars each side, 11-bar window). Strict: if any other bar in the window equals that high, still a swing high only if `i` is the unique argmax; on ties for the max, take the **leftmost** bar inside the window as the pivot (stable). |
| confirmation | A swing high at `i` is confirmable only when bar `i+L` is known, i.e. `i+L <= cutoff_index`. Last confirmable pivot index ≤ `cutoff_index - L`. |
| lookback | Among confirmable swing highs with index ≤ `cutoff_index - L`, take the **last 3** in time order (oldest → newest: H1, H2, H3). |
| answer | YES iff there are at least 3 such highs AND `high[H1] > high[H2] > high[H3]` (each strictly lower than previous). Otherwise NO, with reason (`need 3, have k` or `not strictly descending`). |
| units | boolean + pivot prices |
| viewport_draw | Purple dots on the (up to 3) swing-high bars at their high price; purple dashed polyline connecting them in time order; price labels. Label box with pivot rule and YES/NO. Do not recolour unrelated candles. |

### 4. `VIEW_VOL_VS_MEAN_20D` — Volume today vs mean of last 20 (mockup 4)

| Field | Value |
|---|---|
| status | READY |
| mockup | `docs/viewport_mocks/4_volume_vs_20d.png` |
| measured quantity | `V_cutoff / mean(V over last 20 completed daily bars ending at cutoff inclusive)` |
| NOT this | C22 / I080 RVOL20, which uses `V_t / SMA20(V over t-20..t-1)` (**today excluded from the base**). That item is READY under its own id below; do not silently substitute. |
| window | Nearest **N=20** completed daily bars ending at cutoff, **inclusive** of cutoff |
| timeframe | 1d |
| inputs | volume |
| edge | If any of the 20 volumes is missing/nonfinite, blank. If mean == 0, blank (do not draw ratio). |
| output | `V_cutoff`, `mean_20`, `ratio = V_cutoff / mean_20` |
| units | shares (or source volume units); ratio unitless |
| viewport_draw | In the volume pane, recolour those exact 20 volume bars purple. Draw a horizontal purple line at `mean_20` labelled `20d avg`. Mark the cutoff bar `today`. Label: `Volume today vs 20-day average volume` + values + ratio. |

---

## READY — existing dictionary / native items with clear draw

These may appear in the picker after the four mockups. Each already has an
exact recipe in-repo; viewport_draw is stated so Kimi does not invent geometry.

### `lower_highs10` (pinned chart picture)

| Field | Value |
|---|---|
| status | READY |
| source | `docs/NATIVE_CHART_PICTURE_V1.md` / `world_chart_picture.py` |
| measured | Count of bars in the last 10 completed native bars where `High < High of immediately preceding bar` |
| viewport_draw | Recolour purple every bar inside the 10-bar window that satisfies `High < prior High`; show the integer count. Label must say `lower_highs10` (not the fractal mockup). |

### `cp_gr_body20` (pinned chart picture)

| Field | Value |
|---|---|
| status | READY |
| source | `docs/NATIVE_CHART_PICTURE_V1.md` |
| measured | Sum of green absolute bodies / sum of red absolute bodies over last 20 bars; green=`close>open`, red=`close<open`, doji neither; body=`abs(close-open)` |
| viewport_draw | Recolour the 20-bar window purple; annotate green-body sum, red-body sum, ratio. Label **must** say `body-sum ratio` so it cannot be read as candle count. |

### C22 / I080 `RVOL20` (dictionary)

| Field | Value |
|---|---|
| status | READY |
| source | `dictionary/WORLD_SNAPSHOT_DICTIONARY.csv` C22 / I080 |
| measured | `RVOL = V_cutoff / SMA(V, 20 over the 20 bars strictly before cutoff)`; spike if `RVOL > 3` (code default) |
| viewport_draw | Purple the cutoff volume bar; draw horizontal line at the prior-20 SMA; label RVOL. Do not use the inclusive-20 mean from `VIEW_VOL_VS_MEAN_20D`. |

### I074 Pivot Points Standard (calendar prior period)

| Field | Value |
|---|---|
| status | READY (levels only) |
| source | `docs/NATIVE_CALENDAR_PIVOTS_V1.md` |
| measured | From the **prior completed** calendar week/month/quarter: `P=(H+L+C)/3`, `R1=2P-L`, `S1=2P-H`, `R2=P+(H-L)`, `S2=P-(H-L)` with H=max high wick, L=min low wick, C=final session close of that prior period |
| viewport_draw | Draw five horizontal lines (P,R1,S1,R2,S2) with labels. **Do not** pick a single extreme bar to recolour when highs/lows tie — location of a unique extreme is AMBIGUOUS per GPT ACK155; levels alone are fine. |
| parameters | short=week, default=month, long=quarter |

### I101 Donchian(20)

| Field | Value |
|---|---|
| status | READY |
| source | dictionary I101 (`in_code=yes`) |
| measured | Upper = max(high) of prior 20 bars (default); Lower = min(low) of prior 20; mid = average. Use dictionary window (prior bars / code path). |
| viewport_draw | Purple band or lines for upper/lower over the window; optional recolour of the two bars that set the live upper and lower (most-recent tie). |

---

## DO_NOT_DRAW (blocked for the picker)

| Id / family | Blocker |
|---|---|
| I076 Auto Fib, I078 Fibonacci_swing | ZZ(3ATR) confirmation / freeze rules not bound to a single viewport reading yet; use `VIEW_FIB_HHLL_60D` instead |
| I111 / I117 / I202 / I203 | Explicitly vague in #149 wake note |
| `cp_*` tags other than those listed READY | Draw only when the pinned field + viewport_draw are both present |
| Question-tree template families (`retests`, `vs own past`, …) | ~10.7k questions lack exact anchors; GPT rewrite pending |
| Chart-shape similarity / side-by-side (#158) | Cyrus-approved scope, but **GPT owns the N/Y/K grid**. Kimi may stub a disabled menu entry; do not invent N, Y, or K |
| Any dictionary row still readable two ways | Flag AMBIGUOUS; skip |

---

## Implementation order for Kimi

1. Bare OHLC + Volume for one liquid name + setup-date control.
2. Picker lists READY ids above (mockups 1–4 first).
3. On pick, compute from recipe code / the formulas here; paint `viewport_draw`.
4. Ack in METHODOLOGY §0c with this commit SHA.
5. Do not wait for the chart-shape grid or template-family rewrite to ship the gallery.


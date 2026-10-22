# Fixed lookback grid — recorded 2026-10-23 00:05 HKT BEFORE computing (no results looked at for these features)
Windows (all on bars < D; "D-k" = k trading bars before D):
- Lagged: windows ENDING at D-5, D-10, D-21, D-42, D-63, D-126, each LASTING 5, 10, 21 bars -> 18 cells (id `lgE{end}L{len}`).
- Trailing: windows ending at D-1 lasting 3, 5, 10, 20, 40, 60, 120 bars -> 7 cells (id `trL{len}`).
Features per window (8): trend = close(end)/close(start-1)-1; red:green = #red/#green candles (green = C>O; #green floored at 1);
max green-chain length; max red-chain length; max green-chain move; max red-chain move (chain move = close at chain end / close before chain start - 1, |.|);
volume trend = mean volume in window / mean volume of the 20 bars before the window; distance from high = close(end)/max high in window - 1.
=> 25 x 8 = 200 features, coded as terciles over the tradable setup pool (like other NEW rows), tested with the same fixed symmetric pairing,
2020-22 discover / 2023-24 confirm, and global BH over every item x setup. Windows needing bars before 2020-01-02 are NA.

## Path-level set v2 — recorded 2026-10-23 00:07 HKT BEFORE computing (`path2.py`; all bars < D)
- dd126: max drawdown in last 126 bars; dd126_recov: share of that drawdown recovered by D-1; dd126_days_since_peak.
- swings60: count of confirmed swing highs + lows (2-bar fractal) in last 60 bars; swing_up60 / swing_dn60 counts separately.
- trendq: R^2 of a linear fit of log close over the last leg (bars since the last 60-bar extreme, min 10) and over trailing 20/60 bars (straightness).
- hl60 / lh60: number of higher swing lows / lower swing highs in last 60 bars.
- ceiling_tests60: number of bars in last 60 whose high is within 1% of the 60-bar max high (excluding the max bar).
- base_len: consecutive bars up to D-1 that stayed inside a ±7.5% band around the D-1 close; base_shrink: mean range of the last half of the base / first half (<1 = ranges shrank).
- updn_vol_leg: up-day volume / down-day volume over the last leg; spike_share: share of the leg's gain from its single biggest day (1 = one spike, small = steady rise).
- shape60 / shape126: correlation of the z-normalised close path (last 60 / 126 bars) with the average z-path of WINNERS of the same setup, template built on 2020-22 events only.
- nn_win60 / nn_win126: share of winners among the 25 nearest 2020-22 events (Euclidean on the z-path, same setup; leave-one-out for 2020-22 events).
Shape/NN rows are only honest on 2023-24 (the template is fitted on 2020-22), so for them only the 2023-24 confirm numbers count. All rows enter the same global BH family as everything else.

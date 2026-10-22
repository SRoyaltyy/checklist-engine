# Fixed lookback grid — recorded 2026-10-23 00:05 HKT BEFORE computing (no results looked at for these features)
Windows (all on bars < D; "D-k" = k trading bars before D):
- Lagged: windows ENDING at D-5, D-10, D-21, D-42, D-63, D-126, each LASTING 5, 10, 21 bars -> 18 cells (id `lgE{end}L{len}`).
- Trailing: windows ending at D-1 lasting 3, 5, 10, 20, 40, 60, 120 bars -> 7 cells (id `trL{len}`).
Features per window (8): trend = close(end)/close(start-1)-1; red:green = #red/#green candles (green = C>O; #green floored at 1);
max green-chain length; max red-chain length; max green-chain move; max red-chain move (chain move = close at chain end / close before chain start - 1, |.|);
volume trend = mean volume in window / mean volume of the 20 bars before the window; distance from high = close(end)/max high in window - 1.
=> 25 x 8 = 200 features, coded as terciles over the tradable setup pool (like other NEW rows), tested with the same fixed symmetric pairing,
2020-22 discover / 2023-24 confirm, and global BH over every item x setup. Windows needing bars before 2020-01-02 are NA.

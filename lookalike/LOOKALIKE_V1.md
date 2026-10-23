# LOOKALIKE_V1 — "twin" chart test, pre-registered rules (committed BEFORE any feature build, matching or outcome join)
Registered 2026-10-23 ~12:50 HKT. Owner: Trading Bot Taskforce. Asked by Cyrus in War room ("look at history and tell me what happened"):
find past stock-days whose whole last-25-day chart picture looks like today's, and check what happened next.
PRACTICE 2020–24 only, survivors-only (win rates read high). Price read filter date <= 2024-12-31, asserted. **2025–26 stays sealed**
until the joint 23:00 HKT lock (Fri 2026-10-23); nothing here touches it.

## Population, returns, costs (identical to COMBO_MODEL_V2)
Rows = state_test/combo/keys_labels.parquet (300,000-row uniform 2020–22 draw = "train"; all 2023–24 buyable stock-days = "check"),
minus rows failing the $100M market-cap filter (mcap_keep.npy; applied to picks AND to the benchmark mean). Entry open of D.
rA = EXIT_RULE_V1, rB = HOLD_10D, both already net of 30bp each way (0.6% round trip). Excess = r minus same-date mean of the filtered rows
of the same split.

## Inputs (every input uses only bars strictly before D: the 25 bars ending at the last bar < D)
Prices: pricehist/universe_2020_survivors.parquet (sha fb9bbe69…ef337, asserted). scale = mean(high-low) over the 25 bars.
Blocks (each block z-scored per dim on the library, then divided by sqrt(#dims) so every block weighs the same):
1. Candle bodies: (close-open)/scale for each of the 25 bars (25 dims, signed).
2. Path shape: (close - min low)/(max high - min low) for each of the 25 bars (25 dims).
3. Green:red body-size ratio: log((sum green bodies + e)/(sum red bodies + e)), sizes not counts (1 dim).
4. Bollinger position: %B of the last bar, 20-bar SMA ± 2 sd (1 dim).
5. Trend direction: (SMA20[last] - SMA20[last-5]) / scale (1 dim).
6. Dip depth vs own range: (max high - last close)/(max high - min low) (1 dim).
7. New Bot chart-picture tags (Drive 1UAGlXkq0rCdbXtwuGuuUiyImQBf8PfHm, cp_tags.csv sha 54a731b2…0d64 asserted; 7 tags, bars < D):
   YES=+1, NO=-1, not-ready/missing=0 (missing is unknown, not NO) (7 dims).
Self-test: changing any bar on/after D must leave the vector unchanged (asserted on random rows).

## Matching (Euclidean, exact search, faiss IndexFlatL2)
Library = the 2020–22 train rows only. For a target dated D, eligible twins are library rows dated <= (first day of D's month) - 35 calendar
days, so every twin's outcome was finished before D (no lookahead). A target's own ticker-day is never its own twin.
Discovery targets = 2020–22 train rows (those with >= 2,000 eligible library rows, i.e. effectively from mid-2020). Check targets = all
filtered 2023–24 rows. Match widths (widened step by step): K = 10, 25, 50, 100, 200, 400 nearest twins.
Trade-off table reported per K: median distance to the K-th twin, median mean twin distance, and both as a share of the median random-pair distance.

## Trade rule and pass bar
For each K and exit X: twin_win = share of the K twins with rX > 0; twin_ex = mean twin excess xX.
Eligible if twin_win > 55% and twin_ex > 0; buy the top 5 eligible per date by twin_ex (fewer if fewer eligible).
Pass (unchanged bar) in BOTH discovery and check: n >= 30, win > 55% after fees, mean excess vs same-day filtered mean > 0, BH q < 0.05
(date-clustered bootstrap, 500 draws, seed 13, two-sided p on mean excess).
Tests: 6 K x 2 exits x 2 periods = 24. Luck-correction base 14,075 -> family 14,099 (base entered as p=1, as in combo v2).
No setting is changed after seeing any outcome; any deviation goes in a dated addendum before results.

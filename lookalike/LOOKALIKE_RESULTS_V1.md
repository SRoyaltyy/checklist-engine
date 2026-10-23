# LOOKALIKE_V1 results: FAIL, 0 of 156 settings pass in both periods (rules f1cc345 + addendum A d5d4e7a)
Run 2026-10-23 12:40–13:10 HKT. 2020–24 only, survivors-only, price read filter <= 2024-12-31 (asserted); 2025–26 never opened.
New Bot tags: Drive 1UAGlXkq0rCdbXtwuGuuUiyImQBf8PfHm, cp_tags.csv sha 54a731b2af3f…0d64 verified (tarball sha 45209602…25e8).
Lookahead self-test (perturb bars on/after D, vector unchanged): passed. HOLD_10 returns match combo rB to within 1.5e-6.
Rows: 1,319,453 targets with twins (discovery = 2020–22 train draw from 2020-06; check = all filtered 2023–24). Picks: top 5/day.

## Closeness vs number of twins (distance in standardised units; random pair median = 4.18)
| K twins | median dist to K-th twin (2020–22 / 2023–24) | as share of random pair | mean twin dist / random |
|---|---|---|---|
| 10 | 1.66 / 1.58 | 0.40 / 0.38 | 0.38 / 0.36 |
| 25 | 1.75 / 1.66 | 0.42 / 0.40 | 0.40 / 0.38 |
| 50 | 1.82 / 1.72 | 0.43 / 0.41 | 0.41 / 0.39 |
| 100 | 1.89 / 1.79 | 0.45 / 0.43 | 0.43 / 0.41 |
| 200 | 1.98 / 1.87 | 0.47 / 0.45 | 0.45 / 0.42 |
| 400 | 2.07 / 1.95 | 0.50 / 0.47 | 0.47 / 0.44 |
Going from 10 to 400 twins only loosens the match ~25%: even the 10 closest twins are 40% as far apart as two random charts.

## Trade tests (6 K x 26 exits x 2 periods = 312). Pass in both periods: 0. Pass in either period alone: 0.
- Hold 1–21 days: win 33–50% in both periods (below the 55% bar everywhere).
- Sell-early TP_5: 64.6–68.8% wins, but the average stock wins 64.5% with the same rule; excess ~0, BH q >= 0.4. TP_10: 54–58%, excess ~0.
- Discovery had a few significant excess results (e.g. K=400 TP_30 +1.24%, K=100 TP_20 +1.21%) but win < 55%, and they did not repeat in 2023–24.
- +10% reach (K=100, 2023–24): twins 54–57%, our picks 38–46%, average stock 31.5%. Read with care: this mostly reflects picking jumpier stocks,
  which also fall further; it did not turn into wins or excess.

## Winners vs losers inside twin sets (A3; K=100, HOLD_10)
5,912 items tested; 4,693 BH q<0.05 in 2020–22 and 3,812 repeat in 2023–24. These are DESCRIPTIVE ONLY: winners differ from losers mainly
by being more volatile (bigger gaps, deeper 25-day drawdowns, larger ATR, further from 50-day low), which also predicts bigger losses.
p-values treat each pick as independent while twin sets overlap heavily, so they are overstated. Not a buy rule; untested as one.
Luck family: 14,075 + 312 + 5,912 = 20,299.

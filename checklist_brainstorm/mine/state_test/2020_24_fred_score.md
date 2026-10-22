# FRED market-wide rows (New Bot `JA_FRED_MKT`) — 2020–24 score
Built 2026-10-22 HKT. Data: 1,258 sessions 2020-01-02..2024-12-31 only; nothing >= 2025-01-01 read (price reads filtered < 2025; last ~6 sessions of 2024 have no forward return and drop out).
Method: per date, IWM open[t+1] → open[t+6] minus 20 bp round trip (10 bp/side). Edge = mean(YES dates) − mean(other ready dates). 95% CI from a 5-day moving-block bootstrap over dates (2,000 draws); the p-value comes from the same draws. Each side needs ≥30 dates. Secondary: equal-weight mean of non-fund stocks (survivor universe; funds = Finviz Industry starting with ETF / Closed-End Fund / Shell Companies; returns clipped at ±50%), same fee.

## Multiple testing
- 52 ids × 2 sides = 104 tests; 54 fail the ≥30-date rule (27 ids: the rare FOMC/calendar labels and most MAC-JA-36x–39x BUT rows have 2–26 YES dates). **50 tested.**
- Every date is ready, so the NO side is just the YES side with the sign flipped. That leaves **25 independent tests**, and MAC-JA-318-BUT is identical to MAC-JA-318 (the BUT condition is neutralized at market level). In practice that is about 24.
- CI excluding 0: **6 of 50** on IWM and 6 of 50 on EW. That is **3 distinct signals out of 25, against 1.25 expected by chance** (2.5 of 50).
- **Benjamini–Hochberg q=0.05: 0 survivors** on IWM and on EW. The smallest p is about 0.012–0.024, and BH needs about 0.002.

## Nominal hits (none pass BH)
| row | meaning | YES dates | IWM edge | 95% CI | EW edge (CI) | per-year IWM edge 2020/21/22/23/24 (YES n) |
|---|---|---|---|---|---|---|
| CAL-JA-097 | last FOMC decision within 5 sessions was a hold | 125 | +0.93% | [+0.15, +1.78] | +0.80% [+0.01, +1.62] | +0.90(35) / +0.86(40) / +1.67(5) / +0.05(20) / +1.10(25) |
| MAC-JA-318 (=318-BUT) | copper 5d >+2% and 10y 5d < −5bp | 92 | +1.00% | [+0.20, +1.84] | +1.00% [+0.18, +1.86] | +1.53(13) / +0.81(10) / +0.79(28) / +1.36(26) / +1.07(15) |
The NO sides are the same numbers with the sign flipped.

Read: both are positive in all 5 years, which is encouraging. They still don't clear multiple testing, and per-year YES counts are small (5–40). 097 rests on only ~8 FOMC meetings a year, so its dates are clustered. Treat both as candidates for the single blind check, not as confirmed.
Full table: 2020_24_fred_score.csv (status=too_few rows carry counts only).

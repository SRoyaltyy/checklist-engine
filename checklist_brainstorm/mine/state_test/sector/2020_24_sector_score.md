# Sector ETF effect test, 2020-24 only (2025-26 untouched)
Universe: survivors, close>=$2, funds excluded, 2,084,489 max obs; sector = Finviz snap 2026-09-29 mapped to SPDR (XLK..XLC). ETF prices: yfinance adj close, 2019-2024 (asserted <2025).
Signals at close D, enter D+1 open, exit D+1+h open. 30bp/side (0.6% round trip). Matched control = same date x price quintile x ATR% quintile x prior-1d decile.
CI = 1000x date-clustered bootstrap. BH over all 36 trials. Pass = BH & CI clears 0 & win after fee >50% & mean after fee >0 & >=4/5 years same sign.

## Result: 0 of 36 trials pass (bullish or bearish).
Sector effects are real but tiny: +/-0.1 to 0.65% vs matched peers, smaller than the 0.6% round-trip fee. Win rates after fees 43-52%.
Clearest (BH sig, consistent): sector below 50d MA -> stock lags peers -0.33% (5d, all 5 years); stock laggard vs own sector -> mean-reverts +0.19% (5d, 5/5 yrs); stock >10% ahead of sector -> lags -0.65% (20d, 4/5 yrs). Note: 'catch-up' and 'relative strength' behave as mean reversion, not momentum.
Caveats: sector label is 2026 snapshot (static); signals are sector-wide so match control compares within date.

Values in %:

| row                                     |   h |   n_obs | side   |   resid |   boot_lo |   boot_hi |   win_after_fee |   raw_mean_after_fee | signs   | bh    | pass   |
|:----------------------------------------|----:|--------:|:-------|--------:|----------:|----------:|----------------:|---------------------:|:--------|:------|:-------|
| SEC5d-top2of11                          |   5 |  843823 | long   |    0.1  |      0.01 |      0.19 |            44.7 |                -0.32 | +++++   | True  | False  |
| SEC5d-top2of11                          |  20 |  830683 | long   |    0.24 |      0.05 |      0.43 |            47.1 |                -0.1  | +++++   | True  | False  |
| SEC5d-bottom2of11                       |   5 |  832533 | short  |   -0.07 |     -0.15 |      0.01 |            45.9 |                -0.62 | --+-+   | False | False  |
| SEC5d-bottom2of11                       |  20 |  825147 | short  |   -0.1  |     -0.27 |      0.09 |            48.9 |                -0.55 | -++--   | False | False  |
| SEC20d-top2of11                         |   5 |  868656 | long   |    0.13 |      0.05 |      0.21 |            44.6 |                -0.26 | +++++   | True  | False  |
| SEC20d-top2of11                         |  20 |  856224 | long   |    0.19 |      0.04 |      0.35 |            48.2 |                 0.47 | +--++   | True  | False  |
| SEC20d-bottom2of11                      |   5 |  807428 | short  |   -0.1  |     -0.19 |     -0.02 |            46   |                -0.55 | --+--   | True  | False  |
| SEC20d-bottom2of11                      |  20 |  794652 | short  |   -0.48 |     -0.65 |     -0.31 |            49.8 |                -0.32 | -++--   | True  | False  |
| SEC5d>+3%                               |   5 |  657587 | long   |    0.14 |     -0    |      0.27 |            44.8 |                -0.27 | -++-+   | False | False  |
| SEC5d>+3%                               |  20 |  653116 | long   |    0.29 |     -0.02 |      0.58 |            48.2 |                 0.33 | ++-++   | False | False  |
| SEC5d<-3%                               |   5 |  445926 | long   |    0.1  |     -0.07 |      0.26 |            46.8 |                -0.12 | --+++   | False | False  |
| SEC5d<-3%                               |  20 |  432722 | long   |    0.04 |     -0.29 |      0.41 |            49.3 |                 0.46 | -++++   | False | False  |
| SEC20d>+5%                              |   5 | 1058500 | long   |    0.11 |      0    |      0.22 |            44.5 |                -0.28 | +--++   | False | False  |
| SEC20d>+5%                              |  20 | 1043729 | short  |   -0.06 |     -0.24 |      0.13 |            49.1 |                -0.65 | +--++   | False | False  |
| SEC20d<-5%                              |   5 |  462697 | long   |    0.09 |     -0.14 |      0.37 |            47.5 |                -0.34 | --+++   | False | False  |
| SEC20d<-5%                              |  20 |  459361 | short  |   -0.15 |     -0.56 |      0.24 |            44.9 |                -1.29 | -++--   | False | False  |
| SEC-above50MA                           |   5 | 2084489 | long   |    0.11 |      0.02 |      0.21 |            43.7 |                -0.41 | +--++   | True  | False  |
| SEC-above50MA                           |  20 | 2048644 | long   |    0.35 |      0.14 |      0.58 |            46.8 |                -0.26 | +--++   | True  | False  |
| SEC-below50MA                           |   5 | 1351080 | short  |   -0.33 |     -0.49 |     -0.17 |            44.9 |                -0.58 | -----   | True  | False  |
| SEC-below50MA                           |  20 | 1320208 | short  |   -0.46 |     -0.77 |     -0.17 |            47.4 |                -0.8  | -+---   | True  | False  |
| SEC20d-beats-SPY>3%                     |   5 |  841232 | long   |    0.01 |     -0.08 |      0.1  |            45.5 |                -0.35 | -+-++   | False | False  |
| SEC20d-beats-SPY>3%                     |  20 |  831771 | short  |   -0.04 |     -0.21 |      0.14 |            46.2 |                -1.54 | +--++   | False | False  |
| SEC20d-lags-SPY>3%                      |   5 |  932570 | short  |   -0.17 |     -0.26 |     -0.09 |            44.7 |                -0.84 | --+--   | True  | False  |
| SEC20d-lags-SPY>3%                      |  20 |  902636 | short  |   -0.52 |     -0.72 |     -0.33 |            46.8 |                -1.34 | -++--   | True  | False  |
| CATCHUP-sec>50MA&up20d&stock-lags>5%    |   5 |  982319 | long   |    0.03 |     -0.03 |      0.09 |            43.2 |                -0.47 | ++-++   | False | False  |
| CATCHUP-sec>50MA&up20d&stock-lags>5%    |  20 |  971009 | long   |    0.06 |     -0.04 |      0.17 |            44.2 |                -1.01 | +-++-   | False | False  |
| CATCHUP-strict-sec20d>5%&stock-lags>10% |   5 |  268125 | long   |    0.11 |      0.01 |      0.21 |            44.5 |                -0.1  | ++-++   | False | False  |
| CATCHUP-strict-sec20d>5%&stock-lags>10% |  20 |  263677 | long   |    0.02 |     -0.14 |      0.2  |            43.5 |                -1.1  | +-+-+   | False | False  |
| RS-stock-beats-sec20d>10%               |   5 |  779296 | short  |   -0.18 |     -0.26 |     -0.11 |            48.3 |                -0.69 | ----+   | True  | False  |
| RS-stock-beats-sec20d>10%               |  20 |  765838 | short  |   -0.64 |     -0.77 |     -0.52 |            50.8 |                -0.98 | ----+   | True  | False  |
| RS-stock-lags-sec20d>10%                |   5 |  995286 | long   |    0.19 |      0.09 |      0.29 |            44.2 |                -0.46 | +++++   | True  | False  |
| RS-stock-lags-sec20d>10%                |  20 |  981563 | long   |    0.41 |      0.28 |      0.54 |            44.3 |                -0.87 | +-++-   | True  | False  |
| RS-leader-in-up-sector                  |   5 |  510212 | short  |   -0.06 |     -0.17 |      0.03 |            48.8 |                -0.85 | ----+   | False | False  |
| RS-leader-in-up-sector                  |  20 |  502802 | short  |   -0.36 |     -0.52 |     -0.2  |            51.5 |                -1.14 | ----+   | True  | False  |
| RS-laggard-in-down-sector               |   5 |  344649 | long   |    0.32 |      0.1  |      0.56 |            46.1 |                -0.3  | ++++-   | True  | False  |
| RS-laggard-in-down-sector               |  20 |  338767 | long   |    0.66 |      0.35 |      0.95 |            46.6 |                 0.17 | ++++-   | True  | False  |

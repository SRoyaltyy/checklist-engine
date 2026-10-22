# ARQT / NFLX case study + 2020-24 base rate
Data: yfinance daily (ARQT, NFLX), single-ticker illustration only. No 2025-26 aggregates.
Base rate: 2020-24 feat.parquet only (asserted < 2025-01-01). r20 = next-open entry, 20d hold, gross; fee 0.6% round trip.
Files: ARQT_features.csv, NFLX_features.csv, feats.py, base_rate.py, base_rate_2020_24.csv
Key: ARQT Oct 6-7 = pullback (5d -9..-11%, RSI 40-42, MFI 17-27, ext20 -5..-6%, RVOL 0.7-1.05). No bullish signal fired.
Neighbours (n=6,596, 2,470 tickers): 5.5% hit >=+20% in 20d, 46% fell, 12% fell >=10%. Mean +1.1% after fee, median +0.2%, vs control +0.5% mean / +0.07% median.

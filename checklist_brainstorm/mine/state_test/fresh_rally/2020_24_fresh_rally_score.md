# Fresh Clean Rally screen, 2020-24 only (2025-26 sealed / untouched)

Script: `fresh_rally/score.py` sha256 `410991ac8a87ee6cdb0be8c2571335b018f3a774ad531e120961b09d77a24ff0`. Source: existing `ohlcv/feat.parquet` + local `pricehist/universe_2020_survivors.parquet` (open/high/low only; no download). Asserted date max < 2025-01-01.
Universe: survivors, close≥$2, funds already excluded in feat, ~5.04M stock-days, 4,783 tickers.
Trade: signal at close D → enter open D+1, exit open D+1+h (h=5 or 20). Fee 30bp/side (0.6% round trip). Dividends already in feat returns.
Matched control: same date × price quintile × ATR% quintile × prior-1d decile. Residual = stock return − cell mean.
CI: 1000× date-clustered bootstrap. BH q=0.05 over all tested trials. Pass = BH & CI clears 0 & win after fee >50% & mean after fee >0 & ≥4/5 years same sign.

## Signal definition (at close D, no lookahead)
- **Good green:red (N∈{3,5,8}):** body-green days (close>open) / N ≥ 0.7 AND sum of up close-to-close moves ≥ 2× sum of down moves AND N-day run > 0.
- **Little pushback:** N-day run > 0.5%, max single-day drop ≤ ⅓ of run, and (min close / max close − 1) over the window ≤ ⅓ of run in magnitude.
- **Not overbought:** RSI(14) ≤ 70 AND MFI ≤ 80 AND close ≤ 10% above 20d MA (`ext20`≤0.10).
- **Fresh / not aged:** trailing body-green streak length ∈ [2,5] (not a 20+ day aged rally).
- **Optional prior quiet:** 5d return ending the day before the streak started ≤ 0.
Ablations drop one piece at a time on N=5, plus piece-alone and pairwise, plus freshness / green / pushback variants.

## Plain answer: **0 of 48 trials pass** Manager's bar.

The "obviously bullish" fresh clean rally **does not clear the bar as a long**. Most FULL and ablation rows land on the **short** side of the matched residual: after a clean recent green streak that is not overbought, the stock tends to **lag** similar stocks over the next 5–20 days. The lag is real in places (BH on several ablations) but **too small to beat the 0.6% fee** — win rates after fees sit around 41–50%.

### What the pieces do
- **Full combo (N=3 / N=5 / N=8):** none pass. N=3 and N=5 lean short (underperform peers). N=8 is rare (~300 obs) and noisy long — CI includes 0, not BH.
- **Prior quiet** before the streak: does not rescue the long; still fails.
- **Drop "not overbought"** (allow RSI>70 / MFI>80 / ext20>10%): short residual strengthens and is BH-significant (about −0.8% / −1.3% at 5d/20d), but short win after fee is still ~46–49%. So the clean rally that *is* overbought mean-reverts harder — consistent with prior OB findings — still not a trade after fees.
- **Green+Push only (no OB / freshness filters):** clearest short residual (−0.7% / −1.2%), BH, but win after fee 45.7% / 49.7% — closest at 20d, still under 50%.
- **"Not overbought" alone:** tiny long residual (+0.12% / +0.46%) BH and 5/5 years at 20d, but it fires on ~85% of the universe, so yes-rate is huge and fee still eats the edge (win ~44–47%).
- **Green alone / Fresh alone / Green+Fresh:** short residual BH; fee wins ~45–48%.

### Why the "obvious" long is missing
A clean, recent, not-overbought green streak is already partly priced: matched peers with the same price / vol / prior-day bucket do about as well or better. What edge exists is **mean reversion after the clean push** (especially once you allow overbought), not continuation. That matches the earlier OHLCV score where overbought / extension warnings leaned short and oversold leaned long — the "bullish looking" tape is closer to late-rally than early-trend once you condition properly.

Caveats: body-green uses close>open (same as feat `g10`); survivors-only; static 2026 industry filter already applied upstream; N=8 FULL is thin.

Values: resid/boot/raw in decimal (×100 for %); win_after_fee as fraction.

| row | h | n_obs | n_dates | side | resid | boot_lo | boot_hi | win_after_fee | raw_mean_after_fee | signs | bh | pass | yes_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FULL-N3 | 5 | 28488 | 1222 | short | -0.00055 | -0.00186 | 0.00092 | 0.4535 | -0.00596 | -++-- | False | False | 0.0057 |
| FULL-N3 | 20 | 28316 | 1206 | short | -0.00076 | -0.00317 | 0.00160 | 0.4714 | -0.01018 | ----+ | False | False | 0.0057 |
| FULL-N3+priorQuiet | 5 | 20882 | 1199 | short | -0.00060 | -0.00225 | 0.00093 | 0.4596 | -0.00553 | -++-+ | False | False | 0.0042 |
| FULL-N3+priorQuiet | 20 | 20768 | 1183 | short | -0.00035 | -0.00292 | 0.00243 | 0.4739 | -0.01026 | --+-+ | False | False | 0.0042 |
| FULL-N5 | 5 | 2830 | 817 | short | -0.00139 | -0.00446 | 0.00167 | 0.4148 | -0.00812 | -+--+ | False | False | 0.0006 |
| FULL-N5 | 20 | 2815 | 806 | short | -0.00511 | -0.01100 | 0.00050 | 0.4519 | -0.01375 | ----- | False | False | 0.0006 |
| FULL-N5+priorQuiet | 5 | 831 | 436 | short | -0.00216 | -0.00752 | 0.00335 | 0.4116 | -0.00831 | -+-+- | False | False | 0.0002 |
| FULL-N5+priorQuiet | 20 | 830 | 435 | short | -0.00362 | -0.01410 | 0.00714 | 0.4602 | -0.01703 | -+--- | False | False | 0.0002 |
| ABL-dropGreen-N5 | 5 | 4019 | 928 | short | -0.00228 | -0.00502 | 0.00052 | 0.4257 | -0.00721 | ----- | False | False | 0.0008 |
| ABL-dropGreen-N5 | 20 | 3994 | 915 | short | -0.00532 | -0.01057 | -0.00034 | 0.4584 | -0.01195 | ----- | False | False | 0.0008 |
| ABL-dropPush-N5 | 5 | 211266 | 1233 | short | -0.00052 | -0.00100 | -0.00000 | 0.4521 | -0.00512 | -+-+- | False | False | 0.0424 |
| ABL-dropPush-N5 | 20 | 210242 | 1218 | short | -0.00032 | -0.00129 | 0.00071 | 0.4682 | -0.01003 | ---+- | False | False | 0.0424 |
| ABL-dropNotOB-N5 | 5 | 5247 | 1079 | short | -0.00814 | -0.01178 | -0.00431 | 0.4565 | 0.00008 | ----- | True | False | 0.0010 |
| ABL-dropNotOB-N5 | 20 | 5192 | 1065 | short | -0.01293 | -0.01951 | -0.00587 | 0.4917 | -0.00025 | ----- | True | False | 0.0010 |
| ABL-dropFresh-N5 | 5 | 5611 | 1026 | short | -0.00158 | -0.00397 | 0.00074 | 0.4170 | -0.00825 | -+--+ | False | False | 0.0011 |
| ABL-dropFresh-N5 | 20 | 5572 | 1013 | short | -0.00410 | -0.00883 | 0.00050 | 0.4612 | -0.01097 | ----- | False | False | 0.0011 |
| ABL-onlyGreen-N5 | 5 | 574699 | 1238 | short | -0.00137 | -0.00191 | -0.00084 | 0.4598 | -0.00495 | ----- | True | False | 0.1151 |
| ABL-onlyGreen-N5 | 20 | 570970 | 1223 | short | -0.00232 | -0.00321 | -0.00133 | 0.4833 | -0.00757 | ----+ | True | False | 0.1151 |
| ABL-onlyPush-N5 | 5 | 34675 | 1237 | short | -0.00560 | -0.00726 | -0.00391 | 0.4527 | -0.00298 | ----- | True | False | 0.0069 |
| ABL-onlyPush-N5 | 20 | 34238 | 1222 | short | -0.00936 | -0.01223 | -0.00620 | 0.4816 | -0.00421 | ----- | True | False | 0.0069 |
| ABL-onlyNotOB | 5 | 3083885 | 1233 | long | 0.00118 | 0.00048 | 0.00189 | 0.4381 | -0.00427 | ++++- | True | False | 0.8516 |
| ABL-onlyNotOB | 20 | 3038544 | 1218 | long | 0.00462 | 0.00341 | 0.00573 | 0.4651 | -0.00191 | +++++ | True | False | 0.8516 |
| ABL-onlyFresh | 5 | 1029735 | 1238 | short | -0.00114 | -0.00161 | -0.00068 | 0.4632 | -0.00528 | ----+ | True | False | 0.2077 |
| ABL-onlyFresh | 20 | 1020432 | 1223 | short | -0.00124 | -0.00218 | -0.00029 | 0.4816 | -0.00884 | ----+ | True | False | 0.2077 |
| ABL-Green+Fresh-N5 | 5 | 336400 | 1238 | short | -0.00132 | -0.00183 | -0.00078 | 0.4668 | -0.00405 | ----- | True | False | 0.0674 |
| ABL-Green+Fresh-N5 | 20 | 334193 | 1223 | short | -0.00223 | -0.00323 | -0.00116 | 0.4847 | -0.00728 | ----+ | True | False | 0.0674 |
| ABL-Green+NotOB-N5 | 5 | 357963 | 1233 | short | -0.00037 | -0.00083 | 0.00010 | 0.4446 | -0.00618 | -+-+- | False | False | 0.0718 |
| ABL-Green+NotOB-N5 | 20 | 356215 | 1218 | short | -0.00020 | -0.00107 | 0.00066 | 0.4668 | -0.01032 | --++- | False | False | 0.0718 |
| ABL-Green+Push-N5 | 5 | 10276 | 1186 | short | -0.00705 | -0.00981 | -0.00438 | 0.4572 | -0.00146 | ----- | True | False | 0.0021 |
| ABL-Green+Push-N5 | 20 | 10161 | 1171 | short | -0.01241 | -0.01700 | -0.00764 | 0.4972 | 0.00146 | ----- | True | False | 0.0021 |
| ABL-NotOB+Fresh | 5 | 802522 | 1233 | short | -0.00064 | -0.00108 | -0.00013 | 0.4552 | -0.00581 | ----- | True | False | 0.1615 |
| ABL-NotOB+Fresh | 20 | 795840 | 1218 | long | 0.00030 | -0.00056 | 0.00116 | 0.4770 | -0.00139 | --+++ | False | False | 0.1615 |
| FULL-N5-fresh2to3 | 5 | 2258 | 740 | short | -0.00160 | -0.00511 | 0.00185 | 0.4150 | -0.00792 | -+--+ | False | False | 0.0004 |
| FULL-N5-fresh2to3 | 20 | 2243 | 729 | short | -0.00487 | -0.01180 | 0.00224 | 0.4512 | -0.01367 | ---+- | False | False | 0.0004 |
| FULL-N5-fresh4to5 | 5 | 572 | 345 | short | -0.00055 | -0.00624 | 0.00548 | 0.4143 | -0.00891 | ---+- | False | False | 0.0001 |
| FULL-N5-fresh4to5 | 20 | 572 | 345 | short | -0.00599 | -0.01655 | 0.00561 | 0.4546 | -0.01406 | -+--- | False | False | 0.0001 |
| FULL-N5-fresh2to8 | 5 | 3182 | 853 | short | -0.00158 | -0.00474 | 0.00105 | 0.4180 | -0.00807 | -+--+ | False | False | 0.0006 |
| FULL-N5-fresh2to8 | 20 | 3164 | 842 | short | -0.00525 | -0.01131 | 0.00044 | 0.4545 | -0.01278 | ----- | False | False | 0.0006 |
| FULL-N5-gratio0.8 | 5 | 2830 | 817 | short | -0.00139 | -0.00446 | 0.00167 | 0.4148 | -0.00812 | -+--+ | False | False | 0.0006 |
| FULL-N5-gratio0.8 | 20 | 2815 | 806 | short | -0.00511 | -0.01100 | 0.00050 | 0.4519 | -0.01375 | ----- | False | False | 0.0006 |
| FULL-N5-mag3x | 5 | 2821 | 817 | short | -0.00138 | -0.00448 | 0.00162 | 0.4144 | -0.00813 | -+--+ | False | False | 0.0006 |
| FULL-N5-mag3x | 20 | 2806 | 806 | short | -0.00528 | -0.01107 | 0.00047 | 0.4519 | -0.01355 | ----- | False | False | 0.0006 |
| FULL-N5-pushHalf | 5 | 13792 | 1152 | short | -0.00026 | -0.00213 | 0.00157 | 0.4342 | -0.00715 | -+-++ | False | False | 0.0028 |
| FULL-N5-pushHalf | 20 | 13717 | 1138 | short | -0.00248 | -0.00546 | 0.00063 | 0.4617 | -0.01026 | ---++ | False | False | 0.0028 |
| FULL-N8 | 5 | 302 | 210 | long | 0.00775 | -0.00181 | 0.01734 | 0.4967 | 0.00181 | ++-++ | False | False | 0.0001 |
| FULL-N8 | 20 | 299 | 207 | long | 0.00629 | -0.00907 | 0.02151 | 0.5017 | 0.00225 | ++--+ | False | False | 0.0001 |
| FULL-N8+priorQuiet | 5 | 52 | 44 | long | 0.01171 | -0.01543 | 0.04399 | 0.4038 | 0.00043 | ++-+- | False | False | 0.0000 |
| FULL-N8+priorQuiet | 20 | 52 | 44 | short | -0.02297 | -0.07383 | 0.01892 | 0.5192 | 0.02046 | -+--- | False | False | 0.0000 |

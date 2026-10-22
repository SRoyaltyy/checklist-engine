# NB v2 matched-control test, 2020–24 (Taskforce)

Script: state_test/nbv2/matched_nbv2.py (new; locked files untouched). Dates 2020-01-02..2024-12-20 only; every chunk was checked to end before 2025-01-01. No 2025–26 file read.

## (1) Entry timing
- NB/NBX definition (nb_year.py / nbx_year.py docstrings and chunk json): the answer for session D uses only bars dated < D (bar = D−1). Halts = Nasdaq halt records dated D−1. Reg SHO = Nasdaq threshold file dated D−1. FINRA = CNMS file dated D−1, published that evening. So the answer is known before D's open.
- The v2 score (and the "as scored" rows below) used **entry = open of D+1, exit = open of D+6** (`o.shift(-1)` / `o.shift(-6)` on row D). That is one session later than needed. It can't leak, and it skips session D.
- Variant "open D" = entry at D's open, exit at D+5's open. Its results match the D+1 entry closely, so no same-day leak shows and the delay costs little.
- Matching features use only data known before entry: through close D for the D+1 entry, through close D−1 for the D-open entry.

## (2)/(3) Controls
- Each YES stock-day is compared with ready-NO stock-days on the same date, in the same bucket of prior-1-day return (20 per-date quantiles) or, as a second version, prior-5-day return (20 quantiles), and in the same 20-day dollar-volume tercile. There is no point-in-time market cap in the files, so dollar volume stands in for it.
- The residual is YES return minus the cell's control mean. CIs are clustered by date. L5 = top bullish fifth (lean ≥ 0.6205).
- NB-056: YES and control are both restricted to current Finviz Exchange = NASD. Its answers are only ready for NASD anyway.
- Caveat: survivor-only price universe. 5-day holds overlap. NB-015 (distance from close up to the next whole dollar, in ATR units, then ranked) may partly proxy for price level or volatility, which the dollar-volume tercile only partly controls.

| id                        | entry                | control             | scope   |    resid |     lo95 |     hi95 |   n_dates |   n_obs | signs   | nasdaq_only   |
|:--------------------------|:---------------------|:--------------------|:--------|---------:|---------:|---------:|----------:|--------:|:--------|:--------------|
| nb4-PDS-NB-039-W0-EVT     | open D+1 (as scored) | raw same-date       | all     | -0.03051 | -0.03866 | -0.02237 |      1212 |    8284 | -----   | False         |
| nb4-PDS-NB-039-W0-EVT     | open D+1 (as scored) | raw same-date       | L5      | -0.04825 | -0.06066 | -0.03584 |       834 |    2118 | -----   | False         |
| nb4-PDS-NB-039-W0-EVT     | open D+1 (as scored) | match r1x20 + dvol3 | all     | -0.02821 | -0.03547 | -0.02094 |      1206 |    8013 | -----   | False         |
| nb4-PDS-NB-039-W0-EVT     | open D+1 (as scored) | match r1x20 + dvol3 | L5      | -0.04519 | -0.0576  | -0.03278 |       825 |    2069 | -----   | False         |
| nb4-PDS-NB-039-W0-EVT     | open D+1 (as scored) | match r5x20 + dvol3 | all     | -0.03094 | -0.03698 | -0.02489 |      1206 |    8013 | -----   | False         |
| nb4-PDS-NB-039-W0-EVT     | open D+1 (as scored) | match r5x20 + dvol3 | L5      | -0.04444 | -0.05695 | -0.03193 |       825 |    2069 | -----   | False         |
| nb4-PDS-NB-039-W0-EVT     | open D (variant)     | raw same-date       | all     | -0.04047 | -0.05121 | -0.02974 |      1213 |    8300 | -----   | False         |
| nb4-PDS-NB-039-W0-EVT     | open D (variant)     | raw same-date       | L5      | -0.06314 | -0.07734 | -0.04893 |       838 |    2118 | -----   | False         |
| nb4-PDS-NB-039-W0-EVT     | open D (variant)     | match r1x20 + dvol3 | all     | -0.0388  | -0.04693 | -0.03067 |      1206 |    8004 | -----   | False         |
| nb4-PDS-NB-039-W0-EVT     | open D (variant)     | match r1x20 + dvol3 | L5      | -0.05813 | -0.07246 | -0.04381 |       827 |    2062 | -----   | False         |
| nb4-PDS-NB-039-W0-EVT     | open D (variant)     | match r5x20 + dvol3 | all     | -0.04257 | -0.04968 | -0.03547 |      1206 |    8004 | -----   | False         |
| nb4-PDS-NB-039-W0-EVT     | open D (variant)     | match r5x20 + dvol3 | L5      | -0.05985 | -0.07413 | -0.04556 |       827 |    2062 | -----   | False         |
| nb4-PDS-NB-039-T20-CNT    | open D+1 (as scored) | raw same-date       | all     | -0.02486 | -0.03018 | -0.01954 |      1135 |   19545 | +----   | False         |
| nb4-PDS-NB-039-T20-CNT    | open D+1 (as scored) | raw same-date       | L5      | -0.03942 | -0.04954 | -0.02929 |       826 |    2975 | -----   | False         |
| nb4-PDS-NB-039-T20-CNT    | open D+1 (as scored) | match r1x20 + dvol3 | all     | -0.02477 | -0.02954 | -0.02    |      1135 |   19545 | -----   | False         |
| nb4-PDS-NB-039-T20-CNT    | open D+1 (as scored) | match r1x20 + dvol3 | L5      | -0.03769 | -0.04753 | -0.02785 |       826 |    2975 | -----   | False         |
| nb4-PDS-NB-039-T20-CNT    | open D+1 (as scored) | match r5x20 + dvol3 | all     | -0.02528 | -0.02959 | -0.02096 |      1135 |   19545 | -----   | False         |
| nb4-PDS-NB-039-T20-CNT    | open D+1 (as scored) | match r5x20 + dvol3 | L5      | -0.03607 | -0.04598 | -0.02615 |       826 |    2975 | -----   | False         |
| nb4-PDS-NB-039-T20-CNT    | open D (variant)     | raw same-date       | all     | -0.02694 | -0.03247 | -0.0214  |      1136 |   19591 | +----   | False         |
| nb4-PDS-NB-039-T20-CNT    | open D (variant)     | raw same-date       | L5      | -0.04492 | -0.05525 | -0.03459 |       825 |    2975 | -----   | False         |
| nb4-PDS-NB-039-T20-CNT    | open D (variant)     | match r1x20 + dvol3 | all     | -0.02659 | -0.03163 | -0.02155 |      1136 |   19591 | -----   | False         |
| nb4-PDS-NB-039-T20-CNT    | open D (variant)     | match r1x20 + dvol3 | L5      | -0.04214 | -0.05222 | -0.03206 |       825 |    2975 | -----   | False         |
| nb4-PDS-NB-039-T20-CNT    | open D (variant)     | match r5x20 + dvol3 | all     | -0.02741 | -0.03197 | -0.02285 |      1136 |   19591 | -----   | False         |
| nb4-PDS-NB-039-T20-CNT    | open D (variant)     | match r5x20 + dvol3 | L5      | -0.04201 | -0.0522  | -0.03183 |       825 |    2975 | -----   | False         |
| nb4-PDS-NB-039-T20-EXT    | open D+1 (as scored) | raw same-date       | all     | -0.0109  | -0.01286 | -0.00893 |       886 |   54691 | .----   | False         |
| nb4-PDS-NB-039-T20-EXT    | open D+1 (as scored) | raw same-date       | L5      | -0.01373 | -0.01781 | -0.00965 |       834 |    9393 | .----   | False         |
| nb4-PDS-NB-039-T20-EXT    | open D+1 (as scored) | match r1x20 + dvol3 | all     | -0.01043 | -0.01214 | -0.00872 |       886 |   54691 | .----   | False         |
| nb4-PDS-NB-039-T20-EXT    | open D+1 (as scored) | match r1x20 + dvol3 | L5      | -0.01334 | -0.01732 | -0.00937 |       834 |    9393 | .----   | False         |
| nb4-PDS-NB-039-T20-EXT    | open D+1 (as scored) | match r5x20 + dvol3 | all     | -0.01059 | -0.01227 | -0.00892 |       886 |   54691 | .----   | False         |
| nb4-PDS-NB-039-T20-EXT    | open D+1 (as scored) | match r5x20 + dvol3 | L5      | -0.01335 | -0.01736 | -0.00934 |       834 |    9393 | .----   | False         |
| nb4-PDS-NB-039-T20-EXT    | open D (variant)     | raw same-date       | all     | -0.01238 | -0.01436 | -0.01039 |       887 |   54815 | .----   | False         |
| nb4-PDS-NB-039-T20-EXT    | open D (variant)     | raw same-date       | L5      | -0.01456 | -0.01869 | -0.01043 |       835 |    9400 | .----   | False         |
| nb4-PDS-NB-039-T20-EXT    | open D (variant)     | match r1x20 + dvol3 | all     | -0.01193 | -0.01365 | -0.01021 |       887 |   54815 | .----   | False         |
| nb4-PDS-NB-039-T20-EXT    | open D (variant)     | match r1x20 + dvol3 | L5      | -0.01353 | -0.01764 | -0.00942 |       835 |    9400 | .----   | False         |
| nb4-PDS-NB-039-T20-EXT    | open D (variant)     | match r5x20 + dvol3 | all     | -0.0122  | -0.0139  | -0.0105  |       887 |   54815 | .----   | False         |
| nb4-PDS-NB-039-T20-EXT    | open D (variant)     | match r5x20 + dvol3 | L5      | -0.01431 | -0.01838 | -0.01024 |       835 |    9400 | .----   | False         |
| nb4-BRW-NB-056-W0-EVT     | open D+1 (as scored) | raw same-date       | all     | -0.02491 | -0.02961 | -0.02021 |      1245 |   10257 | -+---   | True          |
| nb4-BRW-NB-056-W0-EVT     | open D+1 (as scored) | raw same-date       | L5      | -0.02286 | -0.03595 | -0.00978 |       667 |    1443 | ++---   | True          |
| nb4-BRW-NB-056-W0-EVT     | open D+1 (as scored) | match r1x20 + dvol3 | all     | -0.02189 | -0.02649 | -0.01729 |      1239 |   10206 | -+---   | True          |
| nb4-BRW-NB-056-W0-EVT     | open D+1 (as scored) | match r1x20 + dvol3 | L5      | -0.01732 | -0.03028 | -0.00436 |       665 |    1432 | ++---   | True          |
| nb4-BRW-NB-056-W0-EVT     | open D+1 (as scored) | match r5x20 + dvol3 | all     | -0.02205 | -0.02664 | -0.01745 |      1239 |   10206 | -+---   | True          |
| nb4-BRW-NB-056-W0-EVT     | open D+1 (as scored) | match r5x20 + dvol3 | L5      | -0.01907 | -0.03184 | -0.0063  |       665 |    1432 | ++---   | True          |
| nb4-BRW-NB-056-W0-EVT     | open D (variant)     | raw same-date       | all     | -0.02683 | -0.0316  | -0.02206 |      1246 |   10279 | -+---   | True          |
| nb4-BRW-NB-056-W0-EVT     | open D (variant)     | raw same-date       | L5      | -0.02757 | -0.04123 | -0.01392 |       667 |    1444 | -+---   | True          |
| nb4-BRW-NB-056-W0-EVT     | open D (variant)     | match r1x20 + dvol3 | all     | -0.02367 | -0.02833 | -0.01902 |      1238 |   10195 | -+---   | True          |
| nb4-BRW-NB-056-W0-EVT     | open D (variant)     | match r1x20 + dvol3 | L5      | -0.02097 | -0.03443 | -0.00752 |       665 |    1430 | ++---   | True          |
| nb4-BRW-NB-056-W0-EVT     | open D (variant)     | match r5x20 + dvol3 | all     | -0.02383 | -0.0285  | -0.01916 |      1238 |   10195 | -+---   | True          |
| nb4-BRW-NB-056-W0-EVT     | open D (variant)     | match r5x20 + dvol3 | L5      | -0.02357 | -0.03701 | -0.01014 |       665 |    1430 | -+---   | True          |
| nb4-BRW-NB-056-T20-EXT    | open D+1 (as scored) | raw same-date       | all     | -0.02435 | -0.02868 | -0.02001 |       978 |   12582 | .----   | True          |
| nb4-BRW-NB-056-T20-EXT    | open D+1 (as scored) | raw same-date       | L5      | -0.01563 | -0.02703 | -0.00423 |       601 |    1567 | .+---   | True          |
| nb4-BRW-NB-056-T20-EXT    | open D+1 (as scored) | match r1x20 + dvol3 | all     | -0.02241 | -0.02657 | -0.01825 |       978 |   12582 | .----   | True          |
| nb4-BRW-NB-056-T20-EXT    | open D+1 (as scored) | match r1x20 + dvol3 | L5      | -0.0119  | -0.02312 | -0.00068 |       601 |    1567 | .+---   | True          |
| nb4-BRW-NB-056-T20-EXT    | open D+1 (as scored) | match r5x20 + dvol3 | all     | -0.02265 | -0.02679 | -0.01851 |       978 |   12582 | .----   | True          |
| nb4-BRW-NB-056-T20-EXT    | open D+1 (as scored) | match r5x20 + dvol3 | L5      | -0.01288 | -0.02396 | -0.00181 |       601 |    1567 | .+---   | True          |
| nb4-BRW-NB-056-T20-EXT    | open D (variant)     | raw same-date       | all     | -0.0254  | -0.02976 | -0.02105 |       979 |   12615 | .----   | True          |
| nb4-BRW-NB-056-T20-EXT    | open D (variant)     | raw same-date       | L5      | -0.01478 | -0.02647 | -0.0031  |       603 |    1568 | .+---   | True          |
| nb4-BRW-NB-056-T20-EXT    | open D (variant)     | match r1x20 + dvol3 | all     | -0.02355 | -0.02772 | -0.01938 |       979 |   12615 | .----   | True          |
| nb4-BRW-NB-056-T20-EXT    | open D (variant)     | match r1x20 + dvol3 | L5      | -0.01099 | -0.02253 |  0.00055 |       603 |    1568 | .+---   | True          |
| nb4-BRW-NB-056-T20-EXT    | open D (variant)     | match r5x20 + dvol3 | all     | -0.0238  | -0.02796 | -0.01964 |       979 |   12615 | .----   | True          |
| nb4-BRW-NB-056-T20-EXT    | open D (variant)     | match r5x20 + dvol3 | L5      | -0.0118  | -0.02321 | -0.00039 |       603 |    1568 | .+---   | True          |
| nb4-BRW-NB-056-T20-CNT    | open D+1 (as scored) | raw same-date       | all     | -0.01823 | -0.02174 | -0.01472 |      1231 |   22670 | ++---   | True          |
| nb4-BRW-NB-056-T20-CNT    | open D+1 (as scored) | raw same-date       | L5      | -0.00298 | -0.01235 |  0.00638 |       850 |    2817 | ++---   | True          |
| nb4-BRW-NB-056-T20-CNT    | open D+1 (as scored) | match r1x20 + dvol3 | all     | -0.01632 | -0.01963 | -0.01302 |      1231 |   22670 | ++---   | True          |
| nb4-BRW-NB-056-T20-CNT    | open D+1 (as scored) | match r1x20 + dvol3 | L5      |  0.00085 | -0.00818 |  0.00989 |       850 |    2817 | ++---   | True          |
| nb4-BRW-NB-056-T20-CNT    | open D+1 (as scored) | match r5x20 + dvol3 | all     | -0.01619 | -0.01947 | -0.01291 |      1231 |   22670 | ++---   | True          |
| nb4-BRW-NB-056-T20-CNT    | open D+1 (as scored) | match r5x20 + dvol3 | L5      |  0.00106 | -0.00791 |  0.01004 |       850 |    2817 | ++---   | True          |
| nb4-BRW-NB-056-T20-CNT    | open D (variant)     | raw same-date       | all     | -0.01849 | -0.02201 | -0.01497 |      1232 |   22721 | ++---   | True          |
| nb4-BRW-NB-056-T20-CNT    | open D (variant)     | raw same-date       | L5      | -0.00401 | -0.01323 |  0.00521 |       851 |    2818 | ++---   | True          |
| nb4-BRW-NB-056-T20-CNT    | open D (variant)     | match r1x20 + dvol3 | all     | -0.01656 | -0.01987 | -0.01324 |      1232 |   22721 | ++---   | True          |
| nb4-BRW-NB-056-T20-CNT    | open D (variant)     | match r1x20 + dvol3 | L5      |  0.00057 | -0.00836 |  0.00949 |       851 |    2818 | ++---   | True          |
| nb4-BRW-NB-056-T20-CNT    | open D (variant)     | match r5x20 + dvol3 | all     | -0.01644 | -0.01974 | -0.01315 |      1232 |   22721 | ++---   | True          |
| nb4-BRW-NB-056-T20-CNT    | open D (variant)     | match r5x20 + dvol3 | L5      | -1e-05   | -0.00896 |  0.00893 |       851 |    2818 | ++---   | True          |
| nb4-PDS-NB-015-T1-RNK     | open D+1 (as scored) | raw same-date       | all     | -0.00956 | -0.0106  | -0.00852 |      1237 |  449375 | -----   | False         |
| nb4-PDS-NB-015-T1-RNK     | open D+1 (as scored) | raw same-date       | L5      | -0.0065  | -0.00817 | -0.00483 |      1164 |   67774 | -----   | False         |
| nb4-PDS-NB-015-T1-RNK     | open D+1 (as scored) | match r1x20 + dvol3 | all     | -0.0101  | -0.01096 | -0.00923 |      1237 |  449375 | -----   | False         |
| nb4-PDS-NB-015-T1-RNK     | open D+1 (as scored) | match r1x20 + dvol3 | L5      | -0.00693 | -0.0084  | -0.00546 |      1164 |   67774 | -----   | False         |
| nb4-PDS-NB-015-T1-RNK     | open D+1 (as scored) | match r5x20 + dvol3 | all     | -0.01033 | -0.01117 | -0.00949 |      1237 |  449375 | -----   | False         |
| nb4-PDS-NB-015-T1-RNK     | open D+1 (as scored) | match r5x20 + dvol3 | L5      | -0.00608 | -0.00751 | -0.00465 |      1164 |   67774 | -----   | False         |
| nb4-PDS-NB-015-T1-RNK     | open D (variant)     | raw same-date       | all     | -0.00977 | -0.0108  | -0.00873 |      1238 |  449796 | -----   | False         |
| nb4-PDS-NB-015-T1-RNK     | open D (variant)     | raw same-date       | L5      | -0.00611 | -0.00792 | -0.00431 |      1165 |   67781 | -----   | False         |
| nb4-PDS-NB-015-T1-RNK     | open D (variant)     | match r1x20 + dvol3 | all     | -0.0103  | -0.01117 | -0.00943 |      1238 |  449796 | -----   | False         |
| nb4-PDS-NB-015-T1-RNK     | open D (variant)     | match r1x20 + dvol3 | L5      | -0.00565 | -0.00721 | -0.00408 |      1165 |   67781 | -----   | False         |
| nb4-PDS-NB-015-T1-RNK     | open D (variant)     | match r5x20 + dvol3 | all     | -0.01053 | -0.01137 | -0.00969 |      1238 |  449796 | -----   | False         |
| nb4-PDS-NB-015-T1-RNK     | open D (variant)     | match r5x20 + dvol3 | L5      | -0.00566 | -0.00719 | -0.00413 |      1165 |   67781 | -----   | False         |
| nb4-PDS-NB-015-T1-RNK-BUT | open D+1 (as scored) | raw same-date       | all     |  0.0075  |  0.00682 |  0.00818 |      1237 |  451306 | +++++   | False         |
| nb4-PDS-NB-015-T1-RNK-BUT | open D+1 (as scored) | raw same-date       | L5      |  0.00796 |  0.00678 |  0.00915 |      1163 |   71169 | +++++   | False         |
| nb4-PDS-NB-015-T1-RNK-BUT | open D+1 (as scored) | match r1x20 + dvol3 | all     |  0.00745 |  0.00696 |  0.00794 |      1237 |  451306 | +++++   | False         |
| nb4-PDS-NB-015-T1-RNK-BUT | open D+1 (as scored) | match r1x20 + dvol3 | L5      |  0.00687 |  0.00579 |  0.00795 |      1163 |   71169 | +++++   | False         |
| nb4-PDS-NB-015-T1-RNK-BUT | open D+1 (as scored) | match r5x20 + dvol3 | all     |  0.00759 |  0.00711 |  0.00807 |      1237 |  451306 | +++++   | False         |
| nb4-PDS-NB-015-T1-RNK-BUT | open D+1 (as scored) | match r5x20 + dvol3 | L5      |  0.00768 |  0.0066  |  0.00876 |      1163 |   71169 | +++++   | False         |
| nb4-PDS-NB-015-T1-RNK-BUT | open D (variant)     | raw same-date       | all     |  0.00759 |  0.00692 |  0.00827 |      1238 |  451734 | +++++   | False         |
| nb4-PDS-NB-015-T1-RNK-BUT | open D (variant)     | raw same-date       | L5      |  0.00801 |  0.00681 |  0.00922 |      1164 |   71172 | +++++   | False         |
| nb4-PDS-NB-015-T1-RNK-BUT | open D (variant)     | match r1x20 + dvol3 | all     |  0.00745 |  0.00697 |  0.00793 |      1238 |  451734 | +++++   | False         |
| nb4-PDS-NB-015-T1-RNK-BUT | open D (variant)     | match r1x20 + dvol3 | L5      |  0.00719 |  0.00608 |  0.00829 |      1164 |   71172 | +++++   | False         |
| nb4-PDS-NB-015-T1-RNK-BUT | open D (variant)     | match r5x20 + dvol3 | all     |  0.00761 |  0.00714 |  0.00809 |      1238 |  451734 | +++++   | False         |
| nb4-PDS-NB-015-T1-RNK-BUT | open D (variant)     | match r5x20 + dvol3 | L5      |  0.00737 |  0.00627 |  0.00846 |      1164 |   71172 | +++++   | False         |
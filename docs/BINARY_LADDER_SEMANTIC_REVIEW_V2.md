# Ladder semantic review, second batch

The unchanged source still contains 2,680 rows. This batch adds 12 verified
aliases to the first batch's four RSI aliases: 16 aliases, 2,664 canonical
ladders, 80 reviewed source declarations, and 2,600 still unreviewed.
The master has 65,540 rows, including the same 62,876 BOUND definitions.
Cross-ladder/master semantic review remains pending. This is a partial review,
not an executable-question or question-quality approval.

Each new pair is `Ixxx-L09 → Ixxx-L05`. The explicit default parameter
annotation and `[default]` select the same dictionary scalar on the last
completed daily candle. Comparator, threshold, missingness and PIT text match
exactly. Neither alternate settings nor multi-output names are normalized away.

| Item | Selected scalar | Registered default | Shared predicate |
| --- | --- | --- | --- |
| I028 Stochastic | slowK, explicitly dictionary output[0], not slowD | 14,3,3 | >80 |
| I029 Williams %R | %R | period 14 | >−20 |
| I036 CCI | CCI | period 20 | >100 |
| I037 CMO | CMO | period 14 | >50 |
| I043 Fisher | Fisher transform | period 9 | >1.5 |
| I048 Relative Vigor | relative vigor ratio | period 10 | >60 |
| I049 Relative Volatility Index | RSI on split stdev | stdev 10, RMA 14 | >60 |
| I051 SMI | dictionary's double-EMA scalar | range 10, smoothing 3,3 | >40 |
| I055 Ultimate Oscillator | weighted 4:2:1 composite | 7,14,28 | >70 |
| I056 Connors RSI | mean of the three dictionary components | 3,2,100 | >90 |
| I058 Choppiness | dictionary logarithmic scalar | period 14 | >61.8 |
| I084 MFI | money-flow index | period 14 | >80 |

`LADDER_SCALAR_REVIEW_V2.json` contains each reviewed scalar, default parameters,
verbatim dictionary definition and its SHA256. The review fails if the build
root's proof, dictionary definition, selected name or registered native default
changes. This is an explicit whitelist, not a generic annotation-stripping
rule. Signatures retain the selected scalar, parameter object, definition hash,
unit, endpoint, timeframe, comparator, literal threshold and NI/PIT policies.

I034 names ADX/+DI/−DI, I041 names Aroon Up/Down/Oscillator, and I052 names
StochRSI K/D without selecting an output. Their candidate pairs stay unreviewed
and separate. Stochastic I028 is different: its dictionary explicitly selects
slowK and excludes slowD, so its scalar identity is established.

I048 also needs a separate quality correction: its dictionary defines Relative
Vigor as an unscaled ratio, while its ladder uses 40/50/60 oscillator thresholds.
This batch proves that two copies of `>60` ask the same question; it does not
approve that threshold, rescale the ratio, or substitute Relative Volatility
Index I049. Those are distinct items and remain distinct signatures. No values
are measured here and no constant-question test is claimed.

All source IDs remain in the original source and the complete review map.
Canonical IDs are stable under source reordering. An authenticated comparison
with revision `1095a1aca85bd35f26837dfd49b35e1d26c543e3` requires every retained
row to match exactly, including all 62,876 BOUND rows; only these 12 source IDs
leave the canonical export. The ratio revision's separate historical proof is
pinned to its original package so later ladder work cannot silently change it.
CI regenerates and uploads the new package, maps and scalar proof.

The original [first-batch proof](BINARY_LADDER_SEMANTIC_REVIEW_V1.md) remains
historical evidence. DEFINE/CHART/DERIVE/mining gates remain pending.

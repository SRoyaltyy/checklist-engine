# James v5.5f polarity tags

File: `James-v5.5f-polarity.csv` (row_id, meaning, tag_reason), 7780 rows, 0 unclassified.
Tagged on question meaning only (variant, strict_definition, sheet's yes_means, lens, data_type) — never answers/returns.
Labels use the room's shared set: bullish, loud_bearish, quiet_warning, asterisk, neutral (renamed from bearish/warning).

## Counts: meaning x scope
```
scope          PER_STOCK  SECTOR  SHARED   All
meaning                                       
asterisk             313       0     112   425
bullish               28     218    3225  3471
loud_bearish          23     205    2889  3117
neutral                0       0      20    20
quiet_warning        412      11     324   747
All                  776     434    6570  7780
```

## Counts by reason
```
tag_reason
BUT snap-back twin = same outlier, direction flipped; plain read per yes_means    2340
sheet yes_means=Bullish, plain directional condition                              2074
sheet yes_means=Bearish, plain directional condition                              1947
BUT clause undercuts the plain read; YES leans bearish                             580
BUT clause: true-with-a-catch, weakens the clean bearish read                      425
outlier gap filled (failed breakout); YES leans bearish                             65
outlier reversed by opposite outlier; YES leans bearish                             65
outlier gap filled (failed breakout); YES leans bullish                             65
outlier reversed by opposite outlier; YES leans bullish                             65
momentum reversal vs prior reading; YES leans bullish                               46
divergence; YES leans bullish                                                       41
calendar/event timing, no inherent direction                                        20
divergence; YES leans bearish                                                       19
momentum reversal vs prior reading; YES leans bearish                               10
price/volume confirmation test; YES leans bullish                                   10
price/volume confirmation test; YES leans bearish                                    8
```

Rule text below says warning=quiet_warning, bearish=loud_bearish.

## Rules (priority order)
1. Calendar/event flags without a market condition -> neutral.
2. '(BUT snap-back)' twins are direction-flipped outlier twins, not catches -> plain bullish/bearish per yes_means. Other BUT clause (BUT twins, Contrary/BUT) -> warning if YES leans bearish, asterisk if YES leans bullish. "BUT momentum" exhaustion rows are trend-continuation, not BUT clauses.
3. Quiet-sign patterns (divergence, outlier then opposite outlier/snap-back, outlier gap filled, reversal vs prior reading, price/volume confirmation, streak break) -> warning if bearish, bullish if bullish.
4. Otherwise the sheet's yes_means: bullish / bearish.

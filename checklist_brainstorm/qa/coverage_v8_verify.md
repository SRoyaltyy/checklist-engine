# Coverage v8 independent check (Manager Bot, 2026-10-22 HKT)
Inputs: Drive coverage v8 (1vny5AD6kY68b8xCFg-Z9zx1W3smBcbL7), merged_draft_v8.csv (21,258 rows), tradingview_master.csv, four owner tag files (Taskforce compact rows, James, New Bot in_compact=True, Theme Radar ids with `-C` stripped). All 19,832 non-Grok rows joined to a tag (100%). Grok has no tag file, so Grok's rows are checked by subtraction.

## 1. Have items with rows: PASS (144 / 165)
Per-item, per-owner counts in the table match the tag files exactly for every M-id; only diff is M293 (Theme Radar 116 short-float rows), moved off-chart under the strict rule (correct). The 21 empty items match Grok's list: 9 bullish twins, not 10 (M225,229,244,247,251,256,260,264,267) – the pattern code covers both sides, the tag just lands on the bearish twin; M292/M293 (rows exist, now off-chart: TF 60, TR 116); 10 others: M008, M013, M030, M047, M117, M157, M158, M210, M272, M278. Total 9+2+10 = 21. Small label fixes: the empty item is M117 'MovingAvg Cross' (Grok wrote 'MA Cross'; M088 'MA Cross' has 20 Theme Radar rows).

## 2. On/off chart 19,359 / 1,899: PASS (exact)
Off-chart: Taskforce 480, James 119, New Bot 108, Theme Radar 872 (756 + 116 short), Grok 320 (CFTC COT) = 1,899. Note: New Bot's 24 "add-on" rows (Share count jump/Tiny float, M286) count as on-chart.

## 3. Pulled vs math: PASS (exact)
Taskforce 300/7,976; James 746/7,568; Theme Radar 1,460/1,132; New Bot 336/314 (all exact from tag files). Grok 1,301/125 follows by subtraction (on-chart 981/125 + 320 CFTC raw). Total 4,143/17,115.
Misclassification flag: Grok's 102 M294 beta rows ("756-day beta computed by us") are counted as pulled; they are math. Corrected Grok ≈ 1,199/227, total ≈ 4,041/17,217.

## 4. Holds
- Finviz market cap/shares 194: PASS on count, with edges. = New Bot 24 (Share count jump 12 + Tiny float 12, exactly as New Bot says, none on market cap) + Theme Radar 88 direct (shares out 34, float 34, market cap 20) + Theme Radar 82 short-float rows (Finviz short float = short interest / Finviz float, so holding is reasonable). Taskforce's 20 "Short % of float" rows are not held (they don't use Finviz). Gap: 154 Theme Radar Finviz ratios built on market cap (P/S 34, EV, EV/EBITDA, EV/Sales, P/B, P/FCF, P/Cash 20 each) are NOT held; owners should decide.
- Theme Radar 08-06/08-10 volume 386: PASS. 236 volume-named rows + 150 divergence rows that use relative-volume change. All really use volume.
- Earnings dates 40: PASS (Theme Radar sessions until/since earnings, 4 x 10).
- Note: table's hold_rows column sums to 468 because it shows only on-chart rows; it is not the sum of the three hold groups.

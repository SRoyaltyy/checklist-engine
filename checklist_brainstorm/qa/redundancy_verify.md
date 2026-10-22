# Manager Bot recheck of Grok Bot's redundancy audit (v7)
Run 2026-10-22 ~03:45 HKT. Read-only: no files in qa/redundancy/ were changed. My own code: /tmp/v.py (recomputes from raw_sample_signals.parquet).

## Verdict per claim
| Claim | Result | Why |
|---|---|---|
| v7 has 21,308 rows | PASS | tagged_final.pkl has 21,308 rows |
| 466 rows tested, 50 stocks, 2019-2025 | PASS | raw file is 88,000 stock-days x 466 rows. Owner mix: TF 230, James 170, TR 60, New Bot 5, Grok 1 |
| Pair scores are computed correctly | PASS | I recomputed agreement, phi, Jaccard and kappa for 30 pairs (the 10 strongest plus 20 random). Largest difference from pairs.npz: 0.000002 |
| 437 groups at one 80% cutoff | PASS, but the label is misleading | It's a single cutoff (complete linkage at 0.8). But the cutoff is on **kappa** (agreement beyond chance), not raw "80% agreement". Raw agreement would be badly inflated: 55% of rows fire on fewer than 10% of days, so 66% of all pairs "agree" at 80% or more, and raw agreement gives only 80 groups. Using kappa, phi or Jaccard gives 437 / 437 / 449, so the result holds up against rows that are mostly "no" |
| About 141 independent signals | PASS (reproduced: 140.9) | Measured on 459 live rows. 7 rows never fire: 6 Taskforce candle "level (BUT)" rows and 1 "return vs sector (BUT)" row. Those look like coding problems in the audit, not real dead rows: the candle rows' text says "YES if K==0", which should fire almost every day |
| About 200 for the whole sheet | NOT JUSTIFIED (rough guess only) | The 466 rows aren't a random sample. They're quota picks of rows that could be computed from price bars, with Taskforce and James taking up 86%. The ~200 comes from fitting a curve to smaller subsets of those same 459 rows and extending it out to 21k. That curve flattens by construction, and it leaves out the Finviz, COT, FINRA, analyst and halt rows completely. Fair reading: at least ~140 for the price-bar part. The whole-sheet number is unknown |
| 86% of rows are math on price bars | PASS with a caveat | The price-bar data sources add up to 18,011 rows (84.5%), or 18,629 (87.4%) if the VIX and put/call rows count. The 63% figure for a single stock's own bars checks out (13,407) |
| James: 2,621 BUT twins with the same rule as the base row | PASS | 2,621 rows carry "[BUT twin of the same condition]". In the 5 I checked, the YES text is word-for-word the same as the base row |
| James: 520 impossible big-candle rows | PASS | 520 rows match "exactly 1 session ago" plus close below the candle's own low (or above its own high). Yesterday's close can't sit outside yesterday's own range. All 5 spot checks are this pattern |
| TF div_volume (BUT) rows agree at 0.95-0.98 | PARTLY | Only the top pairs reach that (best is 0.98: CMO14 vs up-volume share). Across all 66 pairs in that lens, phi runs from 0.12 to 0.98 with a median of 0.45, and the mean of 0.54 is right. Also, the 0.96 heatmap example belongs to div_price (BUT), not div_volume |
| PPO hist vs MACD hist 0.93 | PASS | phi 0.931 |
| TR gap / relvol vs TF at 0.70 / 0.68 | PASS | phi 0.704 and 0.676 (kappa 0.69 / 0.67) |
| New Bot: 32 BUT rows with the same wording as their base | FAIL as worded | There are 32 rows with "BUT mirror: YES if same difference <= -3%", but their text isn't the same as their base row: 0 of New Bot's BUT rows match their base. In the 5 I checked, the base says "event return minus SPY/industry >= +3%" and the mirror is the <= -3% side, so it's a real opposite. The wording "same difference" is vague and should be written out, but these aren't copies. (The audit's phrase "doesn't apply to an event flag" is also wrong: they compare returns, not the flag) |
| Grok: 64 duplicate ids | PASS | 64 ids are used twice (128 rows), all FV-GB-24xx. Each pair is two different rules (for example target-price change vs an upgrade action), so they need renumbering. They aren't duplicate signals |
| "89 rows share identical rule text" | UNCLEAR | The audit's own flag dup_identical_text_group marks 3,233 rows, mostly the James twins. The 89 couldn't be traced to the code |

## Bottom line
The math is right. My numbers match to 6 decimals, and the clustering is safe against rows that are mostly "no" because it uses kappa, not raw agreement. Fixes needed:
(a) call the cutoff "kappa 0.8", not "80% agreement";
(b) drop the "~200 for the whole sheet" figure or mark it as a guess;
(c) withdraw the New Bot "32 identical" claim;
(d) soften "0.95-0.98" to "up to 0.98, median 0.45";
(e) fix the 7 "dead" rows in the engine (candle BUT = K==0).

# NB32_V1 results — PRACTICE 2020–24, HINT, survivors-only (rules NB32_V1_RULES.md, committed before results)
32 New Bot rows (21 CAC dividend, 11 DIL dilution) not in nb193_v1; every buyable stock-day 2020–24 (1,970,427 tradable tagged stock-days). 2025–26 sealed.
**0 PASS / 28 FAIL / 4 TOO_RARE / 0 NOT_COMPUTABLE.**
- POSSIBLE_LOOKAHEAD group (21 CAC): 17 FAIL, 4 TOO_RARE (043-W0-EVT, 042-T20-CNT, 043-T20-CNT, 043-T20-RXS).
- SEC_PIT group (11 DIL): 11 FAIL.
Tests added 32 × 2 = 64 → global BH family 13,700 + 64 = 13,764.
Closest misses:
- nb4-CAC-NB-042-T20-RXM-BUT (EXIT_RULE_V1): 2020–22 win 57.8% (n=2,388), excess +1.5%, BH q ≈ 0.00 (survives luck check);
  2023–24 win 52.9% (n=2,535), excess +0.7% → fails the 55% confirm bar. POSSIBLE_LOOKAHEAD anyway.
- nb4-CAC-NB-043-T20-EXT (EXIT_RULE_V1): win 54.2% (n=646) / 58.7% (n=518), excess +0.9% both; q = 1.0 → FAIL.
- nb4-CAC-NB-043-T20-RXS-BUT: 60.4% (n=169) / 52.0% (n=148); q = 1.0.
- Dilution best: DIL-050-T20-RXM 52.8% / 52.7%, excess +1.3% then −0.6% → FAIL.
Caveats: $100M mcap floor not applied; dividend dates as Nasdaq shows today, Nasdaq-listed only; DIL split filter heuristic.

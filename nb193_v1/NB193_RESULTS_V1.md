# NB193_V1 results — PRACTICE 2020–24, HINT, survivors-only (rules: NB193_V1_RULES.md, committed ee3ab4a before results)
193 New Bot rows (for_james_step3.csv), every buyable stock-day 2020–24 (1,970,427 tradable tagged stock-days). 2025–26 sealed.
**0 PASS / 165 FAIL / 18 TOO_RARE (<30 trades in a period) / 10 NOT_COMPUTABLE (never YES).**
Tests added: 193 rows × 2 labels = 386 → global BH family 10,112 + 386 = 10,498 (untested_v2 adds its own count separately).
Closest miss (no BH): nb4-HIS-NB-029-DUR90-SUP (+ identical -BUT twin), EXIT_RULE_V1: win 56.5% (n=147) 2020–22, 59.5% (n=864) 2023–24,
excess +11.3% / +1.6% vs average buyable stock; BH q = 1.0 → FAIL. 10-day label win 32.0% / 44.1%.
Caveats: earnings consensus may be back-filled, reaction day may be ±1, AVWAP from daily bars; $100M mcap filter not applied.
Look-ahead rule not triggered (no earnings row passed).

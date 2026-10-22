# TRAJECTORY_RESULTS_V1
Pre-registration: trajectory/TRAJECTORY_V1.md (v1 commit 21d02e0, v1.1 add-only commit 1ff719c). Practice data only, 2020–24: survivors-only, minus drop_list_v2. 2025–26 was not read.
Entry is the open of the run's first day. One trade per run per bucket (RUNLEN: one per bucket). Fees 0.6% round trip.
- A = EXIT_RULE_V1 (+20% target / close of day 15). B = close of day 10.
- The BH family is cumulative: 6,702 tests, made of the 6,446 earlier tests plus 256 new ones.
- Full table: trajectory_results_v1.csv (n, win, mean, median, excess vs ALL same-day, date-clustered 95% CI, p, q).

Frozen cutoffs:
- F5 s5 13/79, s10 16/83, flip5 15/21; DIV NORISE level >= 34; DIVC cut 0.443.
- F1 s5 −54/−15, s10 −65/−10, flip5 47/76; NORISE level >= 61/60/60; DIVC cut 0.333.

## Rule for "held"
q < 0.05 on 2020–22 AND the same sign with q < 0.05 on 2023–24.

## Held (1 of 128 bucket×exit pairs)
| family | bucket | exit | 2020–22 excess / median / win / n / q | 2023–24 excess / median / win / n / q |
|---|---|---|---|---|
| F1 (bottom-fifth score) | DIV3_PDOWN (non-price yes-count up >=2 over 3d, price down >= 1×ADR20) | A | +1.76% / +4.20% / 58.4% / 1121 / 0.025 | +1.41% / +3.46% / 58.1% / 728 / 0.048 |

Same bucket, exit B: 2020–22 +1.77% (q=0.12, not significant); 2023–24 +2.10% (q=0.039).
Siblings DIV5_PDOWN and DIV10_PDOWN on F1 pass on 2023–24 only (A +1.65% q=0.018; +2.17% q=0.001), not on 2020–22. So they do not count as held, but they point the same way.

## Did not hold
- **F5 (top-fifth) trajectories.** RUNLEN (first day vs 2nd vs 5th), SLOPE5/10, FLIP5, LASTFLIP, REPASS, and the non-price divergence controls all failed to hold.
  - Some significant 2020–22 negatives (DIV3/5/10 exit B, REPASS B, SLOPE5 DOWN B) faded to non-significant on 2023–24.
  - The F5 run-start baseline is about 0 vs ALL (A −0.03% / +0.02%).
- **Rising vs falling score, fresh vs repeat, what flipped last:** no stable edge in either family.
- **F1 baseline.** It is positive on 2023–24 only (A +0.52%, B +0.93%) and not on 2020–22. This is the same "runs backwards / survivors-flattered" pattern as SCORE_V1.
- **Controls.** For F1, CTRL_PUP and NORISE are weaker than the price-down divergence bucket, and none held.

## Caution
- The one survivor is "jumpy, loser-sign stock falling hard while volume and range build up", a capitulation look.
- Survivors-only data flatters exactly this kind of trade: the stocks that kept falling and got delisted are missing.
- The median is high (+3–4%), but treat it as unproven until live post-lock days come in.
- LASTFLIP has very unbalanced buckets (F5 is 95% W_LAST, F1 is 98% L_LAST), so it carries little information.

# STACKS_RESULTS_V1 — results for STACKS_V1.md (practice 2020–24, HINT only)
STACKS_V1.md (pre-registration) sha256 b877df0f929c9b2547a0ea3647909a312a23c3a09b6055d0fc277c055c8220e2 — unchanged since written before the run.
Sector leg of "running ahead" not computed: SPY only (stock 20d return − SPY 20d return >= +10pp).
BH q=0.05 over 6,426 tests = 1,890 stack cells (5 stacks x 126 rules x 3 periods) + 4,536 exit_grid_v1 cells.

## n and +10% intraday hit within days 1–21 (2020–24 | 2020–22 | 2023–24)
| group | n | hit+10% |
|---|---|---|
| ALL | 2,408,833 | 35.2 / 37.7 / 32.0 |
| S1 Q5&noBig | 469,163 | 32.1 / 34.6 / 29.2 |
| S2 Q7&noBig | 829,381 | 35.1 / 37.1 / 32.5 |
| S3 Q5&noBig&near26 | 97,298 | 10.2 / 11.2 / 9.4 |
| S4 Q7&noBig&near26 | 96,947 | 10.0 / 10.7 / 9.3 |
| S5 (Q5|Q7)&noBig&near26 | 171,557 | 10.4 / 11.4 / 9.6 |

## Discover 2020–22 -> confirm 2023–24
- Best 2020–22 stack cell: S1, X=20, stop X/2, H=21: win 46.5%, mean +0.80%, excess +0.53% [+0.25,+0.87], q=0.012.
  2023–24: win 46.2%, mean +0.14%, excess +0.09% [+0.01,+0.16], q=0.059 -> same sign, ~1/6 the size, misses BH.
- Best per stack (2020–22 -> 2023–24 excess): S2 X20/half/H21 +0.26% -> +0.06% [−0.02,+0.13] (fails); S3 +0.03% (n.s.) -> −0.11%;
  S4 +0.01% -> +0.02%; S5 +0.02% -> +0.02% (all n.s.). Near-26w-high stacks' BH passes are all NEGATIVE excess.
- 23 cells pass BH on both halves with positive excess: S1 21, S2 2. Best confirmed: S1 X=20 no stop H=15: 2023–24 win 49.3%, mean +0.41%, excess +0.11% [+0.03,+0.19], q=0.036.
- No stack reaches a 50% win rate in 2023–24 at X>=10.

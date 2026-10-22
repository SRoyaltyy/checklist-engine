# NB193_V1 — rules (pre-registered; committed BEFORE any result is computed)
PRACTICE 2020–24 only, **HINT, survivors-only**. No bar after 2024-12-31 is read (filtered on load + asserted). 2025–26 stays sealed.
Price file: /workspace/pricehist/universe_2020_survivors.parquet, sha fb9bbe69…ef337 (asserted). qa/redundancy/feats.py not used.

## Scope
New Bot `for_james_step3.csv` (193 rows: 21 WIRED never tested + 140 newly wired + 32 SI/FINRA side rows), from Drive tar
1kk2VvkUtsLgv3A3Qhr1Z71yMN2JJoN32 (nb_tags_v1.tar.gz, sha 42de7de6…01483, verified) = branch new-bot/nb-wire-v1 @ 56113cf.
Answers: nb_tags_{2020..2024}.parquet, 2-bit packed (0 NR, 1 NO, 2 YES) in nb_tags_ids.json order; answer at D uses bars < D.
Each row is one test, run on EVERY buyable stock-day 2020–24 present in the tag files (full universe, not the ledger cells).

## Trades and controls (same as untested_v1)
- Trade = (ticker, D) with answer YES, entry at open D. Untradeable removed from trades and controls: drop_list_v2 (already removed
  upstream; re-applied). $100M market-cap minimum NOT applied (no point-in-time share counts). Flagged.
- Control = mean return of all buyable stock-days on the same date (story_q/panel.parquet minus drop_list_v2).
- Labels, 30bp/side (0.6% round trip): (B) 10-day open D → close D+9; (A) EXIT_RULE_V1: +20% take-profit (gap fills at open),
  no stop, else close of day 15. Needs bars D..D+20 ≤ 2024-12-31.

## Pass bar (per label; row passes if it passes under either label, both reported)
Discover 2020–22 AND confirm 2023–24, each: n ≥ 30, win rate (net > 0) > 55%, mean excess vs control > 0.
Plus discover-period BH q < 0.10 (date-clustered bootstrap, 500 draws, seed 13) over the GLOBAL family:
10,112 prior tests + 2 × 193 here (prior p-values treated as p = 1, conservative). untested_v2 runs in parallel; its count is separate.
Status: NOT_COMPUTABLE (never YES / all NR), TOO_RARE (< 30 YES trades in either period), FAIL, PASS. Constant-answer rows reported.
Nothing passes as a "keep"; any pass is a live-day HINT only.

## Caveats carried (New Bot)
Earnings consensus may have been back-filled after the fact; reaction day may be one day off (BMO/AMC timing unknown);
anchored price (AVWAP) estimated from daily bars.

## Look-ahead rule (add-only, Manager/Grok steering, before results)
Any earnings-consensus or earnings-reaction row (ids containing ERN-, NB-014, NB-022, NB-023, NB-024, NB-091) that passes is marked
**POSSIBLE LOOK-AHEAD** and counts as HINT only, not a keep, until re-checked with data that was really known at the time.

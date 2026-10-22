# NB32_V1 — rules (pre-registered; committed BEFORE any result is computed)
Add-only follow-on to nb193_v1 (rules ee3ab4a, results c49ebe0). PRACTICE 2020–24 only, **HINT, survivors-only**.
No bar after 2024-12-31 is read (filtered on load + asserted). 2025–26 stays sealed. Price file sha fb9bbe69…ef337 (asserted). qa/redundancy/feats.py not used.

## Scope
The 32 rows in new_bot/nb_wire_v2/for_james_step3_v2.csv (sha 6d3cdec4…03b2, Drive 1RWCDkZA02_hHmOxLFR1X_JmGcpTlcBo8, main 46a1c3a = e4ecbdd)
that are NOT in nb193_v1's 193: 21 CAC-NB-042/043 (Nasdaq dividends) + 11 DIL-NB-050 (SEC shares outstanding). List: nb32_rows.csv.
Answers: nb_tags_v2 (Drive 1VnJMB0eoB2jGWw-z5KeIix1_0rNyiXO4, sha 573fcea3…86ffb3, verified), same 2-bit packing, ids from nb_tags_v2 json.

## Method — identical to nb193_v1 (code copied, inputs swapped)
Trades = YES stock-days, entry open D; untradeable (drop_list_v2) removed from trades and controls; control = mean of all buyable
stock-days same date. Labels after 30bp/side: (A) EXIT_RULE_V1 (+20% TP, no stop, day-15 close), (B) 10-day hold.
Pass (per label): discover 2020–22 AND confirm 2023–24 each n ≥ 30, win > 55%, excess vs control > 0; plus discover BH q < 0.10
(date-clustered bootstrap, 500 draws, seed 13) over global family = 13,700 prior (running count, prior p = 1) + 2 × 32 = 13,764.
Statuses: NOT_COMPUTABLE (never YES), TOO_RARE, FAIL, PASS. $100M mcap floor not applied in this run. Any pass = live-day HINT only.

## Look-ahead groups
- group POSSIBLE_LOOKAHEAD: all 21 CAC rows — declaration dates are as Nasdaq shows them today (may be revised); results reported
  separately and never a keep even if they pass. Also NR for non-Nasdaq listings (coverage bias).
- group SEC_PIT: 11 DIL rows — only facts filed ≤ bar date and ≤ 2024-12-31; split filter heuristic.

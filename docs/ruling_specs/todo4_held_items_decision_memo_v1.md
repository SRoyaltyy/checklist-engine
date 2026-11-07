# Held ruling items — decision memo for Cyrus (TODO item 4)

**Purpose:** the three items below are all that block Kimi lane item 4 ("ruling
parts 5–8"). Each is stated as the exact decision needed, with a recommended
default so the ruling can be a one-line approval. James to take to Cyrus.

---

## 1. MA30 group contradiction (34 question IDs: `deepest_pullback_ma`, `bounce_ceiling`)

**The conflict.** These tree rows measure pullbacks/bounces against MA30 and
SMA5..SMA30, but the registered MA group settings are {10, 20, 50, 200}.
Either the L3 group or the outcome sets must move.

**Options.**
- **A (recommended): extend the MA group with the missing registered
  settings.** Add SMA5 and SMA30 to the MA L3 settings (making the group
  {5, 10, 20, 30, 50, 200}). Cost: more variants per MA facet; benefit: the
  two families bind exactly as the tree words them, and 30-day MAs are a
  standard chart overlay Cyrus already references.
- **B: amend the two families** to use only {10, 20, 50, 200}. Cost: the tree
  text changes (needs a tree revision); 30-day-pullback questions disappear.

**Recommended ruling: A** — "MA group becomes {5, 10, 20, 30, 50, 200}".

## 2. VWAP_anchored anchor definition (`{above_usual, usual, below_usual}` outcomes)

**The gap.** Session VWAP is definable now, but `VWAP_anchored` needs the
anchor event that resets the accumulation. The anchor is a *semantic* choice:
different anchors ask different questions.

**Options.**
- **A (recommended): fixed anchor set = {last earnings date, last 52-week
  high, last gap ≥ 1 ATR14}** — three named anchors, each strict (earnings
  from the calendar block; 52w high and gaps already computed for other
  families). No anchor in the lookback → fall back to session VWAP, flagged in
  the feature. Each anchor produces its own question set (facet suffix in the
  feature expression), so nothing is silently mixed.
- **B: rolling lookback anchor (20/50/200 sessions)** — cheaper, but
  "anchored VWAP over last N sessions" is nearly identical to a long SMA and
  adds little beyond session VWAP.
- **C: drop the anchored variant**; bind session VWAP only.

**Recommended ruling: A** — anchor set {earnings, 52w high, ≥1×ATR14 gap}.

## 3. SPY_VIX cross-asset plumbing + thresholds

**The gap.** `market_condition × SPY_VIX` families need (i) how a market-wide
series joins a per-stock day-D question and (ii) the VIX threshold values for
the outcome sets.

**Join rule (recommended, PIT-safe):** the context value is the **prior
completed session's** SPY/VIX values (same rule as all evidence: ends < D).
Market-wide context has no per-stock join key — every stock at D sees the same
context value; the feature is stamped `market_context` in `feature_json` so
combination mining can treat it as a market regime input, not a stock signal.
No same-day VIX: VIX prints during the session, so day-D VIX is not knowable
at D's open.

**VIX thresholds (recommended defaults, amendable later without touching
definitions — thresholds are dials):** low < 15, normal 15–25, high > 25,
crisis > 35. SPY side: distance of SPY close from its own 50/200-day SMA as
band outcomes (mirrors the existing MA band machinery), SPY 20-day return
terciles vs its own 252-day history.

**Recommended ruling:** approve the join rule (prior completed session,
market_context stamp) and the default VIX/SPY thresholds as dials.

---

**If all three rulings land as recommended:** MA30/SMA5 extend the MA group
(facets re-run mechanically), VWAP_anchored binds with the three-anchor set,
and the market_condition × SPY_VIX block becomes spec-able — unblocking the
rest of parts 5–8 (time_in_zone zone definitions and price_divergence
swing-pairing proposals are already drafted and queued in the part-5/6 spec
comments on PR #177).

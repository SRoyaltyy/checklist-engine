"""I192 XBRL fundamental ratio/growth measurements for strict binary defs.

Inputs are per-date fact points produced by world_sec_facts.fact_values_at
(which already enforces filed date strictly < D and carries the value status).
Every function propagates NOT_EVALUABLE (None) on any non-VALUE status
(VALUE / CONFLICTING_VALUES_SAME_FILED_DATE / MULTIPLE_VALID_PERIOD_STARTS /
NO_KNOWN_FACT) — ratios are never partially imputed. Price inputs are raw
D-1 closes (never adjusted) per METHODOLOGY P4; day D is execution only.
"""
import math


def _value(point):
    if point is None or point.get('status') != 'VALUE':
        return None
    value = float(point['value'])
    return value if math.isfinite(value) else None


def pe_ratio_v1(eps_diluted_ttm, price_dminus1):
    """Price / diluted EPS (TTM). NE on any non-VALUE fact status, a
    non-positive EPS (P/E not meaningful), or a non-positive price."""
    eps = _value(eps_diluted_ttm)
    price = _value(price_dminus1) if isinstance(price_dminus1, dict) else float(price_dminus1)
    if eps is None or eps <= 0 or price is None or price <= 0:
        return None
    return price / eps


def pb_ratio_v1(equity_instant, shares_out_instant, price_dminus1):
    """Price / book value per share. NE on any non-VALUE status, zero/negative
    book value per share, or a non-positive price."""
    equity = _value(equity_instant)
    shares = _value(shares_out_instant)
    price = _value(price_dminus1) if isinstance(price_dminus1, dict) else float(price_dminus1)
    if (equity is None or shares is None or shares <= 0 or price is None or price <= 0):
        return None
    book = equity / shares
    if book <= 0:
        return None
    return price / book


def revenue_growth_yoy_v1(revenue_ttm_current, revenue_ttm_prior):
    """(current - prior) / prior * 100, TTM durations. NE on any non-VALUE
    status or a zero/negative prior base (growth rate not meaningful)."""
    cur = _value(revenue_ttm_current)
    prev = _value(revenue_ttm_prior)
    if cur is None or prev is None or prev <= 0:
        return None
    return (cur - prev) / prev * 100.0


def margin_expanded_yoy_v1(net_income_ttm_current, revenue_ttm_current,
                           net_income_ttm_prior, revenue_ttm_prior):
    """True when the net margin (NI/revenue) of the current TTM period exceeds
    the prior period's. NE on any non-VALUE status or a zero revenue either
    side."""
    ni_c, rev_c = _value(net_income_ttm_current), _value(revenue_ttm_current)
    ni_p, rev_p = _value(net_income_ttm_prior), _value(revenue_ttm_prior)
    if None in (ni_c, rev_c, ni_p, rev_p) or rev_c == 0 or rev_p == 0:
        return None
    return (ni_c / rev_c) > (ni_p / rev_p)

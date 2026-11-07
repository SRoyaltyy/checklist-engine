"""Point-in-time daily-ratio measurements for non-price market series (Kimi lane).

I189 FINRA per-stock short volume and I201 CBOE market-wide options context.
Same contract as world_sec_events.py: a record is usable at setup date D only
if its publication timestamp is strictly before D 09:30 ET (dictionary C29);
missing/undefined values are NOT_EVALUABLE (None), never NO; a known 0 is
evaluable.

I201 era discipline (docs/OPTIONS_MONEYFLOW_INVENTORY_V1.md): the 2019-10-07
exchange/group definition break and the post-2022 0DTE discontinuity split the
CBOE series into eras; percentile facets never cross an era boundary. Ratios
are derived from raw counts at declared precision, not from convenience columns.
"""
from datetime import date, datetime, time

ET_OPEN = time(9, 30)

NE_NO_USABLE_RECORD = 'NE: no usable record before D 09:30 ET'
NE_ZERO_DENOMINATOR = 'NE: zero denominator (zero call volume/OI or zero total volume)'
NE_INSUFFICIENT_SAME_ERA_HISTORY = 'NE: insufficient usable history within the current CBOE era'
NE_INSUFFICIENT_HISTORY = 'NE: insufficient usable history'

CBOE_ERA_BREAK = date(2019, 10, 7)      # exchange/group definition break
CBOE_0DTE_FLAG_DATE = date(2022, 11, 14)  # post-2022 0DTE discontinuity flag


def cboe_era(session):
    if session < CBOE_ERA_BREAK:
        return 'pre_2019_10_07'
    if session < CBOE_0DTE_FLAG_DATE:
        return 'mid_2019_10_07_to_2022_0dte'
    return 'post_2022_0dte'


def usable_records(records, setup_date):
    limit = datetime.combine(setup_date, ET_OPEN)
    return [r for r in records if r['public_dt'] < limit]


def _usable_in_window(records, sessions, setup_date, window=None, group=None):
    prior = [s for s in sessions if s < setup_date]
    win = set(prior[-window:] if window else prior)
    out = []
    for r in usable_records(records, setup_date):
        if r['session'] not in win:
            continue
        if group is not None and r.get('group') != group:
            continue
        out.append(r)
    return out


def finra_short_ratio_v1(records, sessions, setup_date):
    """short_volume / total_volume of the latest usable session (0..1).
    NE when no usable record or the latest usable total volume is 0."""
    pool = _usable_in_window(records, sessions, setup_date)
    if not pool:
        return None
    latest = max(pool, key=lambda r: r['session'])
    if float(latest['total_vol']) == 0:
        return None
    return float(latest['short_vol']) / float(latest['total_vol'])


def finra_short_ratio_mean_v1(records, sessions, setup_date, window):
    """Mean of per-session short ratios over the last `window` usable sessions.
    NE when fewer than `window` usable sessions or any of them has zero total."""
    pool = _usable_in_window(records, sessions, setup_date, window)
    if len(pool) < window:
        return None
    ratios = []
    for r in pool:
        if float(r['total_vol']) == 0:
            return None
        ratios.append(float(r['short_vol']) / float(r['total_vol']))
    return sum(ratios) / len(ratios)


def finra_short_ratio_percentile_v1(records, sessions, setup_date, lookback):
    """Fraction of the last `lookback` usable sessions whose short ratio is
    <= the latest session's ratio (own-history percentile in [0,1]).
    NE when fewer than `lookback` usable sessions or a zero total anywhere."""
    pool = _usable_in_window(records, sessions, setup_date, lookback)
    if len(pool) < lookback:
        return None
    ratios = []
    for r in sorted(pool, key=lambda r: r['session']):
        if float(r['total_vol']) == 0:
            return None
        ratios.append(float(r['short_vol']) / float(r['total_vol']))
    latest = ratios[-1]
    return sum(1 for x in ratios if x <= latest) / len(ratios)


def finra_short_ratio_cross_median_v1(records, sessions, setup_date, lookback, within):
    """True when the short ratio crossed above the median of the prior
    `lookback` usable sessions at any point within the last `within` sessions.
    NE when there are fewer than lookback+within usable sessions or a zero
    total volume occurs in the evaluated history."""
    prior = [s for s in sessions if s < setup_date]
    pool = _usable_in_window(records, sessions, setup_date)
    if len(pool) < lookback + within:
        return None
    by_session = {r['session']: r for r in pool}
    ordered = [s for s in prior if s in by_session]
    ratios = {}
    for s in ordered:
        r = by_session[s]
        if float(r['total_vol']) == 0:
            return None
        ratios[s] = float(r['short_vol']) / float(r['total_vol'])
    for i in range(len(ordered) - within, len(ordered)):
        if i < lookback:
            return None
        base = ordered[i - lookback:i]
        if len(base) < lookback:
            return None
        median = sorted(ratios[s] for s in base)[lookback // 2]
        session = ordered[i]
        prev = ratios[ordered[i - 1]]
        if prev <= median < ratios[session]:
            return True
    return False


def cboe_put_call_volume_ratio_v1(records, sessions, setup_date, group='equity'):
    """put_volume / call_volume from raw counts, latest usable session.
    NE when no usable record or zero call volume (explicit zero-call rule)."""
    pool = _usable_in_window(records, sessions, setup_date, group=group)
    if not pool:
        return None
    latest = max(pool, key=lambda r: r['session'])
    if float(latest['call_vol']) == 0:
        return None
    return float(latest['put_vol']) / float(latest['call_vol'])


def cboe_put_call_oi_ratio_v1(records, sessions, setup_date, group='equity'):
    """put_OI / call_OI from raw counts, latest usable session. Same NE rules."""
    pool = _usable_in_window(records, sessions, setup_date, group=group)
    if not pool:
        return None
    latest = max(pool, key=lambda r: r['session'])
    if float(latest['call_oi']) == 0:
        return None
    return float(latest['put_oi']) / float(latest['call_oi'])


def cboe_pc_ratio_percentile_v1(records, sessions, setup_date, lookback, group='equity'):
    """Own-history percentile of the latest put/call volume ratio within the
    CURRENT era only — never crosses the 2019-10-07 break or the 0DTE flag.
    NE when the current era has fewer than `lookback` usable sessions or a
    zero call volume occurs in the evaluated history."""
    pool = _usable_in_window(records, sessions, setup_date, group=group)
    if not pool:
        return None
    latest = max(pool, key=lambda r: r['session'])
    era = cboe_era(latest['session'])
    era_pool = [r for r in pool if cboe_era(r['session']) == era]
    if len(era_pool) < lookback:
        return None
    ratios = []
    for r in sorted(era_pool, key=lambda r: r['session']):
        if float(r['call_vol']) == 0:
            return None
        ratios.append(float(r['put_vol']) / float(r['call_vol']))
    latest_ratio = ratios[-1]
    return sum(1 for x in ratios if x <= latest_ratio) / len(ratios)


def vix_level_v1(records, sessions, setup_date):
    """Latest usable VIX close. NE when no usable record."""
    pool = _usable_in_window(records, sessions, setup_date)
    if not pool:
        return None
    latest = max(pool, key=lambda r: r['session'])
    return float(latest['vix'])


def vix_term_structure_state_v1(records, sessions, setup_date):
    """'contango' when front-month implied vol (VIX) < 3-month (VIX3M),
    'backwardation' otherwise; fixed set of two outcomes. NE when the latest
    usable record lacks either value."""
    pool = _usable_in_window(records, sessions, setup_date)
    if not pool:
        return None
    latest = max(pool, key=lambda r: r['session'])
    if latest.get('vix3m') is None:
        return None
    return 'contango' if float(latest['vix']) < float(latest['vix3m']) else 'backwardation'


def cboe_skew_v1(records, sessions, setup_date):
    """Latest usable SKEW index level. NE when no usable record."""
    pool = _usable_in_window(records, sessions, setup_date)
    if not pool:
        return None
    latest = max(pool, key=lambda r: r['session'])
    if latest.get('skew') is None:
        return None
    return float(latest['skew'])

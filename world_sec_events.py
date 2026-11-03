"""Point-in-time SEC/event measurements for strict binary definitions (Kimi lane).

Definitions only — this module computes nothing from live data; Venice's
pipelines supply dated event records. Every measurement enforces dictionary C29:
a record is usable at setup date D only if its public timestamp (SEC acceptance
datetime, analyst publish time, ...) is strictly before D 09:30 ET. Records
public on/after that cutoff are invisible at D (never retroactively usable),
which is what makes the leak testable: shifting an event's public_dt across the
boundary must flip the answer to NOT_EVALUABLE/NO, never the other way.

NOT_EVALUABLE (excluded, never NO) is returned as None with a reason code via
the module-level NE_* constants; a known 0 is evaluable.
"""
from datetime import datetime, time

ET_OPEN = time(9, 30)  # dictionary C29: public timestamp must be < D 09:30 ET

NE_NO_USABLE_EVENT = 'NE: no usable event before D 09:30 ET'
NE_EMPTY_SESSIONS = 'NE: session calendar missing/empty'

# Fixed direction mapping table (spec docs/ruling_specs/todo3_sec_options_defs_v1.md
# section 2, draft pending Cyrus/James confirmation). Analyst and Form 4 only;
# 13F carries NO direction mapping (position-change is quantitative only).
_BULLISH = {'form4': frozenset({'P'}), 'analyst': frozenset({'upgrade'})}
_BEARISH = {'form4': frozenset({'S'}), 'analyst': frozenset({'downgrade'})}


def event_direction(source, action_code):
    """'bullish' / 'bearish' / None (countable, not directional)."""
    code = str(action_code).strip()
    if code in _BULLISH[source]:
        return 'bullish'
    if code in _BEARISH[source]:
        return 'bearish'
    return None


def _cutoff(setup_date):
    return datetime.combine(setup_date, ET_OPEN)


def usable_events(events, setup_date):
    """Records public strictly before D 09:30 ET, session-aligned."""
    limit = _cutoff(setup_date)
    return [e for e in events if e['public_dt'] < limit]


def _matching(events, source=None, direction=None):
    out = []
    for e in events:
        if source is not None and e['source'] != source:
            continue
        if direction is not None and event_direction(e['source'], e['action']) != direction:
            continue
        out.append(e)
    return out


def _window_sessions(sessions, setup_date, window):
    """The last `window` completed sessions before D (sessions are sorted dates)."""
    prior = [s for s in sessions if s < setup_date]
    return prior[-window:] if window else prior


def days_since_last(events, sessions, setup_date, source=None, direction=None):
    """Trading days between the latest matching usable event and D.

    The event's own session counts as day 0; sessions strictly after it and
    before D are counted. None (= NOT_EVALUABLE) when no matching usable event.
    """
    pool = _matching(usable_events(events, setup_date), source, direction)
    if not pool:
        return None
    last = max(e['session'] for e in pool)
    if last >= setup_date:
        return None  # defensive: session calendar disagrees with public_dt
    return sum(1 for s in sessions if last < s < setup_date)


def count_in_window(events, sessions, setup_date, window, source=None, direction=None):
    """Count of matching usable events whose session is in the last `window`
    completed sessions before D. Evaluable (0) even when empty."""
    win = set(_window_sessions(sessions, setup_date, window))
    pool = _matching(usable_events(events, setup_date), source, direction)
    return sum(1 for e in pool if e['session'] in win)


def insider_cluster(events, sessions, setup_date, window, min_insiders,
                    source='form4', action='P'):
    """True when >= `min_insiders` DISTINCT insiders have a usable `action`
    event in the last `window` sessions (dictionary I187 cluster facet)."""
    win = set(_window_sessions(sessions, setup_date, window))
    pool = [e for e in usable_events(events, setup_date)
            if e['source'] == source and e['action'] == action and e['session'] in win]
    return len({e['insider_id'] for e in pool}) >= min_insiders


def net_dollars(events, sessions, setup_date, window, source='form4'):
    """sum($ purchases) - sum($ sales) over usable events in the window.
    Non-directional codes (A/F/G/M/...) contribute 0 and are excluded from the
    sum by construction; evaluable (0.0) even when empty."""
    win = set(_window_sessions(sessions, setup_date, window))
    total = 0.0
    for e in usable_events(events, setup_date):
        if e['source'] != source or e['session'] not in win:
            continue
        direction = event_direction(source, e['action'])
        if direction == 'bullish':
            total += float(e['dollars'])
        elif direction == 'bearish':
            total -= float(e['dollars'])
    return total


def max_trade_dollars(events, sessions, setup_date, window, source='form4',
                      direction='bullish'):
    """Largest single matching usable event $ in the window; None (= NE) when
    no matching usable event exists."""
    win = set(_window_sessions(sessions, setup_date, window))
    pool = [e for e in _matching(usable_events(events, setup_date), source, direction)
            if e['session'] in win]
    if not pool:
        return None
    return max(float(e['dollars']) for e in pool)


def net_direction_count(events, sessions, setup_date, window, source):
    """upgrades - downgrades (bullish count - bearish count) over the last
    `window` completed sessions; non-directional actions contribute 0.
    Evaluable (0) even when empty; source 'analyst' or 'form4'."""
    win = set(_window_sessions(sessions, setup_date, window))
    total = 0
    for e in _matching(usable_events(events, setup_date), source):
        if e['session'] not in win:
            continue
        direction = event_direction(source, e['action'])
        if direction == 'bullish':
            total += 1
        elif direction == 'bearish':
            total -= 1
    return total


def last_pt_change_pct(events, sessions, setup_date):
    """pt_change_pct of the latest usable analyst action (signed, percent).
    NE when no usable analyst event or it carries no price-target change."""
    pool = _matching(usable_events(events, setup_date), 'analyst')
    if not pool:
        return None
    latest = max(pool, key=lambda e: (e['session'], e['public_dt']))
    if latest.get('pt_change_pct') is None:
        return None
    return float(latest['pt_change_pct'])


def _filing_observations(events, sessions, setup_date):
    """Usable 13F observations (one per filing), ordered by session."""
    pool = [e for e in usable_events(events, setup_date)
            if e['source'] == '13f' and e['session'] < setup_date]
    return sorted(pool, key=lambda e: (e['session'], e['public_dt']))


def filers_13f_v1(events, sessions, setup_date):
    """Filer count of the latest usable 13F filing. NE when none usable."""
    obs = _filing_observations(events, sessions, setup_date)
    if not obs:
        return None
    return len(obs[-1]['filers'])


def shares_change_pct_13f_v1(events, sessions, setup_date):
    """Total-shares quarter-over-quarter change % between the latest two usable
    13F filings. NE when fewer than two usable filings."""
    obs = _filing_observations(events, sessions, setup_date)
    if len(obs) < 2:
        return None
    prev, latest = float(obs[-2]['shares']), float(obs[-1]['shares'])
    if prev == 0:
        return None
    return (latest - prev) / prev * 100.0


def new_filer_13f_v1(events, sessions, setup_date):
    """True when the latest usable 13F filing contains a filer absent from the
    previous usable filing. NE when fewer than two usable filings."""
    obs = _filing_observations(events, sessions, setup_date)
    if len(obs) < 2:
        return None
    return not obs[-1]['filers'] <= obs[-2]['filers']


# ---- I188 FINRA short interest (bi-weekly settlement publications) -----------

def _obs(records, setup_date, source):
    pool = [r for r in usable_events(records, setup_date)
            if r['source'] == source and r['session'] < setup_date]
    return sorted(pool, key=lambda r: (r['session'], r['public_dt']))


def si_pct_float_v1(records, setup_date):
    """Short interest as % of float, latest usable publication. NE when no
    usable publication or the float is zero."""
    obs = _obs(records, setup_date, 'short_interest')
    if not obs or float(obs[-1]['float_shares']) == 0:
        return None
    return float(obs[-1]['si_shares']) / float(obs[-1]['float_shares']) * 100.0


def si_days_to_cover_v1(records, setup_date):
    """Short interest / average daily volume, latest usable publication.
    NE when no usable publication or ADV is missing/zero."""
    obs = _obs(records, setup_date, 'short_interest')
    if not obs:
        return None
    adv = obs[-1].get('avg_daily_vol')
    if adv is None or float(adv) == 0:
        return None
    return float(obs[-1]['si_shares']) / float(adv)


def si_pct_percentile_v1(records, setup_date, lookback):
    """Percentile of the latest SI% within the last `lookback` PUBLICATION
    POINTS (own history, [0,1]). NE when fewer than `lookback` usable
    publications or a zero float occurs in them."""
    obs = _obs(records, setup_date, 'short_interest')
    if len(obs) < lookback:
        return None
    window = obs[-lookback:]
    values = []
    for r in window:
        if float(r['float_shares']) == 0:
            return None
        values.append(float(r['si_shares']) / float(r['float_shares']))
    latest = values[-1]
    return sum(1 for x in values if x <= latest) / len(values)


def si_tercile_state_change_v1(records, setup_date):
    """True when the SI% tercile (by percentile within the prior 11 publication
    points) moved across the 1/3 or 2/3 boundary between the last two usable
    publications. NE when fewer than 12 usable publications."""
    obs = _obs(records, setup_date, 'short_interest')
    if len(obs) < 12:
        return None
    def tercile(idx_end):
        window = obs[idx_end - 11:idx_end]
        vals = []
        for r in window:
            if float(r['float_shares']) == 0:
                return None
            vals.append(float(r['si_shares']) / float(r['float_shares']))
        latest = vals[-1]
        pct = sum(1 for x in vals if x <= latest) / len(vals)
        return 0 if pct <= 1 / 3 else (2 if pct >= 2 / 3 else 1)
    prev, latest_t = tercile(len(obs) - 1), tercile(len(obs))
    if prev is None or latest_t is None:
        return None
    return (prev < 1 < latest_t) or (prev > 1 > latest_t) or prev != latest_t and 1 in (prev, latest_t)


# ---- C26 sector membership (SEC SIC/GICS filed <= D-1) -----------------------

def sector_membership_days(records, sessions, setup_date):
    """Trading days the current sector code has been in force: sessions after
    the most recent usable publication whose sector_code differs from the
    latest usable one. NE when no usable publication."""
    obs = _obs(records, setup_date, 'sector')
    if not obs:
        return None
    current = obs[-1]['sector_code']
    change = None
    for o in reversed(obs[:-1]):
        if o['sector_code'] != current:
            change = o['session']
            break
    start = change if change is not None else obs[0]['session']
    return sum(1 for s in sessions if start < s < setup_date)


def sector_changed_within(records, sessions, setup_date, within):
    """True when the sector code most recently changed within the last
    `within` sessions. Evaluable (False) with a single usable publication."""
    obs = _obs(records, setup_date, 'sector')
    if not obs:
        return None
    current = obs[-1]['sector_code']
    # the current code began at its FIRST publication in the trailing same-code
    # run (not at the last publication of the previous code)
    first_of_current = obs[0]['session']
    for i in range(len(obs) - 1, 0, -1):
        if obs[i - 1]['sector_code'] != current:
            first_of_current = obs[i]['session']
            break
    days = sum(1 for s in sessions if first_of_current < s < setup_date)
    return days <= within


def sector_change_count(records, sessions, setup_date, window):
    """Number of sector-code transitions among usable publications whose
    session is within the last `window` sessions. NE when no usable
    publication in the window."""
    obs = [o for o in _obs(records, setup_date, 'sector')
           if o['session'] in set(_window_sessions(sessions, setup_date, window))]
    if not obs:
        return None
    return sum(1 for a, b in zip(obs, obs[1:]) if a['sector_code'] != b['sector_code'])


# ---- I193 shares outstanding (SEC dei) ---------------------------------------

def shares_out_change_pct_v1(records, setup_date):
    """Change % of shares outstanding between the latest two usable dei
    records. NE when fewer than two usable records or the prior value is 0."""
    obs = _obs(records, setup_date, 'shares_out')
    if len(obs) < 2 or float(obs[-2]['shares']) == 0:
        return None
    return (float(obs[-1]['shares']) - float(obs[-2]['shares'])) / float(obs[-2]['shares']) * 100.0


def shares_out_event_within(records, setup_date, threshold_pct):
    """True when a shares-outstanding change with |%| >= threshold occurred
    between the two latest usable records. NE when <2 usable records."""
    if len(_obs(records, setup_date, 'shares_out')) < 2:
        return None
    change = shares_out_change_pct_v1(records, setup_date)
    return abs(change) >= threshold_pct


# ---- I196 dividends ----------------------------------------------------------

def days_since_ex_dividend_v1(records, sessions, setup_date):
    """Trading days since the most recent usable ex-dividend date (event day
    = 0). NE when no usable dividend record."""
    obs = _obs(records, setup_date, 'dividend')
    if not obs:
        return None
    last = max(o['ex_date'] for o in obs)
    if last >= setup_date:
        return None
    return sum(1 for s in sessions if last < s < setup_date)


def dps_changed_v1(records, setup_date):
    """True when the dividend per share of the latest usable record differs
    from the previous usable record. NE when fewer than two usable records."""
    obs = _obs(records, setup_date, 'dividend')
    if len(obs) < 2:
        return None
    return float(obs[-1]['dps']) != float(obs[-2]['dps'])

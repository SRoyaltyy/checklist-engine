"""I074 traditional calendar pivots, sampled at native availability.

Calendar anchors are independent of candle size. They use complete daily HLC,
never HLC of a native candle straddling an anchor boundary. The prior calendar
period is selected relative to each native row's availability session. Missing
periods remain blank; an older successful period is never substituted.
"""
import numpy as np
import pandas as pd

from world_relative_context import _calendar, native_grid

ANCHORS = {'short': ('week', 'W-SUN'), 'default': ('month', 'M'),
           'long': ('quarter', 'Q-DEC')}
LEVELS = ('p', 'r1', 's1', 'r2', 's2')


def anchor_tables(bars, calendar, query_day):
    """Return complete/unknown HLC periods with exact session-count evidence.

    The first period in the supplied calendar is conservatively unavailable:
    its left boundary cannot be certified from a calendar starting inside it.
    A later period is complete only when a subsequent period has begun.
    """
    calendar = _calendar(calendar)
    day = pd.Timestamp(query_day)
    if day not in calendar or day.tz is not None:
        raise ValueError('pivot query must be an actual naive market session')
    if not {'date', 'high', 'low', 'close'} <= set(bars):
        raise ValueError('calendar pivots require explicit daily HLC')
    if 'ticker' in bars and (bars.ticker.isna().any() or bars.ticker.nunique() > 1):
        raise ValueError('calendar pivots require one literal ticker')
    dates = pd.DatetimeIndex(pd.to_datetime(bars.date)).as_unit('ns')
    if (dates.tz is not None or dates.hasnans or dates.has_duplicates
            or not dates.is_monotonic_increasing):
        raise ValueError('pivot price dates must be ordered unique and naive')
    own = bars[['high', 'low', 'close']].copy()
    own.index = dates
    own = own.loc[(own.index >= calendar[0]) & (own.index < day)]
    if not own.index.isin(calendar).all():
        raise ValueError('pivot price row outside the frozen market calendar')
    cal = calendar[calendar < day]
    aligned = own.reindex(cal).astype('float64')
    values = aligned.to_numpy()
    valid = (np.isfinite(values).all(axis=1) & (aligned.low.to_numpy() > 0)
             & (aligned.high.to_numpy() >= aligned.close.to_numpy())
             & (aligned.close.to_numpy() >= aligned.low.to_numpy()))
    result = {}
    for setting, (anchor, frequency) in ANCHORS.items():
        periods = cal.to_period(frequency)
        current = day.to_period(frequency)
        table = aligned.assign(session=cal, known=valid).groupby(periods, sort=True).agg(
            anchor_start=('session', 'first'), anchor_end=('session', 'last'),
            expected_sessions=('session', 'size'), known_sessions=('known', 'sum'),
            high=('high', 'max'), low=('low', 'min'), close=('close', 'last'))
        table = table.loc[table.index < current].copy()
        table['complete'] = ((table.index != calendar[0].to_period(frequency))
                             & table.known_sessions.eq(table.expected_sessions))
        table.loc[~table.complete, ['high', 'low', 'close']] = np.nan
        high, low, close = table.high, table.low, table.close
        table['p'] = p = (high + low + close) / 3
        table['r1'], table['s1'] = 2*p-low, 2*p-high
        table['r2'], table['s2'] = p+(high-low), p-(high-low)
        table.index = table.index.astype(str).rename('period')
        table.attrs = dict(anchor=anchor, frequency=frequency)
        result[setting] = table
    return result


def native_calendar_pivots(bars, calendar, timeframe, query_day):
    """Existing I074 short/default/long settings on the genuine native grid.

    The levels become known at the first session of the next anchor period.
    They are sampled when a native candle becomes available, then held by the
    existing row-view join until the next native availability. Calendar-anchor
    levels need not change with candle size; they are never rolling N-bar
    proxies. This function does not infer current-bar or trade eligibility.
    """
    calendar = _calendar(calendar)
    out = native_grid(calendar, timeframe, query_day)
    tables = anchor_tables(bars, calendar, query_day)
    receipts = {}
    for setting, (anchor, frequency) in ANCHORS.items():
        wanted = (pd.DatetimeIndex(out.available_from).to_period(frequency) - 1).astype(str)
        selected = tables[setting].reindex(wanted)
        for level in LEVELS:
            out['I074_' + setting + '_' + level] = selected[level].to_numpy(dtype='float64')
        receipts[setting] = dict(anchor=anchor, periods=len(tables[setting]),
                                complete_periods=int(tables[setting].complete.sum()),
                                native_known_rows=int(selected.p.notna().sum()))
    out.attrs = dict(item='I074', settings={k: v[0] for k, v in ANCHORS.items()},
                     timeframe=timeframe, query_day=str(pd.Timestamp(query_day).date()),
                     anchors=receipts, precision='float64',
                     prior_rule='Immediately preceding calendar period relative to native available_from; never carry across a missing period.',
                     boundary_rule='First calendar period unavailable; complete anchor HLC requires every expected daily session.',
                     source_rule='All daily HLC dates strictly before native availability and query D; no current partial anchor.',
                     full_universe_gate='NOT_RUN', world_gate='NOT_PROVEN', scoring_gate='CLOSED')
    return out

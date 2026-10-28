"""Monthly options expiry is the third Friday, or the previous NYSE session."""

import datetime as dt

import pandas as pd


def expiry_sessions(sessions):
    """Return expiry dates that fall inside the supplied session index."""
    days = pd.DatetimeIndex(pd.to_datetime(sessions)).sort_values().unique()
    session_set = set(days)
    found = []
    months = sorted({(day.year, day.month) for day in days})
    for year, month in months:
        first = dt.date(year, month, 1)
        offset = (4 - first.weekday()) % 7
        third = pd.Timestamp(first + dt.timedelta(days=offset + 14))
        if third in session_set:
            expiry = third
        else:
            earlier = days[days < third]
            if len(earlier) == 0:
                continue
            expiry = earlier[-1]
        if days.min() <= expiry <= days.max():
            found.append(expiry)
    return found

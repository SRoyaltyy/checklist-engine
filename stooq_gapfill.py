"""Coverage of the Stooq gap-fill files on the accepted stitch window.

Stooq prices are adjusted for splits and dividends. These rows are a side
check for the names left out of the accepted base. They do not replace that
base and they do not feed the running world build.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd


def parse_stooq_dates(text):
    """Daily bar dates from one Stooq file. The header is skipped."""
    dates = []
    for line in text.splitlines():
        parts = line.split(",")
        if len(parts) < 8 or not parts[2].isdigit() or len(parts[2]) != 8:
            continue
        dates.append(datetime.strptime(parts[2], "%Y%m%d").date())
    return dates


def classify_dates(dates, sessions):
    """Score one name on an inclusive session index.

    A late listing is not a hole when the bars from the first session through
    the last session cover at least 95 percent. A name that stops early keeps
    that same test and is labeled ended-before. Internal gaps below 95 percent
    are excluded. The caller keeps the file either way.
    """
    sessions = pd.DatetimeIndex(pd.to_datetime(list(sessions))).tz_localize(None)
    if len(sessions) == 0:
        raise ValueError("session window is empty")
    window = set(sessions.date)
    window_start = sessions[0].date()
    window_end = sessions[-1].date()
    in_window = sorted(day for day in set(dates) if day in window)
    if not in_window:
        return dict(status="EXCLUDE", reason="NO_WINDOW_BARS", internal_percent=0.0,
                    full_window_percent=0.0, first=None, last=None, bars_in_window=0,
                    span_sessions=0, window_sessions=len(sessions))
    first, last = in_window[0], in_window[-1]
    span = [day for day in sessions.date if first <= day <= last]
    internal = 100 * len(in_window) / len(span)
    full = 100 * len(in_window) / len(sessions)
    if internal < 95:
        reason = "HOLES_BETWEEN_FIRST_AND_LAST"
        status = "EXCLUDE"
    elif first == window_start and last == window_end:
        reason = "COVERS_WINDOW"
        status = "PASS"
    elif last < window_end:
        reason = "ENDED_BEFORE_WINDOW_END"
        status = "PASS"
    else:
        reason = "LISTED_AFTER_WINDOW_START"
        status = "PASS"
    return dict(status=status, reason=reason, internal_percent=round(internal, 4),
                full_window_percent=round(full, 4), first=first.isoformat(), last=last.isoformat(),
                bars_in_window=len(in_window), span_sessions=len(span), window_sessions=len(sessions))

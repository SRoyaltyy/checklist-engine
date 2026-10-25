"""Canonical nanosecond date keys for pandas/Arrow source joins."""
import pandas as pd


def date_ns(values, **kwargs):
    return pd.to_datetime(values, **kwargs).astype('datetime64[ns]')


def normalize_dates(frame):
    if frame is None:return None
    frame=frame.copy()
    for column in ('date','report_date','filed','file_date','period_end','period_start',
                   'period_ending','publication_date','obs_date','vintage_date','halt_d','resume_d'):
        if column in frame:frame[column]=date_ns(frame[column])
    return frame

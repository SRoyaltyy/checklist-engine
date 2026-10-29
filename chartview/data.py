"""Data loader for the viewport gallery.

Reads a daily-ohlcv parquet with columns date, open, high, low, close, volume
(the light-daily-box release schema) and truncates at the setup date:
cutoff = last bar with date < S. Day-S OHLCV is never read (#159 rule 2).
"""
import numpy as np
import pandas as pd


def load_daily(path):
    df = pd.read_parquet(path)
    df = df.sort_values('date').reset_index(drop=True)
    df['date'] = pd.to_datetime(df['date'])
    need = {'date', 'open', 'high', 'low', 'close', 'volume'}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f'{path}: missing columns {sorted(missing)}')
    return df


def as_of(df, setup_date):
    """-> (dates, O, H, L, C, V, cutoff). Only bars with candle end < setup_date."""
    setup = pd.Timestamp(setup_date)
    m = df['date'].values < np.datetime64(setup)
    if not m.any():
        raise ValueError(f'no bars before {setup_date} in {len(df)} rows')
    sub = df.loc[m]
    return (sub['date'].values,
            sub['open'].to_numpy(float), sub['high'].to_numpy(float),
            sub['low'].to_numpy(float), sub['close'].to_numpy(float),
            sub['volume'].to_numpy(float), len(sub) - 1)

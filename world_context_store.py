"""Lossless factored stock-day view of already stored native context values.

The reader performs availability joins, not indicator recomputation. Shared
values remain stored once and every declared feature column stays addressable.
"""
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from world_context_native import KEYS,attach_context


def validate_factor(frame):
    if not set(KEYS)<=set(frame):raise ValueError('native context keys missing')
    dates=pd.DatetimeIndex(frame.available_from)
    if (dates.tz is not None or dates.hasnans or dates.has_duplicates or not dates.is_monotonic_increasing
        or not (frame.source_candle_end<frame.available_from).all()
        or not (frame.candle_start<=frame.source_candle_end).all()):
        raise ValueError('native context availability invalid')
    columns=[c for c in frame if c not in KEYS]
    if (not columns or len(set(frame))!=len(frame.columns)
        or any(not is_numeric_dtype(frame[c]) for c in columns)
        or any(c.startswith('execution_') or c=='ticker' for c in columns)):
        raise ValueError('context feature schema invalid or contains execution-only fields')
    return columns


def context_row_view(ticker,query_dates,timeframe,factors):
    """Return one stock session row with every stored requested factor column."""
    if not isinstance(ticker,str) or not ticker:raise ValueError('literal stock identity required')
    if not factors:raise ValueError('at least one native factor required')
    output=pd.DataFrame({'date':pd.DatetimeIndex(query_dates).as_unit('ns')})
    for frame in factors:
        validate_factor(frame)
        attached=attach_context(query_dates,frame,timeframe)
        columns=[c for c in attached if c!='date']
        if set(columns)&set(output):raise ValueError('duplicate context features')
        if not attached.date.equals(output.date):raise ValueError('context stock-session row keys differ')
        output=pd.concat([output,attached[columns]],axis=1)
    output.insert(0,'ticker',ticker)
    return output


def checked_weights(frame):
    if set(frame)!= {'date','stock_days'}:raise ValueError('stock-day weights schema differs')
    dates=pd.DatetimeIndex(pd.to_datetime(frame.date)).as_unit('ns')
    values=pd.to_numeric(frame.stock_days,errors='raise').to_numpy(dtype=float)
    if (dates.tz is not None or dates.hasnans or dates.has_duplicates or not dates.is_monotonic_increasing
        or not np.isfinite(values).all() or not (values>0).all() or (values%1!=0).any()
        or (values>8727).any()):
        raise ValueError('stock-day weights must be ordered unique dates and positive exact integer counts')
    return dates,values.astype(np.int64)


def weighted_coverage(native,weights,timeframe,family):
    """Exact all-stock counts from date weights; do not substitute session counts."""
    columns=validate_factor(native);dates,multipliers=checked_weights(weights)
    attached=attach_context(dates,native,timeframe)
    total=int(multipliers.sum());rows=[]
    for column in columns:
        name=column+'__'+timeframe;valid=attached[name].notna().to_numpy()
        count=int(multipliers[valid].sum());present=dates[valid]
        rows.append(dict(family=family,timeframe=timeframe,native_column=column,column=name,
            dtype=str(native[column].dtype),query_stock_days=total,non_null_stock_days=count,
            non_null_pct=100*count/total if total else 0,first_date=str(present.min().date()) if len(present) else '',
            last_date=str(present.max().date()) if len(present) else '',query_market_sessions=len(dates),
            non_null_market_sessions=int(valid.sum()),
            status='MEASURED_NATIVE_FACTOR_ON_APPROVED_STOCK_DAYS' if count else 'NO_OBSERVED_VALUES',
            denominator='EXACT_APPROVED_STITCH_STOCK_DAY_WEIGHTS'))
    return rows

"""On-demand stock/ETF comparisons on genuine, complete native candle grids.

Only existing registered formulas/settings are applied. A literal benchmark
does not select a stock's historical sector/industry, and no current mapping
is inferred. Inputs, registry and code must be bound by the calling recipe.
"""
import re

import numpy as np
import pandas as pd

from outside_compare import compare_one, FLAT, FALL, BREAK_BASELINE
from outside_market import NAMED_ETFS, INDUSTRY_ETFS, completed_market_candles
from world_bar_statistics import relative_statistics
from world_context_native import KEYS, native_intervals
from world_context_store import context_row_view, validate_factor
from world_timeframes import PRICE_COLS, TIMEFRAMES

RETURN_WINDOWS = (1,5,10,20,60)
CORRELATION_WINDOWS = (5,10,20,60)


def _calendar(values):
    dates=pd.DatetimeIndex(pd.to_datetime(values)).as_unit('ns')
    if (dates.empty or dates.tz is not None or dates.hasnans or dates.has_duplicates
            or not dates.is_monotonic_increasing):
        raise ValueError('relative context needs ordered unique naive calendar sessions')
    return dates


def native_grid(calendar,timeframe,query_day):
    """Use the frozen anchor and actual next session for monthly availability."""
    calendar=_calendar(calendar)
    day=pd.Timestamp(query_day)
    if day.tz is not None or day not in calendar:
        raise ValueError('query day must be an actual naive market session')
    grid=native_intervals(calendar,timeframe)
    positions=calendar.searchsorted(pd.DatetimeIndex(grid.source_candle_end),side='right')
    if (positions>=len(calendar)).any():
        raise ValueError('native interval has no next market session')
    grid['available_from']=calendar[positions].to_numpy()
    return grid.loc[grid.available_from<=day,list(KEYS)].reset_index(drop=True)


def _on_grid(bars,calendar,timeframe,day,grid):
    required={'date',*PRICE_COLS}
    if not required <= set(bars):
        raise ValueError('native comparisons require explicit daily OHLCV')
    own=bars.loc[:,['date',*PRICE_COLS]].copy()
    dates=pd.DatetimeIndex(pd.to_datetime(own.date)).as_unit('ns')
    if dates.tz is not None or dates.hasnans or dates.has_duplicates or not dates.is_monotonic_increasing:
        raise ValueError('daily comparison dates must be ordered unique and naive')
    own['date']=dates
    # The query-day open is never read. The complete daily row is excluded.
    own=own.loc[(own.date>=calendar[0])&(own.date<pd.Timestamp(day))].copy()
    if not pd.DatetimeIndex(own.date).isin(calendar).all():
        raise ValueError('daily comparison row outside the frozen calendar')
    valid=np.isfinite(own[list(PRICE_COLS)].to_numpy(dtype='float64')).all(axis=1)
    invalid=int((~valid).sum())
    candles=completed_market_candles(own.loc[valid],timeframe,calendar)
    candles=candles.rename(columns={'date':'source_candle_end'})
    for key in KEYS:
        candles[key]=pd.to_datetime(candles[key]).astype('datetime64[ns]')
    aligned=grid.merge(candles,on=list(KEYS),how='left',validate='one_to_one')
    return aligned,dict(known_daily_rows=len(own),invalid_ohlcv_rows=invalid,
                        complete_native_rows=int(aligned.close.notna().sum()),
                        unavailable_native_rows=int(aligned.close.isna().sum()))


def ratio_variants(numerator,denominator):
    a=np.asarray(numerator,dtype='float64');b=np.asarray(denominator,dtype='float64')
    if a.shape!=b.shape:
        raise ValueError('relative ratio operand shapes differ')
    blank=np.full(a.shape,np.nan,dtype='float64')
    finite=np.isfinite(a)&np.isfinite(b)
    np.divide(a,b,out=blank,where=finite&(b!=0))
    infinite=blank.copy()
    infinite[finite&(b==0)&(a>0)]=np.inf
    infinite[finite&(b==0)&(a<0)]=-np.inf
    return infinite,blank


def native_comparisons(ticker,benchmark,stock_bars,benchmark_bars,calendar,timeframe,query_day,
                       *,windows=RETURN_WINDOWS,correlation_windows=CORRELATION_WINDOWS,
                       flat=FLAT,fall=FALL,break_baseline=BREAK_BASELINE):
    """Return one bounded native frame; never materialize the universe matrix.

    Missing/invalid native intervals remain explicit NaN rows before any
    lookback computation. Windows count native candles, never joined dates.
    Literal self-comparisons are explicitly excluded with missing outcomes.
    """
    if not isinstance(ticker,str) or not ticker or ticker!=ticker.strip():
        raise ValueError('literal target ticker required')
    if benchmark not in set(NAMED_ETFS)|set(INDUSTRY_ETFS):
        raise ValueError('literal benchmark must be an existing registered ETF')
    if timeframe not in TIMEFRAMES:
        raise ValueError('unknown relative timeframe')
    windows=tuple(windows)
    correlation_windows=tuple(correlation_windows)
    for identity,source in ((ticker,stock_bars),(benchmark,benchmark_bars)):
        if 'ticker' in source and set(source.ticker)!={identity}:
            raise ValueError('daily price identity differs from literal source')
    calendar=_calendar(calendar)
    grid=native_grid(calendar,timeframe,query_day)
    stock,stock_meta=_on_grid(stock_bars,calendar,timeframe,query_day,grid)
    other,other_meta=_on_grid(benchmark_bars,calendar,timeframe,query_day,grid)
    left=stock[['source_candle_end','close']].rename(columns={'source_candle_end':'date'})
    right=other[['source_candle_end','close']].rename(columns={'source_candle_end':'date'})
    base=compare_one(left,right,windows=windows,correlation_windows=correlation_windows,
                     flat=flat,fall=fall,break_baseline=break_baseline)
    if not base.date.equals(grid.source_candle_end.rename('date')):
        raise ValueError('comparison formulas compressed or changed the native grid')
    # Existing I218/I219/Mansfield definitions, with explicit float64 output.
    registered=relative_statistics(stock.rename(columns={'source_candle_end':'date'}),
                                   other.rename(columns={'source_candle_end':'date'}),
                                   'benchmark',dtype=np.float64)
    prefix='relative_'+benchmark.lower()+'_'
    out=grid.copy()
    for name in base:
        if name!='date':
            out[prefix+re.sub(r'_(\d+)d$',r'_n\1',name)]=base[name].to_numpy(dtype='float64')
    for name,values in registered.items():
        out[prefix+name.replace('_benchmark_','_n')]=values
    infinite,blank=ratio_variants(stock.close,other.close)
    out[prefix+'ratio_inf']=infinite
    out[prefix+'ratio_blank']=blank
    with np.errstate(divide='ignore',invalid='ignore'):
        out[prefix+'log_rs_inf']=np.where(infinite>0,np.log(infinite),np.nan)
        out[prefix+'log_rs_blank']=np.where(blank>0,np.log(blank),np.nan)
    features=validate_factor(out) if len(out) else [c for c in out if c not in KEYS]
    if ticker==benchmark:
        out.loc[:,features]=np.nan
    out.attrs=dict(ticker=ticker,benchmark=benchmark,timeframe=timeframe,query_day=str(pd.Timestamp(query_day).date()),
                   windows=list(windows),correlation_windows=list(correlation_windows),flat=float(flat),fall=float(fall),
                   correlation_break_native_baseline=break_baseline,stock=stock_meta,benchmark_source=other_meta,
                   self_comparison_exclusion='SELF_COMPARISON' if ticker==benchmark else None,
                   membership='LITERAL_BENCHMARK_ONLY_NO_SECTOR_OR_INDUSTRY_SELECTION',
                   source_rule='Every expected native session present; source candle end < available_from <= query D; no day-D OHLCV',
                   numeric_precision='float64, no tolerance rounding',storage='Recompute one stock/benchmark/timeframe on demand from bound raw inputs and code',
                   world_gate='NOT_PROVEN',scoring_gate='CLOSED')
    return out


def relative_row_view(ticker,query_dates,benchmark,stock_bars,benchmark_bars,calendar,timeframe,**settings):
    dates=_calendar(query_dates)
    if not dates.isin(_calendar(calendar)).all():
        raise ValueError('relative query dates outside the market calendar')
    native=native_comparisons(ticker,benchmark,stock_bars,benchmark_bars,calendar,timeframe,dates[-1],**settings)
    rows=context_row_view(ticker,dates,timeframe,[native])
    rows.attrs=dict(native.attrs)
    return rows

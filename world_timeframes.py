"""Completed-candle world state. No candle containing day D is visible at D.

5d/10d/20d candles are non-overlapping trading-session blocks. A supplied
market-session calendar fixes shared boundaries across entities; legacy callers
without one retain the first supplied entity session as anchor. monthly uses actual calendar months, not
21 daily values relabelled as monthly. Prefix truncation preserves the anchor.
"""
import numpy as np
import pandas as pd

TIMEFRAMES = tuple(f'{k}d' for k in range(1,22)) + ('monthly',)
PRICE_COLS = ('open', 'high', 'low', 'close', 'volume')


def completed_candles(bars, timeframe, session_calendar=None):
    """Aggregate actual sessions. A supplied calendar gives every entity the
    same interval boundaries; partial IPO/halt buckets are omitted explicitly.
    Without it, retain the original per-entity anchor for legacy callers.
    """
    b = bars.sort_values('date').reset_index(drop=True).copy()
    if b.date.duplicated().any():
        raise ValueError('duplicate ticker sessions')
    b['date'] = pd.to_datetime(b.date).astype('datetime64[ns]')
    columns=['candle_start','date','available_from',*PRICE_COLS]
    if not len(b):
        return pd.DataFrame(columns=columns)
    if timeframe not in TIMEFRAMES:
        raise ValueError(timeframe)
    cal=None;expected={}
    if session_calendar is not None:
        cal=pd.DatetimeIndex(pd.to_datetime(session_calendar)).as_unit('ns')
        if cal.has_duplicates or not cal.is_monotonic_increasing:
            raise ValueError('session calendar must be ordered and unique')
        positions=cal.get_indexer(b.date)
        if np.any(positions<0):
            raise ValueError('entity has dates outside the shared session calendar')
    if timeframe == 'monthly':
        key = b.date.dt.to_period('M')
        avail = {p: (p + 1).start_time for p in key.unique()}
        if cal is not None:
            for p in key.unique():
                # A source calendar ending inside a month cannot certify that
                # month complete. Later months provide its completion proof.
                if p>=cal[-1].to_period('M'):continue
                expected[p]=cal[cal.to_period('M')==p]
    else:
        k=int(timeframe[:-1])
        key=(positions//k) if cal is not None else np.arange(len(b))//k
        if cal is not None:
            avail={i:cal[(i+1)*k] for i in np.unique(key) if (i+1)*k<len(cal)}
            expected={i:cal[i*k:(i+1)*k] for i in avail}
        else:
            avail={i:b.date.iloc[(i+1)*k] for i in np.unique(key) if (i+1)*k<len(b)}
    grouped=b.groupby(key,sort=True)
    result=grouped.agg(candle_start=('date','first'),date=('date','last'),
        open=('open','first'),high=('high','max'),low=('low','min'),
        close=('close','last'),volume=('volume','sum'))
    result['available_from']=result.index.map(avail.get)
    valid=result.available_from.notna()
    if cal is not None:
        counts=grouped.size()
        wanted_count=pd.Series({g:len(ds) for g,ds in expected.items()})
        wanted_start=pd.Series({g:ds[0] for g,ds in expected.items()})
        wanted_end=pd.Series({g:ds[-1] for g,ds in expected.items()})
        valid &= counts.eq(wanted_count.reindex(result.index))
        valid &= result.candle_start.eq(wanted_start.reindex(result.index))
        valid &= result.date.eq(wanted_end.reindex(result.index))
    result=result.loc[valid,columns].reset_index(drop=True)
    for column in ('candle_start','date','available_from'):
        result[column]=pd.to_datetime(result[column]).astype('datetime64[ns]')
    return result


def parameter_variants(o, h, l, c, v):
    """Named dictionary periods, distinct from TA-Lib's default instances."""
    import talib
    out = {}
    for name, periods in {'SMA': tuple(range(5,251)),
                          'EMA': (8,13,20,21,34,55), 'RSI': (6,12,14,24),
                          'ROC': (5,20,60), 'WMA': (9,20,50,100,200), 'DEMA': (9,20,50,100,200),
                          'TEMA': (9,20,50,100,200), 'KAMA': (9,20,50,100,200), 'LINEARREG': (9,20,50,100,200)}.items():
        fn = getattr(talib, name)
        for n in periods:
            out[f'{name}{n}'] = fn(c, timeperiod=n).astype(np.float32)
    upper,mid,lower=talib.BBANDS(c,timeperiod=20,nbdevup=2,nbdevdn=2,matype=0)
    out['BBANDS20_upper']=upper.astype(np.float32)
    out['BBANDS20_mid']=mid.astype(np.float32)
    out['BBANDS20_lower']=lower.astype(np.float32)
    sk,sd=talib.STOCH(h,l,c,fastk_period=14,slowk_period=3,slowk_matype=0,slowd_period=3,slowd_matype=0)
    out['STOCH14_3_3_k']=sk.astype(np.float32)
    out['STOCH14_3_3_d']=sd.astype(np.float32)
    out['ATR14'] = talib.ATR(h,l,c,timeperiod=14).astype(np.float32)
    out['CCI20'] = talib.CCI(h,l,c,timeperiod=20).astype(np.float32)
    out['MFI14'] = talib.MFI(h,l,c,v,timeperiod=14).astype(np.float32)
    out['WILLR14'] = talib.WILLR(h,l,c,timeperiod=14).astype(np.float32)
    for name in ('ADX','PLUS_DI','MINUS_DI'):
        out[f'{name}14'] = getattr(talib,name)(h,l,c,timeperiod=14).astype(np.float32)
    out['RVOL20'] = (pd.Series(v)/pd.Series(v).rolling(20).mean()).to_numpy(np.float32)
    return out


def candle_features(candles, funcs, timeframe="1d"):
    import facets_world as fw
    if not len(candles):
        return pd.DataFrame(columns=['available_from'])
    arrays = [candles[x].to_numpy(dtype=float) for x in PRICE_COLS]
    cols = fw.compute_talib(*arrays, funcs)
    cols.update(parameter_variants(*arrays))
    from world_indicator_settings import configured_indicators
    from world_bar_statistics import bar_statistics
    cols.update(configured_indicators(*arrays, dates=candles.date.to_numpy()))
    cols.update(bar_statistics(*arrays, timeframe=timeframe))
    from world_food_statistics import additional_bar_statistics
    cols.update(additional_bar_statistics(*arrays))
    from world_moving_averages import extra_moving_averages
    cols.update(extra_moving_averages(*arrays))
    # Existing TV extras require at least one bar; all warmups remain explicit
    # NaNs. Schema alignment never treats an absent feature as an observed zero.
    cols.update(fw.compute_tv_extra(*arrays, dates=candles.date.to_numpy()))
    cols.update({name: values.astype(np.float32) for name,values in zip(PRICE_COLS,arrays)})
    frame = pd.DataFrame(cols)
    frame['available_from'] = pd.to_datetime(candles.available_from).astype('datetime64[ns]').to_numpy()
    return frame


def align_features(query_dates, features, timeframe):
    q = pd.DataFrame({'date': pd.to_datetime(query_dates).astype('datetime64[ns]')})
    if features.empty:
        return q
    aligned = pd.merge_asof(q, features.sort_values('available_from'),
                            left_on='date', right_on='available_from',
                            direction='backward', allow_exact_matches=True)
    # The source candle ended BEFORE available_from, which may equal D.
    aligned = aligned.drop(columns='available_from')
    return aligned.rename(columns={c:f'{c}__{timeframe}' for c in aligned if c!='date'})


def world_timeframes(bars, funcs, daily_external=None, session_calendar=None):
    """One row per stock session. External fields are already strictly PIT;
    aggregate their last KNOWN value at each completed candle boundary. Keep
    these separate from indicators recomputed on genuine composite OHLCV.
    """
    out = pd.DataFrame({'date': pd.to_datetime(bars.date).to_numpy()})
    for tf in TIMEFRAMES:
        candles = completed_candles(bars, tf, session_calendar=session_calendar)
        features = candle_features(candles, funcs, timeframe=tf)
        if daily_external is not None and len(candles):
            ext = daily_external.sort_values('date').copy()
            ext['date']=pd.to_datetime(ext.date).astype('datetime64[ns]')
            extcols = [c for c in ext if c not in ('ticker','date')]
            ext = pd.merge_asof(candles[['available_from']].sort_values('available_from'),
                                ext[['date', *extcols]].sort_values('date'),
                                left_on='available_from', right_on='date', direction='backward')
            for c in extcols:
                features[c] = ext[c].to_numpy()
            # Difference windows count native candles after sampling known levels.
            for c in extcols:
                if c.startswith('fred_') and not c.endswith(('_odays','_vintage_days')):
                    for window in (20,60):features[c+'_change'+str(window)]=ext[c].diff(window).to_numpy()
        out = out.merge(align_features(bars.date, features, tf), on='date', how='left')
    return out

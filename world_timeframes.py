"""Completed-candle world state. No candle containing day D is visible at D.

5d/10d/20d candles are non-overlapping trading-session blocks anchored at the
first supplied historical session. monthly uses actual calendar months, not
21 daily values relabelled as monthly. Prefix truncation preserves the anchor.
"""
import numpy as np
import pandas as pd

TIMEFRAMES = ('1d', '5d', '10d', '20d', 'monthly')
PRICE_COLS = ('open', 'high', 'low', 'close', 'volume')


def completed_candles(bars, timeframe):
    b = bars.sort_values('date').reset_index(drop=True).copy()
    if b.date.duplicated().any():
        raise ValueError('duplicate ticker sessions')
    b['date'] = pd.to_datetime(b.date).astype('datetime64[ns]')
    if not len(b):
        return pd.DataFrame(columns=['date', 'available_from', *PRICE_COLS])
    if timeframe == 'monthly':
        key = b.date.dt.to_period('M')
        avail = {p: (p + 1).start_time for p in key.unique()}
    else:
        if timeframe not in TIMEFRAMES:
            raise ValueError(timeframe)
        k = int(timeframe[:-1])
        key = np.arange(len(b)) // k
        # The next observed stock session is the earliest query row allowed to
        # consume a completed candle. Last/incomplete groups are not exposed.
        avail = {i: b.date.iloc[(i + 1) * k] for i in np.unique(key)
                 if (i + 1) * k < len(b)}
    rows = []
    for group, g in b.groupby(key, sort=True):
        if group not in avail:
            continue
        rows.append(dict(date=g.date.iloc[-1], available_from=avail[group],
                         open=g.open.iloc[0], high=g.high.max(), low=g.low.min(),
                         close=g.close.iloc[-1], volume=g.volume.sum()))
    result=pd.DataFrame(rows, columns=['date','available_from',*PRICE_COLS])
    for column in ('date','available_from'):
        result[column]=pd.to_datetime(result[column]).astype('datetime64[ns]')
    return result


def parameter_variants(o, h, l, c, v):
    """Named dictionary periods, distinct from TA-Lib's default instances."""
    import talib
    out = {}
    for name, periods in {'SMA': (5,10,20,30,50,100,200),
                          'EMA': (20,21), 'RSI': (6,12,14,24),
                          'ROC': (5,20,60), 'WMA': (20,), 'DEMA': (20,),
                          'TEMA': (20,), 'KAMA': (20,), 'LINEARREG': (100,)}.items():
        fn = getattr(talib, name)
        for n in periods:
            out[f'{name}{n}'] = fn(c, timeperiod=n).astype(np.float32)
    out['ATR14'] = talib.ATR(h,l,c,timeperiod=14).astype(np.float32)
    out['CCI20'] = talib.CCI(h,l,c,timeperiod=20).astype(np.float32)
    out['MFI14'] = talib.MFI(h,l,c,v,timeperiod=14).astype(np.float32)
    out['WILLR14'] = talib.WILLR(h,l,c,timeperiod=14).astype(np.float32)
    for name in ('ADX','PLUS_DI','MINUS_DI'):
        out[f'{name}14'] = getattr(talib,name)(h,l,c,timeperiod=14).astype(np.float32)
    out['RVOL20'] = (pd.Series(v)/pd.Series(v).rolling(20).mean()).to_numpy(np.float32)
    return out


def candle_features(candles, funcs):
    import facets_world as fw
    if not len(candles):
        return pd.DataFrame(columns=['available_from'])
    arrays = [candles[x].to_numpy(dtype=float) for x in PRICE_COLS]
    cols = fw.compute_talib(*arrays, funcs)
    cols.update(parameter_variants(*arrays))
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


def world_timeframes(bars, funcs, daily_external=None):
    """One row per stock session. External fields are already strictly PIT;
    aggregate their last KNOWN value at each completed candle boundary. Keep
    these separate from indicators recomputed on genuine composite OHLCV.
    """
    out = pd.DataFrame({'date': pd.to_datetime(bars.date).to_numpy()})
    for tf in TIMEFRAMES:
        candles = completed_candles(bars, tf)
        features = candle_features(candles, funcs)
        if daily_external is not None and len(candles):
            ext = daily_external.sort_values('date').copy()
            ext['date']=pd.to_datetime(ext.date).astype('datetime64[ns]')
            extcols = [c for c in ext if c not in ('ticker','date')]
            ext = pd.merge_asof(candles[['available_from']].sort_values('available_from'),
                                ext[['date', *extcols]].sort_values('date'),
                                left_on='available_from', right_on='date', direction='backward')
            for c in extcols:
                features[c] = ext[c].to_numpy()
        out = out.merge(align_features(bars.date, features, tf), on='date', how='left')
    return out

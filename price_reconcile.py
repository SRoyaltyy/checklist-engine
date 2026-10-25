"""Extend frozen indicator prices only after an explicit overlap integrity check.
No claim is made that the vendor quote is a historical nominal price.
"""
import numpy as np
import pandas as pd
from world_dates import date_ns
PRICE = ['open','high','low','close']
FIELDS = ['ticker','date',*PRICE,'volume']


def reconcile_one(ticker, frozen, supplemental, min_overlap=60):
    old=frozen.copy();new=supplemental.copy()
    for frame in (old,new):
        frame['date']=date_ns(frame.date)
        if frame.date.duplicated().any():raise ValueError(f'{ticker}: duplicate daily dates')
    old=old.sort_values('date');new=new.sort_values('date')
    overlap=old[['date','close','volume']].merge(new[['date','close','volume']],on='date',suffixes=('_frozen','_new')).dropna()
    if len(overlap)<min_overlap:raise ValueError(f'{ticker}: insufficient overlap: {len(overlap)}')
    if (overlap[['close_frozen','close_new']]<=0).any().any():raise ValueError(f'{ticker}: nonpositive close')
    diff=(overlap.close_frozen.pct_change(fill_method=None)-overlap.close_new.pct_change(fill_method=None)).abs().dropna()
    volume=(overlap.volume_frozen/overlap.volume_new.replace(0,np.nan)).replace([np.inf,-np.inf],np.nan).dropna()
    evidence=dict(ticker=ticker,overlap_rows=len(overlap),median_return_difference=float(diff.median()),
        p99_return_difference=float(diff.quantile(.99)),median_volume_ratio=float(volume.median()),
        frozen_start=str(old.date.min().date()),frozen_end=str(old.date.max().date()),
        supplemental_start=str(new.date.min().date()),supplemental_end=str(new.date.max().date()),
        nominal_historical_price_verified=False)
    if not (evidence['median_return_difference']<=.002 and evidence['p99_return_difference']<=.02
            and .8<=evidence['median_volume_ratio']<=1.25):
        raise ValueError(f'PRICE_RECONCILIATION_FAIL {evidence}')
    first=float(overlap.iloc[0].close_frozen/overlap.iloc[0].close_new)
    last=float(overlap.iloc[-1].close_frozen/overlap.iloc[-1].close_new)
    early=new[new.date<old.date.min()].copy();late=new[new.date>old.date.max()].copy()
    early[PRICE]=early[PRICE]*first;late[PRICE]=late[PRICE]*last
    result=pd.concat([early[FIELDS],old[FIELDS],late[FIELDS]],ignore_index=True)
    retained=result[result.date.isin(old.date)].reset_index(drop=True)
    for field in PRICE+['volume']:
        np.testing.assert_array_equal(retained[field].to_numpy(),old[field].to_numpy())
    evidence.update(status='PASS',warmup_rows=len(early),extension_rows=len(late),
        first_overlap_scale=first,last_overlap_scale=last,frozen_values_unchanged=True)
    return result,evidence

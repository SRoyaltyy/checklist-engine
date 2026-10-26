"""Extend frozen indicator prices only after an explicit, evidence-backed bridge.
Quote prices preserve the locked split-adjusted basis; nominal price/liquidity
remain separate gates. Later split metadata changes units, never frozen values.
"""
import numpy as np
import pandas as pd
from world_dates import date_ns
PRICE=['open','high','low','close']
FIELDS=['ticker','date',*PRICE,'volume']

def reconcile_one(ticker,frozen,supplemental,min_overlap=60,allow_short_history=False,events=None):
    old=frozen.copy();new=supplemental.copy();basis='provided_indicator_basis'
    if all('vendor_'+c in new for c in PRICE):
        for column in PRICE:new[column]=new['vendor_'+column]
        basis='vendor_split_adjusted_quote_matching_frozen'
    if 'vendor_volume' in new:new['volume']=new.vendor_volume
    for frame in (old,new):
        frame['date']=date_ns(frame.date)
        if frame.date.duplicated().any():raise ValueError(f'{ticker}: duplicate daily dates')
    old=old.sort_values('date');new=new.sort_values('date')
    overlap=old[['date','close','volume']].merge(new[['date','close','volume']],on='date',suffixes=('_frozen','_new')).dropna()
    short_exact=False
    if len(overlap)<min_overlap:
        if allow_short_history and 2<=len(old)<min_overlap and len(overlap)==len(old) and old.date.min()==new.date.min():
            both=old[['date',*PRICE,'volume']].merge(new[['date',*PRICE,'volume']],on='date',suffixes=('_old','_new'))
            short_exact=all(np.allclose(both[c+'_old'],both[c+'_new'],rtol=1e-5,atol=1e-6,equal_nan=False) for c in PRICE+['volume'])
        if not short_exact:raise ValueError(f'{ticker}: insufficient overlap: {len(overlap)}; exact complete short-history verification={short_exact}')
    if (overlap[['close_frozen','close_new']]<=0).any().any():raise ValueError(f'{ticker}: nonpositive close')
    split_evidence=[];volume_scale=1.
    original_volume=overlap.volume_frozen/overlap.volume_new.replace(0,np.nan)
    if events is not None and len(events):
        later=events[(events.kind=='split')&(pd.to_datetime(events.date)>old.date.max())&(pd.to_datetime(events.date)<=new.date.max())]
        split_product=float(later.value.prod())
        price_scale=float((overlap.close_frozen/overlap.close_new).median())
        if len(later) and split_product>0 and np.isclose(price_scale,split_product,rtol=.002) and not .8<=float(original_volume.median())<=1.25:
            candidate_scale=1./split_product
            error=(overlap.volume_frozen-overlap.volume_new*candidate_scale).abs()
            tolerance=abs(candidate_scale)+1+.001*overlap.volume_frozen.abs()
            if (error<=tolerance).mean()>=.99:
                volume_scale=candidate_scale;new['volume']*=volume_scale
                overlap['volume_new']*=volume_scale
                split_evidence=later.astype({'date':str}).to_dict('records')
    zero_volume=bool((overlap[['volume_frozen','volume_new']]==0).all().all())
    diff=(overlap.close_frozen.pct_change(fill_method=None)-overlap.close_new.pct_change(fill_method=None)).abs().dropna()
    volume=(overlap.volume_frozen/overlap.volume_new.replace(0,np.nan)).replace([np.inf,-np.inf],np.nan).dropna()
    evidence=dict(ticker=ticker,overlap_rows=len(overlap),median_return_difference=float(diff.median()),
        p99_return_difference=float(diff.quantile(.99)),median_volume_ratio=float(volume.median()),
        frozen_start=str(old.date.min().date()),frozen_end=str(old.date.max().date()),
        supplemental_start=str(new.date.min().date()),supplemental_end=str(new.date.max().date()),
        nominal_historical_price_verified=False,supplemental_basis=basis,
        short_history_all_sessions_exact=short_exact,original_minimum_overlap=min_overlap,
        volume_normalization_scale=volume_scale,split_normalization_events=split_evidence,
        all_overlap_volumes_zero=zero_volume)
    if not (evidence['median_return_difference']<=.002 and evidence['p99_return_difference']<=.02
            and (zero_volume or .8<=evidence['median_volume_ratio']<=1.25)):
        raise ValueError(f'PRICE_RECONCILIATION_FAIL {evidence}')
    first=float(overlap.iloc[0].close_frozen/overlap.iloc[0].close_new)
    last=float(overlap.iloc[-1].close_frozen/overlap.iloc[-1].close_new)
    early=new[new.date<old.date.min()].copy();late=new[new.date>old.date.max()].copy()
    early[PRICE]=early[PRICE]*first;late[PRICE]=late[PRICE]*last
    result=pd.concat([early[FIELDS],old[FIELDS],late[FIELDS]],ignore_index=True)
    retained=result[result.date.isin(old.date)].reset_index(drop=True)
    for field in PRICE+['volume']:np.testing.assert_array_equal(retained[field].to_numpy(),old[field].to_numpy())
    evidence.update(status='PASS',warmup_rows=len(early),extension_rows=len(late),
        first_overlap_scale=first,last_overlap_scale=last,frozen_values_unchanged=True)
    return result,evidence

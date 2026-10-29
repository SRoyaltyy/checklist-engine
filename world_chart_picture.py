"""Pinned chart-picture values/tags from METHODOLOGY11a01175; no new questions.

Every input is a completed native candle. The native adapter excludes day D
and preserves unavailable intervals before computing any lookback.
"""
from dataclasses import asdict,dataclass

import numpy as np
import pandas as pd


PIN='11a01175af8fc7dd0a842ac823d2b0835e556d8b'
MINIMUM_BARS=60


@dataclass(frozen=True)
class ChartSettings:
    bb_period:int=20
    bb_width:float=2.
    atr_period:int=14
    high_window:int=20
    prior_low_window:int=20
    mid_lag:int=5
    body_window:int=20
    body_threshold:float=.9
    pct_b_threshold:float=.12
    dip_atr_limit:float=4.2
    high_age_min:int=5
    high_age_max:int=18
    dd_run_threshold:float=.5
    volume_window:int=10
    volume_threshold:float=1.
    lower_high_window:int=10

    def __post_init__(self):
        for key in ('bb_period','atr_period','high_window','prior_low_window','mid_lag','body_window','volume_window','lower_high_window'):
            if type(getattr(self,key)) is not int or getattr(self,key)<1:raise ValueError('positive integer chart window required: '+key)
        if (type(self.high_age_min) is not int or type(self.high_age_max) is not int
                or not 0<=self.high_age_min<=self.high_age_max<self.high_window):raise ValueError('chart high-age range outside registered window')
        for key in ('bb_width','body_threshold','pct_b_threshold','dip_atr_limit','dd_run_threshold','volume_threshold'):
            if isinstance(getattr(self,key),bool) or not np.isfinite(getattr(self,key)):raise ValueError('finite chart parameter required: '+key)
        if self.bb_width<=0:raise ValueError('positive Bollinger width required')


DEFAULT=ChartSettings()


def _ratio(a,b):
    a=np.asarray(a,dtype='float64');b=np.asarray(b,dtype='float64')
    blank=np.full(a.shape,np.nan,dtype='float64');valid=np.isfinite(a)&np.isfinite(b)
    np.divide(a,b,out=blank,where=valid&(b!=0));infinite=blank.copy()
    infinite[valid&(b==0)&(a>0)]=np.inf
    infinite[valid&(b==0)&(a<0)]=-np.inf
    return infinite,blank


def _wilder(tr,period):
    out=np.full(len(tr),np.nan,dtype='float64');seed=[];previous=np.nan;started=False
    for i,value in enumerate(tr):
        if not np.isfinite(value):
            # Leading pre-history is unavailable. An internal unknown input
            # makes the recursive state unknown; never invent a fresh seed.
            if started:break
        elif not np.isfinite(previous):
            started=True
            seed.append(float(value))
            if len(seed)==period:previous=sum(seed)/period;out[i]=previous
        else:previous=(previous*(period-1)+float(value))/period;out[i]=previous
    return out


def chart_metrics(o,h,l,c,v,settings=DEFAULT):
    """Raw inputs to the pinned tags. Named settings are supplied explicitly.

    This API declares no new cutoff grid. Exporters must bind `settings` and
    qualify nondefault variants separately; default names retain the pin.
    """
    if not isinstance(settings,ChartSettings):raise ValueError('explicit ChartSettings required')
    arrays=[np.asarray(a,dtype='float64') for a in (o,h,l,c,v)]
    if any(a.ndim!=1 or a.shape!=arrays[0].shape for a in arrays):raise ValueError('one identical native OHLCV shape required')
    o,h,l,c,v=arrays;n=len(c);s=settings
    valid=np.isfinite(np.column_stack(arrays)).all(axis=1)
    valid&=(l>0)&(o>0)&(c>0)&(h>=np.maximum(o,c))&(l<=np.minimum(o,c))&(h>=l)&(v>=0)
    o,h,l,c,v=[np.where(valid,a,np.nan) for a in arrays]
    known=pd.Series(valid).rolling(MINIMUM_BARS,min_periods=MINIMUM_BARS).sum().eq(MINIMUM_BARS).to_numpy()
    cs=pd.Series(c);mid=cs.rolling(s.bb_period).mean();sd=cs.rolling(s.bb_period).std(ddof=0)
    upper=mid+s.bb_width*sd;lower=mid-s.bb_width*sd
    # %B has its explicit equal-band exception, irrespective of ratio policy.
    pct_b=np.divide(c-lower.to_numpy(),(upper-lower).to_numpy(),out=np.full(n,np.nan),where=(upper-lower).to_numpy()!=0)
    tr=np.full(n,np.nan,dtype='float64')
    if n:
        if n>1:tr[1:]=np.maximum(h[1:]-l[1:],np.maximum(abs(h[1:]-c[:-1]),abs(l[1:]-c[:-1])))
        observed=np.flatnonzero(valid)
        if len(observed):tr[observed[0]]=h[observed[0]]-l[observed[0]]
    atr=_wilder(tr,s.atr_period)
    body=abs(c-o);green=pd.Series(np.where(np.isfinite(body),np.where(c>o,body,0.),np.nan))
    red=pd.Series(np.where(np.isfinite(body),np.where(c<o,body,0.),np.nan))
    body_inf,body_blank=_ratio(green.rolling(s.body_window).sum(),red.rolling(s.body_window).sum())
    gv=pd.Series(np.where(valid,np.where(c>o,v,0.),np.nan));rv=pd.Series(np.where(valid,np.where(c<o,v,0.),np.nan))
    volume_inf,volume_blank=_ratio(rv.rolling(s.volume_window).sum(),gv.rolling(s.volume_window).sum())
    high=np.full(n,np.nan);age=high.copy();prior_low=high.copy();drawdown=high.copy();run=high.copy()
    for t in range(s.high_window-1,n):
        window=h[t-s.high_window+1:t+1]
        if not np.isfinite(window).all():continue
        # Reversing makes argmax select the most recent equal high.
        i=t-int(np.argmax(window[::-1]));high[t]=h[i];age[t]=t-i
        if i<s.prior_low_window:continue
        before=l[i-s.prior_low_window:i];after=l[i:t+1]
        if not np.isfinite(before).all() or not np.isfinite(after).all():continue
        prior_low[t]=before.min();run[t]=high[t]-prior_low[t]
        drawdown[t]=high[t]-after.min()
    # Nonpositive run is explicitly blank, never an infinite pass.
    run=np.where(run>0,run,np.nan)
    dd_inf,dd_blank=_ratio(drawdown,run);dip_inf,dip_blank=_ratio(high-c,atr)
    prior_h=np.r_[np.nan,h[:-1]] if n else h.copy()
    lower_high=pd.Series(np.where(np.isfinite(h)&np.isfinite(prior_h),(h<prior_h).astype(float),np.nan)).rolling(s.lower_high_window).sum()
    frame=pd.DataFrame(dict(bb_mid=mid,bb_upper=upper,bb_lower=lower,atr=atr,
        mid_change=mid-mid.shift(s.mid_lag),green_red_body_ratio_inf=body_inf,green_red_body_ratio_blank=body_blank,
        pct_b=pct_b,x_high=high,high_age=age,pre_high_low=prior_low,drawdown=drawdown,run=run,
        dip_atr_inf=dip_inf,dip_atr_blank=dip_blank,dd_vs_run_inf=dd_inf,dd_vs_run_blank=dd_blank,
        red_green_volume_ratio_inf=volume_inf,red_green_volume_ratio_blank=volume_blank,lower_high_count=lower_high))
    frame=frame.astype('float64');frame.loc[~known,:]=np.nan
    frame.attrs=dict(pin=PIN,parameters=asdict(s),minimum_complete_native_bars=MINIMUM_BARS,
                     warmup='All metric/tag values remain blank; the hard-gate consumer treats blank as failure.',
                     recursive_gap_policy='After history begins, an unknown true range invalidates subsequent ATR state; no reseeding or compressed-gap approximation.')
    return frame


def _tag(values,threshold,operation):
    values=np.asarray(values,dtype='float64')
    return np.where(np.isnan(values),np.nan,operation(values,threshold).astype('float64'))


def chart_tags(metrics,settings=DEFAULT):
    """Default fixed tags plus separately labelled inf/blank ratio policies."""
    if metrics.attrs.get('parameters')!=asdict(settings):raise ValueError('chart metric/tag parameter binding differs')
    s=settings;out=pd.DataFrame(index=metrics.index)
    out['cp_mid_slope_up']=_tag(metrics.mid_change,0,np.greater)
    out['cp_pctB']=_tag(metrics.pct_b,s.pct_b_threshold,np.greater_equal)
    out['cp_days_since_h20']=np.where(metrics.high_age.isna(),np.nan,metrics.high_age.between(s.high_age_min,s.high_age_max).astype(float))
    for policy in ('inf','blank'):
        out['cp_gr_body20_'+policy]=_tag(metrics['green_red_body_ratio_'+policy],s.body_threshold,np.greater_equal)
        out['cp_dip_atr_'+policy]=_tag(metrics['dip_atr_'+policy],s.dip_atr_limit,np.less_equal)
        out['cp_dd_vs_run_'+policy]=_tag(metrics['dd_vs_run_'+policy],s.dd_run_threshold,np.greater_equal)
        out['cp_redgreen_vol10_'+policy]=_tag(metrics['red_green_volume_ratio_'+policy],s.volume_threshold,np.greater)
    aliases={name:name+'_inf' for name in ('cp_gr_body20','cp_dip_atr','cp_dd_vs_run','cp_redgreen_vol10')}
    for alias,canonical in aliases.items():out[alias]=out[canonical]
    core=['cp_mid_slope_up','cp_gr_body20','cp_pctB','cp_dip_atr','cp_days_since_h20','cp_dd_vs_run']
    blank_core=[name+'_blank' if name in aliases else name for name in core]
    out['cp_hard_all_inf']=out[core].eq(1).all(axis=1).astype('float64')
    out['cp_hard_all_blank']=out[blank_core].eq(1).all(axis=1).astype('float64')
    out['cp_hard_all']=out.cp_hard_all_inf;aliases['cp_hard_all']='cp_hard_all_inf'
    out['lower_highs10']=metrics.lower_high_count
    warm=metrics.notna().any(axis=1)
    # Preserve warmup blanks; hard_gate_mask is explicitly false for them.
    out.loc[~warm,:]=np.nan
    out.attrs=dict(metrics.attrs,aliases=aliases,hard_core=core,warning_only='cp_redgreen_vol10',
                   question_policy='Aliases never inflate unique question/formula counts.')
    return out


def hard_gate_mask(tags):return tags.cp_hard_all.eq(1).to_numpy(dtype=bool)


def native_chart_picture(bars,calendar,timeframe,query_day,settings=DEFAULT):
    from world_relative_context import _calendar,_on_grid,native_grid
    from world_context_native import KEYS
    if 'ticker' in bars and (bars.ticker.isna().any() or bars.ticker.nunique()>1):
        raise ValueError('native chart tags require one literal source ticker')
    calendar=_calendar(calendar);grid=native_grid(calendar,timeframe,query_day)
    own=bars.copy();fields=['open','high','low','close','volume']
    values=own[fields].to_numpy(dtype='float64');o,h,l,c,v=values.T
    valid=np.isfinite(values).all(axis=1)&(l>0)&(o>0)&(c>0)&(h>=np.maximum(o,c))&(l<=np.minimum(o,c))&(h>=l)&(v>=0)
    own.loc[~valid,fields]=np.nan
    native,source=_on_grid(own,calendar,timeframe,query_day,grid)
    metrics=chart_metrics(*(native[name].to_numpy(dtype='float64') for name in ('open','high','low','close','volume')),settings)
    tags=chart_tags(metrics,settings);out=grid.copy()
    for name in metrics:out['cp_metric_'+name]=metrics[name].to_numpy(dtype='float64')
    for name in tags:out[name]=tags[name].to_numpy(dtype='float64')
    out.attrs=dict(tags.attrs,timeframe=timeframe,query_day=str(pd.Timestamp(query_day).date()),source=source,
                   ticker=str(bars.ticker.iloc[0]) if 'ticker' in bars and len(bars) else None,
                   source_rule='Complete native OHLCV, source end < availability <= D; no day-D input; missing intervals retained.',
                   variant_rule='Explicit settings bound in metadata; nondefault exports need distinct registered variant identities.',
                   full_world_gate='NOT_PROVEN',scoring_gate='CLOSED')
    out.attrs['aliases']=dict(tags.attrs['aliases'],cp_dd_vs_run_blank='cp_dd_vs_run_inf',
                               cp_metric_dd_vs_run_blank='cp_metric_dd_vs_run_inf',lower_highs10='cp_metric_lower_high_count')
    if list(out[list(KEYS)])!=list(KEYS):raise ValueError('chart native grid changed')
    return out

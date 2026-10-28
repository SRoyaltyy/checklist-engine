"""Compile ALFRED availability timelines once; retain first releases and latest-known values."""
import numpy as np
import pandas as pd
from world_dates import date_ns

def compile_timelines(frame):
    if frame is None or frame.empty:return {}
    source=frame.copy()
    for c in ('obs_date','vintage_date'):source[c]=date_ns(source[c])
    keys=['series','obs_date','vintage_date']
    if (source.groupby(keys,dropna=False).value.nunique(dropna=False)>1).any():
        raise ValueError('Conflicting ALFRED values at the same observation and vintage')
    source=source.drop_duplicates(keys).sort_values(['series','vintage_date','obs_date'])
    timelines={}
    for sid,group in source.groupby('series',sort=True):
        first={};latest_observation=None;latest_value=np.nan;rows=[]
        for vintage,changes in group.groupby('vintage_date',sort=True):
            for row in changes.itertuples():
                observation=pd.Timestamp(row.obs_date)
                if observation>vintage or pd.isna(row.value):continue
                first.setdefault(observation,float(row.value))
                if latest_observation is None or observation>=latest_observation:
                    latest_observation=observation;latest_value=float(row.value)
            if latest_observation is not None:
                rows.append((vintage,latest_observation,latest_value,first[latest_observation]))
        if rows:
            timelines[str(sid)]=pd.DataFrame(rows,columns=['vintage_date','obs_date','value','first_release'])
    return timelines

def columns(dates,timelines):
    query=pd.DataFrame({'date':date_ns(dates)});out={}
    for sid,right in timelines.items():
        prefix='fred_'+sid.lower()
        joined=pd.merge_asof(query,right,left_on='date',right_on='vintage_date',direction='backward',allow_exact_matches=False)
        out[prefix]=joined.value.to_numpy(np.float64)
        out[prefix+'_first_release']=joined.first_release.to_numpy(np.float64)
        out[prefix+'_odays']=(joined.date-joined.obs_date).dt.days.to_numpy(np.float64)
        out[prefix+'_vintage_days']=(joined.date-joined.vintage_date).dt.days.to_numpy(np.float64)
    return out

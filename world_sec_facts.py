"""Compile filing-version fact states before native world values are stored.

Source columns match fetch.fetch_sec_world.FACT_COLUMNS. This component never
fetches SEC data, maps tickers or overrides source identity quarantines.
"""
from dataclasses import asdict,dataclass
import re
import struct
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class FactSelection:
    taxonomy:str
    metric:str
    unit:str
    period_kind:str
    duration_days:tuple|None=None
    allowed_forms:tuple|None=None

    def validate(self):
        if any(not isinstance(v,str) or not v for v in (self.taxonomy,self.metric,self.unit)):
            raise ValueError('explicit taxonomy, metric and unit required')
        if self.period_kind not in ('instant','duration'):raise ValueError('explicit instant or duration period required')
        if self.period_kind=='instant' and self.duration_days is not None:raise ValueError('instant facts do not have duration windows')
        if self.period_kind=='duration':
            bounds=self.duration_days
            if not bounds or len(bounds)!=2 or any(type(n) is not int for n in bounds) or not 1<=bounds[0]<=bounds[1]:
                raise ValueError('explicit inclusive duration-day bounds required')
        if self.allowed_forms is not None and (not self.allowed_forms or any(not isinstance(x,str) or not x for x in self.allowed_forms)):
            raise ValueError('nonempty explicit filing-form set required')


DATES=('known_from','period_start','period_end','filed','first_recorded_filed')
COLUMNS=(*DATES,'accn','form','val','first_recorded_val','status')
STATUSES={'VALUE','CONFLICTING_VALUES_SAME_FILED_DATE','MULTIPLE_VALID_PERIOD_STARTS'}


def date_only(series,allow_missing=False):
    dates=pd.to_datetime(series,errors='raise')
    if dates.dt.tz is not None or (not allow_missing and dates.isna().any()):raise ValueError('date-only source keys required')
    valid=dates.dropna()
    if (valid!=valid.dt.normalize()).any():raise ValueError('source keys must be date-only, not truncated timestamps')
    return dates.astype('datetime64[ns]')


def _frame(rows):
    frame=pd.DataFrame(rows,columns=COLUMNS)
    for column in DATES:frame[column]=pd.to_datetime(frame[column]).astype('datetime64[ns]')
    for column in ('val','first_recorded_val'):frame[column]=frame[column].astype('float64')
    frame['status']=frame.status.astype('string')
    return frame


def _signature(row):
    result=[]
    for key in COLUMNS:
        if key=='known_from':continue
        value=row.get(key)
        if value is None or pd.isna(value):result.append(None)
        elif isinstance(value,(float,np.floating)):result.append(struct.pack('<d',float(value)))
        elif isinstance(value,pd.Timestamp):result.append(value.value)
        else:result.append(value)
    return tuple(result)


def compile_fact_timeline(facts,cik,selection):
    """Latest reported period, then latest prior-D filing for that period.

Duration filters use actual start/end, not fp labels that also label YTD rows.
Conflicting same-day versions remain unknown; no arbitrary accession order
or fallback to an older period fabricates a current value.
"""
    selection.validate()
    required={'cik','taxonomy','metric','unit','period_start','period_end','filed','accn','form','val'}
    if not required<=set(facts):raise ValueError('filing-version companyfacts columns missing')
    if isinstance(cik,bool) or not re.fullmatch(r'\d{1,10}',str(cik)) or not 0<int(cik)<=9999999999:
        raise ValueError('canonical numeric CIK required')
    identities=pd.to_numeric(facts.cik,errors='raise')
    if identities.isna().any() or (identities!=int(cik)).any():raise ValueError('mixed or foreign source CIK')
    own=facts[(facts.taxonomy==selection.taxonomy)&(facts.metric==selection.metric)&(facts.unit==selection.unit)].copy()
    audit=dict(input_rows=len(facts),matching_rows=len(own),rejected_future_period_rows=0,rejected_period_rows=0,
               rejected_form_rows=0,same_date_value_conflicts=0,selection=asdict(selection),cik=int(cik),
               identity_scope='CIK_KEY_ONLY_NOT_HISTORICAL_TICKER_APPROVAL',
               first_value_scope='first value recorded in supplied archived facts; not proof of exhaustive original-publication coverage')
    for column in ('filed','period_end'):own[column]=date_only(own[column])
    own['period_start']=date_only(own.period_start,allow_missing=True)
    if own.accn.isna().any() or not own.accn.map(lambda x:bool(re.fullmatch(r'\d{10}-\d{2}-\d{6}',str(x)))).all():
        raise ValueError('source accession identifier missing or invalid')
    if own.val.map(lambda x:isinstance(x,(bool,np.bool_))).any():raise ValueError('boolean is not a numeric financial fact')
    if own.val.map(lambda x:isinstance(x,(int,np.integer)) and abs(int(x))>2**53).any():
        raise ValueError('large integer fact requires exact representation; do not silently round')
    numeric=pd.to_numeric(own.val,errors='raise')
    values=numeric.to_numpy(dtype=np.float64)
    if not np.isfinite(values).all():raise ValueError('nonfinite financial fact')
    own['val']=values
    future=own.period_end>own.filed;audit['rejected_future_period_rows']=int(future.sum());own=own[~future]
    if selection.allowed_forms is not None:
        valid=own.form.isin(selection.allowed_forms);audit['rejected_form_rows']=int((~valid).sum());own=own[valid]
    if selection.period_kind=='instant':valid=own.period_start.isna()
    else:
        days=(own.period_end-own.period_start).dt.days+1
        valid=own.period_start.notna()&days.between(*selection.duration_days)
    audit['rejected_period_rows']=int((~valid).sum());own=own[valid].copy()
    own['_value_bits']=own.val.map(lambda value:struct.pack('<d',float(value)))
    own=own.drop_duplicates()
    audit['eligible_rows']=len(own)
    states={};first={};rows=[];previous=None
    for filed,batch in own.sort_values(['filed','period_end','period_start','accn']).groupby('filed',sort=True):
        groups={}
        for record in batch.itertuples():
            key=(None if pd.isna(record.period_start) else pd.Timestamp(record.period_start),pd.Timestamp(record.period_end))
            groups.setdefault(key,[]).append(record)
        for key,records in groups.items():
            unique={struct.pack('<d',float(r.val)) for r in records}
            conflict=len(unique)>1
            record=max(records,key=lambda r:str(r.accn))
            value=np.nan if conflict else float(record.val)
            if conflict:audit['same_date_value_conflicts']+=1
            first.setdefault(key,(value,pd.Timestamp(filed)))
            states[key]=dict(period_start=key[0],period_end=key[1],filed=pd.Timestamp(filed),
                accn=None if conflict else str(record.accn),form=None if pd.isna(record.form) else str(record.form),
                val=value,first_recorded_val=first[key][0],first_recorded_filed=first[key][1],
                status='CONFLICTING_VALUES_SAME_FILED_DATE' if conflict else 'VALUE')
        newest_end=max(key[1] for key in states)
        candidates=[record for key,record in states.items() if key[1]==newest_end]
        newest_filing=max(record['filed'] for record in candidates)
        candidates=[record for record in candidates if record['filed']==newest_filing]
        if len(candidates)==1:current=dict(candidates[0])
        else:
            current=dict(period_start=None,period_end=newest_end,filed=newest_filing,accn=None,form=None,
                val=np.nan,first_recorded_val=np.nan,first_recorded_filed=None,status='MULTIPLE_VALID_PERIOD_STARTS')
        signature=_signature(current)
        if signature!=previous:rows.append(dict(known_from=pd.Timestamp(filed),**current));previous=signature
    frame=_frame(rows);frame.attrs['audit']=audit
    return frame


def fact_values_at(query_dates,timeline,prefix):
    """Compute native-sample values to persist, with filing date strictly < D."""
    if not re.fullmatch('[A-Za-z][A-Za-z0-9_]*',prefix):raise ValueError('fixed financial feature prefix required')
    dates=date_only(pd.Series(query_dates))
    if dates.duplicated().any() or not dates.is_monotonic_increasing:raise ValueError('ordered unique fact query dates required')
    out=pd.DataFrame({'date':dates})
    names=('value','first_recorded_value','filed_calendar_days','period_calendar_days')
    if timeline.empty:
        for name in names:out[prefix+'_'+name]=np.nan
        out[prefix+'_status']=pd.Series(['NO_KNOWN_FACT']*len(out),dtype='string')
        return out
    source=timeline.copy()
    if not set(COLUMNS)<=set(source):raise ValueError('filing state timeline columns missing')
    for column in DATES:source[column]=date_only(source[column],allow_missing=column in ('period_start','first_recorded_filed'))
    if (source.known_from.duplicated().any() or not source.known_from.is_monotonic_increasing
        or not source.status.isin(STATUSES).all() or not (source.filed<=source.known_from).all()
        or not (source.period_end<=source.filed).all()
        or (source.period_start.notna()&(source.period_start>source.period_end)).any()
        or (source.first_recorded_filed.notna()&(source.first_recorded_filed>source.filed)).any()
        or not np.array_equal(np.isfinite(source.val.to_numpy(dtype=np.float64)),source.status.eq('VALUE').to_numpy(dtype=bool))
        or np.isinf(source.first_recorded_val.to_numpy(dtype=np.float64)).any()):raise ValueError('invalid filing state timeline')
    joined=pd.merge_asof(out,source,left_on='date',right_on='known_from',direction='backward',allow_exact_matches=False)
    out[prefix+'_value']=joined.val.to_numpy(dtype=np.float64)
    out[prefix+'_first_recorded_value']=joined.first_recorded_val.to_numpy(dtype=np.float64)
    out[prefix+'_filed_calendar_days']=(joined.date-joined.filed).dt.days.to_numpy(dtype=np.float64)
    out[prefix+'_period_calendar_days']=(joined.date-joined.period_end).dt.days.to_numpy(dtype=np.float64)
    out[prefix+'_status']=joined.status.fillna('NO_KNOWN_FACT').astype('string')
    return out

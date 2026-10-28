import numpy as np
import pandas as pd
import pytest
from world_sec_facts import FactSelection,compile_fact_timeline,fact_values_at

CIK=320193
INSTANT=FactSelection('us-gaap','Assets','USD','instant')
QUARTER=FactSelection('us-gaap','Revenues','USD','duration',(60,120))


def fact(value=100.,end='2019-12-31',filed='2020-02-10',start=None,sequence=1,metric='Assets',unit='USD',taxonomy='us-gaap',form='10-K',cik=CIK):
    return dict(cik=cik,taxonomy=taxonomy,metric=metric,unit=unit,period_start=start,period_end=end,
                filed=filed,accn=f'0000320193-20-{sequence:06d}',form=form,frame=None,val=value)


def project(rows,dates,selection=INSTANT):
    return fact_values_at(pd.to_datetime(dates),compile_fact_timeline(pd.DataFrame(rows),CIK,selection),'xb')


def test_same_day_filing_is_unavailable_and_later_restatement_starts_after_its_filed_day():
    rows=[fact(),fact(110.,filed='2020-02-20',sequence=2,form='10-K/A')]
    out=project(rows,['2020-02-10','2020-02-11','2020-02-20','2020-02-21'])
    np.testing.assert_equal(out.xb_value.to_numpy(),[np.nan,100.,100.,110.])
    np.testing.assert_equal(out.xb_first_recorded_value.to_numpy(),[np.nan,100.,100.,100.])
    assert out.xb_filed_calendar_days.iloc[-1]==1 and out.xb_status.iloc[0]=='NO_KNOWN_FACT'


def test_later_filing_for_an_old_period_never_replaces_the_newest_reported_period():
    rows=[fact(),fact(120.,end='2020-03-31',filed='2020-05-05',sequence=2,form='10-Q'),
          fact(999.,filed='2020-06-10',sequence=3,form='10-K/A')]
    timeline=compile_fact_timeline(pd.DataFrame(rows),CIK,INSTANT)
    assert len(timeline)==2 and timeline.attrs['audit']['eligible_rows']==3
    out=fact_values_at(pd.to_datetime(['2020-06-11']),timeline,'xb')
    assert out.xb_value.iloc[0]==120. and out.xb_filed_calendar_days.iloc[0]==37


def test_quarter_duration_does_not_confuse_same_fp_ytd_or_annual_figures():
    rows=[fact(900.,end='2020-09-30',start='2020-01-01',filed='2020-11-05',metric='Revenues',form='10-Q'),
          fact(300.,end='2020-09-30',start='2020-07-01',filed='2020-11-05',sequence=2,metric='Revenues',form='10-Q')]
    timeline=compile_fact_timeline(pd.DataFrame(rows),CIK,QUARTER)
    assert timeline.val.iloc[0]==300. and timeline.attrs['audit']['rejected_period_rows']==1
    assert timeline.period_start.iloc[0]==pd.Timestamp('2020-07-01')


def test_instant_selection_rejects_duration_and_never_mixes_currency_or_taxonomy():
    rows=[fact(),fact(999.,start='2019-01-01',sequence=2),fact(900.,unit='EUR',sequence=3),fact(800.,taxonomy='ifrs-full',sequence=4)]
    out=project(rows,['2020-02-11'])
    assert out.xb_value.iloc[0]==100.


def test_same_date_conflicts_are_unknown_until_a_later_unambiguous_filing():
    rows=[fact(),fact(110.,sequence=2),fact(105.,filed='2020-02-20',sequence=3)]
    out=project(rows,['2020-02-11','2020-02-21'])
    assert np.isnan(out.xb_value.iloc[0]) and out.xb_status.iloc[0]=='CONFLICTING_VALUES_SAME_FILED_DATE'
    assert out.xb_value.iloc[1]==105. and np.isnan(out.xb_first_recorded_value.iloc[1])


def test_multiple_valid_period_starts_are_not_arbitrarily_resolved_on_the_same_filed_date():
    rows=[fact(300.,end='2020-09-30',start='2020-07-01',filed='2020-11-05',metric='Revenues'),
          fact(310.,end='2020-09-30',start='2020-07-02',filed='2020-11-05',sequence=2,metric='Revenues'),
          fact(302.,end='2020-09-30',start='2020-07-01',filed='2020-11-06',sequence=3,metric='Revenues')]
    out=project(rows,['2020-11-06','2020-11-09'],QUARTER)
    assert out.xb_status.iloc[0]=='MULTIPLE_VALID_PERIOD_STARTS' and np.isnan(out.xb_value.iloc[0])
    assert out.xb_value.iloc[1]==302. and out.xb_first_recorded_value.iloc[1]==300.


def test_actual_zero_and_float64_precision_remain_distinct_from_unknown():
    rows=[fact(0.),fact(1.0000000001,filed='2020-02-20',sequence=2)]
    out=project(rows,['2020-02-10','2020-02-11','2020-02-21'])
    assert np.isnan(out.xb_value.iloc[0]) and out.xb_value.iloc[1]==0.
    assert out.xb_value.iloc[2]==1.0000000001 and out.xb_value.dtype==np.float64


def test_exact_duplicate_rows_coalesce_without_changing_a_value_or_first_record():
    row=fact(0.)
    timeline=compile_fact_timeline(pd.DataFrame([row,row]),CIK,INSTANT)
    assert len(timeline)==1 and timeline.val.iloc[0]==0. and timeline.status.iloc[0]=='VALUE'


def test_future_period_is_not_used_as_a_reported_historical_actual():
    timeline=compile_fact_timeline(pd.DataFrame([fact(end='2030-12-31')]),CIK,INSTANT)
    assert timeline.empty and timeline.attrs['audit']['rejected_future_period_rows']==1
    out=fact_values_at(pd.to_datetime(['2020-02-11']),timeline,'xb')
    assert np.isnan(out.xb_value.iloc[0]) and out.xb_status.iloc[0]=='NO_KNOWN_FACT'


@pytest.mark.parametrize('bad',[True,np.inf,np.nan,2**60])
def test_invalid_or_unrepresentable_values_are_never_coerced_to_usable_facts(bad):
    with pytest.raises(ValueError):compile_fact_timeline(pd.DataFrame([fact(bad)]),CIK,INSTANT)


def test_foreign_cik_invalid_accession_or_intraday_filed_key_fails_loudly():
    with pytest.raises(ValueError,match='foreign source CIK'):
        compile_fact_timeline(pd.DataFrame([fact(cik=789019)]),CIK,INSTANT)
    wrong=fact();wrong['accn']='unproven'
    with pytest.raises(ValueError,match='accession'):compile_fact_timeline(pd.DataFrame([wrong]),CIK,INSTANT)
    with pytest.raises(ValueError,match='date-only'):
        compile_fact_timeline(pd.DataFrame([fact(filed='2020-02-10 12:00:00')]),CIK,INSTANT)


def test_explicit_form_policy_does_not_silently_select_an_unregistered_filing_type():
    selection=FactSelection('us-gaap','Assets','USD','instant',allowed_forms=('10-K','10-K/A'))
    rows=[fact(),fact(300.,end='2020-03-31',filed='2020-05-05',form='10-Q',sequence=2)]
    timeline=compile_fact_timeline(pd.DataFrame(rows),CIK,selection)
    assert timeline.val.iloc[-1]==100. and timeline.attrs['audit']['rejected_form_rows']==1


@pytest.mark.parametrize('selection',[FactSelection('us-gaap','Assets','USD','instant',(60,120)),
    FactSelection('us-gaap','Revenues','USD','duration'),FactSelection('us-gaap','Revenues','USD','duration',(120,60))])
def test_undefined_or_ambiguous_period_policy_is_not_inferred(selection):
    with pytest.raises(ValueError):compile_fact_timeline(pd.DataFrame([fact()]),CIK,selection)


def test_independent_truncations_match_all_prior_query_values_exactly():
    rows=[fact(),fact(110.,filed='2020-02-20',sequence=2),
          fact(200.,end='2020-03-31',filed='2020-05-05',sequence=3),fact(999.,filed='2020-06-10',sequence=4)]
    source=pd.DataFrame(rows);dates=pd.to_datetime(['2020-02-10','2020-02-11','2020-02-21','2020-05-06','2020-06-11'])
    full=fact_values_at(dates,compile_fact_timeline(source,CIK,INSTANT),'xb')
    for cut in dates:
        past=source[pd.to_datetime(source.filed)<cut]
        prefix=fact_values_at(dates[dates<=cut],compile_fact_timeline(past,CIK,INSTANT),'xb')
        pd.testing.assert_frame_equal(full[full.date<=cut].reset_index(drop=True),prefix,check_exact=True)


def test_unavailable_concept_and_empty_queries_keep_typed_missing_states():
    source=pd.DataFrame([fact(metric='OtherMetric')])
    timeline=compile_fact_timeline(source,CIK,INSTANT)
    assert timeline.empty and timeline.attrs['audit']['matching_rows']==0
    out=fact_values_at(pd.to_datetime(['2020-02-11']),timeline,'xb')
    assert np.isnan(out.xb_value.iloc[0]) and out.xb_status.iloc[0]=='NO_KNOWN_FACT'
    assert out.xb_value.dtype==np.float64
    assert fact_values_at(pd.DatetimeIndex([]),timeline,'xb').empty


@pytest.mark.parametrize('column,value',[('known_from','2020-02-09'),('period_start','2021-01-01'),
    ('first_recorded_filed','2021-01-01'),('val',np.nan),('status','UNKNOWN_LABEL'),('first_recorded_val',np.inf)])
def test_corrupt_stored_timelines_cannot_create_a_usable_native_value(column,value):
    timeline=compile_fact_timeline(pd.DataFrame([fact()]),CIK,INSTANT)
    timeline.loc[0,column]=pd.Timestamp(value) if column in ('known_from','period_start','first_recorded_filed') else value
    with pytest.raises(ValueError,match='timeline'):
        fact_values_at(pd.to_datetime(['2020-02-11']),timeline,'xb')


@pytest.mark.parametrize('sequence',[1,2])
def test_signed_zero_conflict_is_not_silently_collapsed_by_deduplication(sequence):
    timeline=compile_fact_timeline(pd.DataFrame([fact(-0.),fact(0.,sequence=sequence)]),CIK,INSTANT)
    assert timeline.status.iloc[0]=='CONFLICTING_VALUES_SAME_FILED_DATE'

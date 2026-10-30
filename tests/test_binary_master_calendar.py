from copy import deepcopy
from dataclasses import replace
from datetime import date,timedelta
import numpy as np
import pandas as pd
import pytest
from world_binary_master import NativeBar,_tf_window,evaluate_master
from world_binary_price import NativeCandle,bind_price_question,measurement
from world_question_grid import CanonicalGrid,ROOT
from world_timeframes import completed_candles


def source(n):
    calendar=pd.bdate_range('2024-01-01',periods=n+1)
    close=100.+np.arange(n);opened=close-.25
    frame=pd.DataFrame(dict(date=calendar[:n],open=opened,high=close+1,low=opened-1,close=close,volume=np.ones(n)))
    bars={i:NativeBar(end=calendar[i].date(),available_from=calendar[i+1].date(),
        open=float(r.open),high=float(r.high),low=float(r.low),close=float(r.close)) for i,r in frame.iterrows()}
    return frame,calendar,bars


@pytest.mark.parametrize('days',range(1,22))
def test_daily_adapter_matches_existing_fixed_calendar_resampler(days):
    frame,calendar,bars=source(160);slot=5*days;setup=calendar[slot+1].date()
    expected=completed_candles(frame,f'{days}d',session_calendar=calendar)
    expected=expected[expected.available_from<=pd.Timestamp(setup)].tail(2)
    actual=_tf_window(bars,setup,slot,2,days)
    assert len(actual)==len(expected)==2
    for bar,(_,row) in zip(actual,expected.iterrows()):
        assert (bar.open,bar.high,bar.low,bar.close)==(row.open,row.high,row.low,row.close)
        assert bar.end==row.date.date() and bar.available_from==row.available_from.date()


def probe(recipe='native_body_colour_balance_v1',days=3,lookback=1):
    return dict(feature=dict(recipe=recipe,transform='identity',candle_days=days,lookback=lookback),
                comparator='>',comparison_threshold='1',feature_kind='continuous')


@pytest.mark.parametrize('field',['open','high','low','close'])
@pytest.mark.parametrize('bad',[None,np.nan,np.inf,-np.inf,0.,-1.])
def test_unavailable_daily_price_is_not_hidden_by_native_aggregation(field,bad):
    _,calendar,bars=source(10);bars[4]=replace(bars[4],**{field:bad})
    answer=evaluate_master(probe(),bars,calendar[6].date(),5)
    assert answer.answer=='NOT_EVALUABLE'


@pytest.mark.parametrize('change',[dict(high=1.),dict(low=1000.)])
def test_invalid_daily_ohlc_cannot_become_a_known_native_ratio(change):
    _,calendar,bars=source(10);bars[4]=replace(bars[4],**change)
    assert evaluate_master(probe(),bars,calendar[6].date(),5).answer=='NOT_EVALUABLE'


def test_partial_future_bucket_cannot_change_last_fixed_candle():
    _,calendar,bars=source(12);baseline=_tf_window(bars,calendar[8].date(),7,1,3)
    bars[6]=replace(bars[6],high=None);bars[7]=replace(bars[7],close=np.nan)
    bars[8]=replace(bars[8],open=1e10,high=1e11,low=1.,close=2e10)
    assert _tf_window(bars,calendar[8].date(),7,1,3)==baseline
    assert baseline[0].end==calendar[5].date()


def test_no_complete_bucket_is_missing_not_a_rolling_substitute():
    _,calendar,bars=source(12)
    assert evaluate_master(probe(),bars,calendar[2].date(),1).answer=='NOT_EVALUABLE'


@pytest.mark.parametrize('kind',['intraday_change','interday_change','run_structure'])
def test_gpt_fallback_receives_native_candles_not_daily_slots(kind):
    grid=CanonicalGrid(ROOT)
    qid=next(q for q,row in grid.tree.items() if row['part']=='base' and row['L3_derivative']=='OHLC'
             and row['L4_analysis']==kind and int(row['L2_timeframe'].split('x')[0])>1)
    definition=bind_price_question(grid.tree[qid],next(grid.variants(qid)))[0]
    feature=definition['feature'];days=feature['candle_days'];lookback=feature['lookback']
    n=(lookback+8)*days+10;frame,calendar,bars=source(n);slot=(lookback+5)*days+1;setup=calendar[slot+1].date()
    # A descending DAILY tail must not replace the fixed native candle history.
    for offset,i in enumerate(range(slot-lookback,slot+1)):
        value=10000.-100*offset;bars[i]=replace(bars[i],open=value-.25,close=value,high=value+1,low=value-1)
        frame.loc[i,['open','close','high','low']]=[value-.25,value,value+1,value-1]
    expected=completed_candles(frame,f'{days}d',session_calendar=calendar)
    expected=expected[expected.available_from<=pd.Timestamp(setup)]
    native={int(calendar.get_loc(row.candle_start)//days):NativeCandle(end=row.date.date(),
        available_from=row.available_from.date(),open=row.open,close=row.close) for _,row in expected.iterrows()}
    value=measurement(kind,native,setup,max(native),lookback)
    assert value is not None
    equality=deepcopy(definition);equality['feature']['transform']='identity';equality['comparator']='=';equality['comparison_threshold']=str(value)
    assert evaluate_master(equality,bars,setup,slot).answer=='YES'

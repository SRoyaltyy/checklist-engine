import pandas as pd
import pytest

from ci.breadth_warmup_fix import availability_changes, corrected_prefix_checks
from outside_breadth import aggregate, available_breadth, breadth_candles, stock_contributions


def data():
    dates=pd.bdate_range('2019-01-01','2021-02-02')
    close=pd.Series(range(len(dates)),dtype='float64')+20
    prices=pd.DataFrame(dict(date=dates,open=close,high=close+1,low=close-1,close=close,volume=1000.))
    daily=aggregate(stock_contributions(prices),dates,dates[-2],retain_history=True)
    return dates,daily


def test_availability_proof_records_only_known_to_missing_without_changing_values():
    dates,parent=data()
    actual=available_breadth(parent)
    changes=availability_changes(parent,actual,['date'])
    assert changes['new_high']['newly_unavailable']==251
    assert changes['ad_net']['newly_unavailable']==1
    changed=actual.copy()
    changed.loc[changed.new_high.notna(),'new_high']+=1
    with pytest.raises(ValueError,match='observed numeric'):
        availability_changes(parent,changed,['date'])


def test_availability_proof_cannot_invent_observations_or_drop_keys():
    dates,parent=data()
    actual=available_breadth(parent)
    actual.loc[0,'pct_above_sma20']=.5
    with pytest.raises(ValueError,match='observed numeric'):
        availability_changes(parent,actual,['date'])
    with pytest.raises(ValueError,match='rows or source schema'):
        availability_changes(parent,parent.iloc[1:],['date'])


def test_availability_prefixes_keep_unknowns_on_all22_grids():
    dates,parent=data()
    actual=available_breadth(parent)
    native=breadth_candles(actual,dates)
    checks=corrected_prefix_checks(parent,actual,native,dates,['2020-01-03','2020-12-02'])
    assert len(checks)==44 and all(row['mismatches']==0 for row in checks)

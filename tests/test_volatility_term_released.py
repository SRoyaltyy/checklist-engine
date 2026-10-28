import numpy as np
import pandas as pd
import pytest
from ci import volatility_term_released as producer


def fixture(monkeypatch):
    monkeypatch.setattr(producer,'TIMEFRAMES',('1d','3d','monthly'))
    calendar=pd.bdate_range('2019-12-02','2020-05-01').as_unit('ns')
    histories={name:pd.DataFrame(dict(DATE=calendar,CLOSE=np.arange(len(calendar),dtype=float)+offset))
               for name,offset in zip(producer.LEVELS,(10.,5.,20.,100.))}
    histories['VVIX']=histories['VVIX'].drop(index=20)
    full={tf:producer.rebuild_indices(histories,calendar,tf) for tf in producer.TIMEFRAMES}
    return calendar,histories,full


def test_raw_source_cutoff_rebuilds_all_selected_levels_and_terms(monkeypatch):
    calendar,histories,full=fixture(monkeypatch)
    checks=producer.verify_cutoff(full,histories,calendar,'2020-03-02')
    assert len(checks)==3 and all(c['mismatches']==0 and c['source_columns']>4 and c['ratio_columns']==5 for c in checks)
    histories['VIX'].loc[histories['VIX'].DATE>='2020-03-02','CLOSE']=99999.
    assert producer.verify_cutoff(full,histories,calendar,'2020-03-02')==checks


def test_changed_eligible_source_print_fails_the_independent_proof(monkeypatch):
    calendar,histories,full=fixture(monkeypatch)
    histories['VIX'].loc[10,'CLOSE']=12345.
    with pytest.raises((AssertionError,ValueError)):
        producer.verify_cutoff(full,histories,calendar,'2020-03-02')

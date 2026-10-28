import hashlib
import numpy as np
import pandas as pd
import pytest
from ci import outside_market_released as source
from light_box_market import build_candles


def test_real_cutoff_rebuild_compares_all_rows_columns_and_float_bits():
    calendar=pd.bdate_range('2020-01-02',periods=65)
    panel=pd.DataFrame(dict(ticker='SPY',date=calendar[:50],open=np.arange(50.)+1,high=np.arange(50.)+2,
        low=np.arange(50.),close=np.arange(50.)+1,volume=np.arange(50)+100))
    full=build_candles(panel,calendar,calendar[49])
    checks=source.prefix_checks(panel,calendar,full,[str(calendar[20].date()),str(calendar[40].date())])
    assert len(checks)==2 and all(c['native_rows']>0 and c['mismatches']==0 for c in checks)
    altered=full.copy();altered.loc[0,'open']=np.nextafter(altered.loc[0,'open'],np.inf)
    with pytest.raises(AssertionError):source.prefix_checks(panel,calendar,altered,[str(calendar[40].date())])


def test_source_download_checks_immutable_fingerprint(tmp_path,monkeypatch):
    file=tmp_path/'source.json';file.write_bytes(b'{}')
    monkeypatch.setattr(source,'download_asset',lambda *a:file)
    assert source.checked_download('tag',file.name,hashlib.sha256(b'{}').hexdigest(),tmp_path)==file
    with pytest.raises(ValueError,match='fingerprint'):source.checked_download('tag',file.name,'0'*64,tmp_path)


def test_overlap_checks_each_ohlcv_field_not_only_close(tmp_path,monkeypatch):
    prior=pd.DataFrame(dict(date=pd.date_range('2020-01-02',periods=2),open=[1.,2.],high=[2.,3.],
        low=[0.,1.],close=[1.,2.],volume=[100.,200.]))
    file=tmp_path/'prior.parquet';prior.to_parquet(file,index=False)
    panel=prior.copy();panel['ticker']='SPY';panel.loc[0,'open']=1.000000000000001
    monkeypatch.setattr(source,'NAMED_ETFS',('SPY',));monkeypatch.setattr(source,'checked_download',lambda *a:file)
    checks=source.overlap_proof(panel,dict(records=[dict(ticker='SPY',file=file.name,sha256='unused')]),dict(native_release='tag'),tmp_path)
    assert checks[0]['fields']['close']['bit_mismatches']==0
    assert checks[0]['fields']['open']['bit_mismatches']==1

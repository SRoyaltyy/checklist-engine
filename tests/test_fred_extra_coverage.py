import json
import pytest
from ci.fred_extra_coverage import master_row


def test_sticky_cpi_keeps_requested_and_official_identifiers_explicit():
    row=dict(native_column='fred_stickcpim159s',column='fred_stickcpim159s__5d',timeframe='5d',non_null_pct=100.,
             query_stock_days=50,non_null_stock_days=50,query_market_sessions=5,first_date='2020-01-02',last_date='2020-01-08')
    result=master_row(row,'STICKCPIM159S','STICKCPIM159SFRBATL',dict(file='5d.parquet',sha256='hash'))
    source=json.loads(result['source_evidence'])
    assert result['item_id']==source['requested_series']=='STICKCPIM159S'
    assert source['source_series']=='STICKCPIM159SFRBATL' and result['status']=='MEASURED'
    with pytest.raises(ValueError):master_row(row,'INDPRO','INDPRO',dict(file='5d.parquet',sha256='hash'))


def test_zero_observations_cannot_be_reported_as_wired_or_known_zero():
    row=dict(native_column='fred_indpro',column='fred_indpro__1d',timeframe='1d',non_null_pct=0.,
             query_stock_days=50,non_null_stock_days=0,query_market_sessions=5,first_date='',last_date='')
    result=master_row(row,'INDPRO','INDPRO',dict(file='1d.parquet',sha256='hash'))
    assert result['status']=='NO_OBSERVED_VALUES' and result['first_date_available']==''
    assert result['non_null_pct_2020_2026']=='0.0000' and 'missing stays explicit' in result['reason']

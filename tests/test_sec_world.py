import json,subprocess
from unittest.mock import patch
import pandas as pd
import pytest
from fetch.fetch_sec_world import numeric_facts,identities,publish_part

def test_all_numeric_facts_preserve_taxonomy_units_filing_versions_and_instant_shares():
    payload=dict(cik=123,facts={'us-gaap':{'UnlistedMetric':{'units':{'pure':[dict(val=2,end='2020-12-31',filed='2021-02-01',accn='a',form='10-K'),dict(val=3,end='2020-12-31',filed='2022-02-01',accn='b',form='10-K/A'),dict(val=True,end='2020-12-31',filed='2022-02-01',accn='b')]}}},'dei':{'EntityCommonStockSharesOutstanding':{'units':{'shares':[dict(val=100,end='2021-01-01',filed='2021-02-01',accn='a',form='10-K')]}}}})
    frame=numeric_facts(123,payload)
    assert len(frame)==3
    assert list(frame[frame.metric=='UnlistedMetric'].val)==[2.,3.]
    assert set(frame.filed)=={'2021-02-01','2022-02-01'}
    assert frame.loc[frame.unit=='shares','period_start'].isna().all()
    with pytest.raises(ValueError,match='identity'):numeric_facts(124,payload)

def test_identity_conflicts_stay_explicit_and_no_cik_does_not_become_zero():
    universe=pd.DataFrame(dict(ticker=['ABC','BRK.B','NO_MAP']))
    frozen=pd.DataFrame(dict(ticker=['ABC','BRK.B'],cik=[1,3]))
    current={'0':dict(ticker='ABC',cik_str=2),'1':dict(ticker='BRK-B',cik_str=3)}
    result={r['ticker']:r for r in identities(universe,frozen,current)}
    assert result['ABC']['status']=='AMBIGUOUS_CIK'
    assert {r['cik'] for r in result['ABC']['candidates']}=={1,2}
    assert result['BRK.B']['status']=='UNIQUE_CIK'
    assert result['NO_MAP']['status']=='NO_CIK' and result['NO_MAP']['candidates']==[]

def test_checkpoint_upload_failure_preserves_local_source_files(tmp_path,monkeypatch):
    monkeypatch.setenv('GITHUB_SHA','test-source')
    root=tmp_path/'data';root.mkdir();source=root/'company.json';source.write_text('{"facts":1}')
    with patch('fetch.fetch_sec_world.subprocess.run',side_effect=subprocess.CalledProcessError(1,['gh'])):
        with pytest.raises(subprocess.CalledProcessError):publish_part(root,[source],dict(completed={}), 'tag',0,0)
    assert source.read_text()=='{"facts":1}'
    assert (tmp_path/'sec_world_shard_000_attempt_1_part_000.tar').exists()

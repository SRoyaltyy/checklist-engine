import gzip
import hashlib
import io
import json
import tarfile

import pandas as pd
import pytest

from ci.sec_archive_state_measure import native_values,prefix_proof,selections,verified_facts
from fetch.fetch_sec_world import numeric_facts
from world_sec_facts import compile_fact_timeline
from world_timeframes import TIMEFRAMES


def fixture_archive():
    payload=dict(cik=1750,facts={'us-gaap':{'Assets':{'units':{'USD':[
        dict(val=0.,end='2019-12-31',filed='2020-01-10',accn='0000001750-20-000001',form='10-K'),
        dict(val=1.0000000001,end='2019-12-31',filed='2020-02-10',accn='0000001750-20-000002',form='10-K/A')]}}}})
    facts=numeric_facts(1750,payload)
    bodies={'CIK0000001750.companyfacts.json.gz':gzip.compress(json.dumps(payload).encode()),
            'CIK0000001750.facts.parquet':facts.to_parquet(index=False)}
    buffer=io.BytesIO();members=[]
    with tarfile.open(fileobj=buffer,mode='w') as archive:
        for name,raw in bodies.items():
            member=tarfile.TarInfo(name);member.size=len(raw);archive.addfile(member,io.BytesIO(raw))
            members.append(dict(name=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    raw=buffer.getvalue()
    return raw,dict(archive_sha256=hashlib.sha256(raw).hexdigest(),members=members),facts


def test_existing_raw_and_numeric_members_are_reverified_without_provider_access():
    archive,manifest,expected=fixture_archive()
    result=verified_facts(archive,manifest,set())
    assert len(result)==1 and result[0][0]==1750
    pd.testing.assert_frame_equal(result[0][1],expected,check_exact=True)
    with pytest.raises(ValueError,match='quarantined'):verified_facts(archive,manifest,{1750})


@pytest.mark.parametrize('corruption',['archive','member','duplicate','size','missing'])
def test_corrupt_archive_or_manifest_does_not_create_a_source_claim(corruption):
    archive,manifest,_=fixture_archive()
    if corruption=='archive':archive=archive[:-1]+b'X'
    elif corruption=='member':manifest['members'][0]['sha256']='0'*64
    elif corruption=='duplicate':manifest['members'].append(dict(manifest['members'][0]))
    elif corruption=='size':manifest['members'][0]['bytes']+=1
    else:manifest['members'].pop()
    with pytest.raises(ValueError):verified_facts(archive,manifest,set())


def test_all_22_native_grids_have_exact_independent_cutoff_proofs_and_no_tag_fallback():
    _,_,facts=fixture_archive();calendar=pd.bdate_range('2019-12-02','2020-05-15').as_unit('ns')
    timelines={name:compile_fact_timeline(facts,1750,spec) for name,spec in selections().items()}
    full={tf:native_values(calendar,tf,timelines) for tf in TIMEFRAMES}
    for cut in ('2020-01-15','2020-02-17','2020-04-03'):
        proof=prefix_proof(facts,1750,calendar,full,cut)
        assert proof['timeframes']==22 and proof['mismatches']==0 and proof['cells_compared']>0
    daily=full['1d']
    assert daily.loc[daily.available_from==pd.Timestamp('2020-01-13'),'sec_assets_value'].iloc[0]==0.
    assert daily.loc[daily.available_from==pd.Timestamp('2020-02-11'),'sec_assets_value'].iloc[0]==1.0000000001
    assert daily.sec_contract_revenues_quarter_value.isna().all()
    assert set(daily.sec_contract_revenues_quarter_status)=={'NO_KNOWN_FACT'}

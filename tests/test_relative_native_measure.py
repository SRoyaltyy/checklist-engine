import io
import json

import numpy as np
import pandas as pd
import pytest

from ci import relative_native_measure as proof


def fixture_sources(monkeypatch):
    calendar=pd.bdate_range('2020-01-01',periods=300)
    blobs={}
    def bind(asset,raw):
        blobs[asset]=raw
        return dict(release='test-source',asset=asset,sha256=proof.digest(raw),bytes=len(raw))
    def parquet(frame):
        out=io.BytesIO();frame.to_parquet(out,index=False);return out.getvalue()
    stocks=[]
    for i,ticker in enumerate(('MAN','MNTS','EYE','SPY')):
        close=40*np.exp(np.cumsum(np.random.default_rng(i).normal(0,.01,len(calendar))))
        frame=pd.DataFrame(dict(date=calendar,open=close,high=close+1,low=close-1,close=close,volume=1000.))
        binding=bind(ticker+'.parquet',parquet(frame))
        if ticker=='SPY':benchmark=binding
        else:stocks.append(dict(binding,ticker=ticker))
    parent=dict(status='EXACT_RECOMPUTATION_SAMPLE_ONLY',errors=[],
                samples=[dict(ticker=s['ticker'],raw_source_sha256=s['sha256']) for s in stocks],
                etf=dict(raw_source_sha256=benchmark['sha256']))
    request=dict(stocks=stocks,benchmark=benchmark,
                 calendar=bind('calendar.parquet',parquet(pd.DataFrame(dict(date=calendar)))),
                 parent_proof=bind('parent.json',json.dumps(parent).encode()),
                 cutoffs=[str(calendar[150].date()),str(calendar[250].date())])
    monkeypatch.setattr(proof,'raw_asset',lambda tag,name:blobs[name])
    monkeypatch.setattr(proof,'TIMEFRAMES',('1d','5d','monthly'))
    monkeypatch.setenv('GITHUB_SHA','test-commit')
    return request,blobs


def test_controller_reopens_and_recomputes_every_frame_with_real_parquet(tmp_path,monkeypatch):
    request,_=fixture_sources(monkeypatch)
    report=proof.measure(tmp_path,request)
    assert report['prefix_checks']==18
    assert {s['ticker'] for s in report['samples']}=={'MAN','MNTS','EYE'}
    assert all(len(s['checks'])==3 and len(s['prefixes'])==6 for s in report['samples'])
    assert all(c['numeric_cells']>0 and c['non_null_cells']>0 and c['recomputed_mismatches']==0
               for s in report['samples'] for c in s['checks'])
    assert len(list(tmp_path.glob('*.parquet')))==9
    assert report['world_gate']=='NOT_PROVEN' and report['full_universe_estimate_bytes'] is None


def test_controller_rejects_changed_source_or_duplicate_sample(tmp_path,monkeypatch):
    request,blobs=fixture_sources(monkeypatch)
    blobs[request['benchmark']['asset']]+=b'changed'
    with pytest.raises(ValueError,match='bytes differ'):
        proof.measure(tmp_path,request)
    request['stocks'].append(request['stocks'][0])
    with pytest.raises(ValueError,match='same three stocks'):
        proof.measure(tmp_path,request)

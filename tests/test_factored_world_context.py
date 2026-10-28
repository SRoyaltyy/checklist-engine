import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from ci import factored_world_context as pipeline
from world_context_native import native_intervals
from world_timeframes import TIMEFRAMES


def inputs_fixture(root,monkeypatch):
    files={}
    def save(tag,name,contents):
        file=root/tag/name;file.parent.mkdir(parents=True,exist_ok=True)
        if isinstance(contents,pd.DataFrame):contents.to_parquet(file,index=False)
        elif isinstance(contents,dict):file.write_text(json.dumps(contents))
        else:file.write_text(contents)
        files[tag,name]=file;return file
    calendar=pd.bdate_range('2020-01-02',periods=50)
    calendar_file=save('inputs','market_sessions.parquet',pd.DataFrame({'date':calendar}))
    calendar_hash=pipeline.sha(calendar_file)
    input_file=save('inputs','BUILD_INPUTS.json',{'calendar_sha256':calendar_hash})
    weights=save('stocks','ACCEPTED_PRICE_STOCK_DAYS.csv','date,stock_days\n2020-01-03,8316\n2020-01-06,8316\n')
    status=save('stocks','ACCEPTED_PRICE_STITCH.json',dict(original_universe=8727,accepted_tickers=8316,accepted_percent=100*8316/8727,
        query_rows=16632,stock_days_sha256=pipeline.sha(weights),inputs_tag='inputs',inputs_sha256=pipeline.sha(input_file)))
    reports={}
    for tag,column in [('shared','fred_test'),('etfs','etf_spy_close')]:
        parts=[]
        for tf in TIMEFRAMES:
            frame=native_intervals(calendar,tf).drop(columns='expected_sessions')
            frame[column]=np.arange(len(frame),dtype=float)+1
            if len(frame)>1:frame.loc[1,column]=np.nan
            file=save(tag,tf+'.parquet',frame)
            parts.append(dict(file=file.name,sha256=pipeline.sha(file),native_rows=len(frame),feature_columns=1,timeframe=tf))
        report=dict(calendar_sha256=calendar_hash,timeframes=list(TIMEFRAMES),parts=parts)
        if tag=='shared':
            report.update(format_version=2,numeric_precision='float64; no unproven precision reduction',
                code_sha256={name:pipeline.sha(name) for name in ('world_context_native.py','world_fred.py','ci/shared_context_build.py')})
            reports[tag]=save(tag,'SHARED_CONTEXT_STATUS.json',report)
        else:
            report.update(source_complete=True,available_symbols=[f'ETF{i}' for i in range(25)])
            reports[tag]=save(tag,'ETF_CONTEXT_STATUS.json',report)
    monkeypatch.setattr(pipeline,'download_asset',lambda tag,name,directory:files[tag,name])
    monkeypatch.setattr(pipeline,'asset_index',lambda tag:{name:{'size':file.stat().st_size} for (t,name),file in files.items() if t==tag})
    calls=[];monkeypatch.setattr(pipeline,'gh_retry',lambda *args:calls.append(args))
    monkeypatch.setattr(pipeline,'publish_assets',lambda *args:calls.append(args))
    for name,value in [('GITHUB_SHA','commit'),('GITHUB_RUN_ID','123'),('GITHUB_RUN_ATTEMPT','1')]:monkeypatch.setenv(name,value)
    request=dict(stock_release='stocks',stock_status_sha256=pipeline.sha(status),calendar_sha256=calendar_hash,
        etf_release='etfs',etf_status_sha256=pipeline.sha(reports['etfs']))
    return request,files,calls


def test_full_producer_binds_all_factor_files_and_exact_stock_day_coverage(tmp_path,monkeypatch):
    request,files,calls=inputs_fixture(tmp_path/'sources',monkeypatch)
    out=tmp_path/'out';pipeline.build(out,request,'shared')
    manifest=json.loads((out/'FACTORED_WORLD_CONTEXT_STORE.json').read_text())
    status=json.loads((out/'FACTORED_WORLD_CONTEXT_STATUS.json').read_text())
    coverage=pd.read_csv(out/'WORLD_SHARED_STOCK_DAY_COVERAGE.csv',keep_default_na=False)
    assert len(manifest['factors'])==44 and status['context_column_timeframe_rows']==44
    assert set(coverage.query_stock_days)=={16632}
    own=coverage[(coverage.family=='macro_cboe')&(coverage.timeframe=='1d')].iloc[0]
    assert own.non_null_stock_days==8316 and own.non_null_pct==50
    assert all(r['all_source_columns_preserved'] for r in manifest['factors'])
    assert manifest['world_gate']=='NOT_PROVEN' and calls


def test_followon_attaches_calendar_flags(tmp_path,monkeypatch):
    request,files,calls=inputs_fixture(tmp_path/'sources',monkeypatch)
    directory=tmp_path/'outside';directory.mkdir()
    calendar=pd.DataFrame({
        'timeframe':['1d','1d'],
        'candle_start':pd.to_datetime(['2020-01-02','2020-01-03']),
        'date':pd.to_datetime(['2020-01-02','2020-01-03']),
        'available_from':pd.to_datetime(['2020-01-03','2020-01-06']),
        'is_fomc':[True,False],
    })
    calendar.to_parquet(directory/'outside_event_calendar_candles.parquet',index=False)
    request['outside_followon']=str(directory)
    out=tmp_path/'out';pipeline.build(out,request,'shared')
    manifest=json.loads((out/'FACTORED_WORLD_CONTEXT_STORE.json').read_text())
    families={row['family'] for row in manifest['factors']}
    assert 'calendar' in families and 'macro_cboe' in families and 'etf' in families
    calendar_rows=[row for row in manifest['factors'] if row['family']=='calendar']
    assert calendar_rows and calendar_rows[0]['columns']==['calendar_is_fomc']
    assert len(manifest['factors'])==45
    assert calls


def test_changed_stock_proof_rejects_before_publication(tmp_path,monkeypatch):
    request,files,calls=inputs_fixture(tmp_path/'sources',monkeypatch)
    request['stock_status_sha256']='0'*64
    with pytest.raises(ValueError,match='approved stock stitch differs'):pipeline.build(tmp_path/'out',request,'shared')
    assert calls==[]


def test_changed_factor_bytes_reject_before_publishing_any_world_manifest(tmp_path,monkeypatch):
    request,files,calls=inputs_fixture(tmp_path/'sources',monkeypatch)
    file=files['shared','1d.parquet'];frame=pd.read_parquet(file);frame['fred_test']=0.;frame.to_parquet(file,index=False)
    with pytest.raises(ValueError,match='factor bytes differ'):pipeline.build(tmp_path/'out',request,'shared')
    assert calls==[]

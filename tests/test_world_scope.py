import pytest
from world_scope import NEWS_DROP_REASON,PUT_CALL_DROP_REASON


def test_news_probe_stops_before_network_or_files(tmp_path,monkeypatch):
    from fetch import gdelt_source_probe as probe
    monkeypatch.setattr(probe.urllib.request,'urlopen',lambda *a,**k:pytest.fail('news access is disabled'))
    with pytest.raises(RuntimeError,match='dropped by Cyrus'):probe.probe(tmp_path,{})
    assert not list(tmp_path.iterdir())


def test_legacy_world_does_not_read_or_accept_news(monkeypatch):
    import facets_world as fw
    monkeypatch.setattr(fw.os.path,'exists',lambda *a:pytest.fail('archived news must not be read'))
    assert fw.load_gdelt({'TEST'}) is None
    with pytest.raises(ValueError,match='News inputs dropped'):
        fw.ticker_frame('TEST',None,{},None,None,None,gd=object())


def test_coverage_exempts_only_owner_dropped_item_and_rejects_news_columns():
    from ci.world_v2_coverage import build
    measured=dict(rows=1,date_min='2020-01-01',date_max='2026-10-23',columns={
        'gd_n7__1d':dict(non_null_rows=1,non_null_pct=100.,first_date='2020-01-01')})
    rows,failures=build(measured)
    news=[r for r in rows if r['namespace']=='dictionary' and r['item_id']=='I200']
    assert len(news)==22
    assert all(r['status']=='DROPPED_BY_OWNER' and r['reason']==NEWS_DROP_REASON and r['snapshot_columns']=='' for r in news)
    assert 'OWNER_DROPPED_NEWS_COLUMN:gd_n7__1d' in failures


def test_owner_exclusion_cannot_hide_an_unrelated_missing_item(monkeypatch):
    from ci import world_v2_coverage as coverage
    monkeypatch.setattr(coverage,'mappings',lambda:({'I999':dict(status='DROPPED_BY_OWNER',note=NEWS_DROP_REASON)},{}))
    monkeypatch.setattr(coverage,'read_csv',lambda path:[dict(id='I999',item='Other')] if path.name=='DATA_SOURCES.csv' else [])
    _,failures=coverage.build(dict(rows=1,date_max='2026-10-23',columns={}))
    assert any('unauthorized scope exemption' in f for f in failures)


def test_putcall_drop_survives_missing_or_blocked_source_without_dropping_vix():
    from ci.world_v2_coverage import build
    measured=dict(rows=1,date_min='2020-01-01',date_max='2026-10-23',columns={})
    rows,failures=build(measured,source_evidence={'I201':dict(status='BLOCKED',reason='HTTP 403')})
    dropped=[r for r in rows if r['namespace']=='dictionary' and r['item_id']=='I201']
    assert len(dropped)==22
    assert all(r['status']=='DROPPED_BY_OWNER' and r['reason']==PUT_CALL_DROP_REASON and
               r['snapshot_columns']=='' and r['source_evidence']=='{}' for r in dropped)
    assert not any(f.startswith('dictionary:I201__') for f in failures)
    vix=[r for r in rows if r['namespace']=='dictionary' and r['item_id']=='I178']
    assert len(vix)==22 and all(r['status']!='DROPPED_BY_OWNER' for r in vix)
    assert any(f.startswith('dictionary:I178__') for f in failures)


def test_putcall_reason_cannot_exempt_a_tradingview_item(monkeypatch):
    from ci import world_v2_coverage as coverage
    monkeypatch.setattr(coverage,'mappings',lambda:({},{}))
    monkeypatch.setattr(coverage,'read_csv',lambda path:[] if path.name=='DATA_SOURCES.csv' else
                        [dict(item_id='I201',item='Unrelated TV item',status='DROPPED_BY_OWNER',reason=PUT_CALL_DROP_REASON)])
    _,failures=coverage.build(dict(rows=1,date_max='2026-10-23',columns={}))
    assert any('unauthorized scope exemption' in f for f in failures)

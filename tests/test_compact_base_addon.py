import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from ci import native_price_base as base
from ci.compact_base_addon import verify_jobs


def test_mixed_run_overall_failure_does_not_discard_successful_raw_builds():
    source=dict(run=1,head='commit',shards=[13,14,15])
    jobs=[dict(id=n,name=f'build ({n})',status='completed',conclusion='success') for n in source['shards']]
    run=dict(id=1,head_sha='commit',run_attempt=1,conclusion='failure')
    assert len(verify_jobs(source,run,jobs))==3
    jobs[0]['conclusion']='failure'
    with pytest.raises(ValueError,match='has not succeeded'):verify_jobs(source,run,jobs)


def test_same_part_number_in_old_and_recovery_release_keeps_distinct_cached_bytes(tmp_path,monkeypatch):
    inputs=dict(recipe_fingerprint='recipe',records=[dict(ticker='NA',ordinal=13),dict(ticker='B',ordinal=29)])
    content={};parts=[]
    for number,release in enumerate(('old-013','recovery-013')):
        coverage=('timeframe,column,query_rows,non_null_rows,tickers_with_values,first_date,last_date\n'
                  f'1d,close,1,1,1,2020-01-0{number+2},2020-01-0{number+2}\n').encode()
        dates=f'date,stock_days\n2020-01-0{number+2},1\n'.encode()
        content[release]=dict(coverage=coverage,dates=dates)
        parts.append(dict(part='base_0000',release=release,tickers=['NA' if number==0 else 'B'],
            archive_sha256='archive',coverage_sha256=hashlib.sha256(coverage).hexdigest(),
            stock_days_sha256=hashlib.sha256(dates).hexdigest()))
    def download(tag,name,directory):
        directory=Path(directory);directory.mkdir(parents=True,exist_ok=True);file=directory/name
        raw=json.dumps(inputs).encode() if name=='BUILD_INPUTS.json' else content[tag]['coverage' if name.endswith('.coverage.csv') else 'dates']
        # Match the production cache behavior: a different release cannot reuse
        # an existing same-named file with different bytes.
        if file.exists() and file.read_bytes()!=raw:raise ValueError('cached source asset fingerprint differs')
        file.write_bytes(raw);return file
    monkeypatch.setattr(base,'download',download)
    monkeypatch.setattr(base,'recipe_fingerprint',lambda:('recipe',{}))
    report=dict(parts=parts,records=[dict(ticker='NA',query_rows=1),dict(ticker='B',query_rows=1)])
    monkeypatch.setattr(base,'collect_base_reports',lambda *args:[('recovery-013',tmp_path/'13',report)])
    monkeypatch.setattr(base,'asset_index',lambda tag:{})
    monkeypatch.setattr(base,'verify_base_asset_digests',lambda *args:None)
    monkeypatch.setattr(base,'gh',lambda *args:None)
    for key,value in [('GITHUB_SHA','commit'),('GITHUB_RUN_ID','2'),('GITHUB_RUN_ATTEMPT','1')]:monkeypatch.setenv(key,value)
    base.merge(SimpleNamespace(directory=str(tmp_path),inputs_tag='inputs',build_prefix='old',routes=None))
    status=json.loads((tmp_path/'NATIVE_PRICE_BASE_STATUS_V1.json').read_text())
    assert status['selected_tickers']==2 and status['query_rows']==2
    assert len(list((tmp_path/'13').rglob('base_0000.coverage.csv')))==2

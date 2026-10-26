import hashlib,json,subprocess,tarfile
from datetime import datetime,timezone
from unittest.mock import patch
from pathlib import Path
import pytest
from fetch.fetch_world_prices import chart_rows,provider_symbol,period_end,publish_checkpoint
from ci.full_price_sources import summarize


def chart(symbol='TEST',timestamps=None):
    return {'chart':{'result':[dict(meta=dict(symbol=symbol,dataGranularity='1d'),
        timestamp=timestamps if timestamps is not None else [1735830000,1735916400],
        indicators=dict(quote=[dict(open=[10.,11.],high=[12.,13.],low=[9.,10.],close=[11.,12.],volume=[100.,200.])],
                        adjclose=[dict(adjclose=[11.,12.])]),events={})]}}


def test_share_class_provider_alias_preserves_canonical_identity():
    assert provider_symbol('BRK.B')=='BRK-B'
    frame,_=chart_rows('BRK.B',chart('BRK-B'))
    assert set(frame.ticker)=={'BRK.B'}


def test_wrong_symbol_cannot_be_joined_under_the_requested_ticker():
    with pytest.raises(ValueError,match='identity mismatch'):chart_rows('TEST',chart('OTHER'))


def test_duplicate_source_sessions_are_not_silently_discarded():
    with pytest.raises(ValueError,match='duplicate'):chart_rows('TEST',chart(timestamps=[1735830000]*2))


def test_empty_source_cannot_count_as_a_completed_ticker():
    payload={'chart':{'result':[dict(meta=dict(symbol='TEST',dataGranularity='1d'),timestamp=[],
        indicators=dict(quote=[dict(open=[],high=[],low=[],close=[],volume=[])],adjclose=[dict(adjclose=[])]))]}}
    with pytest.raises(ValueError,match='no usable daily bars'):chart_rows('TEST',payload)


def test_end_date_is_the_next_new_york_midnight():
    value=datetime.fromtimestamp(period_end('2026-10-23'),timezone.utc)
    assert value==datetime(2026,10,24,4,0,tzinfo=timezone.utc)


def test_uploaded_checkpoint_contains_original_bytes_and_fingerprints(tmp_path):
    out=tmp_path/'prices';out.mkdir();data=b'original source parquet bytes'
    file=out/('TEST'.encode().hex()+'.parquet');file.write_bytes(data)
    report=dict(requested_end_date='2026-10-23',requested=['TEST'],completed={},errors={})
    def inspect_upload(command,**kwargs):
        assert '--clobber' not in command
        archive=Path(command[-2])
        manifest=json.loads(Path(command[-1]).read_text())
        assert manifest['archive_sha256']==hashlib.sha256(archive.read_bytes()).hexdigest()
        with tarfile.open(archive) as tar:assert tar.extractfile(file.name).read()==data
        assert manifest['members'][0]['sha256']==hashlib.sha256(data).hexdigest()
        return subprocess.CompletedProcess(command,0)
    with patch('subprocess.run',side_effect=inspect_upload):
        record=publish_checkpoint(out,0,0,['TEST'],report,'provisional-tag')
    assert record['status']=='PROVISIONAL_SOURCE_CHECKPOINT' and file.read_bytes()==data


def test_missing_source_shard_cannot_pass_the_full_universe_gate(tmp_path):
    universe=tmp_path/'universe.json';parts=tmp_path/'parts';parts.mkdir();out=tmp_path/'summary'
    universe.write_text(json.dumps(dict(tickers=['A','B'],shards=2,source_commit='x',
        requested_end_date='2026-10-23',universe_label='test frozen universe')))
    record=dict(source_commit='x',requested_end_date='2026-10-23',shard=0,attempt=1,part=0,
        report=dict(requested=['A'],completed={'A':dict(rows=2,first='2020-01-01',last='2026-10-23',rows_2025_2026=1)},errors={}))
    (parts/'prices_shard_000_attempt_1_part_000.json').write_text(json.dumps(record))
    with pytest.raises(SystemExit):summarize(universe,parts,out)
    result=json.loads((out/'PRICE_SOURCE_SUMMARY.json').read_text())
    assert result['status']=='FAIL' and result['missing_shards']==[1]
    assert result['status_counts']['PENDING']==1 and not result['world_coverage_approved']

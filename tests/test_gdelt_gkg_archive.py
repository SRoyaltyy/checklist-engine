import hashlib
import io
import json
import urllib.error
import zipfile
import pytest
from fetch.gdelt_gkg_archive import alias_index,checked_stamp,parse_archive,select_catalog

STAMP='20200101000000'
ENTITIES=[dict(entity_id='probe_apple',aliases=['Apple Inc','Apple Incorporated']),
          dict(entity_id='probe_microsoft',aliases=['Microsoft Corporation'])]


def record(sequence=1,orgs='Apple Inc',tone='-1.25,1,2.25,3.25,4,5,100',date=STAMP):
    fields=['']*27
    fields[0]=STAMP+'-'+str(sequence);fields[1]=date;fields[2]='1'
    fields[3]='example.invalid';fields[4]='https://example.invalid/article-private-text'
    fields[13]=orgs;fields[15]=tone;fields[22]='narrative quotes must never be features'
    return ('\t'.join(fields)+'\n').encode()


def archive(lines,name=None):
    raw=io.BytesIO()
    with zipfile.ZipFile(raw,'w',compression=zipfile.ZIP_STORED) as file:file.writestr(name or STAMP+'.gkg.csv',b''.join(lines))
    payload=raw.getvalue()
    return payload,dict(stamp=STAMP,bytes=len(payload),md5=hashlib.md5(payload,usedforsecurity=False).hexdigest())


def test_exact_catalog_receipt_upgrades_transport_to_https_without_guessing_files():
    line=f'123 '+('a'*32)+f' http://data.gdeltproject.org/gdeltv2/{STAMP}.gkg.csv.zip\n'
    selected,receipt=select_catalog(io.BytesIO(line.encode()),[STAMP,'20250101000000'])
    assert selected[STAMP]['url'].startswith('https://data.gdeltproject.org/')
    assert selected[STAMP]['bytes']==123 and receipt['complete_catalog']
    assert receipt['missing_stamps']==['20250101000000']
    assert receipt['sha256']==hashlib.sha256(line.encode()).hexdigest()


def test_conflicting_catalog_or_nonofficial_download_is_rejected():
    first=f'123 '+('a'*32)+f' http://data.gdeltproject.org/gdeltv2/{STAMP}.gkg.csv.zip\n'
    changed=first.replace('123 ','124 ')
    with pytest.raises(ValueError,match='conflicting'):select_catalog(io.BytesIO((first+changed).encode()),[STAMP])
    foreign=first.replace('data.gdeltproject.org','other.invalid')
    with pytest.raises(ValueError,match='outside official'):select_catalog(io.BytesIO(foreign.encode()),[STAMP])
    with pytest.raises(ValueError,match='bounded'):select_catalog(io.BytesIO(first.encode()),[STAMP],10)


def test_official_root_marker_and_blank_lines_are_counted_and_hashed():
    # Actual master catalog line 123679 is a bare official directory URL.
    body=f'http://data.gdeltproject.org/gdeltv2/\n\n123 '+('a'*32)+f' http://data.gdeltproject.org/gdeltv2/{STAMP}.gkg.csv.zip\n'
    selected,receipt=select_catalog(io.BytesIO(body.encode()),[STAMP])
    assert selected[STAMP]['bytes']==123 and receipt['official_root_marker_lines']==1 and receipt['blank_lines']==1
    assert receipt['sha256']==hashlib.sha256(body.encode()).hexdigest() and receipt['lines']==3


def test_unknown_malformed_lines_are_not_silently_ignored():
    with pytest.raises(ValueError,match='line schema'):
        select_catalog(io.BytesIO(b'https://other.invalid/\n'),[STAMP])


def test_unpadded_catalog_md5_has_exactly_equivalent_zero_padded_value():
    body=f'123 abc http://data.gdeltproject.org/gdeltv2/{STAMP}.gkg.csv.zip\n'
    selected,_=select_catalog(io.BytesIO(body.encode()),[STAMP])
    assert selected[STAMP]['md5']=='abc'.zfill(32)


@pytest.mark.parametrize('stamp',['2020010100000','20200101000100','20200101000001','20200230000000'])
def test_invalid_or_nonquarterhour_batch_is_rejected(stamp):
    with pytest.raises(ValueError):checked_stamp(stamp)


def test_unique_records_fractional_tone_and_alias_deduplication_are_preserved():
    first=record(orgs='Apple Inc;Apple Incorporated;Apple Inc')
    raw,receipt=archive([first,record(2,tone='2.5,3.5,1,4.5,0,0,221'),first,record(3,orgs='Microsoft Corporation',tone='')])
    rows,stats=parse_archive(raw,receipt,ENTITIES);own={r['entity_id']:r for r in rows}
    assert own['probe_apple']['record_count']==2 and own['probe_apple']['tone_mean']==.625
    assert own['probe_apple']['word_count']==321
    assert own['probe_microsoft']['record_count']==1 and own['probe_microsoft']['tone_mean'] is None
    assert own['__corpus__']['record_count']==3 and stats['identical_duplicate_rows']==1
    assert stats['free_text_persisted'] is False
    assert 'article-private-text' not in str(rows) and 'narrative quotes' not in str(rows)


def test_duplicate_record_with_conflicting_values_is_not_silently_counted():
    raw,receipt=archive([record(),record(tone='0,0,0,0,0,0,10')])
    with pytest.raises(ValueError,match='conflicting duplicate'):parse_archive(raw,receipt,ENTITIES)


def test_old_history_cannot_accept_a_recent_substitution():
    raw,receipt=archive([record(date='20261023000000')])
    with pytest.raises(ValueError,match='requested historical batch'):parse_archive(raw,receipt,ENTITIES)


def test_neutral_tone_is_zero_and_missing_tone_is_not_zero():
    raw,receipt=archive([record(tone='0,0,0,0,0,0,1'),record(2,tone='')])
    rows,_=parse_archive(raw,receipt,ENTITIES);row=next(r for r in rows if r['entity_id']=='probe_apple')
    assert row['record_count']==2 and row['tone_observations']==1 and row['tone_missing']==1
    assert row['tone_mean']==0 and row['neutral_records']==1


@pytest.mark.parametrize('tone',['NaN,0,0,0,0,0,2','1,0,0,0,0,0,2.5','101,0,0,0,0,0,2','1,0,0'])
def test_invalid_tone_keeps_record_count_but_cannot_make_a_fake_mean(tone):
    raw,receipt=archive([record(tone=tone)])
    rows,stats=parse_archive(raw,receipt,ENTITIES);row=next(r for r in rows if r['entity_id']=='probe_apple')
    assert row['record_count']==1 and row['tone_mean'] is None and stats['invalid_tone_rows']==1


def test_corrupt_or_unreadable_org_rows_cannot_become_whole_file_zero_counts():
    malformed=record(orgs='unmatched').replace(b'unmatched',b'\xff')
    raw,receipt=archive([malformed])
    rows,stats=parse_archive(raw,receipt,ENTITIES)
    assert stats['quarantine']=={'ORGANIZATION_ENCODING':1}
    assert all(r['record_count'] is None for r in rows if r['entity_id']!='__corpus__')
    assert all(not r['complete_file_parse'] for r in rows)


def test_zero_matches_only_means_no_declared_alias_in_the_complete_requested_file():
    raw,receipt=archive([record(orgs='Unrelated Organization')])
    rows,_=parse_archive(raw,receipt,ENTITIES)
    assert next(r for r in rows if r['entity_id']=='probe_apple')['record_count']==0
    assert all(r['identity_scope']=='EXPLICIT_PROBE_ALIASES_NOT_HISTORICAL_TICKER_MAPPING' for r in rows)


def test_zip_names_md5_and_expansion_bounds_are_checked():
    raw,receipt=archive([record()],name='../'+STAMP+'.gkg.csv')
    with pytest.raises(ValueError,match='member/expanded size'):parse_archive(raw,receipt,ENTITIES)
    raw,receipt=archive([record()]);receipt['md5']='0'*32
    with pytest.raises(ValueError,match='size/MD5'):parse_archive(raw,receipt,ENTITIES)
    raw,receipt=archive([record()])
    with pytest.raises(ValueError,match='member/expanded size'):parse_archive(raw,receipt,ENTITIES,10)


def test_alias_collision_and_empty_archive_cannot_approve_numeric_source():
    with pytest.raises(ValueError,match='ambiguous'):
        alias_index([dict(entity_id='a',aliases=['Company Inc']),dict(entity_id='b',aliases=['company inc'])])
    raw,receipt=archive([])
    with pytest.raises(ValueError,match='not a zero news count'):parse_archive(raw,receipt,ENTITIES)


def test_numeric_release_keeps_nullable_integer_counts_and_float64_tone_schema(tmp_path,monkeypatch):
    import pandas as pd
    from fetch import gdelt_gkg_archive as gkg
    from ci import release_assets
    raw,receipt=archive([record(orgs='unmatched',tone='').replace(b'unmatched',b'\xff')])
    catalog=f"{receipt['bytes']} {receipt['md5']} http://data.gdeltproject.org/gdeltv2/{STAMP}.gkg.csv.zip\n".encode()
    monkeypatch.setattr(gkg.urllib.request,'urlopen',lambda *a,**k:io.BytesIO(catalog))
    monkeypatch.setattr(gkg,'fetch_bytes',lambda *args:(raw,{'http_status':200}))
    monkeypatch.setattr(gkg.time,'sleep',lambda *args:None)
    monkeypatch.setenv('GITHUB_SHA','commit');monkeypatch.setenv('GITHUB_RUN_ID','1');monkeypatch.setenv('GITHUB_RUN_ATTEMPT','1')
    calls=[];monkeypatch.setattr(release_assets,'gh_retry',lambda *args:calls.append(args))
    monkeypatch.setattr(release_assets,'publish_assets',lambda *args:calls.append(args))
    request=dict(stamps=[STAMP],entities=ENTITIES,max_catalog_bytes=1000,max_archive_bytes=10000,max_uncompressed_bytes=10000)
    gkg.run(tmp_path,request)
    frame=pd.read_parquet(tmp_path/(STAMP+'.numeric.parquet'))
    assert str(frame.record_count.dtype)=='Int64' and str(frame.tone_mean.dtype)=='float64'
    assert str(frame.batch_timestamp.dtype)=='datetime64[ns, UTC]'
    assert frame.loc[frame.entity_id=='probe_apple','record_count'].isna().all()
    assert frame.tone_mean.isna().all() and calls


def test_access_error_stops_remaining_requests_and_never_creates_zero_news_release(tmp_path,monkeypatch):
    from fetch import gdelt_gkg_archive as gkg
    from ci import release_assets
    stamps=[STAMP,'20250101000000']
    catalog=''.join(f'123 '+('a'*32)+f' http://data.gdeltproject.org/gdeltv2/{stamp}.gkg.csv.zip\n' for stamp in stamps).encode()
    monkeypatch.setattr(gkg.urllib.request,'urlopen',lambda *a,**k:io.BytesIO(catalog))
    calls=[]
    def denied(url,bound):
        calls.append(url);raise urllib.error.HTTPError(url,403,'Denied',{},None)
    monkeypatch.setattr(gkg,'fetch_bytes',denied);monkeypatch.setattr(gkg.time,'sleep',lambda *args:None)
    monkeypatch.setenv('GITHUB_SHA','commit')
    monkeypatch.setattr(release_assets,'gh_retry',lambda *args:pytest.fail('failed source must not create release'))
    request=dict(stamps=stamps,entities=ENTITIES,max_catalog_bytes=1000,max_archive_bytes=10000,max_uncompressed_bytes=10000)
    with pytest.raises(RuntimeError,match='no zero filling'):gkg.run(tmp_path,request)
    report=json.loads((tmp_path/'GDELT_GKG_SOURCE_REPORT.json').read_text())
    assert len(calls)==1 and report['parts']==[]
    assert report['attempts'][1]['status']=='NOT_ATTEMPTED_AFTER_ACCESS_OR_RATE_LIMIT'

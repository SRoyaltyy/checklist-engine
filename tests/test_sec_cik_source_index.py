import copy
import json
import pytest
from ci.sec_cik_source_index import PROOF_TAG,build_index,digest


def fixture():
    blobs={};proofs=[];tags={};refs=[]
    for shard in range(16):
        cik=1790169 if shard==9 else 1000+shard;quarantine=shard==9;tag='repair' if quarantine else 'base';tags[str(shard)]=tag
        prefix=f'CIK{cik:010d}';receipt=f'sec_world_shard_{shard:03d}_attempt_1_part_000.json'
        members=[dict(name=prefix+suffix,bytes=10,sha256=letter*64) for suffix,letter in (('.facts.parquet','a'),('.companyfacts.json.gz','b'),('.submissions.json.gz','c'))]
        manifest=dict(archive_sha256='d'*64,members=members);raw=json.dumps(manifest).encode();blobs[tag,receipt]=raw
        ref=dict(receipt=receipt,receipt_sha256=digest(raw),archive_sha256='d'*64);refs.append((tag,receipt))
        record=dict(cik=cik,official_cik=cik,root_cik=None if quarantine else cik,quarantined=quarantine,source_tag=tag,
                    raw_sha256='b'*64,parquet_sha256='a'*64,fact_rows=1,entity_name='Example')
        proof=dict(status='INTEGRITY_PASS_WITH_QUARANTINE' if quarantine else 'INTEGRITY_PASS',shard=shard,selected_tag=tag,
                   verified={str(cik):record},verified_ciks=1,numeric_fact_rows=1,archives=[ref])
        name=f'SEC_FULL_SOURCE_PROOF_{shard:03d}.json';raw=json.dumps(proof).encode();blobs[PROOF_TAG,name]=raw;proofs.append(dict(name=name,sha256=digest(raw)))
    summary=dict(status='INTEGRITY_PASS_WITH_QUARANTINE',proof_files=proofs,quarantined=[dict(cik=1790169)],
        selected_sources=tags,verified_ciks=16,numeric_fact_rows=16,archives_verified=16,proof_source_commit='f'*40)
    return summary,blobs,refs


def test_complete_cik_binding_keeps_quarantine_explicit_and_never_infers_tickers():
    summary,blobs,_=fixture();result=build_index(summary,lambda tag,name:blobs[tag,name])
    assert result['source_cik_records']==16 and result['eligible_ciks']==15 and result['eligible_fact_rows']==15
    assert result['quarantined_ciks'][0]['cik']==1790169
    assert all(r['historical_ticker_mapping']=='UNPROVEN' and 'ticker' not in r for r in result['records'])
    assert result['world_gate']=='NOT_PROVEN'


def test_changed_proof_or_receipt_bytes_are_rejected():
    for target in ('proof','receipt'):
        summary,blobs,refs=fixture();key=(PROOF_TAG,summary['proof_files'][0]['name']) if target=='proof' else refs[0]
        blobs[key]+=b' '
        with pytest.raises(ValueError,match='SHA differs'):build_index(summary,lambda tag,name:blobs[tag,name])


@pytest.mark.parametrize('mutation',['archive','numeric','raw','official_missing','duplicate_member','wrong_cik'])
def test_hash_consistent_but_semantically_wrong_source_binding_is_rejected(mutation):
    summary,blobs,refs=fixture();key=refs[0];manifest=json.loads(blobs[key])
    if mutation=='archive':manifest['archive_sha256']='e'*64
    elif mutation=='numeric':manifest['members'][0]['sha256']='e'*64
    elif mutation=='raw':manifest['members'][1]['sha256']='e'*64
    elif mutation=='official_missing':manifest['members'].pop()
    elif mutation=='duplicate_member':manifest['members'].append(copy.deepcopy(manifest['members'][0]))
    elif mutation=='wrong_cik':manifest['members'][0]['name']='CIK0000009999.facts.parquet'
    blobs[key]=json.dumps(manifest).encode()
    spec=summary['proof_files'][0];proof_key=(PROOF_TAG,spec['name']);proof=json.loads(blobs[proof_key])
    proof['archives'][0]['receipt_sha256']=digest(blobs[key]);blobs[proof_key]=json.dumps(proof).encode();spec['sha256']=digest(blobs[proof_key])
    with pytest.raises(ValueError):build_index(summary,lambda tag,name:blobs[tag,name])


def test_incomplete_shards_and_changed_universe_counts_fail():
    summary,blobs,_=fixture();summary['proof_files'].pop()
    with pytest.raises(ValueError,match='sixteen'):build_index(summary,lambda tag,name:blobs[tag,name])
    summary,blobs,_=fixture();summary['verified_ciks']=17
    with pytest.raises(ValueError,match='universe counts'):build_index(summary,lambda tag,name:blobs[tag,name])

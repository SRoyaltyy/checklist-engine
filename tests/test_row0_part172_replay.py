import io
import json
import tarfile
import numpy as np
import pandas as pd
import pyarrow as pa
import pytest
from ci import row0_part172_replay as replay
from world_answer_cache import encode_answers,registry_bytes


def packet(values,recipe,*,row_hash='c'*64):
    schema=[dict(question_id='x__1d',outcomes=[0,1]),dict(question_id='y__1d',outcomes=[0,1])]
    frame=pd.DataFrame(values,columns=['x__1d','y__1d'])
    provenance=dict(input_manifest_sha256='a'*64,recipe_fingerprint=recipe,question_tree_sha256=replay.sha(registry_bytes(schema)),
        row_keys_sha256=row_hash,eligibility_mask_sha256='d'*64)
    chunk,meta=encode_answers(frame,schema,provenance);buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w') as archive:
        for suffix,raw in (('.zst',chunk),('.json',json.dumps(meta).encode())):
            member=tarfile.TarInfo('1d_00000'+suffix);member.size=len(raw);archive.addfile(member,io.BytesIO(raw))
    return bytes(pa.Codec('zstd').compress(buffer.getvalue())),{meta['registry_sha256']:schema}


def test_all_bits_include_missing_and_allow_only_explicit_recipe_version_difference():
    values=[[0,1],[None,0],[1,None]]
    a,registry=packet(values,'1'*64);b,_=packet(values,'2'*64)
    result=replay.compare_payloads(a,b,registry,3,'1'*64,'2'*64)
    assert result==dict(chunks=1,questions=2,compared_cells=6,mismatched_cells=0,known_missing_mismatches=0)
    c,_=packet([[1,1],[0,0],[1,None]],'2'*64)
    changed=replay.compare_payloads(a,c,registry,3,'1'*64,'2'*64)
    assert changed['mismatched_cells']==2 and changed['known_missing_mismatches']==1


@pytest.mark.parametrize('problem',['rows','recipe','row_hash','corrupt'])
def test_wrong_or_corrupt_source_cannot_be_described_as_value_equality(problem):
    a,registry=packet([[0,1],[None,0]],'1'*64)
    b,_=packet([[0,1],[None,0]],'2'*64,row_hash='e'*64 if problem=='row_hash' else 'c'*64)
    if problem=='corrupt':b=b[:15]
    with pytest.raises(Exception):replay.compare_payloads(a,b,registry,3 if problem=='rows' else 2,'1'*64,'3'*64 if problem=='recipe' else '2'*64)


def test_plan_replays_exact_original_part_in_ten_bounded_groups_without_mutation(monkeypatch):
    names=[f'T{i}' for i in range(50)];part=dict(release='source',part='original172',tickers=names)
    old=dict(parts=[{}]*172+[part]);current=dict(parts=[part],request=dict(recipe_transform='RENKO_ZERO_STEP_V1',
        corrected_recipe_fingerprint='40ea182cf6fb377d12710ccbfccd7ab2b5f17b9e6e6f07df08cf4399956ca0c3'),price_answer_per_ticker_limit=5)
    composition=dict(completed=[dict(ticker=t) for t in names]);before=json.dumps([old,current,composition],sort_keys=True)
    monkeypatch.setattr(replay,'runtime',lambda:{'synthetic':True})
    plan=replay.make_plan(old,current,composition)
    assert json.dumps([old,current,composition],sort_keys=True)==before
    assert len(plan['parts'])==10 and all(len(p['tickers'])==5 for p in plan['parts'])
    assert [t for p in plan['parts'] for t in p['tickers']]==names and plan['scoring_gate']=='CLOSED'
    current['parts']=[]
    with pytest.raises(ValueError,match='source differs'):replay.make_plan(old,current,composition)

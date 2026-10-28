from copy import deepcopy
import numpy as np
import pandas as pd
import pytest
from world_answer_cache import encode_answers,decode_answers,BoundedAnswerCache,registry_bytes


def fixture(rows=37):
    registry=[dict(question_id='binary',outcomes=[False,True]),
              dict(question_id='direction',outcomes=['sell','hold','buy']),
              dict(question_id='numeric',outcomes=[-1,0,1])]
    frame=pd.DataFrame(dict(binary=([False,True,None]*rows)[:rows],
                            direction=(['hold',None,'buy','sell']*rows)[:rows],
                            numeric=([0,None,1,-1]*rows)[:rows]))
    provenance={key:('abcdef'[i%6]*64) for i,key in enumerate(
        ('input_manifest_sha256','recipe_fingerprint','question_tree_sha256','row_keys_sha256','eligibility_mask_sha256'))}
    return frame,registry,provenance


@pytest.mark.parametrize('rows',[0,1,7,8,9,37,1000])
def test_all_registered_outcomes_and_missing_roundtrip_at_bit_boundaries(rows):
    frame,registry,provenance=fixture(rows)
    compressed,meta=encode_answers(frame,registry,provenance)
    actual=decode_answers(compressed,meta,registry,provenance)
    expected=frame.astype(object).where(frame.notna(),None)
    pd.testing.assert_frame_equal(actual,expected,check_dtype=False)
    assert meta['raw_bytes']==((rows+7)//8)*6


def test_unknown_answer_never_becomes_missing_and_schema_is_not_inferred_from_sample():
    frame,registry,provenance=fixture()
    with pytest.raises(ValueError,match='unregistered'):
        encode_answers(frame.assign(direction='unregistered'),registry,provenance)
    compressed,meta=encode_answers(frame,registry,provenance)
    changed=deepcopy(registry);changed[0]['outcomes']=[True,False]
    with pytest.raises(ValueError,match='schema/provenance'):
        decode_answers(compressed,meta,changed,provenance)


def test_each_provenance_change_invalidates_cached_answers_and_bytes_are_verified():
    frame,registry,provenance=fixture();compressed,meta=encode_answers(frame,registry,provenance)
    for key in provenance:
        changed=dict(provenance);changed[key]='0'*64
        with pytest.raises(ValueError,match='provenance'):
            decode_answers(compressed,meta,registry,changed)
    with pytest.raises(ValueError,match='compressed'):
        decode_answers(compressed+b'!',meta,registry,provenance)
    with pytest.raises(ValueError,match='decode bound'):
        decode_answers(compressed,meta,registry,provenance,max_raw_bytes=1)


def test_cache_eviction_is_a_recomputable_miss_without_dropping_registered_questions():
    frame,registry,provenance=fixture();compressed,meta=encode_answers(frame,registry,provenance)
    import json
    size=len(compressed)+len(json.dumps(meta,sort_keys=True).encode())
    cache=BoundedAnswerCache(size+10)
    cache.put(frame,registry,provenance)
    changed=dict(provenance,row_keys_sha256='0'*64)
    cache.put(frame,registry,changed)
    assert cache.evictions==1 and cache.bytes<=cache.max_bytes
    assert cache.get(registry,provenance) is None
    assert cache.get(registry,changed) is not None
    assert [q['question_id'] for q in registry]==list(frame)
    with pytest.raises(ValueError,match='single answer chunk'):
        BoundedAnswerCache(1).put(frame,registry,provenance)


def test_fixed_outcome_dictionary_and_identifiers_reject_ambiguity():
    for registry in ([dict(question_id='q',outcomes=[None,1])],
                     [dict(question_id='q',outcomes=[False,0])],
                     [dict(question_id='q',outcomes=[float('inf')])]):
        with pytest.raises(ValueError):registry_bytes(registry)

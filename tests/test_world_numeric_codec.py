from copy import deepcopy
import numpy as np
import pytest
from world_numeric_codec import encode_numeric,decode_numeric,PREDICTOR_CHOICES


def source(rows):
    # Explicit uint64 patterns include +/-0, both infinities, the smallest
    # subnormal and several distinct quiet/signalling NaN payloads.
    bits=np.array([0,0x8000000000000000,0x7ff0000000000000,0xfff0000000000000,
                   1,0x7ff8000000000123,0x7ff0000000000456,0xfff8000000000789,
                   0x3ff0000000000000,0x3ff0000000000001],dtype=np.uint64)
    values=np.resize(bits,rows*4).reshape(rows,4).view(np.float64)
    columns=['SMA20','ATR14','volume','other']
    provenance={k:letter*64 for k,letter in zip(('input_manifest_sha256','recipe_fingerprint','row_keys_sha256'),'abc')}
    return values,columns,provenance


@pytest.mark.parametrize('predictors',PREDICTOR_CHOICES)
@pytest.mark.parametrize('rows',[0,1,2,7,8,257])
def test_every_float64_bit_roundtrips_including_nan_payloads_and_signed_zero(rows,predictors):
    values,columns,provenance=source(rows)
    payload,metadata=encode_numeric(values,columns,provenance,predictors=predictors)
    restored=decode_numeric(payload,metadata,columns,provenance)
    assert restored.tobytes()==values.tobytes()
    assert metadata['raw_bytes']==values.nbytes


@pytest.mark.parametrize('predictors',PREDICTOR_CHOICES)
def test_noncontiguous_values_and_big_endian_inputs_keep_exact_bits(predictors):
    values,columns,provenance=source(31)
    for matrix in (values[::-1],values.astype('>f8')):
        payload,metadata=encode_numeric(matrix,columns,provenance,predictors=predictors)
        restored=decode_numeric(payload,metadata,columns,provenance)
        assert restored.tobytes()==matrix.astype('<f8').tobytes()


@pytest.mark.parametrize('dtype',[np.float32,np.int64])
def test_codec_never_implicitly_reduces_precision_or_coerces_integers(dtype):
    values,columns,provenance=source(5)
    with pytest.raises(ValueError,match='float64 matrix'):
        encode_numeric(np.zeros(values.shape,dtype=dtype),columns,provenance)


@pytest.mark.parametrize('field,value',[('rows',-1),('columns',2),('raw_bytes',2**40),('schema_sha256','wrong'),
                                        ('predictors',['NOT_A_PREDICTOR']),('dtype','<f4')])
def test_changed_shape_schema_or_decode_size_fails_before_allocation(field,value):
    values,columns,provenance=source(7);payload,metadata=encode_numeric(values,columns,provenance)
    metadata[field]=value
    with pytest.raises(ValueError,match='shape/schema/provenance or decode bound|unknown numeric predictors'):
        decode_numeric(payload,metadata,columns,provenance)


def test_corrupted_payload_and_wrong_source_cannot_decode():
    values,columns,provenance=source(7);payload,metadata=encode_numeric(values,columns,provenance)
    with pytest.raises(ValueError,match='compressed numeric bytes'):
        decode_numeric(payload[:-1]+bytes([payload[-1]^1]),metadata,columns,provenance)
    changed=dict(provenance,recipe_fingerprint='d'*64)
    with pytest.raises(ValueError,match='provenance'):
        decode_numeric(payload,metadata,columns,changed)


def test_plain_byte_planes_roundtrip_every_special_bit():
    values,columns,provenance=source(30)
    payload,metadata=encode_numeric(values,columns,provenance,predictors=())
    assert metadata['predictors']==[]
    restored=decode_numeric(payload,metadata,columns,provenance)
    assert restored.tobytes()==np.ascontiguousarray(values,dtype='<f8').tobytes()


def test_claiming_plain_planes_for_an_xor_payload_fails_the_bit_check():
    values,columns,provenance=source(12)
    payload,metadata=encode_numeric(values,columns,provenance)
    metadata['predictors']=[]
    with pytest.raises(ValueError,match='decoded numeric bit pattern differs'):
        decode_numeric(payload,metadata,columns,provenance)


@pytest.mark.parametrize('missing',[None,'',False])
def test_missing_or_implicit_predictor_modes_do_not_inherit_plain_encoding(missing):
    values,columns,provenance=source(12);payload,metadata=encode_numeric(values,columns,provenance,predictors=())
    metadata['predictors']=missing
    with pytest.raises(ValueError,match='explicit numeric predictor'):decode_numeric(payload,metadata,columns,provenance)


def test_delta_format_is_distinct_and_uint64_wraparound_is_exact():
    bits=np.array([[0],[2**64-1],[1],[2**63],[0]],dtype=np.uint64)
    columns=['bits'];provenance=source(1)[2]
    payload,metadata=encode_numeric(bits.view(np.float64),columns,provenance,predictors=('DELTA2_TIME','ZIGZAG'))
    assert metadata['format']=='NATIVE_FLOAT64_DELTA_BYTEPLANES_V2'
    assert decode_numeric(payload,metadata,columns,provenance).view(np.uint64).tolist()==bits.tolist()
    metadata['format']='NATIVE_FLOAT64_XOR_BYTEPLANES_V1'
    with pytest.raises(ValueError,match='shape/schema'):decode_numeric(payload,metadata,columns,provenance)


@pytest.mark.parametrize('predictors',PREDICTOR_CHOICES)
def test_unstructured_uint64_patterns_roundtrip_without_float_arithmetic(predictors):
    rng=np.random.default_rng(317)
    bits=rng.integers(0,2**64-1,size=(47,19),dtype=np.uint64)
    columns=[f'field{i}' for i in range(19)];provenance=source(1)[2]
    payload,meta=encode_numeric(bits.view(np.float64),columns,provenance,predictors=predictors)
    assert decode_numeric(payload,meta,columns,provenance).view(np.uint64).tobytes()==bits.tobytes()


def test_repeated_columns_and_time_runs_compress_without_formula_recomputation():
    values=np.tile(np.arange(200,dtype=np.float64)[:,None],(1,20))
    columns=[f'field{i}' for i in range(20)];provenance=source(1)[2]
    payload,metadata=encode_numeric(values,columns,provenance)
    assert len(payload)<values.nbytes/10
    restored=decode_numeric(payload,metadata,columns,provenance)
    assert restored.tobytes()==values.tobytes()

"""Bit-exact float64 storage; no quantization, downcasting or semantic pruning.

Temporal and adjacent-column XOR predictors are reversible compression only.
The decoder does not run indicator formulas or require raw OHLCV to recover
stored values, including signed zero, infinities and NaN payload bits.
"""
import hashlib
import json
import re
import numpy as np
import pyarrow as pa

PROVENANCE=('input_manifest_sha256','recipe_fingerprint','row_keys_sha256')
PREDICTOR_CHOICES=(('XOR_TIME','XOR_ADJACENT_COLUMNS'),(),
    ('DELTA_TIME',),('DELTA_TIME','ZIGZAG'),('DELTA2_TIME',),('DELTA2_TIME','ZIGZAG'),
    ('DELTA_TIME','DELTA_ADJACENT_COLUMNS'),('DELTA_TIME','DELTA_ADJACENT_COLUMNS','ZIGZAG'),
    ('DELTA2_TIME','DELTA_ADJACENT_COLUMNS'),('DELTA2_TIME','DELTA_ADJACENT_COLUMNS','ZIGZAG'))


def checked_predictors(predictors):
    if not isinstance(predictors,(tuple,list)) or any(not isinstance(p,str) for p in predictors):
        raise ValueError('explicit numeric predictor list required')
    result=tuple(predictors)
    if result not in PREDICTOR_CHOICES:raise ValueError('unknown numeric predictors')
    return result


def encoding_format(predictors):
    return 'NATIVE_FLOAT64_DELTA_BYTEPLANES_V2' if any(p.startswith('DELTA') for p in predictors) else 'NATIVE_FLOAT64_XOR_BYTEPLANES_V1'


def transform_words(words,predictors,decode=False):
    """Only uint64 arithmetic, modulo 2**64. No floating point or indicator math."""
    for step in reversed(predictors) if decode else predictors:
        if step=='ZIGZAG':
            words[:]=(words>>np.uint64(1))^(np.uint64(0)-(words&np.uint64(1))) if decode else (words<<np.uint64(1))^(np.uint64(0)-(words>>np.uint64(63)))
        elif step=='XOR_TIME':
            if decode:np.bitwise_xor.accumulate(words,axis=1,out=words)
            elif words.shape[1]>1:words[:,1:]=words[:,1:]^words[:,:-1]
        elif step=='XOR_ADJACENT_COLUMNS':
            if decode:np.bitwise_xor.accumulate(words,axis=0,out=words)
            elif words.shape[0]>1:words[1:]=words[1:]^words[:-1]
        elif step in ('DELTA_TIME','DELTA2_TIME'):
            for _ in range(2 if step=='DELTA2_TIME' else 1):
                if decode:np.add.accumulate(words,axis=1,out=words)
                elif words.shape[1]>1:words[:,1:]=words[:,1:]-words[:,:-1]
        elif step=='DELTA_ADJACENT_COLUMNS':
            if decode:np.add.accumulate(words,axis=0,out=words)
            elif words.shape[0]>1:words[1:]=words[1:]-words[:-1]
    return words


def digest(raw):return hashlib.sha256(raw).hexdigest()


def schema_bytes(columns):
    if not columns or len(columns)!=len(set(columns)) or any(not isinstance(c,str) or not c for c in columns):
        raise ValueError('unique nonempty numeric columns required')
    return json.dumps(list(columns),ensure_ascii=True,separators=(',',':')).encode()


def validate_provenance(provenance):
    if any(not re.fullmatch('[0-9a-f]{64}',str(provenance.get(k,''))) for k in PROVENANCE):
        raise ValueError('complete numeric source/recipe/row provenance required')


def encode_numeric(values,columns,provenance,max_raw_bytes=1000000000,
                   predictors=('XOR_TIME','XOR_ADJACENT_COLUMNS')):
    schema=schema_bytes(columns);validate_provenance(provenance)
    values=np.asarray(values)
    if values.ndim!=2 or values.shape[1]!=len(columns) or values.dtype.kind!='f' or values.dtype.itemsize!=8:
        raise ValueError('numeric codec requires a two-dimensional float64 matrix; no implicit rounding')
    if values.nbytes>max_raw_bytes:raise ValueError('numeric chunk exceeds raw byte bound')
    # Byte order normalization does not convert numerical precision.
    predictors=checked_predictors(predictors)
    original=np.ascontiguousarray(values,dtype='<f8').view('<u8')
    raw=original.tobytes();words=original.T.copy()
    transform_words(words,predictors)
    planes=words.view(np.uint8).reshape(len(columns),len(values),8).transpose(2,0,1).tobytes()
    payload=bytes(pa.Codec('zstd',compression_level=19).compress(planes))
    metadata=dict(format=encoding_format(predictors),rows=len(values),columns=len(columns),
        schema_sha256=digest(schema),provenance=dict(provenance),raw_bytes=len(raw),raw_sha256=digest(raw),
        compressed_bytes=len(payload),compressed_sha256=digest(payload),dtype='<f8',
        compression_level=19,predictors=list(predictors),
        precision='ALL_FLOAT64_BITS_RETAINED',acceptance_gate='ENCODING_ONLY_NOT_WORLD_ACCEPTANCE')
    return payload,metadata


def decode_numeric(payload,metadata,columns,provenance,max_raw_bytes=1000000000):
    schema=schema_bytes(columns);validate_provenance(provenance)
    rows=metadata['rows'];count=metadata['columns']
    predictors=checked_predictors(metadata.get('predictors'))
    if (metadata['format']!=encoding_format(predictors) or metadata['dtype']!='<f8'
        or metadata['schema_sha256']!=digest(schema) or metadata['provenance']!=provenance
        or type(rows) is not int or rows<0 or type(count) is not int or count!=len(columns)
        or metadata['raw_bytes']!=rows*count*8 or not 0<=metadata['raw_bytes']<=max_raw_bytes
        ):
        raise ValueError('numeric shape/schema/provenance or decode bound differs')
    if len(payload)!=metadata['compressed_bytes'] or digest(payload)!=metadata['compressed_sha256']:
        raise ValueError('compressed numeric bytes differ')
    planes=bytes(pa.Codec('zstd').decompress(payload,metadata['raw_bytes']))
    words=np.frombuffer(planes,dtype=np.uint8).reshape(8,count,rows).transpose(1,2,0).copy().view('<u8').reshape(count,rows)
    transform_words(words,predictors,decode=True)
    original=words.T.copy()
    if digest(original.tobytes())!=metadata['raw_sha256']:raise ValueError('decoded numeric bit pattern differs')
    return original.view('<f8')

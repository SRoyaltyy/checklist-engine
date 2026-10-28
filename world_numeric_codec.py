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


def digest(raw):return hashlib.sha256(raw).hexdigest()


def schema_bytes(columns):
    if not columns or len(columns)!=len(set(columns)) or any(not isinstance(c,str) or not c for c in columns):
        raise ValueError('unique nonempty numeric columns required')
    return json.dumps(list(columns),ensure_ascii=True,separators=(',',':')).encode()


def validate_provenance(provenance):
    if any(not re.fullmatch('[0-9a-f]{64}',str(provenance.get(k,''))) for k in PROVENANCE):
        raise ValueError('complete numeric source/recipe/row provenance required')


def encode_numeric(values,columns,provenance,max_raw_bytes=1000000000):
    schema=schema_bytes(columns);validate_provenance(provenance)
    values=np.asarray(values)
    if values.ndim!=2 or values.shape[1]!=len(columns) or values.dtype.kind!='f' or values.dtype.itemsize!=8:
        raise ValueError('numeric codec requires a two-dimensional float64 matrix; no implicit rounding')
    if values.nbytes>max_raw_bytes:raise ValueError('numeric chunk exceeds raw byte bound')
    # Byte order normalization does not convert numerical precision.
    original=np.ascontiguousarray(values,dtype='<f8').view('<u8')
    raw=original.tobytes();words=original.T.copy()
    if words.shape[1]>1:words[:,1:]=words[:,1:]^words[:,:-1]
    if words.shape[0]>1:words[1:]=words[1:]^words[:-1]
    planes=words.view(np.uint8).reshape(len(columns),len(values),8).transpose(2,0,1).tobytes()
    payload=bytes(pa.Codec('zstd',compression_level=19).compress(planes))
    metadata=dict(format='NATIVE_FLOAT64_XOR_BYTEPLANES_V1',rows=len(values),columns=len(columns),
        schema_sha256=digest(schema),provenance=dict(provenance),raw_bytes=len(raw),raw_sha256=digest(raw),
        compressed_bytes=len(payload),compressed_sha256=digest(payload),dtype='<f8',
        compression_level=19,predictors=['XOR_TIME','XOR_ADJACENT_COLUMNS'],
        precision='ALL_FLOAT64_BITS_RETAINED',acceptance_gate='ENCODING_ONLY_NOT_WORLD_ACCEPTANCE')
    return payload,metadata


def decode_numeric(payload,metadata,columns,provenance,max_raw_bytes=1000000000):
    schema=schema_bytes(columns);validate_provenance(provenance)
    rows=metadata['rows'];count=metadata['columns']
    if (metadata['format']!='NATIVE_FLOAT64_XOR_BYTEPLANES_V1' or metadata['dtype']!='<f8'
        or metadata['schema_sha256']!=digest(schema) or metadata['provenance']!=provenance
        or type(rows) is not int or rows<0 or count!=len(columns)
        or metadata['raw_bytes']!=rows*count*8 or not 0<=metadata['raw_bytes']<=max_raw_bytes
        or metadata['predictors']!=['XOR_TIME','XOR_ADJACENT_COLUMNS']):
        raise ValueError('numeric shape/schema/provenance or decode bound differs')
    if len(payload)!=metadata['compressed_bytes'] or digest(payload)!=metadata['compressed_sha256']:
        raise ValueError('compressed numeric bytes differ')
    planes=bytes(pa.Codec('zstd').decompress(payload,metadata['raw_bytes']))
    words=np.frombuffer(planes,dtype=np.uint8).reshape(8,count,rows).transpose(1,2,0).copy().view('<u8').reshape(count,rows)
    if count:np.bitwise_xor.accumulate(words,axis=0,out=words)
    if rows:np.bitwise_xor.accumulate(words,axis=1,out=words)
    original=words.T.copy()
    if digest(original.tobytes())!=metadata['raw_sha256']:raise ValueError('decoded numeric bit pattern differs')
    return original.view('<f8')

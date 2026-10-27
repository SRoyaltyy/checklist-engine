"""Lossless, provenance-bound storage of registered fixed-outcome answers.

The shared registry is stored once. Chunks carry its hash rather than repeated
question names/outcome dictionaries. This codec grants no PIT/world approval.
"""
import hashlib
import json
import math
import re

import numpy as np
import pandas as pd
import pyarrow as pa

PROVENANCE = ('input_manifest_sha256', 'recipe_fingerprint', 'question_tree_sha256',
              'row_keys_sha256', 'eligibility_mask_sha256')


def digest(raw):return hashlib.sha256(raw).hexdigest()


def registry_bytes(registry):
    ids=set()
    for question in registry:
        name=question['question_id'];outcomes=question['outcomes']
        if not isinstance(name,str) or not name or name in ids:raise ValueError('unique registered question ids required')
        if not 1<=len(outcomes)<=65535 or not pd.Index(outcomes).is_unique:
            raise ValueError('unique fixed outcome dictionary required')
        for value in outcomes:
            if value is None or not isinstance(value,(str,int,float,bool)) or (isinstance(value,float) and not math.isfinite(value)):
                raise ValueError('outcome must be a finite registered scalar; missing is implicit')
        ids.add(name)
    if not ids:raise ValueError('empty question registry')
    return json.dumps(registry,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def validate_provenance(provenance):
    if any(not re.fullmatch('[0-9a-f]{64}',str(provenance.get(key,''))) for key in PROVENANCE):
        raise ValueError('complete provenance hashes required')


def encode_answers(frame,registry,provenance,max_cells=10000000):
    schema=registry_bytes(registry);validate_provenance(provenance)
    if list(frame)!=[q['question_id'] for q in registry] or frame.size>max_cells:
        raise ValueError('answer chunk schema/order or size differs')
    planes=[]
    for question in registry:
        values=frame[question['question_id']]
        if (values.notna() & ~values.isin(question['outcomes'])).any():
            raise ValueError('unregistered answer; do not silently make it missing')
        categorical=pd.Categorical(values,categories=question['outcomes'])
        if ((categorical.codes<0)&values.notna().to_numpy()).any():
            raise ValueError('unregistered answer; do not silently make it missing')
        codes=(categorical.codes.astype(np.int64)+1).astype(np.uint16)
        bits=max(1,int(math.ceil(math.log2(len(question['outcomes'])+1))))
        for bit in range(bits):
            planes.append(np.packbits(((codes>>bit)&1).astype(np.uint8),bitorder='little').tobytes())
    raw=b''.join(planes)
    compressed=bytes(pa.Codec('zstd',compression_level=9).compress(raw))
    meta=dict(format='REGISTERED_ANSWER_BITPLANES_V1',rows=len(frame),registry_sha256=digest(schema),
              provenance=dict(provenance),raw_bytes=len(raw),raw_sha256=digest(raw),
              compressed_bytes=len(compressed),compressed_sha256=digest(compressed),
              codec='zstd',compression_level=9,bitorder='little',missing_code=0,
              acceptance_gate='ENCODING_ONLY_NOT_WORLD_OR_PIT_APPROVAL')
    return compressed,meta


def decode_answers(compressed,meta,registry,provenance,max_raw_bytes=256000000):
    schema=registry_bytes(registry);validate_provenance(provenance)
    if (meta['format']!='REGISTERED_ANSWER_BITPLANES_V1' or meta['registry_sha256']!=digest(schema)
        or meta['provenance']!=provenance or meta['rows']<0 or not 0<=meta['raw_bytes']<=max_raw_bytes):
        raise ValueError('answer schema/provenance or decode bound differs')
    if len(compressed)!=meta['compressed_bytes'] or digest(compressed)!=meta['compressed_sha256']:
        raise ValueError('compressed answer bytes differ')
    rows=meta['rows'];stride=(rows+7)//8
    expected=stride*sum(max(1,int(math.ceil(math.log2(len(q['outcomes'])+1)))) for q in registry)
    if expected!=meta['raw_bytes']:raise ValueError('answer bitplane shape differs')
    raw=bytes(pa.Codec('zstd').decompress(compressed,meta['raw_bytes']))
    if digest(raw)!=meta['raw_sha256']:raise ValueError('raw answer bytes differ')
    result={};offset=0
    for question in registry:
        outcomes=question['outcomes'];bits=max(1,int(math.ceil(math.log2(len(outcomes)+1))))
        codes=np.zeros(rows,dtype=np.uint16)
        for bit in range(bits):
            packed=np.frombuffer(raw[offset:offset+stride],dtype=np.uint8);offset+=stride
            unpacked=np.unpackbits(packed,bitorder='little')
            if unpacked[rows:].any():raise ValueError('nonzero answer padding')
            codes|=unpacked[:rows].astype(np.uint16)<<bit
        if (codes>len(outcomes)).any():raise ValueError('answer code outside registered dictionary')
        values=np.empty(rows,dtype=object);values[:]=None
        valid=codes>0
        values[valid]=np.asarray(outcomes,dtype=object)[codes[valid]-1]
        result[question['question_id']]=values
    return pd.DataFrame(result,dtype=object)


class BoundedAnswerCache:
    """Process-local LRU; eviction changes storage only, never the registry.

    Callers recompute a miss from bound inputs. A coordinator must divide a
    global encoded-byte budget among workers; Python object/RSS overhead is
    separate and this local cache is not a global world-output cap proof.
    """
    def __init__(self,max_bytes):
        from collections import OrderedDict
        if type(max_bytes) is not int or max_bytes<1:raise ValueError('positive byte cap required')
        self.max_bytes=max_bytes;self.entries=OrderedDict();self.bytes=0;self.evictions=0

    @staticmethod
    def key(registry,provenance):
        validate_provenance(provenance)
        return digest(registry_bytes(registry)+json.dumps(provenance,sort_keys=True).encode())

    def put(self,frame,registry,provenance):
        compressed,meta=encode_answers(frame,registry,provenance)
        size=len(compressed)+len(json.dumps(meta,sort_keys=True).encode())
        if size>self.max_bytes:raise ValueError('single answer chunk exceeds the cache byte cap')
        key=self.key(registry,provenance)
        if key in self.entries:self.bytes-=self.entries.pop(key)[2]
        while self.bytes+size>self.max_bytes:
            _,entry=self.entries.popitem(last=False);self.bytes-=entry[2];self.evictions+=1
        self.entries[key]=(compressed,meta,size);self.bytes+=size
        return key

    def get(self,registry,provenance):
        key=self.key(registry,provenance)
        if key not in self.entries:return None
        entry=self.entries.pop(key);self.entries[key]=entry
        return decode_answers(entry[0],entry[1],registry,provenance)

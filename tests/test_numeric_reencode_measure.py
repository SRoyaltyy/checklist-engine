import hashlib
import io
import json
import tarfile
import numpy as np
import pyarrow as pa
import pytest
from ci.numeric_reencode_measure import FRAMES,checked_members,choose_encoding,digest,expanded,reencode
from world_numeric_codec import PREDICTOR_CHOICES,decode_numeric,encode_numeric


def fixture(root):
    columns=['a','b','c','d'];ticker='TEST'
    bits=np.resize(np.array([0,2**63,2**64-1,0x7ff0000000000000,0x7ff8000000000123,1,0x3ff0000000000001],dtype=np.uint64),32).reshape(8,4)
    values=bits.view(np.float64);dates=np.arange(8,dtype='<i8').tobytes()
    provenance=dict(input_manifest_sha256='a'*64,recipe_fingerprint='b'*64,row_keys_sha256=digest(ticker.encode()+dates))
    registry={tf:dict(columns=columns) for tf in FRAMES};out=io.BytesIO();frames=[]
    with tarfile.open(fileobj=out,mode='w') as target:
        for tf in FRAMES:
            payload,meta=encode_numeric(values,columns,provenance)
            meta.update(ticker=ticker,timeframe=tf,dates_sha256=digest(dates))
            frames.append(dict(timeframe=tf,native_rows=8,columns=4))
            for suffix,raw in (('.numeric.zst',payload),('.json',json.dumps(meta).encode()),('.dates.zst',bytes(pa.Codec('zstd').compress(dates)))):
                member=tarfile.TarInfo(tf+suffix);member.size=len(raw);target.addfile(member,io.BytesIO(raw))
    packed=bytes(pa.Codec('zstd').compress(out.getvalue()))
    source=root/'source.zst';source.write_bytes(packed);reg=root/'registry.json';reg.write_text(json.dumps(registry))
    stock=dict(ticker=ticker,source_rows=9,container_sha256=digest(packed),recipe_fingerprint='b'*64,timeframes=frames)
    return source,reg,stock,values,dates


def test_trial_selection_retains_special_bits_and_selects_actual_smallest_encoding(tmp_path):
    source,reg,stock,values,dates=fixture(tmp_path);registry=json.loads(reg.read_text())
    old=json.loads(checked_members(source.read_bytes())['1d.json'])
    payload,meta,trials=choose_encoding(values,registry['1d']['columns'],old['provenance'])
    assert len(trials)==len(PREDICTOR_CHOICES)
    assert len(payload)==min(r['bytes'] for r in trials)
    assert decode_numeric(payload,meta,registry['1d']['columns'],old['provenance']).tobytes()==values.tobytes()


def test_persisted_all_timeframe_container_is_exact_without_any_indicator_recompute(tmp_path):
    source,reg,stock,values,dates=fixture(tmp_path)
    result=reencode(source,reg,stock,tmp_path/'out')
    packed=(tmp_path/'out'/'54455354.all_native_values.tar.zst').read_bytes();members=checked_members(packed)
    assert len(members)==66 and len(result['timeframes'])==22 and result['indicator_calls']==0
    assert result['container_sha256']==hashlib.sha256(packed).hexdigest()
    registry=json.loads(reg.read_text())
    for tf in FRAMES:
        meta=json.loads(members[tf+'.json'])
        restored=decode_numeric(members[tf+'.numeric.zst'],meta,registry[tf]['columns'],meta['provenance'])
        assert restored.tobytes()==values.tobytes()
        assert expanded(members[tf+'.dates.zst'],len(dates))==dates


def test_changed_source_container_fails_before_creating_output(tmp_path):
    source,reg,stock,_,_=fixture(tmp_path);stock['container_sha256']='0'*64
    with pytest.raises(ValueError,match='source container fingerprint'):reencode(source,reg,stock,tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_expansion_bound_and_exact_archive_membership_are_enforced():
    compressed=bytes(pa.Codec('zstd').compress(b'1234567890'))
    with pytest.raises(ValueError,match='expansion bound'):expanded(compressed,9)
    output=io.BytesIO()
    with tarfile.open(fileobj=output,mode='w') as target:
        row=tarfile.TarInfo('unexpected');row.size=1;target.addfile(row,io.BytesIO(b'x'))
    with pytest.raises(ValueError,match='member set'):checked_members(bytes(pa.Codec('zstd').compress(output.getvalue())))

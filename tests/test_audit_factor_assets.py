import copy
import hashlib

import pandas as pd
import pytest

from ci.audit_factor_assets import audit, staged_path
from world_timeframes import TIMEFRAMES


@pytest.fixture
def published(tmp_path):
    tag = 'published-v1'
    folder = tmp_path / tag
    folder.mkdir()
    factors = []
    assets = []
    for tf in TIMEFRAMES:
        frame = pd.DataFrame(dict(candle_start=pd.to_datetime(['2019-11-01', '2019-12-02']),
                                  source_candle_end=pd.to_datetime(['2019-11-29', '2019-12-31']),
                                  available_from=pd.to_datetime(['2019-12-02', '2020-01-02']),
                                  value=[1.0000000001, float('nan')]))
        name = 'native_' + tf + '.parquet'
        file = folder / name
        frame.to_parquet(file, index=False)
        fingerprint = hashlib.sha256(file.read_bytes()).hexdigest()
        assets.append(dict(name=name, size=file.stat().st_size, digest='sha256:' + fingerprint, state='uploaded'))
        factors.append(dict(family='example', timeframe=tf, release=tag, asset=name, sha256=fingerprint,
                            columns=['value'], numeric_dtypes={'value': 'float64'}, native_rows=2))
    inventory = {tag: dict(tag_name=tag, draft=False, assets=assets)}
    store = dict(format='FACTORED_NATIVE_WORLD_CONTEXT_V1', factors=factors)
    return tmp_path, store, inventory


def test_actual_release_readback_counts_each_bound_file_and_keeps_world_gates_closed(published):
    root, store, inventory = published
    expected = sum(row['size'] for row in inventory['published-v1']['assets'])
    result = audit(store, root, inventory, expected)
    assert result['status'] == 'PASS_FACTOR_RELEASE_READBACK_ONLY'
    assert result['native_factor_bytes'] == expected and result['checked_bindings'] == 22
    assert result['world_gate'] == result['full_world_storage_gate'] == 'NOT_PROVEN'
    assert result['scoring_gate'] == 'CLOSED'


@pytest.mark.parametrize('change', ['wrong_release', 'local_only_path', 'wrong_rows', 'wrong_dtype', 'wrong_hash', 'draft', 'missing_grid'])
def test_local_success_cannot_hide_unusable_published_binding(published, change):
    root, store, inventory = published
    row = store['factors'][0]
    if change == 'wrong_release':
        row['release'] = 'original-raw-release'
    elif change == 'local_only_path':
        row['asset'] = 'native/' + row['asset']
    elif change == 'wrong_rows':
        row['native_rows'] = 1
    elif change == 'wrong_dtype':
        row['numeric_dtypes']['value'] = 'float32'
    elif change == 'wrong_hash':
        row['sha256'] = '0' * 64
    elif change == 'draft':
        inventory['published-v1']['draft'] = True
    elif change == 'missing_grid':
        store['factors'].pop()
    result = audit(store, root, inventory)
    assert result['status'] == 'FAIL_FACTOR_RELEASE_READBACK' and result['failures']


def test_changed_staged_file_and_underreported_native_bytes_fail(published):
    root, store, inventory = published
    result = audit(store, root, inventory, 1)
    assert any('declared factor bytes' in row['error'] for row in result['failures'])
    file = root / 'published-v1' / store['factors'][0]['asset']
    raw = file.read_bytes()
    file.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
    result = audit(store, root, inventory)
    assert any('staged factor bytes' in row['error'] for row in result['failures'])


def test_duplicate_binding_and_duplicate_attached_column_fail(published):
    root, store, inventory = published
    store['factors'].append(copy.deepcopy(store['factors'][0]))
    result = audit(store, root, inventory)
    assert any('duplicate family' in row['error'] for row in result['failures'])
    store['factors'][-1]['family'] = 'other'
    result = audit(store, root, inventory)
    assert any('duplicate attached feature' in row['error'] for row in result['failures'])


@pytest.mark.parametrize('release,asset', [('../outside', 'data.parquet'), ('release', 'C:data.parquet'), ('release', '../data.parquet')])
def test_manifest_cannot_read_outside_staged_release_root(tmp_path, release, asset):
    with pytest.raises(ValueError):
        staged_path(tmp_path, release, asset)

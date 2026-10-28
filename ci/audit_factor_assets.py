"""Read back every manifest binding from its actual published release.

This offline audit authenticates staged release files against saved GitHub
inventories. Factor bytes are measured once per release/asset, never projected
from a sample. Passing says nothing about missing world types or questions.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

import pandas as pd

from world_context_store import validate_factor
from world_timeframes import TIMEFRAMES


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def staged_path(root, release, asset):
    # GitHub release assets are names, not paths inside the producer workspace.
    for value in (release, asset):
        if not isinstance(value, str) or not value or value in ('.', '..') or any(c in value for c in '/\\:'):
            raise ValueError('literal release tag and asset name required')
    path = (root / release / asset).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('staged asset escapes root')
    return path


def audit(store, directory, inventories, declared_factor_bytes=None):
    """Inventories are the raw public release objects, indexed by tag_name."""
    if store.get('format') != 'FACTORED_NATIVE_WORLD_CONTEXT_V1' or not store.get('factors'):
        raise ValueError('nonempty native factor manifest required')
    root = Path(directory)
    failures = []
    checked = []
    assets = {}
    grids = {}
    columns_seen = set()
    for binding in store['factors']:
        label = {key: binding.get(key) for key in ('family', 'symbol', 'timeframe', 'release', 'asset')}
        try:
            release, name = binding['release'], binding['asset']
            file = staged_path(root, release, name)
            tf = binding['timeframe']
            if tf not in TIMEFRAMES or not binding.get('family'):
                raise ValueError('factor family/timeframe invalid')
            group = (binding['family'], binding.get('symbol'))
            grid = grids.setdefault(group, set())
            if tf in grid:
                raise ValueError('duplicate family/symbol/timeframe binding')
            grid.add(tf)
            inventory = inventories[release]
            if inventory['tag_name'] != release or inventory['draft']:
                raise ValueError('release identity or publication state differs')
            listed = inventory['assets']
            indexed = {row['name']: row for row in listed}
            if len(indexed) != len(listed):
                raise ValueError('duplicate release asset name')
            asset = indexed[name]
            size = asset['size']
            fingerprint = binding['sha256']
            if (asset['state'] != 'uploaded' or type(size) is not int or size < 1
                    or not re.fullmatch('[0-9a-f]{64}', fingerprint)
                    or asset['digest'] != 'sha256:' + fingerprint):
                raise ValueError('published factor digest/size/state differs')
            if file.stat().st_size != size or digest(file) != fingerprint:
                raise ValueError('staged factor bytes differ from the published asset')
            native = pd.read_parquet(file)
            columns = validate_factor(native)
            if (type(binding['native_rows']) is not int or len(native) != binding['native_rows']
                    or columns != binding['columns']
                    or {c: str(native[c].dtype) for c in columns} != binding['numeric_dtypes']):
                raise ValueError('persisted factor dimensions/columns/dtypes differ from binding')
            keys = {(tf, c) for c in columns}
            if keys & columns_seen:
                raise ValueError('duplicate attached feature column/timeframe')
            columns_seen.update(keys)
            assets[(release, name)] = size
            checked.append(dict(label, bytes=size, sha256=fingerprint, native_rows=len(native), columns=len(columns)))
        except (KeyError, ValueError, TypeError, OSError) as exc:
            failures.append(dict(label, error=str(exc)))
    for (family, symbol), grid in sorted(grids.items(), key=lambda x: str(x[0])):
        if grid != set(TIMEFRAMES):
            failures.append(dict(family=family, symbol=symbol, error='incomplete native timeframe grid',
                                 missing=sorted(set(TIMEFRAMES) - grid)))
    measured = sum(assets.values())
    if declared_factor_bytes is not None and (type(declared_factor_bytes) is not int or declared_factor_bytes != measured):
        failures.append(dict(error='declared factor bytes differ from actual unique bound assets',
                             declared=declared_factor_bytes, measured=measured))
    return dict(status='FAIL_FACTOR_RELEASE_READBACK' if failures else 'PASS_FACTOR_RELEASE_READBACK_ONLY',
                audit_code_sha256=digest(Path(__file__)), bindings=len(store['factors']),
                checked_bindings=len(checked), unique_bound_assets=len(assets), native_factor_bytes=measured,
                measured_scope='Only files directly bound by this factor manifest; upstream/raw/code/registry/answers and other world types are outside this total.',
                checked=checked, failures=failures, world_gate='NOT_PROVEN', full_world_storage_gate='NOT_PROVEN', scoring_gate='CLOSED')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--inventory', type=Path, action='append', required=True)
    parser.add_argument('--declared-factor-bytes', type=int)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    inventories = {}
    for file in args.inventory:
        item = json.loads(file.read_text(encoding='utf-8'))
        if item['tag_name'] in inventories:
            raise ValueError('duplicate release inventory')
        inventories[item['tag_name']] = item
    report = audit(json.loads(args.manifest.read_text(encoding='utf-8')), args.directory,
                   inventories, args.declared_factor_bytes)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(report['status'], report['checked_bindings'], report['native_factor_bytes'])
    raise SystemExit(bool(report['failures']))


if __name__ == '__main__':
    main()

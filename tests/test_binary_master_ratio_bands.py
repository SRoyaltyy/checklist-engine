"""Literal endpoint partitions across every registered mirror-band OAT rung."""
from datetime import date, timedelta
from decimal import Decimal, localcontext
import math
import csv
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
import pytest

import world_binary_master as master
from world_question_grid import CanonicalGrid, ROOT
from ci.binary_master_storage import unpack_csv


SPECS = [(facet, spec) for facet, spec in master._iter_specs() if spec.get('mirror')]


@pytest.fixture(scope='module')
def grid():
    return CanonicalGrid(ROOT)


@pytest.mark.parametrize('facet,spec', SPECS, ids=[s['recipe'] for _, s in SPECS])
def test_all_literal_bounds_and_adjacent_floats_partition(grid, monkeypatch, facet, spec):
    l1, l3 = spec['l1_l3'][0]
    qid = f'B|{l1}|{l3}|{facet}|1x10'
    # Exercise the real binder, transform, comparator and missingness dispatch.
    # Supply controlled raw measurements to reach every exact floating edge;
    # the unmocked integer-volume counterexample is tested separately below.
    monkeypatch.setattr(master, '_tf_window', lambda *a: [None])
    monkeypatch.setattr(master, '_native_indicator_history', lambda *a: [None])
    for variant in grid.variants(qid):
        definitions = master.bind_master_question(grid.tree[qid], variant)
        high_text = dict(variant.settings)[spec['cutoff_id']]
        with localcontext() as ctx:
            ctx.prec = 28
            low_text = str(Decimal(1) / Decimal(high_text))
        lo, hi = float(low_text), float(high_text)
        assert all(float(d['feature']['ratio_band_lower']) == lo and
                   float(d['feature']['ratio_band_upper']) == hi for d in definitions)
        outer = [d for d in definitions if d['comparator'] in ('<', '>')]
        assert {float(d['comparison_threshold']) for d in outer} == {lo, hi}
        for raw in [None, math.nan, 0.0, math.inf, lo, hi, (lo + hi) / 2,
                    *[float(np.nextafter(x, direction)) for x in (lo, hi)
                      for direction in (-math.inf, math.inf)],
                    *np.geomspace(0.01, 100, 43)]:
            measured = raw
            selected = definitions
            if spec['binding'] == 'splitband':
                measured = {'bull_ratio': raw, 'bear_ratio': None}
                selected = [d for d in definitions if d['feature']['ratio_key'] == 'bull_ratio']
            monkeypatch.setattr(master, '_measure', lambda *a: measured)
            answers = [master.evaluate_master(d, {}, date(2024, 1, 2), 100).answer
                       for d in selected]
            unknown = raw is None or math.isnan(raw) or lo > hi
            if unknown:
                assert set(answers) == {'NOT_EVALUABLE'}, (qid, variant, raw, answers)
                if lo > hi:
                    assert master.evaluate_master(selected[0], {}, date(2024, 1, 2), 100).reason == 'INVERTED_LITERAL_RATIO_BAND'
            else:
                assert answers.count('YES') == 1, (qid, variant, raw, answers)
                expected = '<' if raw < lo else '>' if raw > hi else '>='
                assert next(d['comparator'] for d, a in zip(selected, answers)
                            if a == 'YES') == expected
            if spec['binding'] == 'splitband':
                other = [d for d in definitions if d['feature']['ratio_key'] == 'bear_ratio']
                assert all(master.evaluate_master(d, {}, date(2024, 1, 2), 100).answer
                           == 'NOT_EVALUABLE' for d in other)


def test_integer_volume_13_to_10_is_even_at_literal_1p3(grid):
    qid = 'B|volume|up_down_volume|dominance|1x10'
    definitions = master.bind_master_question(grid.tree[qid], next(grid.variants(qid)))
    start = date(2024, 1, 1)
    bars = {}
    for i in range(10):
        up = i % 2 == 0
        end = start + timedelta(days=i)
        bars[i] = master.NativeBar(end, end + timedelta(days=1), 100, 102, 98,
                                   101 if up else 99, 13 if up else 10)
    answers = {d['source_outcome']: master.evaluate_master(
        d, bars, start + timedelta(days=10), 9).answer for d in definitions}
    assert answers == {'up_heavy': 'NO', 'down_heavy': 'NO', 'even': 'YES'}
    # The legacy transformed comparison demonstrably drops this real boundary.
    lo = float(next(d['comparison_threshold'] for d in definitions
                    if d['source_outcome'] == 'down_heavy'))
    assert master._apply_transform(13 / 10, 'mirror_min') < lo


def test_closed_band_margin_retains_both_literal_endpoints():
    feature = {'ratio_band_lower': '0.7692307692307692307692307692',
               'ratio_band_upper': '1.3'}
    for key in feature:
        edge = float(feature[key])
        assert master._apply_transform(edge, 'closed_band_margin', feature) == 0
    assert master._apply_transform(None, 'closed_band_margin', feature) is None


def test_legacy_mirror_transform_remains_available():
    assert master._apply_transform(2.0, 'mirror_min') == 0.5
    assert master._apply_transform(0.0, 'mirror_min') == 0.0
    assert master._apply_transform(math.inf, 'mirror_min') == 0.0


def test_package_revision_is_limited_to_versioned_mirror_definitions(tmp_path):
    """Historical revision proof stays pinned as later ladder work progresses."""
    base = '6dcfced3263533afc13f518258d5eec24451db96'
    def blob(path):
        return subprocess.check_output(['git', 'show', base + ':' + path], cwd=ROOT)
    manifest = json.loads(blob('docs/BINARY_MASTER_V1_STORAGE.json'))
    assert manifest['csv_sha256'] == '6b011355c911f4ec4c13d03da73a76aa6ff4d5d8fa553a394fc19768d467e116'
    prior = tmp_path / 'prior.csv'
    digest = hashlib.sha256()
    with prior.open('wb') as stream:
        for part in manifest['chunks']:
            packed = blob('docs/' + part['path'])
            assert hashlib.sha256(packed).hexdigest() == part['sha256']
            raw = gzip.decompress(packed)
            assert len(raw) == part['raw_bytes']
            digest.update(raw)
            stream.write(raw)
    assert digest.hexdigest() == manifest['csv_sha256']
    revision = '1095a1aca85bd35f26837dfd49b35e1d26c543e3'
    def revised_blob(path):
        return subprocess.check_output(['git', 'show', revision + ':' + path], cwd=ROOT)
    revised_manifest = json.loads(revised_blob('docs/BINARY_MASTER_V1_STORAGE.json'))
    assert revised_manifest['csv_sha256'] == 'ee088c514a52046e556b5ea0e2a58f061ca900d9548a7a10b505be48f8a29b3e'
    revised = tmp_path / 'revised.csv'
    digest = hashlib.sha256()
    with revised.open('wb') as stream:
        for part in revised_manifest['chunks']:
            packed = revised_blob('docs/' + part['path'])
            assert hashlib.sha256(packed).hexdigest() == part['sha256']
            raw = gzip.decompress(packed)
            assert len(raw) == part['raw_bytes']
            digest.update(raw)
            stream.write(raw)
    assert digest.hexdigest() == revised_manifest['csv_sha256']
    recipes = {s['recipe'] for _, s in SPECS}
    def inventory(path):
        unchanged = hashlib.sha256()
        changed = {}
        count = 0
        with path.open(encoding='utf-8', newline='') as stream:
            for row in csv.DictReader(stream):
                if row['feature_recipe'] in recipes:
                    key = row['source_variant_id'], row['source_outcome']
                    assert key not in changed
                    changed[key] = row
                else:
                    unchanged.update((json.dumps(row, sort_keys=True) + '\n').encode())
                    count += 1
        return unchanged.hexdigest(), count, changed
    old_digest, old_count, old_rows = inventory(prior)
    new_digest, new_count, new_rows = inventory(revised)
    assert (new_digest, new_count) == (old_digest, old_count)
    assert old_rows.keys() == new_rows.keys() and len(old_rows) > 100
    report = json.loads(revised_blob('docs/BINARY_MASTER_V1_REPORT.json'))
    assert report['ratio_band_binding']['bound_definitions'] == len(new_rows) == 2994
    assert report['ratio_band_binding']['inverted_interval_definitions'] == 888
    assert report['ratio_band_binding']['registered_cutoffs_edited'] is False
    for key, old in old_rows.items():
        new = new_rows[key]
        assert new['question_id'] != old['question_id']
        old_feature = json.loads(old['feature_json'])
        new_feature = json.loads(new['feature_json'])
        assert new_feature.pop('ratio_band_contract') == 'LITERAL_CLOSED_INTERVAL_V2'
        lo = new_feature.pop('ratio_band_lower')
        hi = new_feature.pop('ratio_band_upper')
        if old_feature['transform'] == 'mirror_min':
            assert new_feature['transform'] == 'closed_band_margin'
            new_feature['transform'] = 'mirror_min'
            assert old['comparison_threshold'] == lo
            assert new['comparator'] == '>=' and new['comparison_threshold'] == '0'
        else:
            assert new['comparator'] == old['comparator']
            assert new['comparison_threshold'] == old['comparison_threshold']
            assert old['comparison_threshold'] == (hi if old['comparator'] == '>' else lo)
        assert new_feature == old_feature

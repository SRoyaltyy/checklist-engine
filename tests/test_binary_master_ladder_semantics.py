"""Reviewed spelling aliases preserve predicates, unknowns and source IDs."""
import csv
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import shutil

import pytest

from ci.ladder_semantic_review import (ALIASES, REVIEW, LADDERS, review_ladders,
                                      SCALAR_ITEMS, SCALAR_PROOF, DICTIONARY, SETTINGS,
                                      reviewed_signature, write_review)
from world_question_grid import ROOT
from ci.binary_master_storage import unpack_csv

BASE = 'cae1923a45ec049ce9e9db97fe5c3e07943c99c3'


def inputs():
    with (Path(ROOT) / LADDERS).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def copy_input(root, rows):
    for name in (DICTIONARY, SETTINGS, SCALAR_PROOF):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(ROOT) / name, target)
    path = root / LADDERS
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def test_four_reviewed_rsi_aliases_and_lossless_source_coverage():
    r = review_ladders(ROOT)
    assert len(r['source']) == len(r['review']) == 2680
    assert r['reviewed_source_rows'] == 80
    assert len(r['retained']) == 2664
    assert {(a['source_question_id'], a['canonical_question_id']) for a in r['aliases']} == {
        (f'I{n:03d}-L05', f'I{n:03d}-L02') for n in range(24, 28)} | {
        (item + '-L09', item + '-L05') for item in SCALAR_ITEMS}
    source_ids = {x['question_id'] for x in r['source']}
    canonical = {x['question_id'] for x in r['retained']}
    aliased = {x['source_question_id'] for x in r['aliases']}
    assert not canonical & aliased and canonical | aliased == source_ids
    assert all(x['canonical_question_id'] in canonical for x in r['review'])
    assert r['raw_text_duplicate_pairs'] == 0  # text identity alone missed these


def test_default_annotation_is_not_a_distinct_rsi_setting():
    rows = {r['question_id']: r for r in inputs()}
    left, right = rows['I026-L02'], rows['I026-L05']
    assert left['feature'] != right['feature']
    assert left['comparator'] == right['comparator'] == '>'
    assert left['threshold'] == right['threshold'] == '70'
    assert reviewed_signature(left) == reviewed_signature(right)
    with (Path(ROOT) / 'dictionary/WORLD_SNAPSHOT_DICTIONARY.csv').open(encoding='utf-8-sig', newline='') as stream:
        item = next(r for r in csv.DictReader(stream) if r['id'] == 'I026')
    assert item['item'] == 'RSI(14)' and 'n=14;' in item['parameters']


@pytest.mark.parametrize('change', [
    {'comparator': '>='}, {'threshold': '30'},
    {'feature': 'RSI(14) [default] on last completed 5d candle'},
    {'feature': 'RSI(14) [default] value[D-1] - value[D-6] (5-bar change)'},
    {'not_evaluable_condition': 'different zero-state policy'},
    {'knowable_at_setup_open': 'different availability rule'},
    {'item_id': 'I027', 'item_name': 'RSI(24)'},
    {'threshold': '70th percentile'}, {'threshold': 'Infinity'}, {'comparator': 'truthy'},
])
def test_distinct_or_unresolved_meanings_never_fold(change):
    original = next(r for r in inputs() if r['question_id'] == 'I026-L02')
    altered = dict(original, **change)
    assert reviewed_signature(altered) != reviewed_signature(original)


def test_unreviewed_same_name_or_text_stays_separate(tmp_path):
    row = next(r for r in inputs() if r['item_id'] == 'I117')
    copy_input(tmp_path, [row, dict(row, question_id='another-unreviewed-id')])
    r = review_ladders(tmp_path)
    assert len(r['retained']) == 2 and not r['aliases']
    assert all(x['decision'] == 'KEEP_UNREVIEWED' for x in r['review'])


def test_canonical_id_survives_source_reordering(tmp_path):
    expected = review_ladders(ROOT)
    copy_input(tmp_path, list(reversed(inputs())))
    actual = review_ladders(tmp_path)
    assert {x['source_question_id']: x['canonical_question_id'] for x in actual['review']} == {
        x['source_question_id']: x['canonical_question_id'] for x in expected['review']}


def test_alias_and_review_files_are_deterministic_and_do_not_edit_source(tmp_path):
    copy_input(tmp_path, inputs())
    source = (tmp_path / LADDERS).read_bytes()
    r = review_ladders(tmp_path)
    write_review(tmp_path, r)
    paths = [tmp_path / 'docs' / name for name in (ALIASES, REVIEW)]
    before = [p.read_bytes() for p in paths]
    write_review(tmp_path, review_ladders(tmp_path))
    assert before == [p.read_bytes() for p in paths]
    assert (tmp_path / LADDERS).read_bytes() == source
    with paths[1].open(encoding='utf-8', newline='') as stream:
        assert {x['source_question_id'] for x in csv.DictReader(stream)} == {
            x['question_id'] for x in r['source']}


def test_duplicate_source_ids_fail_before_aliasing(tmp_path):
    row = inputs()[0]
    copy_input(tmp_path, [row, row])
    with pytest.raises(ValueError, match='duplicate ladder source question ID'):
        review_ladders(tmp_path)


def test_committed_ladder_export_changes_only_four_verified_alias_rows(tmp_path):
    """Authenticate the old package, then compare every retained ladder row.

    BOUND definitions have independent versioned formula revisions; this proof
    is specific to the unchanged ladder source and its four reviewed aliases.
    """
    def blob(path):
        return subprocess.check_output(['git', 'show', BASE + ':' + path], cwd=ROOT)

    manifest = json.loads(blob('docs/BINARY_MASTER_V1_STORAGE.json'))
    assert manifest['csv_sha256'] == '918494ae8f46deb33e83de9930bde8c66f804a0081b7aae68e654d6c3eae1c26'
    prior = tmp_path / 'prior.csv'
    digest = hashlib.sha256()
    with prior.open('wb') as stream:
        for entry in manifest['chunks']:
            packed = blob('docs/' + entry['path'])
            assert hashlib.sha256(packed).hexdigest() == entry['sha256']
            raw = gzip.decompress(packed)
            assert len(raw) == entry['raw_bytes']
            digest.update(raw)
            stream.write(raw)
    assert digest.hexdigest() == manifest['csv_sha256']
    current = unpack_csv(Path(ROOT) / 'docs')
    reviewed = review_ladders(ROOT)
    aliases = {r['source_question_id'] for r in reviewed['aliases']}
    checked = removed = 0
    with prior.open(encoding='utf-8', newline='') as old, current.open(encoding='utf-8', newline='') as new:
        previous, actual = csv.DictReader(old), csv.DictReader(new)
        assert previous.fieldnames == actual.fieldnames
        actual_ladders = iter(r for r in actual if r['definition_status'] == 'LADDER_ADDON')
        for row in previous:
            if row['definition_status'] != 'LADDER_ADDON':
                continue
            if row['question_id'] in aliases:
                assert row['definition_status'] == 'LADDER_ADDON'
                removed += 1
                continue
            assert next(actual_ladders) == row
            checked += 1
        assert next(actual_ladders, None) is None
    assert (checked, removed) == (2664, 16)


@pytest.mark.parametrize('item', sorted(SCALAR_ITEMS))
def test_selected_default_scalar_aliases_preserve_literal_predicates(item):
    rows = {r['question_id']: r for r in inputs()}
    left, right = rows[item + '-L05'], rows[item + '-L09']
    assert left['feature'] != right['feature']
    assert reviewed_signature(left) == reviewed_signature(right)
    for change in ({'comparator': '>='}, {'threshold': '999'},
                   {'feature': right['feature'].replace('[default]', '[short]')},
                   {'feature': right['feature'].replace('1d candle', '5d candle')},
                   {'not_evaluable_condition': 'different missingness'},
                   {'knowable_at_setup_open': 'different PIT'}):
        assert reviewed_signature(dict(right, **change)) != reviewed_signature(left)


@pytest.mark.parametrize('item', ['I034', 'I041', 'I052'])
def test_unselected_multi_output_candidates_remain_unreviewed(item):
    rows = [r for r in inputs() if r['item_id'] == item]
    assert all(reviewed_signature(r) is None for r in rows)


def test_review_fails_if_selected_scalar_dictionary_changes(tmp_path):
    row = next(r for r in inputs() if r['item_id'] == 'I028')
    copy_input(tmp_path, [row])
    p = tmp_path / DICTIONARY
    text = p.read_text(encoding='utf-8-sig')
    assert 'value used = slowK' in text
    p.write_text(text.replace('value used = slowK', 'value used = slowD'), encoding='utf-8')
    with pytest.raises(ValueError, match='dictionary/default changed: I028'):
        review_ladders(tmp_path)


def test_review_fails_if_dictionary_default_settings_change(tmp_path):
    row = next(r for r in inputs() if r['item_id'] == 'I029')
    copy_input(tmp_path, [row])
    p = tmp_path / SETTINGS
    data = json.loads(p.read_bytes())
    default = next(s for s in data['items']['I029']['settings'] if s['name'] == 'default')
    default['parameters']['period'] = 28
    p.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError, match='dictionary/default changed: I029'):
        review_ladders(tmp_path)


def test_review_fails_if_build_root_proof_changes(tmp_path):
    row = next(r for r in inputs() if r['item_id'] == 'I029')
    copy_input(tmp_path, [row])
    p = tmp_path / SCALAR_PROOF
    data = json.loads(p.read_bytes())
    data['items'][0]['selected_scalar'] = 'slowD'
    p.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError, match='build-root scalar review differs'):
        review_ladders(tmp_path)


def test_scalar_alias_revision_preserves_all_other_rows(tmp_path):
    base = '1095a1aca85bd35f26837dfd49b35e1d26c543e3'
    def blob(path):
        return subprocess.check_output(['git', 'show', base + ':' + path], cwd=ROOT)
    manifest = json.loads(blob('docs/BINARY_MASTER_V1_STORAGE.json'))
    assert manifest['csv_sha256'] == 'ee088c514a52046e556b5ea0e2a58f061ca900d9548a7a10b505be48f8a29b3e'
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
    current = unpack_csv(Path(ROOT) / 'docs')
    removed_ids = {item + '-L09' for item in SCALAR_ITEMS}
    checked = removed = bound = 0
    with prior.open(encoding='utf-8', newline='') as old, current.open(encoding='utf-8', newline='') as new:
        previous, actual = csv.DictReader(old), csv.DictReader(new)
        assert previous.fieldnames == actual.fieldnames
        for row in previous:
            if row['question_id'] in removed_ids:
                assert row['definition_status'] == 'LADDER_ADDON'
                removed += 1
                continue
            assert next(actual) == row
            checked += 1
            bound += row['definition_status'] == 'BOUND'
        assert next(actual, None) is None
    assert (checked, removed, bound) == (65540, 12, 62876)

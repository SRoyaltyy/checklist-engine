#!/usr/bin/env python3
"""Source-matched tests for docs/venice-audit-v1 generated matrices.

Asserts only properties the builder derives from the four authority files.
No network access, and no inference about coverage or completion status.
"""
import csv
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'docs' / 'venice-audit-v1'
DATA = AUDIT / 'DATA_REQUIREMENTS.csv'
MANIFEST = AUDIT / 'SOURCE_MANIFEST.json'
REQS = AUDIT / 'REQUIREMENTS.csv'
GANTT = AUDIT / 'GANTT_COMPARISON.csv'
EVIDENCE = AUDIT / 'EVIDENCE.json'

COLS = [
    'inventory_id', 'item', 'required_or_excluded', 'authority_ref',
    'source_urls', 'source_link_verification', 'required_fields',
    'required_universe', 'required_period', 'timeframes',
    'availability_or_publication_rule', 'identity_join_requirements',
    'existing_assets', 'coverage_evidence', 'measured_scope', 'missing_scope',
    'next_acquisition_or_build_step', 'owner_lane', 'status',
]

REQ_COLS = [
    'requirement_id', 'authority_path', 'authority_anchor_or_lines',
    'requirement', 'gantt_group', 'owner_lane', 'dependencies',
    'acceptance_condition', 'current_status', 'evidence_refs',
    'remaining_action',
]

GANTT_COLS = [
    'baseline_row_id', 'baseline_group', 'baseline_label',
    'baseline_v16_claim', 'baseline_v20_claim', 'requirement_ids',
    'current_verified_status', 'scope_difference', 'evidence_refs',
    'missing_work', 'dependency_ids', 'percent_basis', 'split_from',
]

EVIDENCE_FIELDS = {
    'id', 'claim', 'artifact_path', 'artifact_blob_sha', 'kind',
    'check_performed', 'result', 'coverage_scope', 'limits', 'evidence_urls',
}

SNAPSHOT_FIELDS = ('branch', 'main_head_observed', 'spec_audit_base', 'delta_note')

SHA_RE = re.compile(r'^[0-9a-f]{40}$')


def load_rows():
    with DATA.open(newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        return reader.fieldnames, list(reader)


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding='utf-8'))


def load_csv(path):
    with path.open(newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        return reader.fieldnames, list(reader)


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding='utf-8'))


def test_header_is_exact():
    fields, _ = load_rows()
    assert fields == COLS, fields


def test_row_count_matches_manifest():
    _, rows = load_rows()
    manifest = load_manifest()
    assert manifest['row_count'] == len(rows)
    assert 250 <= len(rows) <= 260, len(rows)


def test_inventory_ids_are_unique_and_non_empty():
    _, rows = load_rows()
    ids = [r['inventory_id'].strip() for r in rows]
    assert all(ids)
    assert len(set(ids)) == len(ids)


def test_every_row_carries_an_authority_ref_and_item():
    _, rows = load_rows()
    for row in rows:
        ref = row['authority_ref'].strip()
        assert '@' in ref and ':' in ref, row['inventory_id']
        assert row['item'].strip(), row['inventory_id']


def test_declared_controls_are_excluded_and_nothing_else_is():
    _, rows = load_rows()
    excluded = {r['inventory_id'] for r in rows if r['required_or_excluded'] == 'excluded_control'}
    assert {'C28', 'C29'} <= excluded, excluded
    assert not any(i.startswith('I') for i in excluded), excluded
    assert {r['required_or_excluded'] for r in rows} <= {'required', 'excluded_control'}


def test_manifest_records_four_authority_blob_shas():
    manifest = load_manifest()
    shas = manifest['authority_blob_shas']
    assert len(shas) == 4, shas
    for path, sha in shas.items():
        assert SHA_RE.match(sha or ''), (path, sha)
    assert (ROOT / manifest['generated_by']).is_file(), manifest['generated_by']


def test_requirements_header_is_exact():
    fields, _ = load_csv(REQS)
    assert fields == REQ_COLS, fields


def test_requirements_rows_are_unique_and_carry_acceptance():
    _, rows = load_csv(REQS)
    assert len(rows) >= 40, len(rows)
    ids = [r['requirement_id'].strip() for r in rows]
    assert all(ids)
    assert len(set(ids)) == len(ids), sorted(i for i in ids if ids.count(i) > 1)
    for row in rows:
        assert row['requirement'].strip(), row['requirement_id']
        assert row['acceptance_condition'].strip(), row['requirement_id']
        assert row['gantt_group'].strip(), row['requirement_id']


def test_requirements_authority_is_pinned_to_a_blob_or_a_real_file():
    _, rows = load_csv(REQS)
    for row in rows:
        path = row['authority_path'].strip()
        assert path, row['requirement_id']
        if '@' in path:
            _, _, sha = path.rpartition('@')
            assert SHA_RE.match(sha), (row['requirement_id'], sha)
        else:
            assert (ROOT / path).exists(), (row['requirement_id'], path)


def test_gantt_comparison_header_is_exact():
    fields, _ = load_csv(GANTT)
    assert fields == GANTT_COLS, fields


def test_gantt_comparison_has_one_row_per_baseline_id():
    _, rows = load_csv(GANTT)
    assert len(rows) >= 60, len(rows)
    ids = [r['baseline_row_id'].strip() for r in rows]
    assert all(ids)
    assert len(set(ids)) == len(ids), sorted(i for i in ids if ids.count(i) > 1)
    assert {'B0', 'B1', 'D2'} <= set(ids), sorted(set(ids))


def test_gantt_comparison_split_rows_name_a_present_parent():
    _, rows = load_csv(GANTT)
    splits = [r for r in rows if r['split_from'].strip()]
    assert splits, 'expected at least one split row'
    ids = {r['baseline_row_id'].strip() for r in rows}
    for row in splits:
        assert row['split_from'].strip() in ids, row['split_from']


def test_evidence_ledger_separates_snapshot_from_entries():
    doc = load_evidence()
    assert doc['generated_by'], doc
    snapshot = doc['snapshot']
    for key in SNAPSHOT_FIELDS:
        assert snapshot.get(key), key
    assert SHA_RE.match(snapshot['main_head_observed']), snapshot['main_head_observed']


def test_evidence_entries_are_unique_and_state_their_limits():
    doc = load_evidence()
    entries = doc['entries']
    assert len(entries) >= 4, len(entries)
    ids = [e['id'] for e in entries]
    assert all(ids)
    assert len(set(ids)) == len(ids), ids
    for entry in entries:
        missing = EVIDENCE_FIELDS - set(entry)
        assert not missing, (entry.get('id'), sorted(missing))
        assert entry['limits'].strip(), entry['id']
        assert entry['coverage_scope'].strip(), entry['id']
        assert entry['kind'].strip(), entry['id']


def test_gantt_html_is_generated_without_a_fabricated_percentage():
    page = AUDIT / 'GANTT.html'
    if not page.is_file():
        pytest.skip('GANTT.html is written by build_gantt during the build step')
    text = page.read_text(encoding='utf-8').lower()
    assert '<html' in text or '<table' in text, 'GANTT.html is not an html document'
    assert '% complete' not in text, 'GANTT.html states a completion percentage'

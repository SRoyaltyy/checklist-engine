#!/usr/bin/env python3
"""Source-matched tests for docs/venice-audit-v1 generated matrices.

Asserts only properties the builder derives from the four authority files.
No network access, and no inference about coverage or completion status.
"""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'docs' / 'venice-audit-v1'
DATA = AUDIT / 'DATA_REQUIREMENTS.csv'
MANIFEST = AUDIT / 'SOURCE_MANIFEST.json'

COLS = [
    'inventory_id', 'item', 'required_or_excluded', 'authority_ref',
    'source_urls', 'source_link_verification', 'required_fields',
    'required_universe', 'required_period', 'timeframes',
    'availability_or_publication_rule', 'identity_join_requirements',
    'existing_assets', 'coverage_evidence', 'measured_scope', 'missing_scope',
    'next_acquisition_or_build_step', 'owner_lane', 'status',
]
SHA_RE = re.compile(r'^[0-9a-f]{40}$')


def load_rows():
    with DATA.open(newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        return reader.fieldnames, list(reader)


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding='utf-8'))


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

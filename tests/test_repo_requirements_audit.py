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
    'requirement_id', 'parent_substage_id', 'subject_id',
    'scope_definition_status', 'data_acquisition_status',
    'strict_data_definition_status', 'implementation_status',
    'question_design_status', 'answer_generation_status',
    'verification_status', 'main_acceptance_status', 'status_explanation',
    'authority_path', 'authority_anchor_or_lines', 'requirement',
    'gantt_group', 'owner_lane', 'dependencies', 'acceptance_condition',
    'scope', 'evidence_refs', 'missing_work', 'remaining_action',
]

STATUS_FIELDS = [
    'scope_definition_status', 'data_acquisition_status',
    'strict_data_definition_status', 'implementation_status',
    'question_design_status', 'answer_generation_status',
    'verification_status', 'main_acceptance_status',
]

STATUS_VALUES = {
    'NOT_STARTED', 'IN_PROGRESS', 'PARTIAL', 'COMPLETE', 'BLOCKED',
    'UNVERIFIED', 'NOT_APPLICABLE',
}

STAGES = AUDIT / 'STAGES.csv'

STAGES_COLS = [
    'node_id', 'parent_id', 'node_type', 'title', 'status',
    'substage_percent', 'percent_numerator', 'percent_denominator',
    'percent_basis', 'blockers', 'next_action', 'evidence_refs',
    'details_path',
]


def test_stages_header_is_exact():
    fields, _ = load_csv(STAGES)
    assert fields == STAGES_COLS, fields


def test_stage_rows_carry_no_percentage():
    _, rows = load_csv(STAGES)
    stages = [r for r in rows if r['node_type'] == 'stage']
    assert stages, 'expected stage rows'
    for row in stages:
        for key in ('substage_percent', 'percent_numerator', 'percent_denominator'):
            assert not row[key].strip(), (row['node_id'], key, row[key])


def test_substage_rows_carry_only_their_own_percentage():
    _, rows = load_csv(STAGES)
    subs = [r for r in rows if r['node_type'] == 'substage']
    assert subs, 'expected substage rows'
    ids = {r['node_id'] for r in rows}
    for row in subs:
        assert row['parent_id'] in ids, (row['node_id'], row['parent_id'])
        num, den = row['percent_numerator'].strip(), row['percent_denominator'].strip()
        assert num.isdigit() and den.isdigit(), (row['node_id'], num, den)
        assert int(num) <= int(den), (row['node_id'], num, den)
        assert row['percent_basis'].strip(), row['node_id']


def test_requirements_status_fields_use_the_documented_vocabulary():
    _, rows = load_csv(REQS)
    for row in rows:
        assert row['parent_substage_id'].strip(), row['requirement_id']
        for key in STATUS_FIELDS:
            assert row[key].strip() in STATUS_VALUES, (row['requirement_id'], key, row[key])
        assert row['status_explanation'].strip(), row['requirement_id']

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


def test_audit_workflow_is_branch_scoped_and_diff_guarded():
    wf = ROOT / '.github' / 'workflows' / 'venice-repo-requirements-audit.yml'
    assert wf.is_file(), 'audit workflow file is missing'
    text = wf.read_text(encoding='utf-8')
    assert 'venice/repo-hierarchical-audit-v2' in text, 'workflow is not scoped to the audit branch'
    assert 'git diff --cached --quiet' in text, 'workflow commit step is not diff-guarded'
    assert 'git rm -r --cached' in text, 'workflow does not untrack the committed __pycache__'
    assert 'git commit' in text, 'workflow never commits the regenerated outputs'
    assert 'git push' in text, 'workflow never publishes the regenerated outputs'


QIDX = AUDIT / 'QUESTION_INDEX.csv'
QMAN = AUDIT / 'questions' / 'INDEX.json'

QUESTION_COLS = [
    'question_id', 'phase', 'parent_substage_id', 'subject_id', 'inventory_id', 'item',
    'lens', 'timeframe_domain', 'parameter_domain', 'literal_predicate', 'template',
    'source_artifact', 'source_anchor', 'design_status', 'implementation_status',
    'answer_status', 'verification_status', 'evidence_refs', 'missing_work',
    'next_action', 'unresolved_reason',
]

QUESTION_PARENTS = {'S4.1', 'S5.1', 'S5B.1'}
QUESTION_STATES = {'NOT_STARTED', 'PARTIAL', 'COMPLETE', 'UNVERIFIED', 'NOT_APPLICABLE'}
CONTROL_SUFFIX = '-CONTROL'


def load_question_index():
    if not QIDX.is_file():
        pytest.skip('QUESTION_INDEX.csv is written by build_questions during the build step')
    with QIDX.open(newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        return reader.fieldnames, list(reader)


def load_question_manifest():
    if not QMAN.is_file():
        pytest.skip('questions/INDEX.json is written by build_questions during the build step')
    return json.loads(QMAN.read_text(encoding='utf-8'))


def test_question_index_header_is_exact():
    fields, _ = load_question_index()
    assert fields == QUESTION_COLS, fields


def test_question_ids_are_unique_and_namespaced_to_their_inventory_id():
    _, rows = load_question_index()
    assert len(rows) >= 1000, len(rows)
    ids = [r['question_id'].strip() for r in rows]
    assert all(ids), 'empty question_id'
    assert len(set(ids)) == len(ids), sorted(i for i in ids if ids.count(i) > 1)[:5]
    for row in rows:
        assert row['inventory_id'].strip(), row['question_id']
        assert row['question_id'].startswith('Q-' + re.sub(r'[^A-Z0-9]+', '-', row['inventory_id'].upper()).strip('-') + '-'), row['question_id']


def test_every_question_row_hangs_off_a_question_substage():
    _, rows = load_question_index()
    parents = {r['parent_substage_id'].strip() for r in rows}
    assert parents <= QUESTION_PARENTS, sorted(parents - QUESTION_PARENTS)
    for row in rows:
        assert row['phase'].strip(), row['question_id']
        assert row['subject_id'].strip(), row['question_id']


def test_answerable_questions_carry_a_literal_predicate_and_template():
    _, rows = load_question_index()
    answerable = [r for r in rows if not r['question_id'].endswith(CONTROL_SUFFIX)]
    assert answerable, 'expected answerable question rows'
    for row in answerable:
        pred = row['literal_predicate'].strip()
        tmpl = row['template'].strip()
        assert pred, row['question_id']
        assert tmpl, row['question_id']
        assert '{q}' not in pred, row['question_id']
        assert '{q}' in tmpl, row['question_id']
        assert row['parameter_domain'].strip(), row['question_id']
        assert row['timeframe_domain'].strip(), row['question_id']
        assert row['source_artifact'].strip(), row['question_id']
        assert row['source_anchor'].strip(), row['question_id']
        assert row['next_action'].strip(), row['question_id']


def test_control_rows_are_the_only_template_less_rows():
    _, rows = load_question_index()
    controls = [r for r in rows if r['question_id'].endswith(CONTROL_SUFFIX)]
    assert controls, 'expected excluded-control rows'
    for row in controls:
        assert not row['template'].strip(), row['question_id']
        assert row['literal_predicate'].strip().startswith('Excluded control'), row['question_id']
        assert row['unresolved_reason'].strip(), row['question_id']
        assert row['phase'].strip() == 'design', row['question_id']


def test_question_states_use_the_documented_vocabulary():
    _, rows = load_question_index()
    for row in rows:
        for key in ('design_status', 'implementation_status', 'answer_status', 'verification_status'):
            assert row[key].strip() in QUESTION_STATES, (row['question_id'], key, row[key])


def test_question_manifest_reconciles_counts_and_authority_shas():
    _, rows = load_question_index()
    doc = load_question_manifest()
    assert doc['generated_by'] == 'docs/venice-audit-v1/build_questions.py', doc['generated_by']
    assert doc['columns'] == QUESTION_COLS, doc['columns']
    counts = doc['counts']
    assert counts['rows'] == len(rows), (counts['rows'], len(rows))
    assert counts['ids'] == len({r['inventory_id'] for r in rows}), (counts['ids'], len(rows))
    controls = sum(1 for r in rows if r['question_id'].endswith(CONTROL_SUFFIX))
    assert counts['excluded_controls'] == controls, (counts['excluded_controls'], controls)
    assert counts['questions'] == len({r['question_id'] for r in rows}) - controls, counts['questions']
    shas = doc['authority_blob_shas']
    assert len(shas) == 2, shas
    for path, sha in shas.items():
        assert SHA_RE.match(sha or ''), (path, sha)
        assert (ROOT / path).is_file(), path
    assert doc['omissions'], 'expected the omission ledger to be published, not hidden'


def test_question_manifest_phase_map_matches_every_row():
    _, rows = load_question_index()
    doc = load_question_manifest()
    phases = doc['phase_substages']
    for row in rows:
        phase = row['phase'].strip()
        assert phase in phases, (row['question_id'], phase)
        assert phases[phase] == row['parent_substage_id'].strip(), (row['question_id'], phase)


"""Invariant tests for the lens coverage rule set (ci/lenses_coverage.py)."""
from ci.lenses_coverage import (BLOCK_DEFAULT, CLASS_RULES, LENSES, REASONS,
                                classify, potential_count)
import ci.lenses_coverage as coverage
import csv
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


def _inventory():
    root = Path(__file__).resolve().parent.parent
    with (root / 'dictionary' / 'DATA_SOURCES.csv').open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def test_inventory_shape():
    rows = _inventory()
    assert len(rows) == 258
    assert sum(1 for r in rows if r['id'].startswith('I')) == 228
    assert sum(1 for r in rows if r['id'].startswith('C')) == 30


def test_known_key_classifications():
    rows = {r['id']: r for r in _inventory()}
    expect = {'C28': 'NO_QUESTIONS', 'C29': 'NO_QUESTIONS',
              'I200': 'NO_QUESTIONS_DROPPED', 'I201': 'MARKET_GLOBAL',
              'I178': 'MARKET_GLOBAL', 'I195': 'MARKET_GLOBAL',
              'I179': 'MARKET_GLOBAL', 'I180': 'MARKET_GLOBAL',
              'I189': 'STOCK_SCALAR', 'I188': 'SPARSE_NUMERIC',
              'I176': 'STOCK_SCALAR', 'I111': 'CATEGORICAL_STATE',
              'I184': 'EVENT_FACT', 'I121': 'EVENT_COUNT',
              'I198': 'MIXED_SNAPSHOT', 'C30': 'MIXED_SNAPSHOT',
              'I202': 'STOCK_SCALAR', 'I001': 'STOCK_SCALAR'}
    for iid, cls in expect.items():
        got, _ = classify(rows[iid])
        assert got == cls, (iid, got, cls)


def test_every_item_has_disjoint_applicability_states():
    for row in _inventory():
        cls, rule = classify(row)
        assert cls in CLASS_RULES
        eligible, conditional, excluded = rule['applicable'], set(rule['conditional']), set(rule['inapplicable'])
        assert eligible | conditional | excluded == set(LENSES)
        assert not (eligible & conditional or eligible & excluded or conditional & excluded)
        for why in list(rule['inapplicable'].values()) + list(rule['conditional'].values()):
            assert why in REASONS


def test_alias_counted_once_where_present():
    for cls, rule in CLASS_RULES.items():
        if rule.get('alias'):
            a, b = rule['alias']
            assert a in rule['applicable'] and b in rule['applicable']
            assert potential_count(rule) == len(rule['applicable'] | set(rule['conditional'])) - 1


def test_block_defaults_cover_all_blocks():
    rows = _inventory()
    blocks = {r['block'] for r in rows}
    assert blocks <= set(BLOCK_DEFAULT)


def test_missing_references_are_conditional_not_semantically_excluded():
    for rule in CLASS_RULES.values():
        assert not ({'REL_NAMED', 'DIV_PAIR'} & set(rule['inapplicable'].values()))
    for cls in ('EVENT_FACT', 'BOOLEAN_STATE', 'CATEGORICAL_STATE'):
        assert CLASS_RULES[cls]['conditional']['relative'] == 'REL_NAMED'
        assert CLASS_RULES[cls]['conditional']['divergence'] == 'DIV_PAIR'
    assert CLASS_RULES['MARKET_GLOBAL']['inapplicable']['rank'] == 'RANK_GLOBAL'


def test_generated_plan_does_not_certify_implementation_and_is_idempotent():
    workspace = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(dir=workspace) as folder:
        assert Path(folder).resolve().parent == workspace
        md, table = Path(folder) / 'lenses.md', Path(folder) / 'coverage.csv'
        md.write_text('# Preserved prologue\n', encoding='utf-8')
        with patch.object(coverage, 'LENSES_MD', md), patch.object(coverage, 'COVERAGE_CSV', table):
            rows, _ = coverage.build()
            first = (md.read_bytes(), table.read_bytes())
            coverage.build()
            assert first == (md.read_bytes(), table.read_bytes())
        assert len(rows) == 258 and len({r['id'] for r in rows}) == 258
        assert all(r['coverage_scope'] == 'CLASS_APPLICABILITY_ONLY' for r in rows)
        for r in rows:
            if r['id'] in ('C28', 'C29', 'I200'):
                assert r['minimum_6_status'] == r['implementation_status'] == 'NOT_APPLICABLE'
                assert r['implemented_lens_count'] == '0'
            else:
                assert r['implemented_lens_count'] == ''
                assert r['implementation_status'] == 'UNMEASURED'
                assert r['minimum_6_status'] == 'NOT_PROVEN'
        assert md.read_text(encoding='utf-8').startswith('# Preserved prologue\n')
        assert 'not measured' in md.read_text(encoding='utf-8')


def load_tests(loader, suite, pattern):
    """Run the same dependency-free checks under unittest or pytest."""
    for name, test in sorted(globals().items()):
        if name.startswith('test_') and callable(test):
            suite.addTest(unittest.FunctionTestCase(test))
    return suite

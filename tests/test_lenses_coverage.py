"""Invariant tests for the lens coverage rule set (ci/lenses_coverage.py)."""
from ci.lenses_coverage import (BLOCK_DEFAULT, CLASS_RULES, LENSES, REASONS,
                                classify, unique_count)
import csv
from pathlib import Path


def _inventory():
    root = Path(__file__).resolve().parent.parent
    return list(csv.DictReader((root / 'dictionary' / 'DATA_SOURCES.csv')
                               .open(encoding='utf-8-sig', newline='')))


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


def test_every_item_classified_with_min_six_lenses():
    for row in _inventory():
        cls, rule = classify(row)
        assert cls in CLASS_RULES
        assert rule['applicable'] | set(rule['inapplicable']) == set(LENSES)
        assert not (rule['applicable'] & set(rule['inapplicable']))
        for why in rule['inapplicable'].values():
            assert why in REASONS
        if not cls.startswith('NO_QUESTIONS'):
            assert unique_count(rule) >= 6, (row['id'], cls)


def test_alias_counted_once_where_present():
    for cls, rule in CLASS_RULES.items():
        if rule.get('alias'):
            a, b = rule['alias']
            assert a in rule['applicable'] and b in rule['applicable']
            assert unique_count(rule) == len(rule['applicable']) - 1


def test_block_defaults_cover_all_blocks():
    rows = _inventory()
    blocks = {r['block'] for r in rows}
    assert blocks <= set(BLOCK_DEFAULT)

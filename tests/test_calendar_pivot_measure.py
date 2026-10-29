import json
from pathlib import Path

import pytest
import pandas as pd

from ci import calendar_pivot_measure as proof
from market_storage import assert_exact_frame
from world_calendar_pivots import ANCHORS, LEVELS


def request(): return json.loads(Path('ci/CALENDAR_PIVOT_REQUEST.json').read_text(encoding='utf-8'))


def test_bound_original_sample_and_every_existing_registered_anchor_are_preserved():
    current = request(); previous = json.loads(Path('ci/RELATIVE_NATIVE_REQUEST.json').read_text(encoding='utf-8'))
    for key in ('parent_proof', 'stocks', 'benchmark', 'calendar', 'cutoffs'): assert current[key] == previous[key]
    assert current['columns'] == ['I074_'+s+'_'+level for s in ANCHORS for level in LEVELS]
    registry = json.loads(Path('dictionary/INDICATOR_SETTINGS.json').read_text(encoding='utf-8'))
    assert current['settings'] == registry['items']['I074']['settings']


def test_changed_anchor_rejected_before_source_read(tmp_path, monkeypatch):
    current = request(); current['settings'][0]['parameters']['anchor'] = 'day'
    monkeypatch.setattr(proof, 'checked_source', lambda b: pytest.fail('read before anchor validation'))
    with pytest.raises(ValueError, match='every exact registered anchor'): proof.measure(tmp_path, current)


def test_changed_original_raw_input_is_rejected(tmp_path, monkeypatch):
    current = request()
    parent = dict(status='EXACT_RECOMPUTATION_SAMPLE_ONLY', errors=[],
                  samples=[dict(ticker=b['ticker'], raw_source_sha256=b['sha256']) for b in current['stocks']],
                  etf=dict(raw_source_sha256=current['benchmark']['sha256']))
    current['stocks'][0]['sha256'] = 'f'*64
    monkeypatch.setattr(proof, 'checked_source', lambda b: json.dumps(parent).encode())
    with pytest.raises(ValueError, match='immutable sample input changed'): proof.measure(tmp_path, current)


def test_independent_scalar_oracle_checks_every_level_and_missing_anchor():
    from test_calendar_pivots import fixture
    cal, bars = fixture(); cut = pd.Timestamp('2020-02-03')
    bars = bars.loc[bars.date != '2020-01-13']
    actual = proof.native_calendar_pivots(bars, cal, '5d', cut)
    expected = proof.independent_frame(actual, proof.independent_anchors(bars, cal, cut))
    assert_exact_frame(actual, expected)
    changed = actual.copy(); changed.iloc[-1, 3] += 1
    with pytest.raises(AssertionError): assert_exact_frame(changed, expected)

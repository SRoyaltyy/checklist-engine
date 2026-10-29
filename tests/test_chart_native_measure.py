import copy
from dataclasses import asdict
import json
from pathlib import Path

import pytest

from ci import chart_native_measure as proof
from world_chart_picture import DEFAULT,PIN


def request():return json.loads(Path('ci/CHART_NATIVE_REQUEST.json').read_text(encoding='utf-8'))


def test_precommitted_chart_defaults_preserve_the_original_inputs_and_exact_pin():
    current=request();previous=json.loads(Path('ci/RELATIVE_NATIVE_REQUEST.json').read_text(encoding='utf-8'))
    for key in ('parent_proof','stocks','benchmark','calendar','cutoffs'):assert current[key]==previous[key]
    assert current['pin']==PIN and current['settings']==asdict(DEFAULT)
    assert current['expected_numeric_columns']==39 and len(current['required_default_tags'])==9


def test_unbound_chart_defaults_fail_before_any_source_read(tmp_path,monkeypatch):
    current=request();current['settings']['body_threshold']=.1
    monkeypatch.setattr(proof,'checked_source',lambda binding:pytest.fail('source read before default binding'))
    with pytest.raises(ValueError,match='exact named defaults'):proof.measure(tmp_path,current)


def test_changed_sample_bytes_are_rejected_before_native_computation(tmp_path,monkeypatch):
    current=request();parent=dict(status='EXACT_RECOMPUTATION_SAMPLE_ONLY',errors=[],
        samples=[dict(ticker=b['ticker'],raw_source_sha256=b['sha256']) for b in current['stocks']],
        etf=dict(raw_source_sha256=current['benchmark']['sha256']))
    current['stocks'][0]['sha256']='f'*64
    monkeypatch.setattr(proof,'checked_source',lambda binding:json.dumps(parent).encode())
    with pytest.raises(ValueError,match='sample input changed'):proof.measure(tmp_path,current)

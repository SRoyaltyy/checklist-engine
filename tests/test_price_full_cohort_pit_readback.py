import copy
import json

import pytest

from ci.price_full_cohort_pit_readback import (CUTS, FIELDS, NAMES, PLAN_SHA, QUERIES, TIMEFRAMES,
                                             COVERAGE, EVIDENCE, REPORT, read_bundle, validate)


@pytest.fixture(scope='module')
def synthetic_complete_metadata():
    """Synthetic metadata at the required dimensions, never market evidence."""
    names = [f'SYNTHETIC{i:04d}' for i in range(NAMES)]
    fields = [f'FIELD{i:04d}' for i in range(FIELDS)]
    per_stock, extra = divmod(QUERIES, NAMES)
    refs = [dict(ticker=t, query_rows=per_stock + (i < extra)) for i, t in enumerate(names)]
    parts = [dict(tickers=names[i:i + 50]) for i in range(2, NAMES, 50)]
    plan = dict(expected_names=names, references=refs, expected_query_rows=QUERIES,
        timeframes=TIMEFRAMES, price_fields=fields, prefix_cuts=CUTS, quarantine_names=['OUTSIDE'],
        smoke_parts=[dict(tickers=names[:2])], work_parts=parts, source_commit='commit', composition={},
        frozen_build_request={'corrected_recipe_fingerprint': 'recipe'})
    prefix = 'price-full-cohort-pit-v1-41578885310-1'
    evidence, inventories = dict(records=[], errors=[]), []
    for suffix, selected in [('smoke', names[:2])] + [(f'{i:03d}', p['tickers']) for i, p in enumerate(parts)]:
        tag = prefix + '-' + suffix
        assets = []
        for ticker in selected:
            asset = ticker.encode().hex() + '.pit.json.gz'
            evidence['records'].append(dict(ticker=ticker, release=tag, asset=asset, sha256='0' * 64, bytes=1))
            assets.append(dict(name=asset, state='uploaded', size=1, digest='sha256:' + '0' * 64))
        inventories.append(dict(tag_name=tag, draft=False, assets=assets))
    coverage = [dict(timeframe=tf, field=field, stocks=NAMES, query_rows=QUERIES,
        known=QUERIES - 1, finite=QUERIES - 1, infinite=0, missing=1, known_without_source=0,
        first_known_setup='2020-01-02', last_known_setup='2026-10-23') for tf in TIMEFRAMES for field in fields]
    base = dict(stocks=NAMES, different_cells=0, missing_differences=0, availability_failures=0)
    report = dict(format='PRICE_FULL_COHORT_PIT_MEASURED_V1', measurement='MEASURED', plan_sha256=PLAN_SHA,
        expected_names=NAMES, measured_names=NAMES, expected_query_rows=QUERIES, measured_query_rows=QUERIES,
        unmeasured_names=[], fields_per_timeframe=FIELDS, native_timeframes=22, prefix_cuts=CUTS,
        source_commit='commit', composition={}, frozen_recipe='recipe', run_id='41578885310', run_attempt='1',
        inputs_release=prefix + '-inputs', per_stock_evidence_bytes=NAMES,
        prefix_gate='PASS', alignment_gate='PASS', packet_replay_gate='FAIL', scoring_gate='CLOSED',
        canonical_binary_world_gate='NOT_PROVEN', explicit_per_column_available_from_gate='NOT_PROVEN',
        historical_provider_revision_gate='NOT_MEASURED',
        historical_eligibility_gate='NOT_PROVEN_DIAGNOSTIC_ALL_TRUE_ENCODING_MASK_IS_NOT_TRADEABILITY',
        prefix_totals=[dict(base, timeframe=tf, cut=cut, expected_rows=3 * NAMES, rebuilt_rows=3 * NAMES,
            compared_rows=3 * NAMES, cells=3 * NAMES * FIELDS) for tf in TIMEFRAMES for cut in CUTS],
        alignment_totals=[dict(base, timeframe=tf, cells=QUERIES * FIELDS, native_rows=3 * NAMES,
            native_end_not_before_availability=0, selected_source_not_before_setup=0) for tf in TIMEFRAMES],
        packet_replay_totals=[dict(base, timeframe=tf, questions=NAMES * FIELDS * 3, cells=QUERIES * FIELDS * 3,
            **({'different_cells': 1} if tf == '1d' else {})) for tf in TIMEFRAMES],
        failing_stocks=[dict(ticker=names[0], packet_replay_gate='FAIL')])
    return plan, report, coverage, evidence, inventories


def test_complete_bundle_with_observed_failure_is_measured_but_scoring_remains_closed(synthetic_complete_metadata):
    result = validate(*synthetic_complete_metadata, plan_sha256=PLAN_SHA)
    assert result['retained_names'] == 8439 and result['setup_day_rows'] == 12547288
    assert result['field_timeframe_rows'] == 22968 and result['proof_metadata_verified'] == 8439
    assert result['packet_replay_gate'] == 'FAIL' and result['scoring_gate'] == 'CLOSED'


@pytest.mark.parametrize('mutation', ['missing_stock', 'missing_field', 'query_count', 'false_pass',
    'different_digest', 'draft', 'wrong_release', 'hidden_failure', 'false_source', 'false_scope', 'wrong_inputs'])
def test_incomplete_or_contradictory_published_evidence_cannot_be_accepted(synthetic_complete_metadata, mutation):
    plan, report, coverage, evidence, inventories = copy.deepcopy(synthetic_complete_metadata)
    if mutation == 'missing_stock':
        evidence['records'].pop()
    elif mutation == 'missing_field':
        coverage.pop()
    elif mutation == 'query_count':
        coverage[0]['query_rows'] -= 1
    elif mutation == 'false_pass':
        report['packet_replay_gate'] = 'PASS'
    elif mutation == 'different_digest':
        inventories[0]['assets'][0]['digest'] = 'sha256:' + '1' * 64
    elif mutation == 'draft':
        inventories[0]['draft'] = True
    elif mutation == 'wrong_release':
        evidence['records'][0]['release'] += '-counterexample-replay'
    elif mutation == 'hidden_failure':
        report['failing_stocks'] = []
    elif mutation == 'false_source':
        report['frozen_recipe'] = 'other'
    elif mutation == 'false_scope':
        report['measurement'] = 'PARTIAL_NOT_MEASURED_FULL_COHORT'
    else:
        report['inputs_release'] = 'price-full-cohort-pit-v1-other-1-inputs'
    with pytest.raises(ValueError):
        validate(plan, report, coverage, evidence, inventories, plan_sha256=PLAN_SHA)


def test_zero_known_field_remains_measured_without_claiming_quality(synthetic_complete_metadata):
    plan, report, coverage, evidence, inventories = copy.deepcopy(synthetic_complete_metadata)
    coverage[0].update(known=0, finite=0, missing=QUERIES, first_known_setup='', last_known_setup='')
    assert validate(plan, report, coverage, evidence, inventories, plan_sha256=PLAN_SHA)['scoring_gate'] == 'CLOSED'


def test_plan_and_evidence_bytes_are_authenticated(synthetic_complete_metadata, tmp_path):
    with pytest.raises(ValueError, match='plan'):
        validate(*synthetic_complete_metadata, plan_sha256='wrong')
    (tmp_path / 'PRICE_FULL_COHORT_PIT_PLAN_V1.json').write_bytes(b'{}\n')
    (tmp_path / COVERAGE).write_bytes(b'not a verified gzip')
    report = {'evidence': {COVERAGE: {'bytes': 1, 'sha256': 'wrong'}, EVIDENCE: {}}}
    (tmp_path / REPORT).write_text(json.dumps(report))
    with pytest.raises(ValueError, match='fingerprint'):
        read_bundle(tmp_path, [])

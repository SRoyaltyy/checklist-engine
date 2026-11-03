import json

import numpy as np
import pandas as pd
import pytest

from ci.price_full_cohort_pit import (aligned_coverage, diagnostic_answers, matrix_diff,
                                      packet_replay, sha, Accumulator, validate_stock)
from world_timeframes import align_features


def test_exact_matrix_bits_keep_missing_infinity_and_signed_zero_distinct():
    a = np.array([[1., np.nan, np.inf, 0., -np.inf]])
    b = a.copy()
    b[0, 0] = np.nextafter(1., 2.)
    b[0, 1] = 0.
    b[0, 3] = -0.
    result = matrix_diff(a, b, list('abcde'))
    assert result['different_cells'] == 3 and result['missing_differences'] == 1
    assert [d['field'] for d in result['field_differences']] == ['a', 'b', 'd']
    assert matrix_diff(a, a.copy(), list('abcde'))['different_cells'] == 0


def alignment_inputs():
    query = pd.date_range('2024-01-01', periods=4).as_unit('ns')
    native = pd.DataFrame(dict(date=query[:2]))
    full = pd.DataFrame(dict(available_from=query[1:3], x=[10., np.inf], y=[np.nan, 2.]))
    return query, native, full


def test_setup_day_coverage_counts_actual_queries_not_pre2020_native_history():
    q, n, f = alignment_inputs()
    rows, check = aligned_coverage(q, n, f, ['x', 'y'], '1d', align_features)
    assert check['different_cells'] == 0 and check['cells'] == 8
    x, y = rows
    assert (x['query_rows'], x['known'], x['finite'], x['infinite'], x['missing']) == (4, 3, 1, 2, 1)
    assert y['known'] == 2 and y['missing'] == 2
    assert x['first_known_setup'] == '2024-01-02' and x['last_known_setup'] == '2024-01-04'


def test_independent_lookup_catches_forward_alignment_and_late_source():
    q, n, f = alignment_inputs()
    def peeking(query, full, timeframe):
        out = align_features(query + pd.Timedelta(days=1), full, timeframe)
        out['date'] = query
        return out
    rows, check = aligned_coverage(q, n, f, ['x', 'y'], '1d', peeking)
    assert check['different_cells'] > 0 and rows[0]['known_without_source'] == 1
    n['date'] = f.available_from
    _, check = aligned_coverage(q, n, f, ['x', 'y'], '1d', align_features)
    assert check['native_end_not_before_availability'] == 2


def test_vectorized_replay_matches_the_original_per_series_predicates():
    dates = pd.date_range('2024-01-01', periods=40).as_unit('ns')
    full = pd.DataFrame(dict(x=np.sin(np.arange(40)), y=np.arange(40, dtype=float), available_from=dates))
    full.loc[7, 'x'] = np.inf
    full.loc[10, 'y'] = np.nan
    expected = {}
    for name in ('x', 'y'):
        x = full[name]
        mean, std = x.rolling(20).mean(), x.rolling(20).std(ddof=0)
        for facet, right in [('rising1', x.shift(1)), ('above_mean20', mean), ('above_mean_plus_sd20', mean + std)]:
            expected[name + ':' + facet] = np.where(np.isfinite(x) & np.isfinite(right), (x > right).astype(float), np.nan)
    legacy = pd.DataFrame(expected)
    legacy['available_from'] = dates
    old = align_features(dates, legacy, '1d').drop(columns='date')
    new = diagnostic_answers(full, dates, '1d', align_features)
    assert list(old) == list(new)
    assert matrix_diff(old.to_numpy(), new.to_numpy(), list(old))['different_cells'] == 0


def packet():
    from world_answer_cache import encode_answers, registry_bytes
    qids = ['x:rising1__1d', 'y:above_mean20__1d']
    schema = [dict(question_id=q, outcomes=[0, 1], formula='declared binary') for q in qids]
    digest = sha(registry_bytes(schema))
    provenance = dict(input_manifest_sha256='a' * 64, recipe_fingerprint='b' * 64,
                      row_keys_sha256='c' * 64, eligibility_mask_sha256='d' * 64)
    values = pd.DataFrame([[0., np.nan], [1., 0.], [np.nan, 1.]], columns=qids)
    data, meta = encode_answers(values, schema, dict(provenance, question_tree_sha256=digest))
    return {'1d_00000.json': json.dumps(meta).encode(), '1d_00000.zst': data}, {digest: schema}, values, provenance


def test_actual_packet_replay_retains_missing_and_binary_mismatches():
    contents, registry, values, provenance = packet()
    assert packet_replay(contents, registry, '1d', values, provenance, set())['different_cells'] == 0
    values.iloc[0, 0] = 1.
    values.iloc[0, 1] = 0.
    result = packet_replay(contents, registry, '1d', values, provenance, set())
    assert result['different_cells'] == 2 and result['missing_differences'] == 1
    assert result['cells'] == 6 and result['questions'] == 2


def test_packet_row_binding_and_duplicate_questions_fail_closed():
    contents, registry, values, provenance = packet()
    with pytest.raises(ValueError, match='provenance'):
        packet_replay(contents, registry, '1d', values, dict(provenance, row_keys_sha256='e' * 64), set())
    seen = set()
    packet_replay(contents, registry, '1d', values, provenance, seen)
    with pytest.raises(ValueError, match='repeated'):
        packet_replay(contents, registry, '1d', values, provenance, seen)


def stock_fixture(ticker='ONE'):
    dates = pd.date_range('2024-01-01', periods=2).as_unit('ns')
    ref = dict(ticker=ticker, query_rows=2, raw_sha256='a', answer_container_sha256='b')
    plan = dict(timeframes=['1d'], price_fields=['x'], prefix_cuts=['2023-01-03'],
        calendar_sha256='c', registry={'sha256': 'd'},
        frozen_build_request={'corrected_recipe_fingerprint': 'e'}, references=[ref],
        expected_names=[ticker], expected_query_rows=2)
    stock = dict(ticker=ticker, measurement_complete=True, query_rows=2,
        query_dates=[str(d.date()) for d in dates], row_keys_sha256=sha(ticker.encode() + dates.asi8.tobytes()),
        raw_sha256='a', packet_sha256='b', calendar_sha256='c', registry_sha256='d', recipe_fingerprint='e',
        coverage=[dict(timeframe='1d', field='x', query_rows=2, known=1, finite=1, infinite=0, missing=1,
                       known_without_source=0, first_known_setup='2024-01-02', last_known_setup='2024-01-02')],
        prefix_checks=[dict(timeframe='1d', cut='2023-01-03', columns=1, expected_rows=0, rebuilt_rows=0,
            compared_rows=0, cells=0, different_cells=0, missing_differences=0, availability_differences=[])],
        alignment_checks=[dict(timeframe='1d', native_rows=1, native_end_not_before_availability=0,
            selected_source_not_before_setup=0, cells=2, different_cells=0, missing_differences=0)],
        packet_replay=[dict(timeframe='1d', questions=3, cells=6, different_cells=0, missing_differences=0)],
        prefix_gate='PASS', alignment_gate='PASS', packet_replay_gate='PASS', scoring_gate='CLOSED')
    return plan, ref, stock


def test_complete_measurement_can_report_observed_failure_without_opening_scoring():
    plan, _, stock = stock_fixture()
    stock['packet_replay'][0]['different_cells'] = 1
    stock['packet_replay_gate'] = 'FAIL'
    acc = Accumulator(plan)
    acc.add(stock, {'ticker': 'ONE'})
    report = acc.report()
    assert report['measurement'] == 'MEASURED'
    assert report['packet_replay_gate'] == 'FAIL' and report['scoring_gate'] == 'CLOSED'
    assert report['historical_provider_revision_gate'] == 'NOT_MEASURED'
    with pytest.raises(ValueError, match='duplicate'):
        acc.add(stock, {'ticker': 'ONE'})


def test_partial_cohort_cannot_claim_measured_or_pass():
    plan, _, stock = stock_fixture()
    plan['expected_names'].append('TWO')
    plan['expected_query_rows'] = 4
    acc = Accumulator(plan)
    acc.add(stock, {'ticker': 'ONE'})
    report = acc.report()
    assert report['measurement'] == 'PARTIAL_NOT_MEASURED_FULL_COHORT'
    assert report['unmeasured_names'] == ['TWO']
    assert report['prefix_gate'] == 'NOT_MEASURED_FULL_COHORT'
    assert acc.coverage[('1d', 'x')]['query_rows'] == 2


@pytest.mark.parametrize('mutation', ['field', 'source', 'label', 'dates', 'packet'])
def test_full_grid_source_gate_and_setup_date_proofs_are_enforced(mutation):
    plan, ref, stock = stock_fixture()
    if mutation == 'field':
        stock['coverage'] = []
    elif mutation == 'source':
        stock['raw_sha256'] = 'wrong'
    elif mutation == 'label':
        stock['prefix_gate'] = 'FAIL'
    elif mutation == 'dates':
        stock['query_dates'].reverse()
    else:
        stock['packet_replay'][0]['cells'] -= 1
    with pytest.raises(ValueError):
        validate_stock(stock, plan, ref)


def test_prefix_availability_mismatch_is_measured_even_with_no_common_rows():
    from ci.price_v1_sample_gate import align_prefix
    expected = pd.DataFrame(dict(x=[1.], available_from=pd.to_datetime(['2023-01-01'])))
    rebuilt = pd.DataFrame(dict(x=[1.], available_from=pd.to_datetime(['2023-01-02'])))
    left, right, differences = align_prefix(expected, rebuilt)
    assert len(left) == len(right) == 0
    assert differences[0]['different_cells'] == 2


@pytest.mark.parametrize('present', [True, False])
def test_finalizer_recovers_uploaded_proof_without_chunk_receipt_and_publishes_partial_honestly(tmp_path, monkeypatch, present):
    import ci.price_full_cohort_pit as pit
    from ci import release_assets as io
    plan, _, stock = stock_fixture()
    plan.update(smoke_parts=[{'tickers': ['ONE']}], work_parts=[], source_commit='commit', composition={})
    source = tmp_path / 'source.gz'
    pit.write_gzip(source, stock)
    raw = source.read_bytes()
    asset_name = b'ONE'.hex() + '.pit.json.gz'
    monkeypatch.setenv('GITHUB_REPOSITORY', 'SRoyaltyy/checklist-engine')
    monkeypatch.setenv('GITHUB_RUN_ID', '123')
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT', '1')
    monkeypatch.setattr(pit, 'read_plan', lambda *args: plan)
    monkeypatch.setattr(pit, 'create_release', lambda *args: None)
    monkeypatch.setattr(io, 'asset_index', lambda tag: {asset_name: {'digest': 'sha256:' + sha(raw), 'size': len(raw)}} if present else {})
    def download(tag, name, directory):
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / name
        path.write_bytes(raw)
        return path
    monkeypatch.setattr(io, 'download_asset', download)
    published = []
    monkeypatch.setattr(io, 'publish_assets', lambda tag, *paths: published.extend(p.name for p in paths))
    monkeypatch.setattr(io, 'gh_retry', lambda *args: None)
    root = tmp_path / 'final'
    root.mkdir()
    if present:
        pit.finalize(root, 'price-full-cohort-pit-v1-123-1-inputs', 'pin')
    else:
        with pytest.raises(ValueError, match='unmeasured'):
            pit.finalize(root, 'price-full-cohort-pit-v1-123-1-inputs', 'pin')
    report = json.loads((root / 'PRICE_FULL_COHORT_PIT_MEASURED_V1.json').read_bytes())
    assert report['measurement'] == ('MEASURED' if present else 'PARTIAL_NOT_MEASURED_FULL_COHORT')
    assert report['measured_names'] == int(present)
    assert report['scoring_gate'] == 'CLOSED'
    assert 'PRICE_FULL_COHORT_PIT_MEASURED_V1.json' in published
    assert not list((root / 'stock').glob('*.gz'))

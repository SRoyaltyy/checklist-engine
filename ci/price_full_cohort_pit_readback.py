"""Independent, read-only verification of the published full-cohort PIT bundle.

No feature calculation or market download runs here. Stock proof bodies were
checked by the bound runner finalizer; this readback checks its complete bundle
and every current published proof size/digest without claiming a second replay.
"""
import argparse
from datetime import date
import gzip
import hashlib
import json
from pathlib import Path
import re

PLAN_SHA = '18e12eed42099647d598931868547c85f99731b14b6f6138fece0fd87a43043d'
INPUT_RELEASE = 'price-full-cohort-pit-v1-41578885310-1-inputs'
NAMES, QUERIES, FIELDS = 8439, 12547288, 1044
TIMEFRAMES = [f'{i}d' for i in range(1, 22)] + ['monthly']
CUTS = ['2023-01-03', '2025-01-02']
GATES = ('prefix_gate', 'alignment_gate', 'packet_replay_gate')
REPORT = 'PRICE_FULL_COHORT_PIT_MEASURED_V1.json'
COVERAGE = 'PRICE_FULL_COHORT_SETUP_DAY_COVERAGE_V1.json.gz'
EVIDENCE = 'PRICE_FULL_COHORT_PIT_EVIDENCE_V1.json.gz'


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def nonnegative(row, *keys):
    require(all(type(row[k]) is int and row[k] >= 0 for k in keys), 'invalid measurement counter')


def validate(plan, report, coverage, evidence, inventories, *, plan_sha256):
    require(plan_sha256 == PLAN_SHA and report['plan_sha256'] == PLAN_SHA, 'different frozen plan')
    names = set(plan['expected_names'])
    refs = {r['ticker']: r for r in plan['references']}
    require(len(names) == len(plan['expected_names']) == len(refs) == len(plan['references']) == NAMES
            and set(refs) == names and sum(r['query_rows'] for r in refs.values()) == QUERIES
            and plan['expected_query_rows'] == QUERIES, 'incomplete retained cohort')
    require(plan['timeframes'] == TIMEFRAMES and len(set(plan['price_fields'])) == len(plan['price_fields']) == FIELDS
            and plan['prefix_cuts'] == CUTS and not names.intersection(plan['quarantine_names']), 'different price scope')
    require(report['format'] == 'PRICE_FULL_COHORT_PIT_MEASURED_V1' and report['measurement'] == 'MEASURED'
            and report['expected_names'] == report['measured_names'] == NAMES
            and report['expected_query_rows'] == report['measured_query_rows'] == QUERIES
            and not report['unmeasured_names'] and report['fields_per_timeframe'] == FIELDS
            and report['native_timeframes'] == len(TIMEFRAMES) and report['prefix_cuts'] == CUTS, 'partial measurement')
    require(report['source_commit'] == plan['source_commit'] and report['composition'] == plan['composition']
            and report['frozen_recipe'] == plan['frozen_build_request']['corrected_recipe_fingerprint'], 'different source binding')
    require(report['inputs_release'] == INPUT_RELEASE and str(report['run_id']).isdigit()
            and str(report['run_attempt']).isdigit() and int(report['run_attempt']) >= 1, 'different run binding')
    # A later read-only finalizer may have its own run ID; its proof namespace
    # must still be the original immutable measurement input/part namespace.
    prefix = INPUT_RELEASE.removesuffix('-inputs')
    require(report['scoring_gate'] == 'CLOSED' and report['canonical_binary_world_gate'] == 'NOT_PROVEN'
            and report['explicit_per_column_available_from_gate'] == 'NOT_PROVEN'
            and report['historical_provider_revision_gate'] == 'NOT_MEASURED'
            and report['historical_eligibility_gate'] == 'NOT_PROVEN_DIAGNOSTIC_ALL_TRUE_ENCODING_MASK_IS_NOT_TRADEABILITY',
            'measurement overclaims unresolved gates')
    expected_releases = {}
    for suffix, selected in [('smoke', [t for p in plan['smoke_parts'] for t in p['tickers']])] + [
            (f'{i:03d}', p['tickers']) for i, p in enumerate(plan['work_parts'])]:
        for ticker in selected:
            require(ticker not in expected_releases, 'duplicate planned name')
            expected_releases[ticker] = prefix + '-' + suffix
    require(set(expected_releases) == names, 'incomplete source partition')
    release_index = {r['tag_name']: r for r in inventories}
    require(len(release_index) == len(inventories), 'duplicate public release')
    records = evidence['records']
    require(not evidence['errors'] and len(records) == NAMES and {r['ticker'] for r in records} == names,
            'incomplete proof evidence or unresolved errors')
    total_bytes = 0
    for row in records:
        ticker = row['ticker']
        nonnegative(row, 'bytes')
        require(row['release'] == expected_releases[ticker]
                and row['asset'] == ticker.encode().hex() + '.pit.json.gz'
                and re.fullmatch('[0-9a-f]{64}', row['sha256']) is not None, 'different stock proof binding')
        release = release_index.get(row['release'])
        require(release is not None and release['draft'] is False, 'stock proof release is not public')
        assets = {a['name']: a for a in release['assets']}
        require(len(assets) == len(release['assets']), 'duplicate public proof asset')
        asset = assets.get(row['asset'])
        require(asset is not None and asset['state'] == 'uploaded' and asset['size'] == row['bytes'] > 0
                and asset['digest'] == 'sha256:' + row['sha256'], 'public stock proof fingerprint differs')
        total_bytes += row['bytes']
    require(report['per_stock_evidence_bytes'] == total_bytes, 'proof byte accounting differs')
    grid = {(tf, field) for tf in TIMEFRAMES for field in plan['price_fields']}
    require(len(coverage) == len(grid) and {(r['timeframe'], r['field']) for r in coverage} == grid,
            'incomplete setup-day field grid')
    for row in coverage:
        nonnegative(row, 'stocks', 'query_rows', 'known', 'finite', 'infinite', 'missing', 'known_without_source')
        require(row['stocks'] == NAMES and row['query_rows'] == QUERIES
                and row['known'] + row['missing'] == QUERIES and row['finite'] + row['infinite'] == row['known']
                and row['known_without_source'] <= row['known'], 'field coverage accounting differs')
        if row['known']:
            first, last = date.fromisoformat(row['first_known_setup']), date.fromisoformat(row['last_known_setup'])
            require(date(2020, 1, 1) <= first <= last <= date(2026, 10, 23), 'field setup dates differ')
        else:
            require(row['first_known_setup'] == row['last_known_setup'] == '', 'missing field has known dates')
    expected = dict(prefix_totals={(tf, cut) for tf in TIMEFRAMES for cut in CUTS},
                    alignment_totals={(tf,) for tf in TIMEFRAMES}, packet_replay_totals={(tf,) for tf in TIMEFRAMES})
    failed = {}
    for key, wanted in expected.items():
        rows = report[key]
        require(len(rows) == len(wanted) and {
            (r['timeframe'], r['cut']) if key == 'prefix_totals' else (r['timeframe'],) for r in rows} == wanted,
            'incomplete cut/timeframe totals')
        any_failure = False
        for row in rows:
            nonnegative(row, 'stocks', 'cells', 'different_cells', 'missing_differences', 'availability_failures')
            require(row['stocks'] == NAMES and row['missing_differences'] <= row['different_cells'] <= row['cells']
                    and row['availability_failures'] <= NAMES, 'invalid comparison totals')
            if key == 'prefix_totals':
                nonnegative(row, 'expected_rows', 'rebuilt_rows', 'compared_rows')
                require(row['cells'] == row['compared_rows'] * FIELDS
                        and row['compared_rows'] <= min(row['expected_rows'], row['rebuilt_rows']), 'prefix cells differ')
                if not row['availability_failures']:
                    require(row['expected_rows'] == row['rebuilt_rows'] == row['compared_rows'], 'prefix keys differ')
                any_failure |= bool(row['different_cells'] or row['availability_failures'])
            elif key == 'alignment_totals':
                nonnegative(row, 'native_rows', 'native_end_not_before_availability', 'selected_source_not_before_setup')
                require(row['cells'] == QUERIES * FIELDS, 'alignment cell scope differs')
                any_failure |= bool(row['different_cells'] or row['native_end_not_before_availability'] or row['selected_source_not_before_setup'])
            else:
                nonnegative(row, 'questions')
                require(row['questions'] == NAMES * FIELDS * 3 and row['cells'] == QUERIES * FIELDS * 3, 'packet replay cell scope differs')
                any_failure |= bool(row['different_cells'])
        gate = dict(prefix_totals='prefix_gate', alignment_totals='alignment_gate', packet_replay_totals='packet_replay_gate')[key]
        failed[gate] = any_failure
        require(report[gate] == ('FAIL' if any_failure else 'PASS'), 'gate contradicts measured totals')
    failing = report['failing_stocks']
    require(len(failing) == len({r['ticker'] for r in failing}) and {r['ticker'] for r in failing} <= names,
            'duplicate or foreign failing stock')
    for row in failing:
        keys = set(row) - {'ticker'}
        require(bool(keys) and keys <= set(GATES) and all(row[k] == 'FAIL' for k in keys), 'invalid failing-stock verdict')
    require(all(failed[k] == any(k in row for row in failing) for k in GATES), 'failing stock list contradicts totals')
    require(not any(r['known_without_source'] for r in coverage) or failed['alignment_gate'], 'unstamped known field accepted')
    return dict(status='PASS_FULL_RETAINED_COHORT_BUNDLE_AND_PUBLIC_PROOF_METADATA',
        retained_names=NAMES, setup_day_rows=QUERIES, field_timeframe_rows=len(grid),
        proof_metadata_verified=len(records), per_stock_evidence_bytes=total_bytes,
        stock_body_verification='BOUND_GHA_FINALIZER_NOT_A_SECOND_LOCAL_REPLAY',
        **{k: report[k] for k in GATES}, scoring_gate='CLOSED')


def read_bundle(directory, inventories):
    root = Path(directory)
    report = json.loads((root / REPORT).read_bytes())
    raw = (root / 'PRICE_FULL_COHORT_PIT_PLAN_V1.json').read_bytes()
    plan_sha = hashlib.sha256(raw).hexdigest()
    objects = {}
    require(set(report['evidence']) == {COVERAGE, EVIDENCE}, 'unexpected evidence asset set')
    for name in (COVERAGE, EVIDENCE):
        data = (root / name).read_bytes()
        binding = report['evidence'][name]
        require(binding['bytes'] == len(data) and binding['sha256'] == hashlib.sha256(data).hexdigest(), 'evidence body fingerprint differs')
        objects[name] = json.loads(gzip.decompress(data))
    return validate(json.loads(raw), report, objects[COVERAGE], objects[EVIDENCE], inventories, plan_sha256=plan_sha)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True)
    parser.add_argument('--inventories', required=True, help='Authenticated current GitHub release inventory JSON array')
    args = parser.parse_args()
    print(json.dumps(read_bundle(args.directory, json.loads(Path(args.inventories).read_bytes())), indent=2))

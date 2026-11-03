"""Read-only world gate for the completed #203 price rebuild.

Authenticates the actual composed output and every active payload inventory.
Sample tests, diagnostic answers and storage acceptance retain their scopes;
none substitutes for a full-cohort PIT, eligibility or canonical-world proof.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess

from ci.price_recovery_composition import compose

ROOT = Path(__file__).resolve().parents[1]
REQUEST = 'ci/COMPLETED_PRICE_WORLD_GATE_REQUEST.json'
TIMEFRAMES = tuple([f'{i}d' for i in range(1, 22)] + ['monthly'])


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def validate_registry(registry, expected_sha):
    ids = []
    frames = Counter()
    columns = set()
    for digest, questions in registry.items():
        # The published REGISTERED_ANSWER_BITPLANES_V1 canonical JSON format;
        # metadata validation needs no NumPy/Pandas/Arrow installation.
        raw = json.dumps(questions, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        if sha(raw) != digest:
            raise ValueError('registry block digest differs')
        for question in questions:
            qid = question['question_id']
            if (question['outcomes'] != [0, 1] or any(type(v) is not int for v in question['outcomes'])
                    or not isinstance(question.get('formula'), str) or not question['formula'].strip()):
                raise ValueError('diagnostic answer type/formula differs')
            feature, timeframe = qid.rsplit('__', 1)
            column, facet = feature.rsplit(':', 1)
            if timeframe not in TIMEFRAMES or facet not in ('rising1', 'above_mean20', 'above_mean_plus_sd20'):
                raise ValueError('diagnostic timeframe/facet differs')
            ids.append(qid)
            frames[timeframe] += 1
            columns.add(column)
    if len(ids) != len(set(ids)) or len(ids) != 68904 or set(frames) != set(TIMEFRAMES):
        raise ValueError('diagnostic question inventory differs')
    if len(columns) != 1044 or set(frames.values()) != {3132}:
        raise ValueError('diagnostic column/timeframe grid differs')
    return dict(sha256=expected_sha, questions=len(ids), columns_per_timeframe=len(columns),
                timeframes=list(TIMEFRAMES), questions_per_timeframe=dict(sorted(frames.items())),
                kind='DIAGNOSTIC_ROLLING_COMPARISONS_NOT_CANONICAL_BINARY_MASTER')


def verify_payloads(rows, registry_sha, inventories):
    """Check every row's exact public asset metadata, never call this a body audit."""
    seen = set()
    for row in rows:
        ticker = row['ticker']
        if ticker in seen:
            raise ValueError('duplicate completed ticker')
        seen.add(ticker)
        asset = inventories[row['release']].get(row['asset'])
        if (asset is None or asset.get('_draft_release') or asset['state'] != 'uploaded'
                or asset['digest'] != 'sha256:' + row['answer_container_sha256']
                or asset['size'] != row['answer_container_bytes']
                or row['shared_registry_sha256'] != registry_sha
                or row['diagnostic_questions'] != 68904
                or row['roundtrip'] != 'ALL_CELLS_EXACT_WITH_MISSING_DISTINCT'):
            raise ValueError('active payload metadata/provenance differs: ' + ticker)
    return dict(status='PASS', tickers=len(seen), releases=len(inventories),
                scope='Current public asset size/digest/state plus producer roundtrip declarations; bodies not reread')


def validate_worker(raw, binding):
    if sha(raw) != binding['sha256']:
        raise ValueError('pinned diagnostic worker differs')
    if b'eligibility_mask_sha256=sha(np.ones(len(query),dtype=np.uint8).tobytes())' not in raw:
        raise ValueError('diagnostic eligibility encoding policy changed; review the gate claim')


def assess(composed, plan, registry, payloads, sample, reconstruction):
    names = [r['ticker'] for r in composed['completed']]
    expected = [t for p in plan['parts'] for t in p['tickers']]
    if (len(names) != len(set(names)) or set(names) != set(expected)
            or len(names) != plan['accepted_tickers'] or composed['excluded'] or composed['shard_errors']
            or composed['completed_tickers'] != len(names) or composed['build_excluded_tickers'] != 0
            or payloads['tickers'] != len(names) or payloads['status'] != 'PASS'):
        raise ValueError('completed cohort or payload audit is incomplete')
    if not 0 < sample['sample_stocks'] <= len(names):
        raise ValueError('sample scope exceeds the retained cohort')
    checks = {
        'retained_price_cohort_and_current_payload_metadata': dict(status='PASS', measured_names=len(names)),
        'price_dependency_storage_reservation': dict(
            status='PASS' if (composed['storage_gate'] == 'PASS_PRICE_RESERVATION_ONLY_NOT_WORLD'
                              and composed['measured_price_dependency_bytes'] <= plan['request']['hard_world_cap_bytes']) else 'FAIL',
            measured_bytes=composed['measured_price_dependency_bytes'],
            limit_bytes=plan['request']['hard_world_cap_bytes'], scope='Price dependencies, not complete world'),
        'diagnostic_registry_grid': dict(status='PASS', **registry),
        'full_cohort_price_prefix_PIT': dict(
            status='SCOPE_INCOMPLETE' if sample['price_v1_gate'] == 'PASS' and sample['prefix_mismatch_blocks'] == 0 else 'FAIL',
            measured_sample_names=sample['sample_stocks'],
            required_names=len(names), sample_run=sample['run'], sample_compared_cells=sample['compared_cells'],
            sample_mismatch_blocks=sample['prefix_mismatch_blocks'],
            reason='Published proof is the predeclared 100-stock sample; the remaining retained names are unmeasured'),
        'historical_tradeable_and_nominal_100M_eligibility': dict(
            status='NOT_PROVEN', reason='No full-cohort historical eligibility proof is bound to this rebuild; '
            'the diagnostic worker stores an all-true encoding mask, which is not a tradeability approval'),
        'canonical_binary_price_answers_and_quality': dict(
            status='NOT_PROVEN', reason='Published 68,904-question diagnostic registry is not the canonical '
            'BINARY_MASTER; complete tree-to-answer coverage and constant/blank quality proof are absent'),
        'price_column_available_from_and_all_column_leak_traps': dict(
            status='NOT_PROVEN', reason='Packet provenance binds row keys and recipe, but no complete '
            'per-column availability manifest or full-cohort leak-trap proof is published by #203'),
        'full_cohort_exact_numeric_reconstruction': dict(
            status='SCOPE_INCOMPLETE', measured_sample_names=len(reconstruction['samples']),
            sample_recipe_fingerprint=reconstruction['stock_recipe_fingerprint'],
            rebuild_recipe_fingerprint=plan['request']['corrected_recipe_fingerprint'],
            reason='Exact recomputation is authorized, but the existing proof is an older sample, '
            'not complete-cohort evidence for this corrected rebuild'),
        'complete_world_blocks_and_dependency_budget': dict(
            status='NOT_PROVEN', reason='Price-only output has not integrated/measured every required world '
            'block and canonical question dependency; downloads are no longer deferred by the old v1 scope cut'),
    }
    failures = [name for name, check in checks.items() if check['status'] != 'PASS']
    return dict(format='COMPLETED_PRICE_WORLD_GATE_V1', world_gate='NOT_PROVEN' if failures else 'PROVEN',
                scoring_gate='CLOSED', checks=checks, failing_checks=failures,
                retained_names=len(names), query_stock_days=sum(r['query_rows'] for r in composed['completed']),
                original_universe=composed['original_universe'], source_excluded=composed['source_excluded_tickers'],
                build_excluded=0, full_cohort_price_PIT='UNMEASURED',
                payload_asset_metadata=payloads,
                no_new_market_computation=True, protected_source_mutations='NONE',
                limitation='This runner measures complete-cohort source/asset metadata and evaluates the '
                'world prerequisites. It does not claim full payload-body or full-cohort numeric/PIT measurement.')


def run(root):
    from ci import release_assets as io
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    request_raw = (ROOT / REQUEST).read_bytes()
    request = json.loads(request_raw)
    if request['execute'] is not True:
        raise ValueError('explicit completed-price gate execution is disabled')
    files = {}
    evidence = {}
    for name, binding in request['sources'].items():
        file = io.download_asset(binding['release'], binding['asset'], root / 'sources' / name)
        raw = file.read_bytes()
        if sha(raw) != binding['sha256']:
            raise ValueError('gate source body differs: ' + name)
        files[name] = raw
        evidence[name] = dict(binding, bytes=len(raw))
    values = {k: json.loads(raw) for k, raw in files.items()}
    plan, parent, replacement, probe, composed = (values[n] for n in
                                                ('plan', 'parent', 'replacement', 'probe', 'composition'))
    published_request = values['composition_request']
    current_request = json.loads((ROOT / 'ci/PRICE_RECOVERY_COMPOSITION_REQUEST.json').read_bytes())
    if current_request['execute'] is not False:
        raise ValueError('completed composer must remain disabled')
    current_request['execute'] = True
    if current_request != published_request:
        raise ValueError('published composition binding differs from current pinned inputs')
    worker = request['producer_worker']
    if worker['commit'] != published_request['source_commit']:
        raise ValueError('diagnostic worker is not the original producer')
    worker_raw = subprocess.check_output(['git', 'show', worker['commit'] + ':' + worker['path']], cwd=ROOT)
    validate_worker(worker_raw, worker)
    _, replay = compose(plan, parent, replacement, probe, composed['composition']['dependency_byte_ledger'],
                        bindings=published_request, parent_bytes=len(files['parent']),
                        request_bytes=len(files['composition_request']))
    if replay != files['composition']:
        raise ValueError('completed composition exact replay differs')
    registry = validate_registry(values['registry'], plan['request']['registry_sha256'])
    if request['sources']['registry']['sha256'] != plan['request']['registry_sha256']:
        raise ValueError('registry binding is not the rebuilt plan registry')
    inventories = {tag: io.asset_index(tag) for tag in sorted({r['release'] for r in composed['completed']})}
    payloads = verify_payloads(composed['completed'], plan['request']['registry_sha256'], inventories)
    policy = json.loads((ROOT / 'dictionary/REPLAY_QUARANTINE_V1.json').read_bytes())
    # The authenticated plan already records the owner's exact quarantine;
    # compare the policy body hash as well as the complete retained membership.
    policy_raw = (ROOT / 'dictionary/REPLAY_QUARANTINE_V1.json').read_bytes().replace(b'\r\n', b'\n')
    if sha(policy_raw) != plan['request']['replay_quarantine']['lf_sha256']:
        raise ValueError('owner quarantine policy differs')
    names = {r['ticker'] for r in composed['completed']}
    if (len(names) != policy['v1_names'] or
            sum(r['query_rows'] for r in composed['completed']) != policy['v1_stock_days'] or
            names & {r['ticker'] for r in policy['records']}):
        raise ValueError('completed rebuild differs from retained owner cohort')
    sample = json.loads((ROOT / 'docs/ROW0_PRICE_WORLD_GATE_V2.json').read_bytes())
    reconstruction = json.loads((ROOT / 'docs/NUMERIC_RECOMPUTE_MEASURED_V1.json').read_bytes())
    report = assess(composed, plan, registry, payloads, sample, reconstruction)
    report.update(run=int(os.environ['GITHUB_RUN_ID']), source_commit=os.environ['GITHUB_SHA'],
                  authenticated_sources=evidence, request_sha256=sha(request_raw),
                  authenticated_diagnostic_worker=worker,
                  supporting_repo_artifacts={p: sha((ROOT / p).read_bytes()) for p in
                      ('docs/ROW0_PRICE_WORLD_GATE_V2.json', 'docs/NUMERIC_RECOMPUTE_MEASURED_V1.json',
                       'ci/compact_world_storage_budget.py')})
    (root / 'COMPLETED_PRICE_WORLD_GATE_V1.json').write_bytes(encoded(report))
    print('COMPLETED_PRICE_WORLD_GATE', report['world_gate'], 'NAMES', report['retained_names'],
          'FAILING_CHECKS', ','.join(report['failing_checks']), flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True)
    args = parser.parse_args()
    target = Path(args.directory)
    try:
        result = run(target)
    except Exception as exc:
        target.mkdir(parents=True, exist_ok=True)
        result = dict(format='COMPLETED_PRICE_WORLD_GATE_V1', world_gate='NOT_PROVEN', scoring_gate='CLOSED',
                      failing_checks=['source_authentication_or_audit_execution'], error=str(exc),
                      run=int(os.environ['GITHUB_RUN_ID']), source_commit=os.environ['GITHUB_SHA'])
        (target / 'COMPLETED_PRICE_WORLD_GATE_V1.json').write_bytes(encoded(result))
        raise
    raise SystemExit(0 if result['world_gate'] == 'PROVEN' else 1)

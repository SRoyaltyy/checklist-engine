"""Empirical dispatch selector for the frozen price packet worker.

The original world build never recorded its numpy/OpenBLAS CPU dispatch, and
1,308 retained cohort names fail the packet_replay gate only on last-bit-fragile
derived statistics. This diagnostic reruns the unchanged frozen worker for
three observed counterexamples and three PASS controls under two recorded
profiles (native, no_numpy_dispatch) and identifies which profile reproduces
the stored packets bit-exactly. It never rewrites any source packet, never
mutates quarantine, and never claims full-world acceptance by itself.

Modes: ``ticker`` runs one name on one matrix runner; ``finalize`` aggregates
the per-ticker evidence into the selector verdict and publishes it.
"""
import argparse
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from ci.price_full_cohort_pit import (ROOT, checked, create_release, encoded, sha,
                                      tag_for, validate_stock)

REQUEST = 'ci/PRICE_PIT_DISPATCH_SELECTOR_REQUEST.json'
PROFILES = ['native', 'avx512_off', 'no_numpy_dispatch']
COUNTEREXAMPLES = ['AQMS', 'AZIO', 'BYRN']
CONTROLS = ['AVGO', 'CHCO', 'DB']
OVERRIDE_KEYS = ('NPY_DISABLE_CPU_FEATURES', 'OPENBLAS_CORETYPE')


def validate_request(request):
    if (request.get('version') != 1 or type(request.get('execute')) is not bool
            or request.get('profiles') != PROFILES
            or [r['ticker'] for r in request['counterexamples']] != COUNTEREXAMPLES
            or [r['ticker'] for r in request['controls']] != CONTROLS
            or request['worker_commit'] != '8003fb7906c3bf86d88612495664e597de1c65ae'
            or request['worker_lf_sha256'] != 'd48f918fe27bbdab5df56d4408d74284deba47406b323a138dfd459fa3cddbc2'
            or request['plan']['sha256'] != '18e12eed42099647d598931868547c85f99731b14b6f6138fece0fd87a43043d'
            or request.get('repetitions') != {'counterexample_native': 1, 'counterexample_avx512_off': 1, 'counterexample_no_numpy_dispatch': 2, 'control': 1}):
        raise ValueError('dispatch selector scope or frozen worker differs')
    return request


def active_dispatch():
    """Active numpy dispatch feature names on this runner (trace-compatible)."""
    command = [sys.executable, '-c',
        'import json,numpy as n;u=n._core._multiarray_umath;'
        'print(json.dumps([x for x in u.__cpu_dispatch__ if u.__cpu_features__.get(x)]))']
    return json.loads(subprocess.check_output(command, text=True))


def profile_env(profile, features):
    """Child environment for one profile; native must stay unoverridden."""
    if profile == 'native':
        if any(os.environ.get(k) for k in OVERRIDE_KEYS):
            raise ValueError('native profile requires unoverridden dispatch env')
        return None
    if profile == 'avx512_off':
        disabled = [f for f in features if f.startswith('AVX512')]
        if not disabled:
            raise ValueError('avx512_off profile has no AVX512 features to disable')
        env = dict(os.environ)
        env['NPY_DISABLE_CPU_FEATURES'] = ','.join(disabled)
        return env
    if profile == 'no_numpy_dispatch':
        if not features:
            raise ValueError('no_numpy_dispatch profile has no features to disable')
        env = dict(os.environ)
        env['NPY_DISABLE_CPU_FEATURES'] = ','.join(features)
        return env
    raise ValueError('unknown dispatch profile: ' + str(profile))


def profile_runtime_evidence(profile, features):
    """Recorded numpy runtime under one profile (show_runtime + feature lists)."""
    env = profile_env(profile, features)
    dump = subprocess.check_output([sys.executable, '-c',
        'import json,numpy as np,io;u=np._core._multiarray_umath;'
        'out=io.StringIO();np.show_runtime(out=out);'
        'print(json.dumps(dict(show_runtime=out.getvalue(),cpu_baseline=u.__cpu_baseline__,'
        'cpu_dispatch=u.__cpu_dispatch__,'
        'active_features=[x for x in u.__cpu_dispatch__ if u.__cpu_features__.get(x)],'
        'active_ufunc=np.lib.introspect.opt_func_info(func_name="^log$|^sqrt$|^divide$",signature="float64"))))'],
        text=True, env=env)
    evidence = json.loads(dump)
    evidence['profile'] = profile
    evidence['NPY_DISABLE_CPU_FEATURES'] = (env or os.environ).get('NPY_DISABLE_CPU_FEATURES', '')
    return evidence


def runtime_evidence():
    features = active_dispatch()
    profile_runtime = {}
    for profile in PROFILES:
        try:
            profile_runtime[profile] = profile_runtime_evidence(profile, features)
        except ValueError:
            profile_runtime[profile] = dict(profile=profile, status='VACUOUS_NO_AVX512_ON_RUNNER')
    return dict(python=sys.version,
        lscpu=json.loads(subprocess.check_output(['lscpu', '-J'], text=True)),
        active_dispatch_features=features,
        profile_runtime=profile_runtime)


def signature(stock):
    return sha(encoded(stock['packet_replay']))


def summarize(stock):
    return dict(packet_replay_gate=stock['packet_replay_gate'], signature=signature(stock),
        different_cells=sum(r['different_cells'] for r in stock['packet_replay']),
        missing_differences=sum(r['missing_differences'] for r in stock['packet_replay']))


def matches_stored(summary):
    return summary['different_cells'] == 0 and summary['missing_differences'] == 0


def comparison(ticker, role, reference, results):
    """Per-profile evidence: does this profile reproduce the stored packet bits?"""
    if reference['ticker'] != ticker or any(r['ticker'] != ticker for r in results):
        raise ValueError('dispatch selector repetition ticker differs')
    reference_summary = summarize(reference)
    expected_gate = 'FAIL' if role == 'counterexample' else 'PASS'
    if reference_summary['packet_replay_gate'] != expected_gate:
        raise ValueError('predeclared ' + role + ' gate differs')
    profiles = {}
    for profile in PROFILES:
        runs = [r for r in results if r['profile'] == profile]
        summaries = [r['summary'] for r in runs]
        profiles[profile] = dict(repetitions=len(runs),
            signatures=[s['signature'] for s in summaries],
            different_cells=[s['different_cells'] for s in summaries],
            missing_differences=[s['missing_differences'] for s in summaries],
            matches_stored=[matches_stored(s) for s in summaries],
            stable=len(runs) <= 1 or len({s['signature'] for s in summaries}) == 1,
            all_match_stored=bool(runs) and all(matches_stored(s) for s in summaries))
    return dict(ticker=ticker, role=role, reference_signature=reference_summary['signature'],
        reference_gate=reference_summary['packet_replay_gate'],
        reference_different_cells=reference_summary['different_cells'], profiles=profiles)


def verdict(comparisons):
    """Selector outcome across counterexamples and controls; never overclaims."""
    profiles = {}
    for profile in PROFILES:
        recovers = all(c['profiles'][profile]['all_match_stored'] for c in comparisons if c['role'] == 'counterexample')
        holds = all(c['profiles'][profile]['all_match_stored'] for c in comparisons if c['role'] == 'control')
        stable = all(c['profiles'][profile]['stable'] for c in comparisons)
        profiles[profile] = dict(counterexamples_recovered=recovers, controls_hold=holds,
            signatures_stable=stable, selected=recovers and holds and stable)
    selected = [p for p in PROFILES if profiles[p]['selected']]
    if len(selected) == len(PROFILES):
        outcome = 'ALL_PROFILES_MATCH'
    elif selected:
        outcome = 'SELECTED'
    else:
        outcome = 'UNRESOLVED'
    continuation = 'no_numpy_dispatch' if 'no_numpy_dispatch' in selected else (selected[0] if selected else None)
    return dict(outcome=outcome, selected_profiles=selected, continuation_profile=continuation,
        profiles=profiles,
        note='SELECTED lists the profiles that empirically reproduce the stored packets; '
             'continuation prefers the conservative no_numpy_dispatch pin when it matches; '
             'UNRESOLVED stops per ruling without quarantine fallback; '
             'ALL_PROFILES_MATCH means dispatch does not explain the flip on this grid.')


def repetitions_for(request, role, profile):
    key = 'control' if role == 'control' else 'counterexample_' + profile
    return request['repetitions'][key]


def request_tickers(request, key):
    return [r['ticker'] for r in request[key]]


def role_for(request, ticker):
    return 'counterexample' if ticker in request_tickers(request, 'counterexamples') else 'control'


def limited_process(command, directory, seconds, env=None):
    """limited_process clone that accepts an explicit child environment."""
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / 'worker.log').open('wb') as stream:
        with subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, env=env) as child:
            try:
                code = child.wait(timeout=seconds); reason = None if code == 0 else 'STOCK_PROCESS_ERROR'
            except subprocess.TimeoutExpired:
                child.kill(); child.wait(); code = child.returncode; reason = 'STOCK_TIMEOUT'
    with (directory / 'worker.log').open('rb') as stream:
        stream.seek(max(0, stream.seek(0, 2) - 4000)); tail = stream.read().decode(errors='replace')
    return dict(returncode=code, reason=reason, log_tail=tail)


def load_plan(root, request):
    plan = json.loads(checked(request['plan'], root / 'plan').read_bytes())
    refs = {r['ticker']: r for r in plan['references']}
    return plan, refs


def load_observed(root, request, plan, refs):
    from ci.price_full_cohort_pit import validate_stock as _validate
    observed = {}
    for key, expected_gate in (('counterexamples', 'FAIL'), ('controls', 'PASS')):
        for binding in request[key]:
            path = checked(binding, root / 'observed')
            with gzip.open(path, 'rt', encoding='utf-8') as stream:
                stock = json.load(stream)
            _validate(stock, plan, refs[binding['ticker']])
            if stock['packet_replay_gate'] != expected_gate:
                raise ValueError('predeclared ' + key[:-1] + ' is not ' + expected_gate)
            observed[binding['ticker']] = stock
    return observed


def run_ticker(root, ticker):
    """Run one name under both profiles; write <ticker>.selector.json + shards."""
    from ci.compact_world_build import snapshot
    from ci.native_price_blocks import read_member
    from ci.release_assets import describe_failure, download_asset
    request = validate_request(json.loads((ROOT / REQUEST).read_bytes()))
    if request['execute'] is not True:
        raise ValueError('dispatch selector execution disabled')
    if any(os.environ.get(k) for k in OVERRIDE_KEYS):
        raise ValueError('selector job env must stay unoverridden; profiles set child env only')
    if ticker not in request_tickers(request, 'counterexamples') + request_tickers(request, 'controls'):
        raise ValueError('matrix ticker outside declared selector scope')
    worker = ROOT / 'ci/price_full_cohort_pit.py'
    if sha(worker.read_bytes().replace(b'\r\n', b'\n')) != request['worker_lf_sha256']:
        raise ValueError('selector worker changed from the actual full run')
    plan, refs = load_plan(root, request)
    role = role_for(request, ticker)
    reference = refs[ticker]
    recipe, calendar = snapshot(root / 'snapshot', plan['frozen_build_request'])
    registry = checked(plan['registry'], root / 'registry')
    if sha(calendar.read_bytes()) != plan['calendar_sha256']:
        raise ValueError('selector calendar differs')
    part, = [p for p in plan['source_parts'] if ticker in p['tickers']]
    source = root / 'sources' / ticker.encode().hex()
    manifest = json.loads(download_asset(part['release'], part['part'] + '.json', source).read_bytes())
    archive = download_asset(part['release'], part['part'] + '.tar', source)
    if manifest['archive_sha256'] != part['archive_sha256'] or sha(archive.read_bytes()) != part['archive_sha256']:
        raise ValueError('selector raw archive differs')
    raw = read_member(archive, manifest, ticker.encode().hex() + '.bars.parquet')
    if sha(raw) != reference['raw_sha256']:
        raise ValueError('selector raw member differs')
    packet = checked(dict(release=reference['release'], asset=reference['asset'],
                          sha256=reference['answer_container_sha256']), source / 'packet')
    features = active_dispatch()
    evidence = runtime_evidence()
    state = dict(format='PRICE_PIT_DISPATCH_SELECTOR_STOCK_V1', request=request, ticker=ticker, role=role,
        runtime=evidence, source_commit=os.environ.get('GITHUB_SHA', ''), records=[], unmeasured=[])
    for profile in PROFILES:
        if profile == 'avx512_off' and not [f for f in features if f.startswith('AVX512')]:
            state['vacuous'] = dict(profile=profile, reason='VACUOUS_NO_AVX512_ON_RUNNER')
            continue
        env = profile_env(profile, features)
        reps = repetitions_for(request, role, profile)
        for ordinal in range(1, reps + 1):
            own = root / 'processes' / f"{ticker.encode().hex()}-{profile}-{ordinal}"
            own.mkdir(parents=True, exist_ok=True)
            try:
                (own / 'bars.parquet').write_bytes(raw)
                shutil.copyfile(calendar, own / 'market_sessions.parquet')
                shutil.copyfile(packet, own / 'reference.packet')
                config = dict(ticker=ticker, bars_sha256=reference['raw_sha256'],
                    calendar_sha256=plan['calendar_sha256'], packet_sha256=reference['answer_container_sha256'],
                    expected_query_rows=reference['query_rows'], registry_path=str(registry.resolve()),
                    registry_sha256=plan['registry']['sha256'], price_fields=plan['price_fields'],
                    prefix_cuts=plan['prefix_cuts'],
                    recipe_fingerprint=plan['frozen_build_request']['corrected_recipe_fingerprint'],
                    input_manifest_sha256=plan['frozen_build_request']['inputs_sha256'])
                (own / 'WORKER.json').write_bytes(encoded(config))
                outcome = limited_process([sys.executable, '-m', 'ci.price_full_cohort_pit', 'worker',
                    '--directory', str(own.resolve()), '--recipe', str(recipe.resolve())], own, 1200, env=env)
                if outcome['returncode']:
                    raise RuntimeError(str(outcome['reason']) + ':' + outcome['log_tail'])
                path = own / 'STOCK_PRICE_PIT_V1.json.gz'
                with gzip.open(path, 'rt', encoding='utf-8') as stream:
                    stock = json.load(stream)
                validate_stock(stock, plan, reference)
                destination = root / f"{ticker.encode().hex()}.{profile}.rep{ordinal}.pit.json.gz"
                shutil.copyfile(path, destination)
                state['records'].append(dict(ticker=ticker, role=role, profile=profile, repetition=ordinal,
                    asset=destination.name, sha256=sha(destination.read_bytes()), summary=summarize(stock)))
                print('PRICE_PIT_DISPATCH_SELECTOR_REPEAT', ticker, role, profile, ordinal,
                      stock['packet_replay_gate'], flush=True)
            except Exception as exc:
                state['unmeasured'].append(dict(ticker=ticker, role=role, profile=profile,
                    repetition=ordinal, reason=describe_failure(exc)[-4000:]))
    expected = sum(repetitions_for(request, role, p) for p in PROFILES)
    if state.get('vacuous'):
        expected -= repetitions_for(request, role, state['vacuous']['profile'])
    state['measurement'] = 'MEASURED' if len(state['records']) == expected and not state['unmeasured'] else 'PARTIAL_SELECTOR'
    file = root / f"{ticker.encode().hex()}.selector.json"
    file.write_bytes(encoded(state))
    print('PRICE_PIT_DISPATCH_SELECTOR_STOCK', ticker, state['measurement'], flush=True)
    if state['unmeasured']:
        raise ValueError('dispatch selector has explicit unmeasured repetitions')


def finalize(root):
    """Aggregate per-ticker evidence, publish the selector verdict; no overclaim."""
    from ci.release_assets import gh_retry, publish_assets
    request = validate_request(json.loads((ROOT / REQUEST).read_bytes()))
    if request['execute'] is not True:
        raise ValueError('dispatch selector execution disabled')
    plan, refs = load_plan(root, request)
    observed = load_observed(root, request, plan, refs)
    tickers = request_tickers(request, 'counterexamples') + request_tickers(request, 'controls')
    records, unmeasured, runtimes, vacuous = [], [], {}, {}
    for ticker in tickers:
        file = root / f"{ticker.encode().hex()}.selector.json"
        state = json.loads(file.read_bytes())
        if state['ticker'] != ticker or state['request'] != request:
            raise ValueError('selector stock evidence differs from the declared request')
        records.extend(state['records'])
        unmeasured.extend(state['unmeasured'])
        runtimes[ticker] = state['runtime']
        if state.get('vacuous'):
            vacuous[ticker] = state['vacuous']
        for record in state['records']:
            shard = root / record['asset']
            if sha(shard.read_bytes()) != record['sha256']:
                raise ValueError('selector stock shard bytes differ: ' + record['asset'])
    comparisons = []
    for ticker in tickers:
        role = role_for(request, ticker)
        results = [r for r in records if r['ticker'] == ticker]
        comparisons.append(comparison(ticker, role, observed[ticker], results))
    tag = tag_for('dispatch-selector')
    create_release(tag, 'Dispatch-selector diagnostic only: unchanged frozen worker, three counterexamples plus three PASS controls, two recorded profiles. No source rewrite, no quarantine mutation, no scoring approval.')
    state = dict(format='PRICE_PIT_DISPATCH_SELECTOR_V1', request=request, runtimes=runtimes,
        source_commit=os.environ.get('GITHUB_SHA', ''), records=records, comparisons=comparisons,
        unmeasured=unmeasured, vacuous=vacuous, scoring_gate='CLOSED',
        full_cohort_measurement='NOT_EVALUATED_BY_THIS_DIAGNOSTIC')
    state['selector'] = verdict(comparisons)
    expected_records = sum(repetitions_for(request, role_for(request, t), p) for t in tickers for p in PROFILES)
    expected_records -= sum(repetitions_for(request, role_for(request, t), v['profile']) for t, v in vacuous.items())
    state['measurement'] = 'MEASURED_SELECTOR_SIX_NAMES' if len(records) == expected_records and not unmeasured else 'PARTIAL_SELECTOR'
    file = root / 'PRICE_PIT_DISPATCH_SELECTOR_V1.json'
    file.write_bytes(encoded(state))
    publish_assets(tag, ROOT / REQUEST, file, *[root / r['asset'] for r in records])
    gh_retry('release', 'edit', tag, '--draft=false')
    print('PRICE_PIT_DISPATCH_SELECTOR_RESULT', state['measurement'], json.dumps(state['selector']), flush=True)
    if unmeasured:
        raise ValueError('dispatch selector has explicit unmeasured repetitions')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['ticker', 'finalize'])
    parser.add_argument('--directory', required=True)
    parser.add_argument('--ticker')
    args = parser.parse_args()
    root = Path(args.directory).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if args.mode == 'ticker':
        if not args.ticker:
            raise ValueError('ticker mode requires --ticker')
        run_ticker(root, args.ticker)
    else:
        finalize(root)

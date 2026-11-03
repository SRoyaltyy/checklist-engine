"""Default-runtime repetition of three observed price packet counterexamples.

This diagnostic neither replaces the full-cohort measurement nor rewrites any
source packet. Equality concerns reported difference signatures, not a claim
that every recomputed numeric value is identical across processes or hosts.
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

REQUEST = 'ci/PRICE_PIT_COUNTEREXAMPLE_REPLAY_REQUEST.json'
NAMES = ['AQMS', 'AZIO', 'BYRN']


def validate_request(request):
    if (request.get('version') != 1 or type(request.get('execute')) is not bool
            or request.get('repetitions') != 2
            or [r['ticker'] for r in request['observed_proofs']] != NAMES
            or request['worker_commit'] != '8003fb7906c3bf86d88612495664e597de1c65ae'
            or request['worker_lf_sha256'] != 'd48f918fe27bbdab5df56d4408d74284deba47406b323a138dfd459fa3cddbc2'
            or request['plan']['sha256'] != '18e12eed42099647d598931868547c85f99731b14b6f6138fece0fd87a43043d'):
        raise ValueError('counterexample diagnostic scope or frozen worker differs')
    return request


def signature(stock):
    return sha(encoded(stock['packet_replay']))


def comparison(ticker, reference, repeats):
    if reference['ticker'] != ticker or any(s['ticker'] != ticker for s in repeats):
        raise ValueError('counterexample repetition ticker differs')
    signatures = [signature(s) for s in repeats]
    return dict(ticker=ticker, repetitions=len(repeats), observed_signature=signature(reference),
        repeated_reported_signatures=signatures,
        reported_signatures_stable_same_runner=len(repeats) == 2 and len(set(signatures)) == 1,
        matches_original_reported_signature=[s == signature(reference) for s in signatures],
        repeated_different_cells=[sum(r['different_cells'] for r in s['packet_replay']) for s in repeats],
        repeated_missing_differences=[sum(r['missing_differences'] for r in s['packet_replay']) for s in repeats],
        prefix_gates=[s['prefix_gate'] for s in repeats], alignment_gates=[s['alignment_gate'] for s in repeats],
        scope='REPORTED_DIFFERENCE_SIGNATURES_ONLY_NOT_ALL_NUMERIC_OR_ANSWER_BITS', cause='NOT_PROVEN')


def run(root):
    from ci.compact_world_build import limited_process, snapshot
    from ci.native_price_blocks import read_member
    from ci.release_assets import describe_failure, download_asset, gh_retry, publish_assets
    request = validate_request(json.loads((ROOT / REQUEST).read_bytes()))
    if request['execute'] is not True:
        raise ValueError('counterexample diagnostic execution disabled')
    if any(os.environ.get(k) for k in ('NPY_DISABLE_CPU_FEATURES', 'OPENBLAS_CORETYPE')):
        raise ValueError('diagnostic must retain default arithmetic/CPU dispatch')
    worker = ROOT / 'ci/price_full_cohort_pit.py'
    if sha(worker.read_bytes().replace(b'\r\n', b'\n')) != request['worker_lf_sha256']:
        raise ValueError('diagnostic worker changed from the actual full run')
    plan = json.loads(checked(request['plan'], root / 'plan').read_bytes())
    refs = {r['ticker']: r for r in plan['references']}
    observed = {}
    for binding in request['observed_proofs']:
        path = checked(binding, root / 'observed')
        with gzip.open(path, 'rt', encoding='utf-8') as stream:
            stock = json.load(stream)
        validate_stock(stock, plan, refs[binding['ticker']])
        if stock['packet_replay_gate'] != 'FAIL':
            raise ValueError('predeclared observed proof is not a counterexample')
        observed[binding['ticker']] = stock
    recipe, calendar = snapshot(root / 'snapshot', plan['frozen_build_request'])
    registry = checked(plan['registry'], root / 'registry')
    if sha(calendar.read_bytes()) != plan['calendar_sha256']:
        raise ValueError('diagnostic calendar differs')
    runtime = dict(python=sys.version,
        numpy_runtime=subprocess.check_output([sys.executable, '-c', 'import numpy as np; np.show_runtime()'], text=True),
        lscpu=json.loads(subprocess.check_output(['lscpu', '-J'], text=True)),
        cpu_dispatch_overrides={k: os.environ.get(k) for k in ('NPY_DISABLE_CPU_FEATURES', 'OPENBLAS_CORETYPE')})
    tag = tag_for('counterexample-replay')
    create_release(tag, 'Three-name default-runtime diagnostic only. Two clean processes per name; unchanged frozen worker/math/sources. No protected mutation or scoring approval.')
    state = dict(format='PRICE_PIT_COUNTEREXAMPLE_REPLAY_V1', request=request, runtime=runtime,
        source_commit=os.environ['GITHUB_SHA'], records=[], comparisons=[], unmeasured=[],
        cause='NOT_PROVEN', full_cohort_measurement='NOT_EVALUATED_BY_THIS_DIAGNOSTIC', scoring_gate='CLOSED')
    publish_assets(tag, ROOT / REQUEST)
    for ticker in NAMES:
        reference = refs[ticker]
        part, = [p for p in plan['source_parts'] if ticker in p['tickers']]
        source = root / 'sources' / ticker.encode().hex()
        manifest = json.loads(download_asset(part['release'], part['part'] + '.json', source).read_bytes())
        archive = download_asset(part['release'], part['part'] + '.tar', source)
        if manifest['archive_sha256'] != part['archive_sha256'] or sha(archive.read_bytes()) != part['archive_sha256']:
            raise ValueError('diagnostic raw archive differs')
        raw = read_member(archive, manifest, ticker.encode().hex() + '.bars.parquet')
        if sha(raw) != reference['raw_sha256']:
            raise ValueError('diagnostic raw member differs')
        packet = checked(dict(release=reference['release'], asset=reference['asset'],
                              sha256=reference['answer_container_sha256']), source / 'packet')
        repeats = []
        for ordinal in range(1, 3):
            own = root / 'processes' / f'{ticker.encode().hex()}-{ordinal}'
            own.mkdir(parents=True, exist_ok=True)
            assets = []
            try:
                (own / 'bars.parquet').write_bytes(raw)
                shutil.copyfile(calendar, own / 'market_sessions.parquet')
                shutil.copyfile(packet, own / 'reference.packet')
                config = dict(ticker=ticker, bars_sha256=reference['raw_sha256'],
                    calendar_sha256=plan['calendar_sha256'], packet_sha256=reference['answer_container_sha256'],
                    expected_query_rows=reference['query_rows'], registry_path=str(registry.resolve()),
                    registry_sha256=plan['registry']['sha256'], price_fields=plan['price_fields'],
                    prefix_cuts=plan['prefix_cuts'], recipe_fingerprint=plan['frozen_build_request']['corrected_recipe_fingerprint'],
                    input_manifest_sha256=plan['frozen_build_request']['inputs_sha256'])
                (own / 'WORKER.json').write_bytes(encoded(config))
                outcome = limited_process([sys.executable, '-m', 'ci.price_full_cohort_pit', 'worker',
                    '--directory', str(own.resolve()), '--recipe', str(recipe.resolve())], own, 1200)
                if outcome['returncode']:
                    raise RuntimeError(str(outcome['reason']) + ':' + outcome['log_tail'])
                path = own / 'STOCK_PRICE_PIT_V1.json.gz'
                with gzip.open(path, 'rt', encoding='utf-8') as stream:
                    stock = json.load(stream)
                validate_stock(stock, plan, reference)
                destination = root / f'{ticker.encode().hex()}.repeat{ordinal}.pit.json.gz'
                shutil.copyfile(path, destination)
                assets.append(destination)
                repeats.append(stock)
                state['records'].append(dict(ticker=ticker, repetition=ordinal, asset=destination.name,
                    sha256=sha(destination.read_bytes()), reported_signature=signature(stock),
                    packet_replay_gate=stock['packet_replay_gate']))
                print('PRICE_PIT_COUNTEREXAMPLE_REPEAT', ticker, ordinal, stock['packet_replay_gate'], flush=True)
            except Exception as exc:
                state['unmeasured'].append(dict(ticker=ticker, repetition=ordinal, reason=describe_failure(exc)[-4000:]))
            checkpoint = root / f"checkpoint_{len(state['records']) + len(state['unmeasured']):03d}.json"
            checkpoint.write_bytes(encoded(state))
            publish_assets(tag, *assets, checkpoint)
        state['comparisons'].append(comparison(ticker, observed[ticker], repeats))
    state['measurement'] = 'MEASURED_DIAGNOSTIC_THREE_NAMES' if len(state['records']) == 6 and not state['unmeasured'] else 'PARTIAL_DIAGNOSTIC'
    file = root / 'PRICE_PIT_COUNTEREXAMPLE_REPLAY_V1.json'
    file.write_bytes(encoded(state))
    publish_assets(tag, file)
    gh_retry('release', 'edit', tag, '--draft=false')
    print('PRICE_PIT_COUNTEREXAMPLE_RESULT', state['measurement'], json.dumps(state['comparisons']), flush=True)
    if state['unmeasured']:
        raise ValueError('counterexample diagnostic has explicit unmeasured repetitions')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True)
    args = parser.parse_args()
    root = Path(args.directory).resolve()
    root.mkdir(parents=True, exist_ok=True)
    run(root)

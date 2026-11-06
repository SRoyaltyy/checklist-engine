"""GHA-only price-column proof; reuse full PIT evidence and probe frozen math."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / 'ci/PRICE_COLUMN_AVAILABILITY_REQUEST.json'
CONTROLS = ['BPOP', 'DJCO', 'KGRN']
CUTS = ['2023-01-03', '2025-01-02']
SUMMARY_SHA = '7846682fe8297ed0e77218e487ef064a2e2cc6efa37ada4de0520e055f09ccc2'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def require_runner():
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('GITHUB_REPOSITORY') != 'SRoyaltyy/checklist-engine':
        raise ValueError('real price probes run only on the authorized GitHub runner')


def validate_request(request):
    from world_price_availability import PLAN_SHA, REPORT_SHA, FIELDS_SHA, RECIPE, CALENDAR_SHA
    expected = dict(version=1, controls=CONTROLS, prefix_cuts=CUTS,
        base_plan_sha256=PLAN_SHA, measured_report_sha256=REPORT_SHA,
        source_fields_sha256=FIELDS_SHA, recipe_fingerprint=RECIPE,
        calendar_sha256=CALENDAR_SHA, expected_names=8439, expected_query_rows=12547288,
        expected_columns=22968)
    if (type(request.get('execute')) is not bool
            or {k: v for k, v in request.items() if k != 'execute'} != expected):
        raise ValueError('price-column probe changes the exact measured source or declared controls')
    return request


def source_bundle(root):
    """Fresh full-cohort metadata authentication; no stock feature recalculation."""
    from ci import release_assets as io
    from ci.price_full_cohort_pit import checked
    from ci.price_full_cohort_pit_readback import INPUT_RELEASE, PLAN_SHA, REPORT, COVERAGE, EVIDENCE
    from ci.price_pit_recovery_readback import (RUN, RECOVERY_INPUTS, RECOVERY_PLAN,
        RECOVERY_SHA, SUMMARY, read_recovery_bundle)
    from world_price_availability import REPORT_SHA
    root.mkdir(parents=True, exist_ok=True)
    def body(tag, name, pin, destination=root):
        path = checked(dict(release=tag, asset=name, sha256=pin), root / 'downloads')
        destination.mkdir(parents=True, exist_ok=True)
        target = destination / name
        shutil.copyfile(path, target)
        return target
    base = json.loads(body(INPUT_RELEASE, 'PRICE_FULL_COHORT_PIT_PLAN_V1.json', PLAN_SHA).read_bytes())
    measured = f'price-full-cohort-pit-v1-{RUN}-1-measured'
    report = json.loads(body(measured, REPORT, REPORT_SHA).read_bytes())
    summary = json.loads(body(measured, SUMMARY, SUMMARY_SHA).read_bytes())
    body(RECOVERY_INPUTS, RECOVERY_PLAN, RECOVERY_SHA)
    for name in (COVERAGE, EVIDENCE):
        body(measured, name, report['evidence'][name]['sha256'])
    for row in summary['part_receipts']:
        body(row['release'], row['asset'], row['sha256'], root / 'receipts' / str(row['index']))
    tags = [INPUT_RELEASE.removesuffix('-inputs') + '-smoke']
    tags += [INPUT_RELEASE.removesuffix('-inputs') + f'-{i:03d}' for i in range(len(base['work_parts']))]
    tags += [INPUT_RELEASE, RECOVERY_INPUTS, measured]
    inventories = []
    for tag in tags:
        release = io.release_info(tag)
        assets = io.asset_index(tag)
        if release['draft'] or release['tag_name'] != tag:
            raise ValueError('source proof release is not public')
        inventories.append(dict(id=release['id'], tag_name=tag, draft=False,
            assets=[{k: asset[k] for k in ('name', 'state', 'size', 'digest')}
                    for asset in assets.values()]))
    (root / 'PUBLIC_SOURCE_INVENTORIES.json').write_bytes(encoded(inventories))
    result = read_recovery_bundle(root, inventories)
    if result['bundle']['alignment_gate'] != 'PASS' or result['bundle']['prefix_gate'] != 'PASS':
        raise ValueError('source price clocks are not proven on the retained cohort')
    (root / 'SOURCE_PRICE_PIT_READBACK_V1.json').write_bytes(encoded(result))
    return base, result


def worker(root, recipe):
    require_runner()
    sys.path[:0] = [str(recipe.resolve()), str(ROOT)]
    import numpy as np
    import pandas as pd
    import facets_world as fw
    import world_timeframes as wt
    from ci.price_full_cohort_pit import matrix_diff
    from world_price_availability import PriceColumnView, load_contract
    if any(Path(module.__file__).resolve().parent != recipe.resolve() for module in (fw, wt)):
        raise ValueError('column probe loaded unbound price math')
    config = json.loads((root / 'WORKER.json').read_bytes())
    for name, key in (('bars.parquet', 'raw_sha256'), ('market_sessions.parquet', 'calendar_sha256')):
        if digest((root / name).read_bytes()) != config[key]:
            raise ValueError('column probe source bytes differ')
    bars = pd.read_parquet(root / 'bars.parquet')
    calendar = pd.DatetimeIndex(pd.read_parquet(root / 'market_sessions.parquet').date).as_unit('ns')
    query = calendar[(calendar >= pd.Timestamp('2020-01-01')) & calendar.isin(pd.DatetimeIndex(bars.date))]
    if not len(query) or len(query) != config['query_rows']:
        raise ValueError('column probe setup-day membership differs')
    fields = list(load_contract().fields)
    funcs = fw.discover()
    checks = []
    for tf in wt.TIMEFRAMES:
        native = wt.completed_candles(bars, tf, session_calendar=calendar)
        features = wt.candle_features(native, funcs, timeframe=tf)
        if not len(features):
            features = features.reindex(columns=[*fields, 'available_from'])
        view = PriceColumnView(native, features, tf, calendar)
        aligned = view.align(query)
        names = [field + '__' + tf for field in fields]
        original = wt.align_features(query, features, tf).reindex(columns=names)
        comparison = matrix_diff(original.to_numpy(dtype='float64'), aligned.values[names].to_numpy(), fields)
        if comparison['different_cells']:
            raise ValueError('guarded price-column reads change frozen numeric values')
        sample_rows = sorted({0, len(query) // 2, len(query) - 1})
        # Exercise every column's public value/clock pair, including warmups.
        for field in fields:
            column = aligned.column(field).iloc[sample_rows]
            known = column.value.notna()
            if (column.available_from.notna() != known).any() or (column.source_candle_end.notna() != known).any():
                raise ValueError('column value and explicit clock masks differ')
            if ((column.available_from[known] > column.date[known])
                    | (column.source_candle_end[known] >= column.date[known])).any():
                raise ValueError('column read exposes a source not known before setup open')
        cuts = []
        for literal in CUTS:
            cut = pd.Timestamp(literal)
            if cut not in calendar:
                raise ValueError('declared leak cut is outside the bound calendar')
            expected = view.align(pd.DatetimeIndex([cut])).values[names].to_numpy()
            prefix = wt.completed_candles(bars[bars.date < cut], tf, session_calendar=calendar[calendar <= cut])
            short = wt.candle_features(prefix, funcs, timeframe=tf)
            if not len(short):
                short = short.reindex(columns=[*fields, 'available_from'])
            rebuilt = PriceColumnView(prefix, short, tf, calendar).align(pd.DatetimeIndex([cut]))
            prefix_diff = matrix_diff(expected, rebuilt.values[names].to_numpy(), fields)
            altered = bars.copy()
            altered.loc[altered.date >= cut, list(wt.PRICE_COLS)] *= 1.5
            future_native = wt.completed_candles(altered, tf, session_calendar=calendar)
            future = wt.candle_features(future_native, funcs, timeframe=tf)
            if not len(future):
                future = future.reindex(columns=[*fields, 'available_from'])
            poisoned = PriceColumnView(future_native, future, tf, calendar).align(pd.DatetimeIndex([cut]))
            future_diff = matrix_diff(expected, poisoned.values[names].to_numpy(), fields)
            if prefix_diff['different_cells'] or future_diff['different_cells']:
                raise ValueError('price-column prefix or future perturbation leak: ' + tf + '/' + literal)
            cuts.append(dict(cut=literal, columns=len(fields), prefix=prefix_diff, future_perturbation=future_diff))
        checks.append(dict(timeframe=tf, native_rows=len(native), columns=len(fields),
                           query_rows=len(query), clock_pair_checks=len(fields) * len(sample_rows),
                           exact_alignment=comparison, cuts=cuts))
        print('PRICE_COLUMN_CLOCK_PROBE', config['ticker'], tf, len(fields), flush=True)
    result = dict(status='PASS_FROZEN_PRICE_COLUMN_CLOCKS_AND_LEAK_TRAPS', ticker=config['ticker'],
        query_rows=len(query), columns_per_timeframe=len(fields), timeframes=list(wt.TIMEFRAMES),
        column_bindings=len(fields) * len(wt.TIMEFRAMES), checks=checks,
        raw_sha256=config['raw_sha256'], calendar_sha256=config['calendar_sha256'],
        columns_lf_sha256=load_contract().columns_sha256,
        runtime=dict(python=sys.version, numpy=np.__version__, pandas=pd.__version__, talib=fw.talib.__version__),
        scoring_gate='CLOSED')
    (root / 'PRICE_COLUMN_STOCK_PROBE_V1.json').write_bytes(encoded(result))


def run(root):
    require_runner()
    from ci import release_assets as io
    from ci.price_pit_missing_recovery import worker_unchanged
    from ci.compact_world_build import snapshot, limited_process
    from ci.native_price_blocks import read_member
    from world_price_availability import load_contract
    root.mkdir(parents=True, exist_ok=True)
    request = validate_request(json.loads(REQUEST.read_bytes()))
    if request['execute'] is not True:
        raise ValueError('price-column runner probe is disabled')
    worker_unchanged()
    base, source_audit = source_bundle(root / 'source-audit')
    recipe, calendar = snapshot(root / 'snapshot', base['frozen_build_request'])
    references = {row['ticker']: row for row in base['references']}
    results, errors = [], []
    for ticker in CONTROLS:
        reference = references[ticker]
        part, = [part for part in base['source_parts'] if ticker in part['tickers']]
        raw_root = root / 'raw' / digest((part['release'] + '\n' + part['part']).encode())
        try:
            manifest = json.loads(io.download_asset(part['release'], part['part'] + '.json', raw_root).read_bytes())
            archive = io.download_asset(part['release'], part['part'] + '.tar', raw_root)
            if (manifest['archive_sha256'] != part['archive_sha256']
                    or digest(archive.read_bytes()) != part['archive_sha256']):
                raise ValueError('column probe raw archive differs')
            raw = read_member(archive, manifest, ticker.encode().hex() + '.bars.parquet')
            if digest(raw) != reference['raw_sha256']:
                raise ValueError('column probe raw member differs')
            own = root / 'stocks' / ticker.encode().hex()
            own.mkdir(parents=True, exist_ok=True)
            (own / 'bars.parquet').write_bytes(raw)
            shutil.copyfile(calendar, own / 'market_sessions.parquet')
            config = dict(ticker=ticker, raw_sha256=reference['raw_sha256'],
                          calendar_sha256=base['calendar_sha256'], query_rows=reference['query_rows'])
            (own / 'WORKER.json').write_bytes(encoded(config))
            outcome = limited_process([sys.executable, '-m', 'ci.price_column_availability_probe',
                'worker', '--directory', str(own.resolve()), '--recipe', str(recipe.resolve())], own, 900)
            if outcome['returncode'] != 0:
                raise RuntimeError(str(outcome['reason']) + ':' + outcome['log_tail'])
            result = json.loads((own / 'PRICE_COLUMN_STOCK_PROBE_V1.json').read_bytes())
            validate_result(result, ticker, reference['query_rows'], reference['raw_sha256'])
            results.append(result)
        except Exception as exc:
            errors.append(dict(ticker=ticker, reason=io.describe_failure(exc)[-4000:]))
        print('PRICE_COLUMN_CONTROL_RESULT', ticker, len(results), len(errors), flush=True)
    passed = not errors and [row['ticker'] for row in results] == CONTROLS
    proof = dict(format='PRICE_COLUMN_AVAILABILITY_PROOF_V1',
        status='PASS_PRICE_COLUMN_CONTRACT_AND_DECLARED_LEAK_TRAPS' if passed else 'FAIL',
        actual_run_id=os.environ['GITHUB_RUN_ID'], actual_attempt=os.environ['GITHUB_RUN_ATTEMPT'],
        source_commit=os.environ['GITHUB_SHA'], columns_lf_sha256=load_contract().columns_sha256,
        contract_metadata_sha256=load_contract().metadata_sha256,
        produced_fields=1044, native_timeframes=22, explicit_column_bindings=22968,
        source_cohort_readback=source_audit, controls=results, errors=errors,
        scope='Full retained-source metadata/clock evidence; new frozen-math leak probes on BPOP,DJCO,KGRN, all produced columns and declared cuts.',
        world_gate='NOT_PROVEN', scoring_gate='CLOSED', protected_source_mutations='NONE')
    file = root / 'PRICE_COLUMN_AVAILABILITY_PROOF_V1.json'
    file.write_bytes(encoded(proof))
    shutil.copyfile(root / 'source-audit/SOURCE_PRICE_PIT_READBACK_V1.json', root / 'SOURCE_PRICE_PIT_READBACK_V1.json')
    artifacts = [file, root / 'SOURCE_PRICE_PIT_READBACK_V1.json']
    for name in ('PRICE_COLUMN_AVAILABILITY_V1.json', 'PRICE_COLUMN_AVAILABILITY_V1.csv'):
        target = root / name
        shutil.copyfile(ROOT / 'dictionary' / name, target)
        artifacts.append(target)
    tag = f"price-column-availability-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    io.gh_retry('release', 'create', tag, '--draft', '--target', os.environ['GITHUB_SHA'],
        '--title', tag, '--notes', 'Explicit produced-price column clocks and declared leak tests. Frozen source preserved; scoring CLOSED.')
    io.publish_assets(tag, *artifacts)
    io.gh_retry('release', 'edit', tag, '--draft=false')
    if not passed:
        raise ValueError('price-column proof retains failed or missing controls')


def validate_result(result, ticker, query_rows, raw_sha):
    from world_price_availability import TIMEFRAMES, CALENDAR_SHA, load_contract
    if (result['status'] != 'PASS_FROZEN_PRICE_COLUMN_CLOCKS_AND_LEAK_TRAPS'
            or result['ticker'] != ticker or result['query_rows'] != query_rows
            or result['columns_per_timeframe'] != 1044 or result['column_bindings'] != 22968
            or result['timeframes'] != list(TIMEFRAMES) or result['raw_sha256'] != raw_sha
            or result['calendar_sha256'] != CALENDAR_SHA
            or result['columns_lf_sha256'] != load_contract().columns_sha256
            or result['scoring_gate'] != 'CLOSED'
            or [row['timeframe'] for row in result['checks']] != list(TIMEFRAMES)):
        raise ValueError('incomplete or differently bound price-column control')
    for row in result['checks']:
        if (row['columns'] != 1044 or row['query_rows'] != query_rows
                or type(row['native_rows']) is not int or row['native_rows'] < 0
                or row['clock_pair_checks'] != 1044 * min(3, query_rows)
                or [c['cut'] for c in row['cuts']] != CUTS):
            raise ValueError('price-column control omitted fields, rows or cuts')
        comparisons = [(row['exact_alignment'], query_rows * 1044)]
        for cut in row['cuts']:
            if cut['columns'] != 1044:
                raise ValueError('price-column leak cut omitted fields')
            comparisons.extend([(cut['prefix'], 1044), (cut['future_perturbation'], 1044)])
        for comparison, cells in comparisons:
            if (comparison['cells'] != cells or comparison['different_cells'] != 0
                    or comparison['missing_differences'] != 0 or comparison['field_differences']):
                raise ValueError('price-column control contains an exact numeric leak or partial comparison')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('run', 'worker'))
    parser.add_argument('--directory', required=True)
    parser.add_argument('--recipe')
    args = parser.parse_args()
    directory = Path(args.directory).resolve()
    if args.action == 'run':
        run(directory)
    else:
        worker(directory, Path(args.recipe))

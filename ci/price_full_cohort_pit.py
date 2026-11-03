"""Measured price PIT and published-packet replay for the complete retained cohort.

Only GitHub runners execute real-market workers. Frozen recipe/source bytes
are inputs, never rewritten. Prefix/alignment/replay failures remain evidence;
they do not authorize exclusions, altered values or scoring.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
REQUEST = 'ci/PRICE_FULL_COHORT_PIT_REQUEST.json'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def write_gzip(path, value):
    with Path(path).open('wb') as target:
        with gzip.GzipFile(filename='', fileobj=target, mode='wb', mtime=0) as stream:
            stream.write(encoded(value))


def matrix_diff(left, right, fields):
    """Exact known-value bits, with missing distinct; no tolerance or coercion to NO."""
    import numpy as np
    a, b = np.asarray(left, dtype='float64'), np.asarray(right, dtype='float64')
    if a.shape != b.shape or a.ndim != 2 or a.shape[1] != len(fields):
        raise ValueError('PIT matrix/schema shape differs')
    ka, kb = ~np.isnan(a), ~np.isnan(b)
    missing = ka != kb
    changed = missing | (ka & kb & (a.view(np.uint64) != b.view(np.uint64)))
    columns = np.flatnonzero(changed.any(axis=0))
    return dict(cells=int(a.size), different_cells=int(changed.sum()),
                missing_differences=int(missing.sum()), field_differences=[
                    dict(field=fields[int(c)], different_cells=int(changed[:, c].sum()),
                         missing_differences=int(missing[:, c].sum()),
                         example_rows=np.flatnonzero(changed[:, c])[:5].tolist()) for c in columns])


def aligned_coverage(query, native, full, fields, tf, align):
    """Compare the production alignment with an independent past-only index lookup."""
    import numpy as np
    import pandas as pd
    if len(native) != len(full):
        raise ValueError('native candle/feature rows differ')
    availability = pd.DatetimeIndex(full.available_from).as_unit('ns')
    if availability.has_duplicates or not availability.is_monotonic_increasing or availability.hasnans:
        raise ValueError('native availability is not unique, ordered and known')
    end = pd.DatetimeIndex(native.date).as_unit('ns')
    native_late = int((end.asi8 >= availability.asi8).sum())
    indices = availability.searchsorted(query, side='right') - 1
    present = indices >= 0
    expected = np.full((len(query), len(fields)), np.nan, dtype='float64')
    if present.any():
        expected[present] = full[fields].to_numpy(dtype='float64')[indices[present]]
    aligned = align(query, full, tf)
    if not pd.DatetimeIndex(aligned.date).as_unit('ns').equals(query):
        raise ValueError('aligned setup-date keys changed')
    columns = [f'{f}__{tf}' for f in fields]
    actual = aligned.reindex(columns=columns).to_numpy(dtype='float64')
    comparison = matrix_diff(expected, actual, fields)
    selected_late = int(((availability.asi8[indices[present]] > query.asi8[present]) |
                         (end.asi8[indices[present]] >= query.asi8[present])).sum()) if present.any() else 0
    known = ~np.isnan(actual)
    counts = known.sum(axis=0)
    finite = np.isfinite(actual).sum(axis=0)
    infinite = np.isinf(actual).sum(axis=0)
    no_stamp = known[~present].sum(axis=0)
    coverage = []
    for i, field in enumerate(fields):
        dates = query[known[:, i]]
        coverage.append(dict(timeframe=tf, field=field, query_rows=len(query),
            known=int(counts[i]), finite=int(finite[i]), infinite=int(infinite[i]),
            missing=len(query) - int(counts[i]), known_without_source=int(no_stamp[i]),
            first_known_setup=str(dates[0].date()) if len(dates) else '',
            last_known_setup=str(dates[-1].date()) if len(dates) else ''))
    check = dict(timeframe=tf, native_rows=len(full), native_end_not_before_availability=native_late,
                 selected_source_not_before_setup=selected_late, **comparison)
    return coverage, check


def diagnostic_answers(full, query, tf, align):
    """Reproduce the existing #203 predicates on native bars before alignment."""
    import numpy as np
    import pandas as pd
    values = full.drop(columns='available_from')
    x = values.to_numpy(dtype='float64')
    result = np.empty((len(full), len(values.columns) * 3), dtype='float64')
    mean = values.rolling(20).mean()
    std = values.rolling(20).std(ddof=0)
    for j, ref in enumerate((values.shift(1), mean, mean + std)):
        right = ref.to_numpy(dtype='float64')
        valid = np.isfinite(x) & np.isfinite(right)
        result[:, j::3] = np.where(valid, x > right, np.nan)
    names = [name + ':' + facet for name in values for facet in
             ('rising1', 'above_mean20', 'above_mean_plus_sd20')]
    frame = pd.DataFrame(result, columns=names)
    frame['available_from'] = full.available_from.to_numpy()
    return align(query, frame, tf).reindex(columns=[n + '__' + tf for n in names])


def packet_replay(contents, registry, tf, expected, provenance, seen):
    import numpy as np
    from ci.price_numeric_runtime_trace import decode_codes
    differences = []
    cells = missing = changed = questions = 0
    stems = sorted(name[:-5] for name in contents if name.endswith('.json') and name.startswith(tf + '_'))
    if not stems:
        raise ValueError('published packet lacks timeframe: ' + tf)
    for stem in stems:
        meta, schema, actual = decode_codes(contents, stem, registry)
        wanted = dict(provenance, question_tree_sha256=meta['registry_sha256'])
        if (meta['provenance'] != wanted or meta['rows'] != len(expected)
                or meta['format'] != 'REGISTERED_ANSWER_BITPLANES_V1' or meta['missing_code'] != 0
                or meta['bitorder'] != 'little' or meta['codec'] != 'zstd'):
            raise ValueError('published packet row/input/mask/recipe provenance differs')
        qids = [q['question_id'] for q in schema]
        if any(q in seen or not q.endswith('__' + tf) for q in qids):
            raise ValueError('packet question repeated or attached to wrong timeframe')
        seen.update(qids)
        values = expected[qids].to_numpy(dtype='float64').T
        if (~(np.isnan(values) | (values == 0) | (values == 1))).any():
            raise ValueError('replayed predicate is not strict binary or missing')
        codes = np.where(np.isnan(values), 0, np.where(values == 0, 1, 2)).astype(np.uint8)
        delta = actual != codes
        ni = (actual == 0) != (codes == 0)
        cells += int(actual.size)
        missing += int(ni.sum())
        changed += int(delta.sum())
        questions += len(qids)
        for q in np.flatnonzero(delta.any(axis=1)):
            positions = np.flatnonzero(delta[q])
            differences.append(dict(question_id=qids[int(q)], different_cells=int(delta[q].sum()),
                missing_differences=int(ni[q].sum()), examples=[dict(query_row=int(i),
                    stored_code=int(actual[q, i]), replay_code=int(codes[q, i])) for i in positions[:5]]))
    return dict(timeframe=tf, questions=questions, cells=cells, different_cells=changed,
                missing_differences=missing, differences=differences)


def worker(root, recipe):
    sys.path[:0] = [str(recipe.resolve()), str(ROOT)]
    import numpy as np
    import pandas as pd
    import facets_world as fw
    import world_timeframes as wt
    from ci.price_v1_sample_gate import align_prefix
    from ci.row0_part172_replay import members
    if any(Path(m.__file__).resolve().parent != recipe.resolve() for m in (fw, wt)):
        raise ValueError('full-cohort PIT loaded unbound price math')
    config = json.loads((root / 'WORKER.json').read_bytes())
    for name, key in (('bars.parquet', 'bars_sha256'), ('market_sessions.parquet', 'calendar_sha256'),
                      ('reference.packet', 'packet_sha256')):
        if sha((root / name).read_bytes()) != config[key]:
            raise ValueError('PIT worker source body differs: ' + name)
    registry_raw = Path(config['registry_path']).read_bytes()
    if sha(registry_raw) != config['registry_sha256']:
        raise ValueError('PIT registry body differs')
    registry = json.loads(registry_raw)
    contents = members((root / 'reference.packet').read_bytes())
    stems = {n[:-5] for n in contents if n.endswith('.json')}
    if set(contents) != {s + ext for s in stems for ext in ('.json', '.zst')}:
        raise ValueError('published packet member set differs')
    bars = pd.read_parquet(root / 'bars.parquet')
    calendar = pd.DatetimeIndex(pd.read_parquet(root / 'market_sessions.parquet').date).as_unit('ns')
    query = calendar[(calendar >= pd.Timestamp('2020-01-01')) & calendar.isin(pd.DatetimeIndex(bars.date))]
    if len(query) != config['expected_query_rows']:
        raise ValueError('PIT query rows differ from the actual completed rebuild')
    provenance = dict(input_manifest_sha256=config['input_manifest_sha256'],
        recipe_fingerprint=config['recipe_fingerprint'],
        row_keys_sha256=sha(config['ticker'].encode() + query.asi8.tobytes()),
        eligibility_mask_sha256=sha(np.ones(len(query), dtype=np.uint8).tobytes()))
    fields = config['price_fields']
    funcs = fw.discover()
    coverage, alignment, prefixes, replay, seen = [], [], [], [], set()
    for tf in wt.TIMEFRAMES:
        native = wt.completed_candles(bars, tf, session_calendar=calendar)
        full = wt.candle_features(native, funcs, timeframe=tf)
        if len(full) and sorted(c for c in full if c != 'available_from') != fields:
            raise ValueError('full-cohort produced field schema differs: ' + tf)
        if not len(full):
            full = full.reindex(columns=fields + ['available_from'])
        rows, check = aligned_coverage(query, native, full, fields, tf, wt.align_features)
        coverage.extend(rows)
        alignment.append(check)
        expected_answers = diagnostic_answers(full, query, tf, wt.align_features)
        replay.append(packet_replay(contents, registry, tf, expected_answers, provenance, seen))
        del expected_answers
        for literal in config['prefix_cuts']:
            cut = pd.Timestamp(literal)
            candles = wt.completed_candles(bars[bars.date < cut], tf, session_calendar=calendar[calendar <= cut])
            rebuilt = wt.candle_features(candles, funcs, timeframe=tf)
            expected = full[full.available_from <= cut].reset_index(drop=True)
            if len(rebuilt) and sorted(c for c in rebuilt if c != 'available_from') != fields:
                raise ValueError('full-cohort prefix field schema differs')
            a, b, errors = align_prefix(expected, rebuilt)
            stats = matrix_diff(a[fields].to_numpy(dtype='float64'), b[fields].to_numpy(dtype='float64'), fields) if len(a) else dict(
                cells=0, different_cells=0, missing_differences=0, field_differences=[])
            prefixes.append(dict(timeframe=tf, cut=literal, expected_rows=len(expected), rebuilt_rows=len(rebuilt),
                                 compared_rows=len(a), columns=len(fields), availability_differences=errors, **stats))
        print('FULL_PRICE_PIT_TIMEFRAME', config['ticker'], tf, len(full), flush=True)
    expected_ids = {q['question_id'] for questions in registry.values() for q in questions}
    if seen != expected_ids or sum(r['cells'] for r in replay) != len(query) * len(expected_ids):
        raise ValueError('full packet replay did not cover the complete published registry')
    prefix_failures = sum(bool(c['availability_differences'] or c['different_cells']) for c in prefixes)
    alignment_failures = sum(bool(c['native_end_not_before_availability'] or c['selected_source_not_before_setup']
                                  or c['different_cells']) for c in alignment)
    replay_differences = sum(c['different_cells'] for c in replay)
    result = dict(format='PRICE_FULL_COHORT_STOCK_PIT_V1', ticker=config['ticker'], measurement_complete=True,
        query_rows=len(query), query_dates=[str(d.date()) for d in query],
        raw_sha256=config['bars_sha256'], calendar_sha256=config['calendar_sha256'],
        packet_sha256=config['packet_sha256'], registry_sha256=config['registry_sha256'],
        recipe_fingerprint=config['recipe_fingerprint'], row_keys_sha256=provenance['row_keys_sha256'],
        coverage=coverage, alignment_checks=alignment, prefix_checks=prefixes, packet_replay=replay,
        prefix_gate='FAIL' if prefix_failures else 'PASS', alignment_gate='FAIL' if alignment_failures else 'PASS',
        packet_replay_gate='FAIL' if replay_differences else 'PASS',
        runtime=dict(python=sys.version, numpy=np.__version__, pandas=pd.__version__),
        historical_eligibility_gate='NOT_PROVEN_DIAGNOSTIC_ALL_TRUE_ENCODING_MASK_IS_NOT_TRADEABILITY',
        historical_provider_revision_gate='NOT_MEASURED', scoring_gate='CLOSED')
    write_gzip(root / 'STOCK_PRICE_PIT_V1.json.gz', result)


def checked(binding, root):
    from ci.release_assets import download_asset
    file = download_asset(binding['release'], binding['asset'], Path(root) / binding['release'])
    if sha(file.read_bytes()) != binding['sha256']:
        raise ValueError('full-cohort PIT bound input differs: ' + binding['asset'])
    return file


def create_release(tag, notes):
    from ci import release_assets as io
    repository = os.environ['GITHUB_REPOSITORY']
    if repository.lower() != 'sroyaltyy/checklist-engine' or not tag.startswith('price-full-cohort-pit-v1-'):
        raise ValueError('wrong repository or PIT output namespace')
    raw = io.gh_retry('api', f'repos/{repository}/releases', '--method', 'POST',
        '-f', 'tag_name=' + tag, '-f', 'name=' + tag, '-f', 'target_commitish=' + os.environ['GITHUB_SHA'],
        '-F', 'draft=true', '-f', 'body=' + notes)
    release = json.loads(raw)
    if release['tag_name'] != tag or not release['draft']:
        raise ValueError('new PIT release identity differs')
    io._RELEASE_IDS[(repository, tag)] = release['id']


def tag_for(suffix):
    return f"price-full-cohort-pit-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}-{suffix}"


def prepare(root):
    from ci.completed_price_world_gate import validate_registry
    from ci.release_assets import publish_assets, gh_retry, download_asset
    from world_replay_quarantine import load_policy
    request_raw = (ROOT / REQUEST).read_bytes()
    config = json.loads(request_raw)
    if config['execute'] is not True:
        raise ValueError('full-cohort PIT execution is disabled')
    source = json.loads(checked(config['source_plan'], root / 'sources').read_bytes())
    composition = json.loads(checked(config['composition'], root / 'sources').read_bytes())
    registry_file = checked(config['registry'], root / 'sources')
    registry = json.loads(registry_file.read_bytes())
    validate_registry(registry, source['request']['registry_sha256'])
    policy = load_policy()
    expected = [t for part in source['parts'] for t in part['tickers']]
    names = [r['ticker'] for r in composition['completed']]
    if (len(names) != len(set(names)) or len(names) != policy['v1_names'] or set(names) != set(expected)
            or composition['excluded'] or composition['shard_errors']
            or sum(r['query_rows'] for r in composition['completed']) != policy['v1_stock_days']
            or set(names) & {r['ticker'] for r in policy['records']}
            or config['registry']['sha256'] != source['request']['registry_sha256']
            or composition['composition']['bound_inputs']['plan'] != config['source_plan']):
        raise ValueError('PIT measurement is not the exact completed retained cohort')
    if config['prefix_cuts'] != ['2023-01-03', '2025-01-02']:
        raise ValueError('PIT cuts must be the predeclared owner-sample cuts')
    controls = set(config['smoke_names'])
    if controls != {'DJCO', 'BPOP'} or not controls <= set(names):
        raise ValueError('predeclared retained smoke controls differ')
    smoke, work = [], []
    for part in source['parts']:
        for target, take in ((smoke, True), (work, False)):
            selected = [t for t in part['tickers'] if (t in controls) == take]
            if selected:
                target.append(dict(part, tickers=selected))
    if set(t for p in smoke + work for t in p['tickers']) != set(names):
        raise ValueError('smoke and full work partition is incomplete')
    fields = sorted({q['question_id'].rsplit('__', 1)[0].rsplit(':', 1)[0]
                     for block in registry.values() for q in block})
    if len(fields) != 1044 or len(source['parts']) > 256:
        raise ValueError('PIT full field grid or matrix size differs')
    refs = [{k: row[k] for k in ('ticker', 'release', 'asset', 'answer_container_sha256',
                                 'answer_container_bytes', 'query_rows')} for row in composition['completed']]
    raw_hashes = {}
    for part in source['parts']:
        own = root / 'source-manifests' / sha((part['release'] + '\n' + part['part']).encode())
        file = download_asset(part['release'], part['part'] + '.json', own)
        manifest = json.loads(file.read_bytes())
        if manifest['archive_sha256'] != part['archive_sha256']:
            raise ValueError('PIT plan raw member archive binding differs')
        members = {r['name']: r for r in manifest['members']}
        if len(members) != len(manifest['members']):
            raise ValueError('duplicate raw member names')
        for ticker in part['tickers']:
            raw_hashes[ticker] = members[ticker.encode().hex() + '.bars.parquet']['sha256']
    for row in refs:
        row['raw_sha256'] = raw_hashes[row['ticker']]
    inputs = json.loads(checked(dict(release=source['request']['inputs_tag'], asset='BUILD_INPUTS.json',
        sha256=source['request']['inputs_sha256']), root / 'source-inputs').read_bytes())
    plan = dict(format='PRICE_FULL_COHORT_PIT_PLAN_V1', request=config,
        frozen_build_request=source['request'], source_plan=config['source_plan'],
        composition=config['composition'], registry=config['registry'],
        expected_names=sorted(names), expected_query_rows=policy['v1_stock_days'],
        source_parts=source['parts'], smoke_parts=smoke, work_parts=work, references=refs,
        price_fields=fields, timeframes=[f'{i}d' for i in range(1, 22)] + ['monthly'],
        prefix_cuts=config['prefix_cuts'], quarantine_names=sorted(r['ticker'] for r in policy['records']),
        calendar_sha256=inputs['calendar_sha256'], source_commit=os.environ['GITHUB_SHA'],
        request_sha256=sha(request_raw), scoring_gate='CLOSED')
    file = root / 'PRICE_FULL_COHORT_PIT_PLAN_V1.json'
    file.write_bytes(encoded(plan))
    tag = tag_for('inputs')
    create_release(tag, 'Predeclared complete retained-price PIT measurement plan, frozen #203 sources/recipe; no universe change or scoring approval.')
    publish_assets(tag, file, ROOT / REQUEST)
    gh_retry('release', 'edit', tag, '--draft=false')
    with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
        stream.write('inputs_release=' + tag + '\nplan_sha256=' + sha(file.read_bytes()) +
                     '\nmatrix=' + json.dumps(list(range(len(work)))) + '\n')
    print('FULL_PRICE_PIT_PREPARED', len(names), len(work), len(controls), flush=True)


def read_plan(inputs, pin, root):
    return json.loads(checked(dict(release=inputs, asset='PRICE_FULL_COHORT_PIT_PLAN_V1.json', sha256=pin), root).read_bytes())


def validate_stock(stock, plan, reference):
    grid = {(tf, field) for tf in plan['timeframes'] for field in plan['price_fields']}
    cuts = {(tf, cut) for tf in plan['timeframes'] for cut in plan['prefix_cuts']}
    if (stock.get('measurement_complete') is not True or stock['ticker'] != reference['ticker']
            or stock['query_rows'] != reference['query_rows']
            or stock['raw_sha256'] != reference['raw_sha256'] or stock['calendar_sha256'] != plan['calendar_sha256']
            or stock['packet_sha256'] != reference['answer_container_sha256']
            or stock['registry_sha256'] != plan['registry']['sha256']
            or stock['recipe_fingerprint'] != plan['frozen_build_request']['corrected_recipe_fingerprint']
            or len(stock['coverage']) != len(grid)
            or {(r['timeframe'], r['field']) for r in stock['coverage']} != grid
            or len(stock['prefix_checks']) != len(cuts)
            or {(r['timeframe'], r['cut']) for r in stock['prefix_checks']} != cuts
            or len(stock['alignment_checks']) != len(plan['timeframes'])
            or {r['timeframe'] for r in stock['alignment_checks']} != set(plan['timeframes'])
            or len(stock['packet_replay']) != len(plan['timeframes'])
            or {r['timeframe'] for r in stock['packet_replay']} != set(plan['timeframes'])
            or stock['scoring_gate'] != 'CLOSED'):
        raise ValueError('stock PIT evidence is incomplete or bound to a different source')
    for row in stock['coverage']:
        if (row['query_rows'] != reference['query_rows'] or row['known'] + row['missing'] != row['query_rows']
                or row['finite'] + row['infinite'] != row['known']
                or any(type(row[k]) is not int or row[k] < 0 for k in
                       ('query_rows', 'known', 'missing', 'finite', 'infinite', 'known_without_source'))):
            raise ValueError('stock field setup-day coverage accounting differs')
    for row in stock['prefix_checks']:
        if row['columns'] != len(plan['price_fields']) or row['cells'] != row['compared_rows'] * row['columns']:
            raise ValueError('stock prefix did not compare every produced field')
    if (sum(r['cells'] for r in stock['packet_replay']) != reference['query_rows'] * len(grid) * 3
            or any(r['questions'] != len(plan['price_fields']) * 3 or
                   r['cells'] != reference['query_rows'] * r['questions'] for r in stock['packet_replay'])):
        raise ValueError('stock packet replay is not complete')
    gates = dict(prefix_gate=any(r['availability_differences'] or r['different_cells'] for r in stock['prefix_checks']),
        alignment_gate=any(r['native_end_not_before_availability'] or r['selected_source_not_before_setup'] or r['different_cells']
                           for r in stock['alignment_checks']),
        packet_replay_gate=any(r['different_cells'] for r in stock['packet_replay']))
    if any(stock[key] != ('FAIL' if failed else 'PASS') for key, failed in gates.items()):
        raise ValueError('stock gate label contradicts its measured differences')
    import pandas as pd
    dates = pd.DatetimeIndex(pd.to_datetime(stock['query_dates'])).as_unit('ns')
    if (len(dates) != reference['query_rows'] or dates.hasnans or dates.has_duplicates or not dates.is_monotonic_increasing
            or sha(stock['ticker'].encode() + dates.asi8.tobytes()) != stock['row_keys_sha256']):
        raise ValueError('stock setup-date key proof differs')


def chunk(root, inputs, pin, index):
    import shutil
    from ci.compact_world_build import snapshot, limited_process
    from ci.native_price_blocks import read_member
    from ci.release_assets import download_asset, publish_assets, gh_retry, describe_failure
    plan = read_plan(inputs, pin, root / 'plan')
    parts = plan['smoke_parts'] if index == 'smoke' else [plan['work_parts'][int(index)]]
    wanted = [t for p in parts for t in p['tickers']]
    refs = {r['ticker']: r for r in plan['references']}
    recipe, calendar = snapshot(root / 'snapshot', plan['frozen_build_request'])
    registry = checked(plan['registry'], root / 'registry')
    calendar_sha = sha(calendar.read_bytes())
    if calendar_sha != plan['calendar_sha256']:
        raise ValueError('PIT prepared calendar differs from frozen worker snapshot')
    tag = tag_for('smoke' if index == 'smoke' else f'{int(index):03d}')
    create_release(tag, 'Complete-cohort price PIT measurements; all observed differences and unmeasured errors retained. No protected source mutation or scoring approval.')
    state = dict(format='PRICE_FULL_COHORT_PIT_CHUNK_V1', plan_sha256=pin, index=index,
                 expected_names=wanted, records=[], unmeasured=[], scoring_gate='CLOSED')
    start = time.monotonic()
    for part in parts:
        source = root / 'raw' / sha((part['release'] + '\n' + part['part']).encode())
        archive = None
        for ticker in part['tickers']:
            own = root / 'stocks' / ticker.encode().hex()
            own.mkdir(parents=True, exist_ok=True)
            try:
                if time.monotonic() - start > plan['request']['shard_budget_seconds'] - plan['request']['worker_seconds']:
                    raise TimeoutError('SHARD_WALL_BUDGET_REQUIRES_CHECKPOINT_RESUME')
                if archive is None:
                    manifest = json.loads(download_asset(part['release'], part['part'] + '.json', source).read_bytes())
                    candidate = download_asset(part['release'], part['part'] + '.tar', source)
                    if manifest['archive_sha256'] != part['archive_sha256'] or sha(candidate.read_bytes()) != part['archive_sha256']:
                        raise ValueError('PIT source archive differs')
                    archive = candidate
                raw = read_member(archive, manifest, ticker.encode().hex() + '.bars.parquet')
                if sha(raw) != refs[ticker]['raw_sha256']:
                    raise ValueError('PIT raw member differs from its prepared binding')
                (own / 'bars.parquet').write_bytes(raw)
                shutil.copyfile(calendar, own / 'market_sessions.parquet')
                reference = refs[ticker]
                packet = download_asset(reference['release'], reference['asset'], own / 'packet-source')
                if packet.stat().st_size != reference['answer_container_bytes'] or sha(packet.read_bytes()) != reference['answer_container_sha256']:
                    raise ValueError('actual completed packet differs')
                shutil.copyfile(packet, own / 'reference.packet')
                config = dict(ticker=ticker, bars_sha256=sha(raw), calendar_sha256=calendar_sha,
                    packet_sha256=reference['answer_container_sha256'], expected_query_rows=reference['query_rows'],
                    registry_path=str(registry.resolve()), registry_sha256=plan['registry']['sha256'],
                    price_fields=plan['price_fields'], prefix_cuts=plan['prefix_cuts'],
                    recipe_fingerprint=plan['frozen_build_request']['corrected_recipe_fingerprint'],
                    input_manifest_sha256=plan['frozen_build_request']['inputs_sha256'])
                (own / 'WORKER.json').write_bytes(encoded(config))
                outcome = limited_process([sys.executable, '-m', 'ci.price_full_cohort_pit', 'worker',
                    '--directory', str(own.resolve()), '--recipe', str(recipe.resolve())], own,
                    plan['request']['worker_seconds'])
                if outcome['returncode'] != 0:
                    raise RuntimeError(str(outcome['reason']) + ':' + outcome['log_tail'])
                file = own / 'STOCK_PRICE_PIT_V1.json.gz'
                with gzip.open(file, 'rt', encoding='utf-8') as stream:
                    stock = json.load(stream)
                validate_stock(stock, plan, reference)
                dest = root / (ticker.encode().hex() + '.pit.json.gz')
                shutil.copyfile(file, dest)
                publish_assets(tag, dest)
                state['records'].append(dict(ticker=ticker, release=tag, asset=dest.name,
                    sha256=sha(dest.read_bytes()), prefix_gate=stock['prefix_gate'],
                    alignment_gate=stock['alignment_gate'], packet_replay_gate=stock['packet_replay_gate']))
                print('FULL_PRICE_PIT_STOCK', ticker, stock['prefix_gate'], stock['alignment_gate'], stock['packet_replay_gate'], flush=True)
            except Exception as exc:
                state['unmeasured'].append(dict(ticker=ticker, reason=describe_failure(exc)[-4000:]))
                print('FULL_PRICE_PIT_UNMEASURED', ticker, describe_failure(exc)[-4000:], flush=True)
            checkpoint = root / f"checkpoint_{len(state['records']) + len(state['unmeasured']):04d}.json"
            checkpoint.write_bytes(encoded(state))
            publish_assets(tag, checkpoint)
            # Only this worker's generated local files, never remote/source assets.
            allowed = (root / 'stocks').resolve()
            if own.resolve() == allowed or not own.resolve().is_relative_to(allowed):
                raise ValueError('PIT generated cleanup path escapes its worker directory')
            shutil.rmtree(own)
        if archive is not None:
            archive.unlink()
    actual = [r['ticker'] for r in state['records'] + state['unmeasured']]
    if len(actual) != len(set(actual)) or set(actual) != set(wanted):
        raise ValueError('PIT chunk lost a requested name')
    file = root / 'PRICE_FULL_COHORT_PIT_CHUNK_V1.json'
    file.write_bytes(encoded(state))
    publish_assets(tag, file)
    gh_retry('release', 'edit', tag, '--draft=false')
    if state['unmeasured']:
        raise ValueError('PIT chunk has explicit unmeasured names; checkpoint and resume only those names')


class Accumulator:
    """Bounded memory: one aggregate per field/cut, never the full stock grid."""
    def __init__(self, plan):
        self.plan = plan
        self.references = {r['ticker']: r for r in plan['references']}
        self.records, self.failures = {}, []
        self.coverage, self.prefixes, self.alignment, self.replay = {}, {}, {}, {}
        self.query_rows = 0

    def add(self, stock, binding):
        ticker = stock['ticker']
        if ticker in self.records or ticker not in self.references or binding['ticker'] != ticker:
            raise ValueError('duplicate or foreign PIT stock')
        validate_stock(stock, self.plan, self.references[ticker])
        for row in stock['coverage']:
            key = (row['timeframe'], row['field'])
            total = self.coverage.setdefault(key, dict(timeframe=key[0], field=key[1], stocks=0,
                query_rows=0, known=0, finite=0, infinite=0, missing=0, known_without_source=0,
                first_known_setup='', last_known_setup=''))
            total['stocks'] += 1
            for name in ('query_rows', 'known', 'finite', 'infinite', 'missing', 'known_without_source'):
                total[name] += row[name]
            first, last = row['first_known_setup'], row['last_known_setup']
            if first:
                total['first_known_setup'] = min(first, total['first_known_setup'] or first)
                total['last_known_setup'] = max(last, total['last_known_setup'])
        specifications = (
            ('prefix_checks', self.prefixes, ('timeframe', 'cut'),
             ('expected_rows', 'rebuilt_rows', 'compared_rows', 'cells', 'different_cells', 'missing_differences')),
            ('alignment_checks', self.alignment, ('timeframe',),
             ('native_rows', 'native_end_not_before_availability', 'selected_source_not_before_setup',
              'cells', 'different_cells', 'missing_differences')),
            ('packet_replay', self.replay, ('timeframe',),
             ('questions', 'cells', 'different_cells', 'missing_differences')))
        for source, target, keys, numbers in specifications:
            for row in stock[source]:
                key = tuple(row[k] for k in keys)
                total = target.setdefault(key, dict(**{k: row[k] for k in keys}, stocks=0,
                    **{k: 0 for k in numbers}, availability_failures=0))
                total['stocks'] += 1
                for name in numbers:
                    total[name] += row[name]
                total['availability_failures'] += bool(row.get('availability_differences'))
        failed = {k: stock[k] for k in ('prefix_gate', 'alignment_gate', 'packet_replay_gate') if stock[k] != 'PASS'}
        if failed:
            self.failures.append(dict(ticker=ticker, **failed))
        self.records[ticker] = binding
        self.query_rows += stock['query_rows']

    def report(self):
        missing = sorted(set(self.plan['expected_names']) - self.records.keys())
        complete = (not missing and len(self.records) == len(self.plan['expected_names'])
                    and self.query_rows == self.plan['expected_query_rows'])
        def gate(key):
            if any(key in r for r in self.failures):
                return 'FAIL'
            return 'PASS' if complete else 'NOT_MEASURED_FULL_COHORT'
        return dict(format='PRICE_FULL_COHORT_PIT_MEASURED_V1',
            measurement='MEASURED' if complete else 'PARTIAL_NOT_MEASURED_FULL_COHORT',
            expected_names=len(self.plan['expected_names']), measured_names=len(self.records),
            expected_query_rows=self.plan['expected_query_rows'], measured_query_rows=self.query_rows,
            unmeasured_names=missing, failing_stocks=self.failures,
            fields_per_timeframe=len(self.plan['price_fields']), native_timeframes=len(self.plan['timeframes']),
            prefix_cuts=self.plan['prefix_cuts'],
            prefix_gate=gate('prefix_gate'), alignment_gate=gate('alignment_gate'),
            packet_replay_gate=gate('packet_replay_gate'),
            prefix_totals=list(self.prefixes.values()), alignment_totals=list(self.alignment.values()),
            packet_replay_totals=list(self.replay.values()),
            historical_eligibility_gate='NOT_PROVEN_DIAGNOSTIC_ALL_TRUE_ENCODING_MASK_IS_NOT_TRADEABILITY',
            historical_provider_revision_gate='NOT_MEASURED', canonical_binary_world_gate='NOT_PROVEN',
            explicit_per_column_available_from_gate='NOT_PROVEN', scoring_gate='CLOSED')


def finalize(root, inputs, pin):
    from ci import release_assets as io
    plan = read_plan(inputs, pin, root / 'plan')
    accumulator = Accumulator(plan)
    errors = []
    # Fresh inventories recover already uploaded stock proofs even after a runner
    # died before its final receipt/checkpoint. No market work is repeated here.
    partitions = [('smoke', [t for p in plan['smoke_parts'] for t in p['tickers']])]
    partitions += [(f'{i:03d}', p['tickers']) for i, p in enumerate(plan['work_parts'])]
    for suffix, names in partitions:
        tag = inputs.removesuffix('-inputs') + '-' + suffix
        try:
            inventory = io.asset_index(tag)
            io._DOWNLOAD_INVENTORIES[(os.environ['GITHUB_REPOSITORY'], tag)] = inventory
        except Exception as exc:
            errors.append(dict(release=tag, reason=io.describe_failure(exc)[-2000:]))
            continue
        for ticker in names:
            name = ticker.encode().hex() + '.pit.json.gz'
            try:
                asset = inventory.get(name)
                if not asset or not asset.get('digest', '').startswith('sha256:'):
                    raise ValueError('stock proof absent from authenticated release inventory')
                path = io.download_asset(tag, name, root / 'stock')
                with gzip.open(path, 'rt', encoding='utf-8') as stream:
                    stock = json.load(stream)
                binding = dict(ticker=ticker, release=tag, asset=name,
                               sha256=asset['digest'][7:], bytes=asset['size'])
                accumulator.add(stock, binding)
                path.unlink()
            except Exception as exc:
                errors.append(dict(ticker=ticker, release=tag, reason=io.describe_failure(exc)[-2000:]))
        print('FULL_PRICE_PIT_FINALIZE', suffix, len(accumulator.records), flush=True)
    coverage = root / 'PRICE_FULL_COHORT_SETUP_DAY_COVERAGE_V1.json.gz'
    write_gzip(coverage, list(accumulator.coverage.values()))
    evidence = root / 'PRICE_FULL_COHORT_PIT_EVIDENCE_V1.json.gz'
    write_gzip(evidence, dict(records=list(accumulator.records.values()), errors=errors))
    report = accumulator.report()
    report.update(inputs_release=inputs, plan_sha256=pin, source_commit=plan['source_commit'],
        composition=plan['composition'], frozen_recipe=plan['frozen_build_request']['corrected_recipe_fingerprint'],
        evidence={p.name: dict(sha256=sha(p.read_bytes()), bytes=p.stat().st_size) for p in (coverage, evidence)},
        per_stock_evidence_bytes=sum(r['bytes'] for r in accumulator.records.values()),
        run_id=os.environ['GITHUB_RUN_ID'], run_attempt=os.environ['GITHUB_RUN_ATTEMPT'])
    file = root / 'PRICE_FULL_COHORT_PIT_MEASURED_V1.json'
    file.write_bytes(encoded(report))
    tag = tag_for('measured')
    create_release(tag, 'Full retained-cohort price PIT measurement; observed failures and unmeasured names remain explicit. Scoring CLOSED.')
    io.publish_assets(tag, file, coverage, evidence)
    io.gh_retry('release', 'edit', tag, '--draft=false')
    print('FULL_PRICE_PIT_RESULT', report['measurement'], report['measured_names'], report['prefix_gate'],
          report['alignment_gate'], report['packet_replay_gate'], flush=True)
    if report['measurement'] != 'MEASURED':
        raise ValueError('full cohort remains unmeasured; resume only listed unmeasured_names')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'worker', 'chunk', 'finalize'))
    parser.add_argument('--directory', required=True)
    parser.add_argument('--inputs-release')
    parser.add_argument('--plan-sha256')
    parser.add_argument('--index')
    parser.add_argument('--recipe')
    args = parser.parse_args()
    root = Path(args.directory).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if args.action == 'prepare':
        prepare(root)
    elif args.action == 'worker':
        worker(root, Path(args.recipe))
    else:
        if not args.inputs_release or not args.plan_sha256:
            parser.error('bound inputs release and plan digest are required')
        if args.action == 'chunk':
            chunk(root, args.inputs_release, args.plan_sha256, args.index)
        else:
            finalize(root, args.inputs_release, args.plan_sha256)


if __name__ == '__main__':
    main()

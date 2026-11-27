"""Packet-vs-replay split trace for the frozen price packet answers.

The dispatch selector (verdict UNRESOLVED on run 46038599219) refuted CPU
dispatch as the explanation for the 1,308 packet_replay failures: native
reproduces the stored AQMS and BYRN PIT reports byte-identically yet those
packets still fail their own replay, deterministically, on every measured
runner. This diagnostic pre-declares the flipping cells, re-decodes the
stored answer codes, recomputes the same bound-recipe features, and records
bit-level operand evidence for each flipping comparison, evaluating every
cell under BOTH comparison styles: the original build's float32 pandas
Series comparison and the PIT replay's float64 upcast comparison. The two
rails stay separate: AQMS/BYRN split original-build answers versus stable
PIT replay; AZIO's original PIT report itself flipped between two runner
environments. It never rewrites any source packet, never mutates
quarantine, never rewrites predicates, never invents tolerances, and never
claims full-world acceptance by itself. Reproduction of a pre-declared cell
and the expected difference census are MEASURED and recorded, never
asserted: a non-reproduced cell or a census mismatch is evidence, not a
crash, and the per-ticker file is always written. Every pre-declared cell
AND every runner-enumerated difference row is bit-traced under both styles.

Modes: ``ticker`` traces one name on one matrix runner; ``finalize``
aggregates the per-ticker traces into the split verdict and publishes it.
"""
import argparse
import json
import os
from pathlib import Path
import sys

from ci.price_full_cohort_pit import (ROOT, checked, create_release, encoded, sha,
                                      tag_for)
from ci.price_numeric_runtime_trace import decode_codes

REQUEST = 'ci/PRICE_PIT_SPLIT_TRACE_REQUEST.json'
TICKERS = ['AQMS', 'BYRN', 'AZIO']
RAILS = {'AQMS': 'build_vs_replay', 'BYRN': 'build_vs_replay', 'AZIO': 'replay_vs_replay'}
QUESTIONS = {
    'Q1': 'which cells flip',
    'Q2': 'whether the raw operands are identical',
    'Q3': 'whether build and replay use the same function, dtype, and reduction',
    'Q4': 'whether this is the same unstable-stat pattern as the earlier 20-shard diagnosis',
}


def validate_request(request):
    if (request.get('version') != 1 or type(request.get('execute')) is not bool
            or [t['ticker'] for t in request['tickers']] != TICKERS
            or [t['rail'] for t in request['tickers']] != [RAILS[t] for t in TICKERS]
            or request.get('questions') != QUESTIONS
            or request['plan']['sha256'] != '18e12eed42099647d598931868547c85f99731b14b6f6138fece0fd87a43043d'
            or request['selector_verdict']['sha256'] != '7076bb0faf646b77e6a5694019455197324309cd3c5c9a8d8967853595dd8d24'):
        raise ValueError('split trace scope or bindings differ')
    for binding in request['tickers']:
        if binding['rail'] == 'build_vs_replay' and not binding['expected_differences']:
            raise ValueError('split trace rail census differs')
        if binding['rail'] == 'replay_vs_replay' and any(binding['expected_differences'].values()):
            raise ValueError('replay_vs_replay rail must expect a healed census')
        for cell in binding['cells']:
            facet, tf = cell['question_id'].rsplit(':', 1)[1].split('__')
            if facet != 'rising1' or cell['stored_code'] == cell['replay_code']:
                raise ValueError('predeclared cell shape differs')
    return request


def f32(value):
    import numpy as np
    return np.float64(value).astype(np.float32)


def bits32(value):
    import numpy as np
    return int(np.float32(value).view(np.uint32))


def bits64(value):
    import numpy as np
    return int(np.float64(value).view(np.uint64))


def _ord32(value):
    """Order-preserving integer map of a float32 (for ulp distances)."""
    import numpy as np
    raw = int(np.float32(value).view(np.uint32))
    return raw ^ (0xFFFFFFFF if raw >> 31 else 0x80000000)


def ulp32_distance(left, right):
    """Signed float32 ulp distance left-right; 0 means bit-identical."""
    import numpy as np
    if not (np.isfinite(left) and np.isfinite(right)):
        return None
    return _ord32(np.float32(left)) - _ord32(np.float32(right))


def next64(value, steps):
    """Move a float64 by signed ulp steps (order-preserving integer map)."""
    import numpy as np
    raw = int(np.float64(value).view(np.uint64))
    mapped = raw ^ (0xFFFFFFFFFFFFFFFF if raw >> 63 else 0x8000000000000000)
    moved = (mapped + steps) % (1 << 64)
    bits = moved ^ (0x8000000000000000 if moved >> 63 else 0xFFFFFFFFFFFFFFFF)
    return np.uint64(bits).view(np.float64).item()


def straddle(left64, right64):
    """Can a +-1 float64 ulp perturbation of either operand, after the
    production float32 cast, flip the rising1 comparison outcome?"""
    import numpy as np
    base = bool(np.float32(left64) > np.float32(right64))
    for dl in (-1, 0, 1):
        for dr in (-1, 0, 1):
            if dl == 0 and dr == 0:
                continue
            if bool(np.float32(next64(left64, dl)) > np.float32(next64(right64, dr))) != base:
                return True
    return False


def codes_float64_style(series):
    """PIT replay style: upcast to float64, then compare (diagnostic_answers)."""
    import numpy as np
    x = series.to_numpy(dtype='float64')
    right = series.shift(1).to_numpy(dtype='float64')
    valid = np.isfinite(x) & np.isfinite(right)
    return np.where(~valid, 0, np.where(x > right, 2, 1)).astype(np.uint8)


def codes_float32_series_style(series):
    """Original build style: compare the stored float32 pandas Series."""
    import numpy as np
    right = series.shift(1)
    valid = np.isfinite(series) & np.isfinite(right)
    return np.where(~valid.to_numpy(), 0,
                    np.where((series > right).to_numpy(), 2, 1)).astype(np.uint8)


def fragile_series(close, timeframe):
    """float64 pre-cast fragile series, restating bar_statistics exactly."""
    import numpy as np
    import pandas as pd
    from world_bar_statistics import _autocorrelation
    if timeframe.endswith('d') and timeframe[:-1].isdigit() and 1 <= int(timeframe[:-1]) <= 21:
        annual = 252. / int(timeframe[:-1])
    else:
        raise ValueError('split trace unsupported candle duration: ' + timeframe)
    cs = pd.Series(close)
    positive = cs.where(cs > 0)
    ratio = positive / positive.shift(1)
    returns = np.log(ratio)
    out = {'returns': returns.to_numpy(), 'ratio': ratio.to_numpy()}
    for n in (10, 20, 60, 120):
        out[f'HV{n}'] = returns.rolling(n).std(ddof=1).to_numpy() * np.sqrt(annual) * 100
    for n in (20, 60):
        roll = returns.rolling(n)
        out[f'RETURN_EXCESS_KURTOSIS{n}'] = roll.kurt().to_numpy()
        out[f'RETURN_AUTOCORR1_{n}'] = roll.apply(_autocorrelation, raw=True).to_numpy()
    return out


def locate_stem(contents, registry, tf, question_id):
    """Find the packet chunk stem whose registry schema holds question_id."""
    for name in sorted(contents):
        if not name.endswith('.json') or not name.startswith(tf + '_'):
            continue
        meta = json.loads(contents[name])
        schema = registry[meta['registry_sha256']]
        qids = [q['question_id'] for q in schema]
        if question_id in qids:
            return name[:-5], qids.index(question_id)
    raise ValueError('split trace question absent from packet: ' + question_id)


def load_plan(root, request):
    plan = json.loads(checked(request['plan'], root / 'plan').read_bytes())
    refs = {r['ticker']: r for r in plan['references']}
    return plan, refs


def trace_ticker(root, ticker):
    """Re-decode, recompute, and bit-trace every pre-declared flipping cell."""
    import numpy as np
    import pandas as pd
    from ci.compact_world_build import snapshot
    from ci.native_price_blocks import read_member
    from ci.release_assets import download_asset
    from ci.row0_part172_replay import members
    request = validate_request(json.loads((ROOT / REQUEST).read_bytes()))
    if request['execute'] is not True:
        raise ValueError('split trace execution disabled')
    binding, = [t for t in request['tickers'] if t['ticker'] == ticker]
    plan, refs = load_plan(root, request)
    reference = refs[ticker]
    recipe, calendar = snapshot(root / 'snapshot', plan['frozen_build_request'])
    sys.path.insert(0, str(recipe.resolve()))
    import facets_world as fw
    import world_timeframes as wt
    if sha(calendar.read_bytes()) != plan['calendar_sha256']:
        raise ValueError('split trace calendar differs')
    registry = json.loads(checked(plan['registry'], root / 'registry').read_bytes())
    part, = [p for p in plan['source_parts'] if ticker in p['tickers']]
    source = root / 'sources' / ticker.encode().hex()
    manifest = json.loads(download_asset(part['release'], part['part'] + '.json', source).read_bytes())
    archive = download_asset(part['release'], part['part'] + '.tar', source)
    if manifest['archive_sha256'] != part['archive_sha256'] or sha(archive.read_bytes()) != part['archive_sha256']:
        raise ValueError('split trace raw archive differs')
    raw = read_member(archive, manifest, ticker.encode().hex() + '.bars.parquet')
    if sha(raw) != reference['raw_sha256']:
        raise ValueError('split trace raw member differs')
    packet = checked(dict(release=reference['release'], asset=reference['asset'],
                          sha256=reference['answer_container_sha256']), source / 'packet')
    contents = members(packet.read_bytes())
    bars_file = source / (ticker.encode().hex() + '.bars.parquet')
    bars_file.write_bytes(raw)
    bars = pd.read_parquet(bars_file)
    calendar_index = pd.DatetimeIndex(pd.read_parquet(calendar).date).as_unit('ns')
    query = calendar_index[(calendar_index >= pd.Timestamp('2020-01-01')) & calendar_index.isin(pd.DatetimeIndex(bars.date))]
    if len(query) != reference['query_rows']:
        raise ValueError('split trace query rows differ')
    frames, natives, precasts, grids = {}, {}, {}, {}
    contexts = {}

    def context(qid):
        """Per-question recomputation context, built once per question."""
        if qid in contexts:
            return contexts[qid]
        tf = qid.rsplit('__', 1)[1]
        if tf not in frames:
            native = wt.completed_candles(bars, tf, session_calendar=calendar_index)
            frame = wt.candle_features(native, fw.discover(), timeframe=tf)
            frames[tf], natives[tf] = frame, native
            close = native['close'].to_numpy(dtype=float)
            precasts[tf] = fragile_series(close, tf)
            grids[tf] = np.searchsorted(native.available_from.to_numpy(dtype='datetime64[ns]'),
                                        query.to_numpy(dtype='datetime64[ns]'), side='right') - 1
        field = qid.rsplit(':', 1)[0]
        stem, column = locate_stem(contents, registry, tf, qid)
        _, _, codes = decode_codes(contents, stem, registry)
        frame, positions = frames[tf], grids[tf]
        series = frame[field]
        stored_row = codes[column]
        own64 = codes_float64_style(series)[positions]
        own32 = codes_float32_series_style(series)[positions]
        field64 = precasts[tf][field]
        produced = series.to_numpy(dtype=np.float32)
        restated = field64.astype(np.float32)
        finite = np.isfinite(produced) & np.isfinite(restated)
        if (np.isfinite(produced) != np.isfinite(restated)).any() \
                or not np.array_equal(produced[finite], restated[finite]):
            raise ValueError('split trace pre-cast restatement diverges from production: ' + field)
        contexts[qid] = dict(field=field, stem=stem, stored_row=stored_row,
            own64=own64, own32=own32, positions=positions, field64=field64,
            production_dtype=str(series.dtype),
            diffs64=[int(r) for r in np.flatnonzero(own64 != stored_row)],
            diffs32=[int(r) for r in np.flatnonzero(own32 != stored_row)])
        return contexts[qid]

    def trace_row(ctx, row):
        """Bit-level operand evidence for one query row under both styles."""
        index = int(ctx['positions'][row])
        own64r, own32r = int(ctx['own64'][row]), int(ctx['own32'][row])
        left64, right64 = float(ctx['field64'][index]), float(ctx['field64'][index - 1])
        left32, right32 = f32(left64), f32(right64)
        return dict(native_index=index, stem=ctx['stem'],
            stored_code_int=int(ctx['stored_row'][row]),
            code_float64_style=own64r, code_float32_series_style=own32r,
            comparison_styles_agree=bool(own64r == own32r),
            production_dtype=ctx['production_dtype'],
            left64_bits=f'{bits64(left64):016x}', right64_bits=f'{bits64(right64):016x}',
            left32_bits=f'{bits32(left32):08x}', right32_bits=f'{bits32(right32):08x}',
            left64=left64, right64=right64, left32=float(left32), right32=float(right32),
            ulp32_left_vs_right=ulp32_distance(left32, right32),
            straddle_1ulp64=straddle(left64, right64))

    cells = []
    for cell in binding['cells']:
        qid, row = cell['question_id'], int(cell['query_row'])
        tf = qid.rsplit('__', 1)[1]
        ctx = context(qid)
        entry = dict(cell, timeframe=tf, origin='predeclared', **trace_row(ctx, row))
        if binding['rail'] == 'build_vs_replay':
            entry['reproduced'] = bool(row in ctx['diffs64'])
        else:
            entry['healed'] = bool(int(ctx['own64'][row]) == int(ctx['stored_row'][row]))
        cells.append(entry)

    declared = {(c['question_id'], int(c['query_row'])) for c in binding['cells']}
    for qid in sorted(contexts):
        ctx = contexts[qid]
        tf = qid.rsplit('__', 1)[1]
        extra_rows = sorted(set(ctx['diffs64']) | set(ctx['diffs32']))
        for row in extra_rows:
            if (qid, row) in declared:
                continue
            entry = dict(question_id=qid, query_row=row, timeframe=tf,
                stored_code=int(ctx['stored_row'][row]), replay_code=None,
                origin='runner_enumerated', **trace_row(ctx, row))
            if binding['rail'] == 'build_vs_replay':
                entry['reproduced'] = None
            else:
                entry['healed'] = None
            cells.append(entry)

    diffs64 = {q: ctx['diffs64'] for q, ctx in contexts.items()}
    diffs32 = {q: ctx['diffs32'] for q, ctx in contexts.items()}
    expected = binding['expected_differences']
    census_counts = {q: len(r) for q, r in diffs64.items()}
    census_matches_expected = bool(census_counts == expected)
    style_census_agree = all(diffs64[q] == diffs32[q] for q in diffs64)
    env = dict(python=sys.version, numpy=np.__version__, pandas=pd.__version__,
        returns_sha256={tf: sha(p['returns'].tobytes()) for tf, p in precasts.items()},
        ratio_sha256={tf: sha(p['ratio'].tobytes()) for tf, p in precasts.items()},
        close_alignment64={tf: int(natives[tf]['close'].to_numpy(dtype=float).ctypes.data % 64) for tf in natives})
    state = dict(format='PRICE_PIT_SPLIT_TRACE_STOCK_V1', request=request, ticker=ticker,
        rail=binding['rail'], source_commit=os.environ.get('GITHUB_SHA', ''), cells=cells,
        differences_float64_style=diffs64, differences_float32_series_style=diffs32,
        style_census_agree=style_census_agree, expected_census=expected,
        census_matches_expected=census_matches_expected, environment=env,
        scoring_gate='CLOSED')
    file = root / f"{ticker.encode().hex()}.split.json"
    file.write_bytes(encoded(state))
    print('PRICE_PIT_SPLIT_TRACE_STOCK', ticker, binding['rail'], len(cells), flush=True)


def verdict(traces):
    """Aggregate classification across both rails, per the declared rules."""
    cells = [c for trace in traces for c in trace['cells']]
    predeclared = [c for c in cells if c.get('origin', 'predeclared') == 'predeclared']
    styles_agree = all(t['style_census_agree'] for t in traces) and all(c['comparison_styles_agree'] for c in cells)
    all_straddle = all(c['straddle_1ulp64'] for c in cells)
    float32_matches_stored = any(c['code_float32_series_style'] == c['stored_code']
                                 and c['code_float64_style'] != c['stored_code'] for c in cells)
    if float32_matches_stored:
        classification = 'CODE_PATH_DIVERGENCE_SIGNAL_FIX_IN_LATER_PR_NOT_THIS_STEP'
    elif styles_agree and all_straddle:
        classification = 'FEATURE_VALUE_SPLIT_1ULP64_STRADDLES_STYLES_AGREE'
    else:
        classification = 'MIXED_OR_NON_STRADDLE_CELLS_REQUIRE_REVIEW'
    reproduction = {}
    for trace in traces:
        pre = [c for c in trace['cells'] if c.get('origin', 'predeclared') == 'predeclared']
        if trace.get('rail') == 'build_vs_replay':
            reproduction[trace['ticker']] = dict(predeclared=len(pre),
                reproduced=sum(1 for c in pre if c.get('reproduced')),
                census_matches_expected=trace.get('census_matches_expected'))
        elif trace.get('rail') == 'replay_vs_replay':
            reproduction[trace['ticker']] = dict(predeclared=len(pre),
                healed=all(c.get('healed') for c in pre),
                census_matches_expected=trace.get('census_matches_expected'))
    return dict(classification=classification, cells=len(cells),
        predeclared_cells=len(predeclared), reproduction=reproduction,
        comparison_styles_agree_everywhere=styles_agree,
        all_cells_straddle=all_straddle,
        answers={
            'Q1': 'pre-declared flipping-cell reproduction is MEASURED per cell on this runner (reproduced flags), never asserted; runner-enumerated difference rows are bit-traced too; full difference lists included per question',
            'Q2': 'raw inputs are byte-identical by sha256 (bars, calendar, registry, packet); operand bits and intermediate shas recorded',
            'Q3': 'measured, not assumed: bound-recipe modules, casts, and rolling reductions are shared; the two rising1 comparison styles (production-Series build-style, float64 upcast replay-style) are evaluated per cell and their agreement reported',
            'Q4': 'all flipping questions sit in the fragile families of the 20-shard diagnosis (KURTOSIS/AUTOCORR/HV)',
        },
        note='AQMS/BYRN rail: original build answers versus stable PIT replay. AZIO rail: '
             'the original PIT report itself flipped between runner environments; healing '
             'is measured per cell on this runner, not asserted. A 1ulp64 straddle at a '
             'near-tied rising1 comparison means any last-bit environment difference '
             'flips the float32-rounded comparison deterministically. If the float32 '
             'Series style matches stored while the float64 style does not, that is a '
             'code-path divergence to fix in a later PR, never in this step. This '
             'artifact changes no packet, predicate, tolerance, or quarantine.')


def finalize(root):
    """Aggregate per-ticker traces, publish the split verdict; no overclaim."""
    from ci.release_assets import gh_retry, publish_assets
    request = validate_request(json.loads((ROOT / REQUEST).read_bytes()))
    if request['execute'] is not True:
        raise ValueError('split trace execution disabled')
    traces = []
    for ticker in TICKERS:
        file = root / f"{ticker.encode().hex()}.split.json"
        state = json.loads(file.read_bytes())
        if state['ticker'] != ticker or state['request'] != request or state['rail'] != RAILS[ticker]:
            raise ValueError('split trace stock evidence differs from the declared request')
        traces.append(state)
    tag = tag_for('split-trace')
    create_release(tag, 'Packet-vs-replay split trace only: pre-declared flipping cells, stored-code re-decode, bound-recipe recomputation, both rising1 comparison styles measured per cell, bit-level operand straddle evidence. No source rewrite, no predicate rewrite, no tolerance, no quarantine mutation, no scoring approval.')
    state = dict(format='PRICE_PIT_SPLIT_TRACE_V1', request=request,
        source_commit=os.environ.get('GITHUB_SHA', ''), traces=traces,
        scoring_gate='CLOSED', full_cohort_measurement='NOT_EVALUATED_BY_THIS_DIAGNOSTIC')
    state['verdict'] = verdict(traces)
    file = root / 'PRICE_PIT_SPLIT_TRACE_V1.json'
    file.write_bytes(encoded(state))
    publish_assets(tag, ROOT / REQUEST, file, *[root / f"{t.encode().hex()}.split.json" for t in TICKERS])
    gh_retry('release', 'edit', tag, '--draft=false')
    print('PRICE_PIT_SPLIT_TRACE_RESULT', json.dumps(state['verdict']), flush=True)


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
        trace_ticker(root, args.ticker)
    else:
        finalize(root)

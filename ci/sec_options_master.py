"""Emit docs/BINARY_MASTER_SEC_V1.csv — strict SEC/options binary definitions.

Kimi lane (TODO item 3). Standalone emitter: the canonical v2.7 grid and
BINARY_MASTER_V1.csv stay untouched (test_binary_canonical_plan.py pins the
sealed grid totals; extending it is a QUESTION_TREE_v3 decision for James).
Rows use the exact BINARY_MASTER_V1 column schema so a future v3 merge is a
mechanical append. Every row is a definition only — no data is downloaded;
measurements live in world_sec_events.py and answer NOT_EVALUABLE until
Venice's pipelines land (NE is excluded, never NO).
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from world_question_grid import identity, ROOT
from ci.binary_master_build import CSV_COLUMNS

SEC_CSV = 'BINARY_MASTER_SEC_V1.csv'
SEC_REPORT = 'BINARY_MASTER_SEC_V1_REPORT.json'

DATA_GROUP = '8 Non-price data'
NE_CSV = ('NOT_EVALUABLE (excluded, never NO): no usable event/record before D 09:30 ET '
          '(dictionary C29 public-timestamp rule), empty session calendar, or pre-source-start. '
          'A known 0 is evaluable. Measurements: world_sec_events.py')
KNOWABLE_CSV = ('Usable only if the record public timestamp (SEC acceptance datetime) is '
                '< setup date D 09:30 ET (dictionary C29); join on acceptance date < D, '
                'never period end; no day-D information.')
VIEWPORT_CSV = ('CONCRETE event marker: event date, days_since (trading days), direction from '
                'the fixed mapping table (upgrade/P = bullish, downgrade/S = bearish); '
                'no free text, no circles.')

BLOCK_FORM4 = 'E SEC Form 4 (I187)'
BLOCK_SHORTVOL = 'F FINRA short volume (I189)'
BLOCK_CBOE = 'N CBOE market-wide options (I201)'
RECIPE_FORM4 = 'sec_form4'
RECIPE_FINRA = 'finra_short'
RECIPE_CBOE = 'cboe_market'

# Facet x dial grid for the Form 4 group (spec todo3_sec_options_defs_v1.md section 3).
# Thresholds literal; windows in trading days ending D-1.
_DAYS_SINCE = (5, 10, 20)
_COUNT_WINDOWS = (5, 10, 20)
_COUNT_RUNGS = (1, 2)
_NET_WINDOWS = (5, 20)
_NET_RUNGS = (0, 100000, 500000)
_SIZE_WINDOWS = (60,)
_SIZE_RUNGS = (100000, 500000, 1000000)
_DIRECTIONS = ('bullish', 'bearish')


def _row(facet, feature_expression, feature_kind, feature_unit, comparator, threshold,
         formula_expr, yes, outcome, recipe=RECIPE_FORM4, block=BLOCK_FORM4,
         source='I187', extra_feature=None):
    feature = dict(recipe=recipe, expression=feature_expression, kind=feature_kind,
                   unit=feature_unit)
    if extra_feature:
        feature.update(extra_feature)
    semantic = dict(feature=feature, comparator=comparator,
                    comparison_threshold=str(threshold), outcome=outcome)
    return {
        'question_id': 'BS1-' + identity(semantic),
        'feature_id': 'BSF1-' + identity(feature),
        'definition_status': 'BOUND',
        'data_group': DATA_GROUP,
        'block': block,
        'facet': facet,
        'source_question_id': source,
        'source_variant_id': '',
        'source_outcome': outcome,
        'timeframe_days': 1,
        'lookback_bars': '',
        'feature_recipe': recipe,
        'feature_expression': feature_expression,
        'feature_kind': feature_kind,
        'feature_unit': feature_unit,
        'transform': 'identity',
        'comparator': comparator,
        'comparison_threshold': str(threshold),
        'formula': '(' + formula_expr + ') ' + comparator + ' ' + str(threshold),
        'yes_condition': yes,
        'not_evaluable_condition': NE_CSV,
        'viewport_drawing': VIEWPORT_CSV,
        'knowable_at_setup_open': KNOWABLE_CSV,
        'expression': 'CONCRETE',
        'missing': 'sec_definition_only_answers_not_evaluable_until_data_lands',
        'feature_json': json.dumps(feature, sort_keys=True, separators=(',', ':')),
    }


def form4_definitions():
    rows = []
    for direction in _DIRECTIONS:
        for n in _DAYS_SINCE:
            expr = f'sec_form4_days_since_last_v1(direction={direction})'
            rows.append(_row(
                'form4_days_since', expr, 'integer_count', 'trading_days_since_last_' + direction,
                '<=', n, expr,
                f'latest {direction} Form 4 event (P=bullish, S=bearish) is <= {n} trading days '
                f'before D (event day = 0)', f'days_since_{direction}_le{n}'))
        for window in _COUNT_WINDOWS:
            for k in _COUNT_RUNGS:
                expr = f'sec_form4_count_v1(direction={direction},window={window})'
                rows.append(_row(
                    'form4_count', expr, 'integer_count',
                    f'count_{direction}_events_last_{window}_sessions',
                    '>=', k, expr,
                    f'>={k} {direction} Form 4 events in the last {window} completed sessions',
                    f'count_{direction}_w{window}_ge{k}'))
    # cluster: dictionary I187 spec (>=3 distinct insiders with P, 10 sessions)
    expr = 'sec_form4_cluster_v1(min_insiders=3,window=10)'
    rows.append(_row(
        'form4_cluster', expr, 'boolean', 'distinct_insider_buyers_ge3_last_10_sessions',
        '=', 1, expr,
        '>= 3 distinct insiders have a usable P event in the last 10 completed sessions',
        'cluster_ge3_w10', extra_feature=dict(min_insiders=3, window=10)))
    # net dollars is direction-agnostic (sum P - sum S): outside the direction loop
    for window in _NET_WINDOWS:
        for t in _NET_RUNGS:
            expr = f'sec_form4_net_dollars_v1(window={window})'
            rows.append(_row(
                'form4_net_dollars', expr, 'continuous',
                f'net_purchase_dollars_last_{window}_sessions',
                '>=', t, expr,
                f'sum($P) - sum($S) over the last {window} sessions >= {t} USD '
                '(non-directional codes contribute 0)',
                f'net_dollars_w{window}_ge{t}'))
    for window in _SIZE_WINDOWS:
        for t in _SIZE_RUNGS:
            expr = f'sec_form4_max_trade_v1(direction=bullish,window={window})'
            rows.append(_row(
                'form4_max_trade', expr, 'continuous',
                f'largest_purchase_dollars_last_{window}_sessions',
                '>=', t, expr,
                f'largest single P event in the last {window} sessions >= {t} USD',
                f'max_trade_w{window}_ge{t}'))
    return rows


def short_volume_definitions():
    """I189 FINRA daily short volume: per-session short/total ratio facets."""
    rows = []
    recipe, block, source = RECIPE_FINRA, BLOCK_SHORTVOL, 'I189'
    for t in (0.45, 0.5, 0.55):
        expr = 'finra_short_ratio_v1()'
        rows.append(_row(
            'short_volume_ratio', expr, 'continuous', 'short_volume_over_total_volume_latest_session',
            '>=', t, expr,
            f'latest usable session short/total volume ratio >= {t}', f'ratio_ge{t}',
            recipe=recipe, block=block, source=source))
    for window in (5,):
        for t in (0.45, 0.5, 0.55):
            expr = f'finra_short_ratio_mean_v1(window={window})'
            rows.append(_row(
                'short_volume_ratio_mean', expr, 'continuous',
                f'mean_short_ratio_last_{window}_sessions',
                '>=', t, expr,
                f'mean short/total ratio over the last {window} usable sessions >= {t}',
                f'mean_w{window}_ge{t}',
                recipe=recipe, block=block, source=source, extra_feature=dict(window=window)))
    for lookback in (60,):
        for t in (0.8, 0.9):
            expr = f'finra_short_ratio_percentile_v1(lookback={lookback})'
            rows.append(_row(
                'short_volume_ratio_percentile', expr, 'continuous',
                f'short_ratio_percentile_last_{lookback}_sessions',
                '>=', t, expr,
                f'latest short ratio is in the top {round((1-t)*100)}% of its own last '
                f'{lookback} usable sessions (percentile in [0,1])',
                f'pct_l{lookback}_ge{t}',
                recipe=recipe, block=block, source=source, extra_feature=dict(lookback=lookback)))
    expr = 'finra_short_ratio_cross_median_v1(lookback=60,within=5)'
    rows.append(_row(
        'short_volume_ratio_state_change', expr, 'boolean',
        'short_ratio_crossed_above_60session_median_within_5_sessions',
        '=', 1, expr,
        'short/total ratio crossed above the median of the prior 60 usable sessions at any '
        'point within the last 5 sessions',
        'cross_median_60_within5', recipe=recipe, block=block, source=source,
        extra_feature=dict(lookback=60, within=5)))
    return rows


def cboe_definitions():
    """I201 CBOE market-wide options: put/call ratios (raw counts, equity and
    total groups), era-split percentile, VIX level/term structure, SKEW."""
    rows = []
    recipe, block, source = RECIPE_CBOE, BLOCK_CBOE, 'I201'
    for group in ('equity', 'total'):
        for t in (0.7, 0.8, 0.9, 1.0):
            expr = f'cboe_put_call_volume_ratio_v1(group={group})'
            rows.append(_row(
                'cboe_pc_volume_ratio', expr, 'continuous',
                f'put_call_volume_ratio_latest_session_{group}',
                '>=', t, expr,
                f'latest usable session put/call VOLUME ratio ({group} group, raw counts) >= {t}',
                f'pc_vol_{group}_ge{t}',
                recipe=recipe, block=block, source=source, extra_feature=dict(group=group)))
    for t in (0.7, 0.9, 1.1):
        expr = 'cboe_put_call_oi_ratio_v1(group=equity)'
        rows.append(_row(
            'cboe_pc_oi_ratio', expr, 'continuous',
            'put_call_open_interest_ratio_latest_session_equity',
            '>=', t, expr,
            f'latest usable session put/call OPEN INTEREST ratio (equity group, raw counts) >= {t}',
            f'pc_oi_equity_ge{t}',
            recipe=recipe, block=block, source=source, extra_feature=dict(group='equity')))
    for lookback in (252,):
        for t in (0.8, 0.9):
            expr = f'cboe_pc_ratio_percentile_v1(lookback={lookback},group=equity)'
            rows.append(_row(
                'cboe_pc_ratio_percentile', expr, 'continuous',
                'pc_volume_ratio_percentile_current_era_only',
                '>=', t, expr,
                f'latest equity put/call volume ratio is in the top {round((1-t)*100)}% of its '
                f'own last {lookback} usable sessions WITHIN THE CURRENT CBOE ERA '
                '(never crosses the 2019-10-07 definition break or the post-2022 0DTE flag)',
                f'pc_pct_l{lookback}_ge{t}',
                recipe=recipe, block=block, source=source,
                extra_feature=dict(lookback=lookback, group='equity')))
    for t in (12, 20, 30):
        expr = 'vix_level_v1()'
        rows.append(_row(
            'vix_level', expr, 'continuous', 'vix_close_latest_session',
            '>=', t, expr,
            f'latest usable VIX close >= {t}', f'vix_ge{t}',
            recipe=recipe, block=block, source=source))
    for state in ('backwardation', 'contango'):
        expr = 'vix_term_structure_state_v1()'
        rows.append(_row(
            'vix_term_structure', expr, 'category_code', 'vix_vs_vix3m_state_fixed_set',
            '=', state, expr,
            f'VIX term structure state = {state} (contango: VIX < VIX3M; backwardation: '
            'VIX >= VIX3M; fixed two-outcome set)',
            f'term_{state}', recipe=recipe, block=block, source=source))
    for t in (120, 130, 140):
        expr = 'cboe_skew_v1()'
        rows.append(_row(
            'cboe_skew', expr, 'continuous', 'skew_index_latest_session',
            '>=', t, expr,
            f'latest usable CBOE SKEW index level >= {t}', f'skew_ge{t}',
            recipe=recipe, block=block, source=source))
    return rows


def build(root=ROOT):
    root = Path(root)
    rows = (form4_definitions() + short_volume_definitions() + cboe_definitions())
    ids = [r['question_id'] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate question_id in SEC definitions')
    path = root / 'docs' / SEC_CSV
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    report = dict(csv=SEC_CSV, csv_sha256=digest, rows=len(rows),
                  blocks=sorted({r['block'] for r in rows}),
                  facets=sorted({r['facet'] for r in rows}),
                  status='DEFINITIONS_ONLY_NO_ANSWERS')
    (root / 'docs' / SEC_REPORT).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default=str(ROOT))
    args = parser.parse_args()
    print(json.dumps(build(args.root), indent=2))

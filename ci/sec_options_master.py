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
RECIPE_FORM4 = 'sec_form4'

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
         formula_expr, yes, outcome, extra_feature=None):
    feature = dict(recipe=RECIPE_FORM4, expression=feature_expression, kind=feature_kind,
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
        'block': BLOCK_FORM4,
        'facet': facet,
        'source_question_id': 'I187',
        'source_variant_id': '',
        'source_outcome': outcome,
        'timeframe_days': 1,
        'lookback_bars': '',
        'feature_recipe': RECIPE_FORM4,
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


def build(root=ROOT):
    root = Path(root)
    rows = form4_definitions()
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

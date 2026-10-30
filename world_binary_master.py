"""Kimi batch-1 candle facet binders for the canonical binary master.

Strict YES/NO definitions only. Families without an explicit binder here fall
through to world_binary_price.bind_price_question, which raises
NotImplementedError; the emitter counts those, never silently skips them.

Bar model: native multi-day candles are fixed groups of `candle_days`
consecutive shared-calendar slots (slot // candle_days). Every native slot in
the required span must be present with a canonical availability date; the
aggregation is O=first open, H=max high, L=min low, C=last close. This module
derives definitions and evaluates predicates over supplied bars only; it does
not compute features from raw data, join sources, or authorize mining.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, getcontext
from numbers import Real
import math
import numpy as np

from world_binary_questions import evaluate_binary
from world_question_grid import canonical_number, identity
from world_binary_price import bind_price_question as _bind_gpt_price
from world_binary_price import evaluate_price as _eval_gpt_price

# Exact decimal mirror 1/v for ratio-band buckets (README: lower side = 1/hi).
getcontext().prec = 28
MIRROR_PRECISION = 28

BAR_DEFINITION = 'FIXED_SHARED_SESSION_CALENDAR_V1'
PRICE_BASIS = 'PIT_SPLIT_ADJUSTED_OHLC'
CONTRACT = 'FLOAT64_NO_EPSILON_V1'
KNOWN = 'known_ratio_infinite_on_zero_denominator_v1'


@dataclass(frozen=True)
class NativeBar:
    end: date
    available_from: date | None
    open: float | None
    high: float | None
    low: float | None
    close: float | None


def _strict_positive(values, name):
    if any(isinstance(v, bool) or not isinstance(v, Real) for v in values):
        raise TypeError(name + ' must be numeric scalars')
    arr = np.asarray(values, dtype=np.float64)
    if not np.isfinite(arr).all() or not (arr > 0).all():
        return None
    return arr


def _tf_window(bars, setup_date, expected_slot, lookback, candle_days):
    """Aggregate `lookback` native candles of `candle_days` sessions each.

    bars: {shared_calendar_slot: NativeBar}. All lookback*candle_days slots
    must be present and point-in-time knowable at setup_date.
    """
    if type(setup_date) is not date or type(expected_slot) is not int or expected_slot < 0:
        raise ValueError('canonical setup date and shared-calendar slot required')
    if type(lookback) is not int or lookback < 1 or type(candle_days) is not int or candle_days < 1:
        raise ValueError('positive integer lookback and candle_days required')
    span = lookback * candle_days
    first = expected_slot - span + 1
    if first < 0:
        return None
    selected = []
    for slot in range(first, expected_slot + 1):
        bar = bars.get(slot)
        if bar is None:
            return None
        if type(bar.end) is not date or (bar.available_from is not None and type(bar.available_from) is not date):
            raise ValueError('native end/availability must be canonical dates')
        if bar.available_from is None or bar.end >= setup_date or bar.available_from > setup_date:
            return None
        if bar.available_from <= bar.end:
            raise ValueError('native candle cannot be available before the next session')
        if selected and bar.end <= selected[-1].end:
            raise ValueError('native candle ends must increase strictly with shared slot')
        selected.append(bar)
    candles = []
    for i in range(lookback):
        group = selected[i * candle_days:(i + 1) * candle_days]
        candles.append(NativeBar(end=group[-1].end, available_from=None,
                                 open=group[0].open, high=max(b.high for b in group),
                                 low=min(b.low for b in group), close=group[-1].close))
    return candles


def _measure(recipe, candles):
    """Return the binary64 measurement or None (NOT_EVALUABLE)."""
    opened = _strict_positive([b.open for b in candles], 'native open')
    high = _strict_positive([b.high for b in candles], 'native high')
    low = _strict_positive([b.low for b in candles], 'native low')
    close = _strict_positive([b.close for b in candles], 'native close')
    if opened is None or high is None or low is None or close is None:
        return None
    with np.errstate(all='ignore'):
        body = close - opened
        if recipe == 'native_body_colour_balance_v1':
            green = body[body > 0].sum(dtype=np.float64)
            red = -body[body < 0].sum(dtype=np.float64)
            if green == 0 and red == 0:
                return None
            if red == 0:
                return math.inf  # KNOWN signed infinity per ratio rule
            return float(green / red)
        if recipe == 'native_last_green_vs_red_v1':
            greens = body[body > 0]
            reds = body[body < 0]
            if greens.size == 0 or reds.size == 0:
                return None
            ratio = float(greens[-1] / -reds[-1])
            return ratio
        if recipe == 'native_down_up_body_ratio_v1':
            downs = -body[body < 0]
            ups = body[body > 0]
            if downs.size == 0 or ups.size == 0:
                return None
            return float(downs.mean(dtype=np.float64) / ups.mean(dtype=np.float64))
        if recipe == 'native_wick_balance_v1':
            span = high - low
            valid = span > 0
            if not valid.any():
                return None
            upper = high - np.maximum(opened, close)
            lower = np.minimum(opened, close) - low
            score = (upper - lower)[valid] / span[valid]
            return float(score.mean(dtype=np.float64))
    raise NotImplementedError('unbound canonical master feature: ' + recipe)


def _apply_transform(value, transform):
    if value is None:
        return None
    if transform == 'identity':
        return value
    if transform == 'abs':
        return abs(value)
    if transform == 'mirror_min':
        with np.errstate(all='ignore'):
            return float(min(np.float64(value), np.float64(1.0) / np.float64(value)))
    raise ValueError('unknown master feature transform: ' + transform)


# facet -> (recipe, unit, outcomes, cutoff_id, transform_by_outcome, comparator_by_outcome)
FACETS = {
    'red_green_balance': dict(
        recipe='native_body_colour_balance_v1', unit='green_body_sum_over_red_body_sum',
        outcomes=('green', 'red', 'even'), cutoff_id='S_ratio_band_1p5',
        transform_by_outcome={'green': 'identity', 'red': 'identity', 'even': 'mirror_min'},
        comparator_by_outcome={'green': '>', 'red': '<', 'even': '>='}),
    'last_green_vs_red': dict(
        recipe='native_last_green_vs_red_v1', unit='latest_green_body_over_latest_red_body',
        outcomes=('green_bigger', 'red_bigger', 'similar'), cutoff_id='S_ratio_band_1p25',
        transform_by_outcome={'green_bigger': 'identity', 'red_bigger': 'identity', 'similar': 'mirror_min'},
        comparator_by_outcome={'green_bigger': '>', 'red_bigger': '<', 'similar': '>='}),
    'down_vs_up_moves': dict(
        recipe='native_down_up_body_ratio_v1', unit='mean_down_body_over_mean_up_body',
        outcomes=('downs_bigger', 'ups_bigger', 'equal'), cutoff_id='S_ratio_band_1p25',
        transform_by_outcome={'downs_bigger': 'identity', 'ups_bigger': 'identity', 'equal': 'mirror_min'},
        comparator_by_outcome={'downs_bigger': '>', 'ups_bigger': '<', 'equal': '>='}),
    'wick_body': dict(
        recipe='native_wick_balance_v1', unit='mean_upper_minus_lower_wick_over_range',
        outcomes=('upper_dominant', 'lower_dominant', 'balanced'), cutoff_id='C023_wick_body__scalar0p15',
        transform_by_outcome={'upper_dominant': 'identity', 'lower_dominant': 'identity', 'balanced': 'abs'},
        comparator_by_outcome={'upper_dominant': '>', 'lower_dominant': '<', 'balanced': '<='}),
}

NOT_EVALUABLE = ('Fewer completed native sessions than lookback*candle_days (+warmup), a missing/late '
                 'native bar, a non-positive or non-finite price, a zero total body on both sides '
                 '(colour-balance facets), a missing green or red bar (last_green_vs_red, down_vs_up_moves), '
                 'or an all-zero-range window (wick_body) -> NOT_EVALUABLE (excluded, never NO).')
KNOWABLE = ('Uses only native candles with available_from <= setup date D and end < D '
            '(last completed candle = D-1); D open is execution only. Bars are strict '
            + BAR_DEFINITION + ' slot groups; no day-D candle.')
VIEWPORT = ('Purple recolour of the D-1 native candle if YES; ratio/scalar value printed on the '
            'item pane header; no circles.')


def _ratio_thresholds(cutoff_id, v, facet):
    """Exact decimal band thresholds; ratio facets mirror the lower side as 1/v."""
    if cutoff_id == 'C023_wick_body__scalar0p15':
        high = canonical_number(v)
        return high, '-' + high
    high = canonical_number(v)
    low = canonical_number(str(Decimal(1) / Decimal(v)))
    return high, low


def _bind_facet(tree_row, variant, spec):
    settings = dict(variant.settings)
    if set(settings) != {spec['cutoff_id']}:
        raise ValueError('master binding cannot silently ignore a cutoff: ' + str(sorted(settings)))
    v = settings[spec['cutoff_id']]
    high, low = _ratio_thresholds(spec['cutoff_id'], v, tree_row['L4_analysis'])
    timeframe, lookback = map(int, tree_row['L2_timeframe'].split('x'))
    if timeframe not in range(1, 22) or lookback < 1:
        raise ValueError('registered native timeframe/lookback required')
    result = []
    for outcome in spec['outcomes']:
        transform = spec['transform_by_outcome'][outcome]
        operator = spec['comparator_by_outcome'][outcome]
        if tree_row['L4_analysis'] == 'wick_body':
            threshold = high if outcome != 'lower_dominant' else low
        else:
            threshold = high if operator in ('>',) else low
            if operator == '>=':
                threshold = low  # even/equal/similar: mirror_min >= 1/v
        scalar = dict(recipe=spec['recipe'], candle_days=timeframe, lookback=lookback,
                      transform=transform, bar_definition=BAR_DEFINITION,
                      price_basis=PRICE_BASIS, numeric_contract=CONTRACT)
        semantic = dict(feature=scalar, comparator=operator, comparison_threshold=threshold)
        expression = (spec['recipe'] + '(' + str(timeframe) + 'd,N=' + str(lookback) + ')'
                      + (';mirror_min' if transform == 'mirror_min' else ';abs' if transform == 'abs' else ''))
        result.append(dict(
            question_id='BM1-' + identity(semantic), feature_id='BF1-' + identity(scalar),
            feature=scalar, feature_expression=expression, feature_kind='continuous',
            formula='(' + expression + ') ' + operator + ' ' + threshold,
            answer_set=['NO', 'YES'], comparator=operator, comparison_threshold=threshold,
            feature_unit=spec['unit'], source_question_id=variant.source_question_id,
            source_variant_id=variant.variant_id, source_outcome=outcome,
            expression='NOT_YET', missing='tested_master_binding;pending_renderer_and_derive',
            definition_status='BOUND', chart_status='PENDING', derive_status='PENDING',
            mine_status='PENDING'))
    return result


def bind_master_question(tree_row, variant):
    """Bind a canonical source question+variant to strict binary definitions.

    Batch-1 candle facets bind here; everything else falls through to the
    reference price binders, which raise NotImplementedError when unbound.
    """
    if (tree_row['part'] == 'base' and tree_row['L1_type'] == 'candles'
            and tree_row['L3_derivative'] == 'OHLC' and tree_row['L4_analysis'] in FACETS):
        if tree_row['question_id'] != variant.source_question_id:
            raise ValueError('source tree and variant question differ')
        return _bind_facet(tree_row, variant, FACETS[tree_row['L4_analysis']])
    return _bind_gpt_price(tree_row, variant)


_MASTER_RECIPES = {spec['recipe'] for spec in FACETS.values()}


def evaluate_master(definition, bars, setup_date, expected_slot):
    feature = definition['feature']
    if feature['recipe'] in _MASTER_RECIPES:
        candles = _tf_window(bars, setup_date, expected_slot, feature['lookback'], feature['candle_days'])
        value = None if candles is None else _measure(feature['recipe'], candles)
        return evaluate_binary(_apply_transform(value, feature['transform']),
                               definition['comparator'], definition['comparison_threshold'])
    return _eval_gpt_price(definition, bars, setup_date, expected_slot)

"""Exact, explicitly bound price predicates for canonical binary conversion.

Native slot coordinates come from the shared calendar, never the stock's future
bar count. These reference functions do not authorize deriving/mining real rows
before the per-item chart gate. Published legacy rolling-offset arrays are not
replaced by these native-candle definitions.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from numbers import Real
import math
import numpy as np
from world_binary_questions import evaluate_binary
from world_question_grid import canonical_number, identity

RECIPES = {
    'intraday_change': ('C001_intraday_change__pct1', ('up', 'down', 'flat')),
    'interday_change': ('C002_interday_change__pct5', ('up', 'flat', 'down')),
}


@dataclass(frozen=True)
class NativeCandle:
    end: date
    available_from: date | None
    open: float | None
    close: float | None


def _window(bars, setup_date, expected_slot, lookback):
    if type(setup_date) is not date or type(expected_slot) is not int or expected_slot < 0:
        raise ValueError('canonical setup date and shared-calendar slot required')
    if type(lookback) is not int or lookback < 1:
        raise ValueError('positive integer lookback required')
    selected = []
    for slot in range(expected_slot-lookback+1, expected_slot+1):
        bar = bars.get(slot)
        if bar is None:
            return None
        if type(bar.end) is not date or (bar.available_from is not None and type(bar.available_from) is not date):
            raise ValueError('native end/availability must be canonical dates')
        if bar.available_from is None or bar.end >= setup_date or bar.available_from > setup_date:
            return None
        if bar.available_from <= bar.end:
            raise ValueError('native candle cannot be available before the next session')
        selected.append(bar)
    return selected


def _prices(bars, name):
    values = [getattr(bar, name) for bar in bars]
    if any(value is None for value in values):
        return None
    if any(isinstance(value, bool) or not isinstance(value, Real) for value in values):
        raise TypeError('native prices must be numeric scalars')
    values = np.asarray(values, dtype=np.float64)
    if not np.isfinite(values).all() or not (values > 0).all():
        return None
    return values


def measurement(kind, bars, setup_date, expected_slot, lookback):
    if kind not in RECIPES:
        raise NotImplementedError('unbound canonical price feature: '+kind)
    selected = _window(bars, setup_date, expected_slot, lookback)
    if selected is None:
        return None
    close = _prices(selected, 'close')
    if close is None:
        return None
    with np.errstate(all='ignore'):
        if kind == 'intraday_change':
            opened = _prices(selected, 'open')
            if opened is None:
                return None
            # Keep the source's fraction-before-mean operation order.
            value = float(((close-opened)/opened).mean())
        elif kind == 'interday_change':
            value = float(close[-1]/close[0]-1)
        else:
            raise NotImplementedError('unbound canonical price feature: '+kind)
    return None if math.isnan(value) else value


def bind_price_question(tree_row, variant):
    kind = tree_row['L4_analysis']
    if tree_row['part'] != 'base' or tree_row['L3_derivative'] != 'OHLC' or kind not in RECIPES:
        raise NotImplementedError('canonical question needs an explicit feature binding')
    if tree_row['question_id'] != variant.source_question_id:
        raise ValueError('source tree and variant question differ')
    cid, outcomes = RECIPES[kind]
    settings = dict(variant.settings)
    if set(settings) != {cid}:
        raise ValueError('price binding cannot silently ignore a cutoff')
    # Percent -> fraction is an exact decimal power-of-ten conversion, then the
    # predicate helper performs the same binary64 comparison as the source.
    percent = Decimal(settings[cid])
    if not percent.is_finite() or percent <= 0:
        raise ValueError('positive percent cutoff required')
    decimal_tuple = percent.as_tuple()
    cutoff = canonical_number(str(Decimal((decimal_tuple.sign,decimal_tuple.digits,decimal_tuple.exponent-2))))
    timeframe, lookback = map(int, tree_row['L2_timeframe'].split('x'))
    if timeframe not in range(1,22) or lookback < 1:
        raise ValueError('registered native timeframe/lookback required')
    feature = dict(recipe='native_'+kind+'_fraction_v1', candle_days=timeframe,
                   lookback=lookback, bar_definition='FIXED_SHARED_SESSION_CALENDAR_V1')
    result = []
    for outcome in outcomes:
        scalar = dict(feature, transform='abs' if outcome == 'flat' else 'identity')
        operator = {'up': '>', 'down': '<', 'flat': '<='}[outcome]
        threshold = '-'+cutoff if outcome == 'down' else cutoff
        semantic = dict(feature=scalar, comparator=operator, comparison_threshold=threshold)
        result.append(dict(question_id='BM1-'+identity(semantic), feature_id='BF1-'+identity(scalar),
            feature=scalar, feature_expression=scalar['recipe']+'('+str(timeframe)+'d,N='+str(lookback)+')'+
                (';abs' if outcome == 'flat' else ''), comparator=operator, comparison_threshold=threshold,
            feature_unit='fraction', source_question_id=variant.source_question_id,
            source_variant_id=variant.variant_id, source_outcome=outcome,
            expression='NOT_YET', missing='tested_native_price_renderer_binding;released_price_source_binding',
            definition_status='BOUND', chart_status='PENDING', derive_status='PENDING', mine_status='PENDING'))
    return result


def evaluate_price(definition, bars, setup_date, expected_slot):
    feature = definition['feature']
    if feature['transform'] not in ('identity','abs'):
        raise ValueError('unknown feature transform')
    kind = feature['recipe'].removeprefix('native_').removesuffix('_fraction_v1')
    value = measurement(kind, bars, setup_date, expected_slot, feature['lookback'])
    if value is not None and feature['transform'] == 'abs':
        value = abs(value)
    return evaluate_binary(value, definition['comparator'], definition['comparison_threshold'])

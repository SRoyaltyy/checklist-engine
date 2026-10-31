"""Strict binary predicates over already computed, point-in-time measurements.

This module does not compute features, join sources, or establish their PIT
availability. Unknown measurements never become NO. Continuous measurements
retain binary64 comparisons (including known signed infinity); integer
measurements and integral literal cutoffs are compared without float coercion.
"""
from dataclasses import dataclass
from decimal import Decimal
import json
import math
from numbers import Integral, Real
import operator
import re

ANSWER_SET = ('NO', 'YES')
SEMANTICS = 'STRICT_BINARY_V1'
COMPARATORS = {'>': operator.gt, '>=': operator.ge, '=': operator.eq,
               '!=': operator.ne, '<=': operator.le, '<': operator.lt}
FEATURE_KINDS = ('continuous', 'integer_count', 'signed_integer', 'category_code', 'boolean')
_LITERAL = re.compile(r'[+-]?(?:(?:0|[1-9][0-9]*)(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z')


def literal_threshold(text):
    """Return an exact integer or a finite, non-underflowed binary64 cutoff."""
    if not isinstance(text, str) or not _LITERAL.fullmatch(text):
        raise ValueError('comparison threshold must be a literal number')
    number = Decimal(text)
    if number == number.to_integral_value():
        return int(number)
    result = float(number)
    if not math.isfinite(result) or result == 0:
        raise ValueError('comparison threshold is outside nonzero binary64 range')
    return result


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate category code')
        result[key] = value
    return result


def category_codes(text):
    """An explicit immutable codebook is necessary to compare a category code."""
    values = json.loads(text, object_pairs_hook=_unique_object)
    if (not isinstance(values, dict) or not values or
        any(not re.fullmatch(r'0|[1-9][0-9]*', k) or
            not isinstance(v, str) or not v.strip() for k, v in values.items()) or
        len(set(values.values())) != len(values)):
        raise ValueError('category codes require distinct named nonnegative integer codes')
    return {int(k): v for k, v in values.items()}


def validate_predicate(comparator, threshold, feature_kind='continuous', categories=None):
    if comparator not in COMPARATORS:
        raise ValueError('literal comparator must be >, >=, =, !=, <= or <')
    if feature_kind not in FEATURE_KINDS:
        raise ValueError('unknown feature kind')
    value = literal_threshold(threshold)
    if feature_kind == 'category_code' and (
        not isinstance(categories, dict) or not categories or
        any(type(k) is not int or k < 0 or not isinstance(v, str) or not v.strip()
            for k, v in categories.items()) or len(set(categories.values())) != len(categories)):
        raise ValueError('category codebook is missing or invalid')
    if feature_kind in ('category_code', 'boolean'):
        if comparator not in ('=', '!='):
            raise ValueError('unordered category/boolean predicates require = or !=')
        allowed = {0, 1} if feature_kind == 'boolean' else set(categories or {})
        if type(value) is not int or value not in allowed:
            raise ValueError('comparison threshold is not in the explicit feature codebook')
    return value


@dataclass(frozen=True)
class BinaryAnswer:
    answer: str
    reason: str | None = None

    @property
    def evaluable(self):
        return self.answer in ANSWER_SET

    def nullable_bool(self):
        return self.answer == 'YES' if self.evaluable else None

    def __bool__(self):
        raise TypeError('use answer/evaluable explicitly; NOT_EVALUABLE is not NO')


def evaluate_binary(value, comparator, threshold, *, feature_kind='continuous',
                    categories=None, known=True):
    """YES/NO or NOT_EVALUABLE; invalid definitions/types raise, never coerce.

    A source adapter must set known=False for unavailable or not-yet-known
    inputs, even if its storage contains a numerical placeholder. None/NaN
    are also missing. Binary64 equality uses no epsilon. Integer-valued
    measurements compare to the exact decimal literal without losing bits.
    """
    cutoff = validate_predicate(comparator, threshold, feature_kind, categories)
    if type(known) is not bool:
        raise TypeError('known must be a boolean availability decision')
    if not known:
        return BinaryAnswer('NOT_EVALUABLE', 'FEATURE_NOT_KNOWN')
    if value is None:
        return BinaryAnswer('NOT_EVALUABLE', 'FEATURE_MISSING')
    if isinstance(value, bool):
        if feature_kind != 'boolean':
            raise TypeError('boolean measurements require feature_kind=boolean')
        value = int(value)
    if not isinstance(value, Real):
        raise TypeError('feature must be a numeric scalar, None or NaN')
    if isinstance(value, Integral):
        value = int(value)
    else:
        value = float(value)
        if math.isnan(value):
            return BinaryAnswer('NOT_EVALUABLE', 'FEATURE_MISSING')
    if feature_kind != 'continuous':
        if not isinstance(value, int):
            if not math.isfinite(value) or not value.is_integer():
                raise ValueError('discrete feature must be an integer')
            value = int(value)
        if feature_kind == 'integer_count' and value < 0:
            raise ValueError('count cannot be negative')
        if feature_kind == 'category_code' and value not in (categories or {}):
            raise ValueError('measurement is outside its explicit feature codebook')
        if feature_kind == 'boolean' and value not in (0, 1):
            raise ValueError('boolean measurement must be 0 or 1')
    comparison_value = Decimal(threshold) if isinstance(value, int) else cutoff
    passed = COMPARATORS[comparator](value, comparison_value)
    return BinaryAnswer('YES' if passed else 'NO')

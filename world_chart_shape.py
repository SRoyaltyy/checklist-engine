"""Reference primitives for James158's registered shape/viewport definitions.

No universe search, peer selection, eligibility inference or scoring occurs
here. A caller must authenticate its complete candidate pool and PIT inputs.
"""
from datetime import date
import math
from numbers import Real

WINDOWS = (10, 20, 60)
TIMEFRAMES = tuple(str(k)+'d' for k in range(1, 22))+('monthly',)
HORIZONS = tuple(range(1, 22))
SIMILARITY_THRESHOLD = 0.90


def normalise_closes(values):
    """Own-window min/max close normalization; invalid/constant = unknown."""
    values = tuple(values)
    if len(values) < 2: raise ValueError('shape needs at least two closes')
    if any(isinstance(v, bool) or not isinstance(v, Real) or not math.isfinite(v) or v <= 0 for v in values):
        return None
    values = tuple(float(v) for v in values)
    low, high = min(values), max(values)
    if low == high: return None
    return tuple((value-low)/(high-low) for value in values)


def shape_similarity(left, right):
    """Pearson of independently normalized closes; strict binary64 recipe."""
    left, right = tuple(left), tuple(right)
    if len(left) != len(right) or len(left) not in WINDOWS:
        raise ValueError('shape vectors need the same registered N=10/20/60')
    a, b = normalise_closes(left), normalise_closes(right)
    if a is None or b is None: return None
    ma, mb = math.fsum(a)/len(a), math.fsum(b)/len(b)
    a, b = tuple(x-ma for x in a), tuple(x-mb for x in b)
    numerator = math.fsum(x*y for x, y in zip(a, b))
    denominator = math.sqrt(math.fsum(x*x for x in a)*math.fsum(y*y for y in b))
    if denominator == 0: return None
    # Only final roundoff outside the mathematical correlation domain is
    # clamped. No tolerance/rounding is applied at the0.90 match boundary.
    return max(-1., min(1., numerator/denominator))


def match_state(similarity):
    if similarity is None: return None
    if isinstance(similarity, bool) or not isinstance(similarity, Real) or not math.isfinite(similarity) or not -1 <= similarity <= 1:
        raise ValueError('invalid shape correlation')
    return bool(similarity > SIMILARITY_THRESHOLD)


def _day(value):
    if type(value) is date: return value
    if isinstance(value, str):
        parsed = date.fromisoformat(value)
        if parsed.isoformat() == value: return parsed
    raise ValueError('canonical ISO session date or datetime.date required')


def known_forward_return(calendar, close_by_date, candidate_end, setup_date, horizon):
    """Descriptive close-to-close return after K actual trading sessions.

    Mapping keys are datetime.date. Never access the setup-day close or any
    outcome not yet known. K counts daily market sessions even for monthly Y.
    Missing endpoint prices stay unknown; never skip to a later price row.
    """
    if type(horizon) is not int or horizon not in HORIZONS: raise ValueError('K must be1..21 trading sessions')
    calendar = tuple(_day(d) for d in calendar)
    if not calendar or any(a >= b for a, b in zip(calendar, calendar[1:])):
        raise ValueError('shape outcome calendar must be ordered and unique')
    end, setup = _day(candidate_end), _day(setup_date)
    if end not in calendar or setup not in calendar or end >= setup:
        raise ValueError('candidate end and setup must be actual sessions with end < setup')
    position = calendar.index(end)+horizon
    if position >= len(calendar) or calendar[position] >= setup: return None
    initial, final = close_by_date.get(end), close_by_date.get(calendar[position])
    for value in (initial, final):
        if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) or value <= 0:
            return None
    return float(final)/float(initial)-1.

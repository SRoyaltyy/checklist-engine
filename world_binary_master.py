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
    volume: float | None = None      # shares traded; None = not supplied
    dollar: float | None = None      # sum(close*volume) over the candle's sessions (tf aggregates)


def _strict_positive(values, name):
    # GPT integration fix (PR #179, ported): an unavailable daily price
    # (None/NaN/inf/non-positive) makes the window NOT_EVALUABLE; it must not
    # be hidden by native aggregation or crash the evaluator.
    if any(v is not None and (isinstance(v, bool) or not isinstance(v, Real)) for v in values):
        raise TypeError(name + ' must be numeric scalars')
    if any(v is None for v in values):
        return None
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
    # GPT integration fix (PR #179, ported): expected_slot is the last DAILY
    # shared-calendar slot visible at D; a partially observed bucket must not
    # shift the fixed slot//k groups. Align down to the last completed group.
    last = ((expected_slot + 1) // candle_days) * candle_days - 1
    span = lookback * candle_days
    first = last - span + 1
    if first < 0:
        return None
    selected = []
    for slot in range(first, last + 1):
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
    # GPT integration fix (PR #179, ported): reject daily bars whose OHLC is
    # internally inconsistent; they cannot become a known native ratio.
    inputs = [_strict_positive([getattr(bar, field) for bar in selected], 'daily ' + field)
              for field in ('open', 'high', 'low', 'close')]
    if any(values is None for values in inputs):
        return None
    opened_v, high_v, low_v, close_v = inputs
    if ((high_v < np.maximum(opened_v, close_v)) | (low_v > np.minimum(opened_v, close_v))
            | (high_v < low_v)).any():
        return None
    candles = []
    for i in range(lookback):
        group = selected[i * candle_days:(i + 1) * candle_days]
        vols = [b.volume for b in group]
        known_volume = _nonnegative(vols, 'daily volume') is not None
        volume = float(sum(vols)) if known_volume else None
        dollar = float(sum(b.close * b.volume for b in group)) if known_volume else None
        candles.append(NativeBar(end=group[-1].end, available_from=group[-1].available_from,
                                 open=group[0].open, high=max(b.high for b in group),
                                 low=min(b.low for b in group), close=group[-1].close,
                                 volume=volume, dollar=dollar))
    return candles


def _nonnegative(values, name):
    """Volume/dollar path: None or a bad value means NOT_EVALUABLE, never a crash."""
    if any(v is None for v in values):
        return None
    if any(isinstance(v, bool) or not isinstance(v, Real) for v in values):
        raise TypeError(name + ' must be numeric scalars')
    arr = np.asarray(values, dtype=np.float64)
    if not np.isfinite(arr).all() or (arr < 0).any():
        return None
    return arr


def _measure(recipe, candles, feature=None):
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
        if recipe in ('native_gap_up_fate_v1', 'native_gap_down_fate_v1'):
            # candles[0] is the prior candle (evaluate_master requests lookback+1).
            up = recipe == 'native_gap_up_fate_v1'
            fate = {'filled': False, 'open': False, 'none': False}
            if up:
                gaps = [i for i in range(1, len(candles)) if opened[i] > high[i - 1]]
            else:
                gaps = [i for i in range(1, len(candles)) if opened[i] < low[i - 1]]
            if not gaps:
                fate['none'] = True
                return fate
            latest = gaps[-1]
            if up:
                filled = bool(low[latest:].min() <= high[latest - 1])
            else:
                filled = bool(high[latest:].max() >= low[latest - 1])
            fate['filled'] = filled
            fate['open'] = not filled
            return fate
        if recipe == 'native_inside_outside_seq_v1':
            # candles[0] is the prior candle; window = candles[1..N].
            n = len(candles) - 1
            inside = np.zeros(n, dtype=bool)
            outside = np.zeros(n, dtype=bool)
            for i in range(1, n + 1):
                inside[i - 1] = high[i] <= high[i - 1] and low[i] >= low[i - 1]
                outside[i - 1] = high[i] > high[i - 1] and low[i] < low[i - 1]
            run = best = 0
            for flag in inside:
                run = run + 1 if flag else 0
                best = max(best, run)
            after = any(inside[i] and outside[i + 1] for i in range(n - 1))
            return {'inside_max_run': best,
                    'outside_after_inside': bool(after),
                    'mostly_outside': bool(2 * int(outside.sum()) > n),
                    'none': bool(not inside.any() and not outside.any())}
        if recipe == 'native_run_biggest_move_ratio_v1':
            # candles[0] is the prior candle. ATR14 = mean(TR) over the last 14
            # window candles; requires lookback >= 14 and lookback+1 candles.
            n = len(candles) - 1
            if n < 14:
                return None
            prev_close = np.concatenate(([close[0]], close[:-1]))
            tr = np.maximum(high - low, np.maximum(np.abs(high - prev_close),
                                                   np.abs(low - prev_close)))
            atr14 = float(tr[-14:].mean(dtype=np.float64))
            sign = np.sign(close[1:] - opened[1:])
            best_run = None      # (length, biggest_body, most_recent_end)
            i = 0
            while i < n:
                if sign[i] == 0:
                    i += 1
                    continue
                j = i
                while j + 1 < n and sign[j + 1] == sign[i]:
                    j += 1
                seg = np.abs(close[1 + i:1 + j + 1] - opened[1 + i:1 + j + 1])
                cand = (j - i + 1, float(np.max(seg)), j)
                if best_run is None or cand[0] > best_run[0] or (
                        cand[0] == best_run[0] and (
                            cand[1] > best_run[1] or (
                                cand[1] == best_run[1] and cand[2] > best_run[2]))):
                    best_run = cand
                i = j + 1
            if best_run is None:
                return None
            biggest = best_run[1]
            if atr14 == 0:
                if biggest == 0:
                    return None      # 0/0 is unavailable, never invented
                return math.inf      # KNOWN signed infinity per ratio rule
            return float(biggest / atr14)
        if recipe == 'native_up_down_volume_dominance_v1':
            vol = _nonnegative([b.volume for b in candles], 'native volume')
            if vol is None:
                return None
            up = float(vol[body > 0].sum(dtype=np.float64))
            down = float(vol[body < 0].sum(dtype=np.float64))
            if up == 0 and down == 0:
                return None
            if down == 0:
                return math.inf      # all volume on up bars, KNOWN infinity
            if up == 0:
                return 0.0
            return up / down
        if recipe == 'native_volume_dry_up_at_low_v1':
            # candles[0..48] are the 49 prior bars backing the 50-bar median
            # (med50 = median of the 50 bars ending at the reference bar,
            # all strictly before D). Window = candles[49:].
            vol = _nonnegative([b.volume for b in candles], 'native volume')
            if vol is None:
                return None
            n = len(candles) - 49
            if n < 1:
                return None
            win_vol = vol[-n:]
            win_close = close[-n:]
            mult = float(feature['dry_up_mult'])

            def dry(j):
                abs_i = len(candles) - n + j
                med = float(np.median(vol[abs_i - 49:abs_i + 1]))
                if med == 0:
                    return None      # 50-bar median of zero volume: undefined
                return bool(win_vol[j] < mult * med)

            dry_low = dry(int(np.argmin(win_close)))   # first lowest close
            dry_high = dry(int(np.argmax(win_close)))  # first highest close
            if dry_low is None or dry_high is None:
                return None
            return {'at_low': dry_low and not dry_high,
                    'at_high': dry_high and not dry_low,
                    'both': dry_low and dry_high,
                    'none': not dry_low and not dry_high}
        if recipe == 'native_max_vol_position_v1':
            vol = _nonnegative([b.volume for b in candles], 'native volume')
            if vol is None:
                return None
            n = len(candles)
            edge = int(feature['max_vol_edge_bars'])
            pos = int(np.argmax(vol))                  # first max on tie
            at_price_low = pos == int(np.argmin(close))
            start = pos < edge
            end = (n - 1 - pos) < edge
            return {'at_price_low': bool(at_price_low),
                    'start': bool(not at_price_low and start),
                    'middle': bool(not at_price_low and not start and not end),
                    'end': bool(not at_price_low and not start and end)}
        if recipe in ('native_rsi_floor_v1', 'native_rsi_ceiling_v1'):
            # Wilder RSI(period) seeded with the simple average of the first
            # `period` changes over the fetched warmup, then smoothed forward
            # (all bars <= D-1). Window = last lookback candles. The three
            # baked thresholds partition the window extreme into 4 codes
            # (floor: count of thresholds with extreme >= t; ceiling: > t).
            period = int(feature['rsi_period'])
            changes = np.diff(close)
            if len(changes) < period:
                return None
            gains = np.maximum(changes, 0.0)
            losses = np.maximum(-changes, 0.0)
            avg_g = float(gains[:period].mean(dtype=np.float64))
            avg_l = float(losses[:period].mean(dtype=np.float64))
            values = []

            def rsi(ag, al):
                if al == 0:
                    return 100.0 if ag > 0 else None
                return 100.0 - 100.0 / (1.0 + ag / al)

            values.append(rsi(avg_g, avg_l))
            for j in range(period, len(changes)):
                avg_g = (avg_g * (period - 1) + gains[j]) / period
                avg_l = (avg_l * (period - 1) + losses[j]) / period
                values.append(rsi(avg_g, avg_l))
            lookback = len(values)                  # window bars
            if lookback < 1 or any(v is None for v in values):
                return None
            thresholds = sorted(float(feature[k]) for k in ('rsi_t1', 'rsi_t2', 'rsi_t3'))
            if recipe == 'native_rsi_floor_v1':
                extreme = min(values)
                return sum(1 for t in thresholds if extreme >= t)
            extreme = max(values)
            return sum(1 for t in thresholds if extreme > t)
        if recipe == 'native_ma_cross_v1':
            # MA from the L3 derivative (SMA_p / EMA_p, period baked in the
            # feature). candles[0:period] warm the MA (EMA seeded with the
            # SMA of the first period bars); window = last lookback candles,
            # plus one prior bar for the first cross check.
            period = int(feature['ma_period'])
            n = len(candles) - period
            if n < 2:
                return None
            # MA values for candle indices period-1 .. len-1 (the prior bar
            # plus the whole window): SMA = moving mean over `period` closes;
            # EMA seeded with the SMA of the first period closes.
            win_close = close
            if feature['ma_kind'] == 'SMA':
                ma = np.convolve(win_close, np.ones(period) / period, mode='valid')
            else:
                alpha = 2.0 / (period + 1)
                ma = np.empty(len(win_close) - period + 1, dtype=np.float64)
                ma[0] = float(win_close[:period].mean(dtype=np.float64))
                for j in range(period, len(win_close)):
                    ma[j - period + 1] = alpha * win_close[j] + (1 - alpha) * ma[j - period]
            diff = win_close[period - 1:] - ma
            up_cross = bool(any(diff[k - 1] <= 0 and diff[k] > 0
                                for k in range(1, len(diff))))
            down_cross = bool(any(diff[k - 1] >= 0 and diff[k] < 0
                                  for k in range(1, len(diff))))
            return {'up': bool(up_cross and not down_cross),
                    'down': bool(down_cross and not up_cross),
                    'both': bool(up_cross and down_cross),
                    'none': bool(not up_cross and not down_cross)}
        if recipe == 'native_volume_dominance_flip_v1':
            # Window split in half; a side is up-dominant when up-bar volume
            # strictly exceeds down-bar volume. to_up = early not up-dominant
            # and late up-dominant; to_down = mirror; none = same dominance
            # on both halves (incl. neither side dominant).
            vol = _nonnegative([b.volume for b in candles], 'native volume')
            if vol is None:
                return None
            n = len(candles)
            half = n // 2
            if half < 1 or n - half < 1:
                return None

            def up_dom(seg):
                b = close[seg] - opened[seg]
                up = float(vol[seg][b > 0].sum(dtype=np.float64))
                down = float(vol[seg][b < 0].sum(dtype=np.float64))
                return up > down

            early = up_dom(slice(0, half))
            late = up_dom(slice(half, n))
            return {'to_up': bool(not early and late),
                    'to_down': bool(early and not late),
                    'none': bool(early == late)}
        if recipe == 'native_maxvol_wick_v1':
            # candles[0] is the prior candle (TR base). Window's max-volume
            # bar: long lower wick (> v*ATR14) = bull, else long upper wick =
            # bear, else small; bull takes precedence when both exceed.
            vol = _nonnegative([b.volume for b in candles], 'native volume')
            if vol is None:
                return None
            n = len(candles) - 1
            if n < 14:
                return None
            prev_close = np.concatenate(([close[0]], close[:-1]))
            tr = np.maximum(high - low, np.maximum(np.abs(high - prev_close),
                                                   np.abs(low - prev_close)))
            atr14 = float(tr[-14:].mean(dtype=np.float64))
            if atr14 == 0:
                return None
            win_vol = vol[1:]
            i = 1 + int(np.argmax(win_vol))          # first max on tie
            v = float(feature['maxvol_wick_atr'])
            lower = float(min(opened[i], close[i]) - low[i])
            upper = float(high[i] - max(opened[i], close[i]))
            bull = lower > v * atr14
            bear = (not bull) and upper > v * atr14
            return {'bull_wick': bool(bull), 'bear_wick': bool(bear),
                    'small': bool(not bull and not bear)}
        if recipe == 'native_pullback_run_volume_ratio_v1':
            # Last leg = most recent run of >=2 same-sign bodies with at least
            # one opposite-sign bar after it (the pullback, through window
            # end). Ratio = mean pullback volume / mean leg volume, assigned
            # to bull_ratio (up leg) or bear_ratio (down leg); the other side
            # stays None -> NOT_EVALUABLE for its outcomes. Zero-volume leg:
            # skip to an earlier qualifying leg (ratio undefined, not 0/0=0).
            vol = _nonnegative([b.volume for b in candles], 'native volume')
            if vol is None:
                return None
            n = len(candles)
            sign = np.sign(close - opened)
            runs = []
            i = 0
            while i < n:
                if sign[i] == 0:
                    i += 1
                    continue
                j = i
                while j + 1 < n and sign[j + 1] == sign[i]:
                    j += 1
                runs.append((int(sign[i]), i, j))
                i = j + 1
            result = {'bull_ratio': None, 'bear_ratio': None}
            for sg, s, e in reversed(runs):
                if e - s + 1 < 2 or e == n - 1:
                    continue
                pull = [k for k in range(e + 1, n) if sign[k] != 0]
                if not pull or any(sign[k] == sg for k in pull):
                    continue
                leg_mean = float(vol[s:e + 1].mean(dtype=np.float64))
                if leg_mean == 0:
                    continue
                pull_mean = float(vol[pull].mean(dtype=np.float64))
                result['bull_ratio' if sg > 0 else 'bear_ratio'] = pull_mean / leg_mean
                break
            return result
        if recipe == 'native_volume_spike_v1':
            # candles[0:B-1] are the prior bars backing the per-bar baseline
            # median (B = baked C031 dial); window = candles[B-1:]. A window
            # bar is a spike when its volume exceeds mult * median of the B
            # bars ending at that bar (all <= D-1). yes_early/yes_late split
            # on the earliest spike (first half / second half of the window).
            vol = _nonnegative([b.volume for b in candles], 'native volume')
            if vol is None:
                return None
            base_n = int(feature['spike_baseline_bars'])
            n = len(candles) - (base_n - 1)
            if base_n < 2 or n < 1:
                return None
            win = vol[base_n - 1:]
            mult = float(feature['spike_mult'])
            earliest = None
            for j in range(n):
                abs_i = base_n - 1 + j
                med = float(np.median(vol[abs_i - base_n + 1:abs_i + 1]))
                if win[j] > mult * med:
                    earliest = j
                    break
            if earliest is None:
                return {'yes_early': False, 'yes_late': False, 'no': True}
            early = earliest < n // 2
            return {'yes_early': bool(early), 'yes_late': bool(not early),
                    'no': False}
        if recipe == 'native_volume_vs_own_past_v1':
            # candles[0:baseline] are the prior baseline bars; window = last
            # lookback candles. Source = raw share volume (RVOL20).
            base_n = int(feature['baseline_bars'])
            if len(candles) <= base_n:
                return None
            if feature['volume_source'] == 'dollar':
                vals = _nonnegative([b.dollar for b in candles], 'native dollar volume')
            else:
                vals = _nonnegative([b.volume for b in candles], 'native volume')
            if vals is None:
                return None
            win_mean = float(vals[base_n:].mean(dtype=np.float64))
            base_mean = float(vals[:base_n].mean(dtype=np.float64))
            if base_mean == 0:
                if win_mean == 0:
                    return None      # 0/0 is unavailable, never invented
                return math.inf      # KNOWN signed infinity per ratio rule
            return win_mean / base_mean
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


# facet -> spec. binding 'band': ratio/scalar band (mirror or signed thresholds).
# binding 'bool3': three mutually exclusive boolean outcomes, no registered cutoff.
# binding 'mixed': per-outcome declarations (boolean events + one cutoff rung).
FACETS = {
    'red_green_balance': dict(
        binding='band', mirror=True,
        recipe='native_body_colour_balance_v1', unit='green_body_sum_over_red_body_sum',
        outcomes=('green', 'red', 'even'), cutoff_id='S_ratio_band_1p5',
        transform_by_outcome={'green': 'identity', 'red': 'identity', 'even': 'mirror_min'},
        comparator_by_outcome={'green': '>', 'red': '<', 'even': '>='}),
    'last_green_vs_red': dict(
        binding='band', mirror=True,
        recipe='native_last_green_vs_red_v1', unit='latest_green_body_over_latest_red_body',
        outcomes=('green_bigger', 'red_bigger', 'similar'), cutoff_id='S_ratio_band_1p25',
        transform_by_outcome={'green_bigger': 'identity', 'red_bigger': 'identity', 'similar': 'mirror_min'},
        comparator_by_outcome={'green_bigger': '>', 'red_bigger': '<', 'similar': '>='}),
    'down_vs_up_moves': dict(
        binding='band', mirror=True,
        recipe='native_down_up_body_ratio_v1', unit='mean_down_body_over_mean_up_body',
        outcomes=('downs_bigger', 'ups_bigger', 'equal'), cutoff_id='S_ratio_band_1p25',
        transform_by_outcome={'downs_bigger': 'identity', 'ups_bigger': 'identity', 'equal': 'mirror_min'},
        comparator_by_outcome={'downs_bigger': '>', 'ups_bigger': '<', 'equal': '>='}),
    'wick_body': dict(
        binding='band', mirror=False,
        recipe='native_wick_balance_v1', unit='mean_upper_minus_lower_wick_over_range',
        outcomes=('upper_dominant', 'lower_dominant', 'balanced'), cutoff_id='C023_wick_body__scalar0p15',
        transform_by_outcome={'upper_dominant': 'identity', 'lower_dominant': 'identity', 'balanced': 'abs'},
        comparator_by_outcome={'upper_dominant': '>', 'lower_dominant': '<', 'balanced': '<='}),
    'run_biggest_move': dict(
        binding='band', mirror=True,
        recipe='native_run_biggest_move_ratio_v1', unit='biggest_body_in_longest_run_over_atr14',
        outcomes=('big', 'normal', 'small'), cutoff_id='C027_run_biggest_move__atr1p5',
        transform_by_outcome={'big': 'identity', 'normal': 'mirror_min', 'small': 'identity'},
        comparator_by_outcome={'big': '>', 'normal': '>=', 'small': '<'}),
    'gap_up': dict(
        binding='bool3', recipe='native_gap_up_fate_v1',
        unit='latest_gap_up_fate', outcomes=('filled', 'open', 'none'), cutoff_id=None),
    'gap_down': dict(
        binding='bool3', recipe='native_gap_down_fate_v1',
        unit='latest_gap_down_fate', outcomes=('filled', 'open', 'none'), cutoff_id=None),
    'inside_outside': dict(
        binding='mixed', recipe='native_inside_outside_seq_v1',
        unit='inside_outside_sequence',
        outcomes=('inside_cluster_ge', 'outside_after_inside', 'mostly_outside', 'none'),
        cutoff_id='C019_inside_outside__scalar2',
        # outcome -> (kind, comparator, threshold_source)  threshold_source:
        #   'cutoff' = the integer rung v; 'one' = literal 1
        outcome_spec={'inside_cluster_ge': ('integer_count', '>=', 'cutoff'),
                      'outside_after_inside': ('boolean', '=', 'one'),
                      'mostly_outside': ('boolean', '=', 'one'),
                      'none': ('boolean', '=', 'one')}),
    # ---- batch 3: volume group (share volume and dollar volume are native
    # fields of the price world; all evidence bars still end <= D-1) ----
    'dominance': dict(
        binding='band', mirror=True, l1_l3=(('volume', 'up_down_volume'),),
        recipe='native_up_down_volume_dominance_v1',
        unit='sum_volume_up_bars_over_sum_volume_down_bars',
        outcomes=('up_heavy', 'down_heavy', 'even'), cutoff_id='S_ratio_band_1p3',
        transform_by_outcome={'up_heavy': 'identity', 'down_heavy': 'identity',
                              'even': 'mirror_min'},
        comparator_by_outcome={'up_heavy': '>', 'down_heavy': '<', 'even': '>='}),
    'dry_up_at_low': dict(
        binding='mixed', l1_l3=(('volume', 'RVOL20'),),
        recipe='native_volume_dry_up_at_low_v1',
        unit='volume_dry_up_against_50bar_median_at_extreme_close',
        outcomes=('at_low', 'at_high', 'both', 'none'),
        cutoff_id='C032_dry_up_at_low__mult0p6',
        baked_map={'C032_dry_up_at_low__mult0p6': 'dry_up_mult'},
        outcome_spec={'at_low': ('boolean', '=', 'one'),
                      'at_high': ('boolean', '=', 'one'),
                      'both': ('boolean', '=', 'one'),
                      'none': ('boolean', '=', 'one')}),
    'max_vol_position': dict(
        binding='mixed', l1_l3=(('volume', 'RVOL20'),),
        recipe='native_max_vol_position_v1',
        unit='position_of_window_max_volume_bar',
        outcomes=('start', 'middle', 'at_price_low', 'end'),
        cutoff_id='C036_max_vol_position__bars2',
        baked_map={'C036_max_vol_position__bars2': 'max_vol_edge_bars'},
        outcome_spec={'start': ('boolean', '=', 'one'),
                      'middle': ('boolean', '=', 'one'),
                      'at_price_low': ('boolean', '=', 'one'),
                      'end': ('boolean', '=', 'one')}),
    'vs_own_past': dict(
        binding='band', mirror=True,
        l1_l3=(('volume', 'RVOL20'),),
        recipe='native_volume_vs_own_past_v1',
        unit='window_mean_volume_over_prior_baseline_mean_volume',
        outcomes=('high', 'normal', 'low'), cutoff_id='S_ratio_band_1p5',
        baked_cutoff_ids=('S_baseline_bars',),
        baked_map={'S_baseline_bars': 'baseline_bars'},
        volume_source_by_l3={'RVOL20': 'volume'},
        transform_by_outcome={'high': 'identity', 'normal': 'mirror_min', 'low': 'identity'},
        comparator_by_outcome={'high': '>', 'normal': '>=', 'low': '<'}),
    'spike': dict(
        binding='mixed', l1_l3=(('volume', 'RVOL20'),),
        recipe='native_volume_spike_v1',
        unit='earliest_volume_spike_over_baseline_median',
        outcomes=('yes_early', 'yes_late', 'no'),
        cutoff_id=None,
        baked_cutoff_ids=('C031_spike__bars50', 'S_vol_spike_mult'),
        baked_map={'C031_spike__bars50': 'spike_baseline_bars',
                   'S_vol_spike_mult': 'spike_mult'},
        outcome_spec={'yes_early': ('boolean', '=', 'one'),
                      'yes_late': ('boolean', '=', 'one'),
                      'no': ('boolean', '=', 'one')}),
    'maxvol_wick': dict(
        binding='mixed', l1_l3=(('volume', 'RVOL20'),),
        recipe='native_maxvol_wick_v1',
        unit='wick_size_on_max_volume_bar_over_atr14',
        outcomes=('bull_wick', 'bear_wick', 'small'), cutoff_id=None,
        baked_cutoff_ids=('C047_maxvol_wick__atr1',),
        baked_map={'C047_maxvol_wick__atr1': 'maxvol_wick_atr'},
        outcome_spec={'bull_wick': ('boolean', '=', 'one'),
                      'bear_wick': ('boolean', '=', 'one'),
                      'small': ('boolean', '=', 'one')}),
    'pullback_vs_run_volume': dict(
        binding='splitband', mirror=True, l1_l3=(('volume', 'RVOL20'),),
        recipe='native_pullback_run_volume_ratio_v1',
        unit='mean_pullback_volume_over_mean_leg_volume',
        outcomes=('bull_lighter', 'bull_similar', 'bull_heavier',
                  'bear_lighter', 'bear_similar', 'bear_heavier'),
        cutoff_id='S_ratio_band_1p3',
        feature_key_by_outcome={
            'bull_lighter': 'bull_ratio', 'bull_similar': 'bull_ratio',
            'bull_heavier': 'bull_ratio', 'bear_lighter': 'bear_ratio',
            'bear_similar': 'bear_ratio', 'bear_heavier': 'bear_ratio'},
        transform_by_outcome={
            'bull_lighter': 'identity', 'bull_similar': 'mirror_min',
            'bull_heavier': 'identity', 'bear_lighter': 'identity',
            'bear_similar': 'mirror_min', 'bear_heavier': 'identity'},
        comparator_by_outcome={
            'bull_lighter': '<', 'bull_similar': '>=', 'bull_heavier': '>',
            'bear_lighter': '<', 'bear_similar': '>=', 'bear_heavier': '>'}),
    'rsi_floor': dict(
        binding='mixed',
        l1_l3=tuple(('overbought_oversold', 'RSI' + str(n)) for n in (6, 12, 14, 24)),
        recipe='native_rsi_floor_v1', unit='minimum_window_rsi_threshold_code',
        outcomes=('below_extreme', 'low_band', 'mid_band', 'high_band'),
        cutoff_id=None,
        baked_cutoff_ids=('S_rsi_extreme_low', 'C221_rsi_floor__scalar40',
                          'C222_rsi_floor__scalar50'),
        baked_map={'S_rsi_extreme_low': 'rsi_t1',
                   'C221_rsi_floor__scalar40': 'rsi_t2',
                   'C222_rsi_floor__scalar50': 'rsi_t3'},
        l3_map={'RSI6': {'rsi_period': '6'}, 'RSI12': {'rsi_period': '12'},
                'RSI14': {'rsi_period': '14'}, 'RSI24': {'rsi_period': '24'}},
        outcome_spec={'below_extreme': ('integer_count', '=', 'code0'),
                      'low_band': ('integer_count', '=', 'code1'),
                      'mid_band': ('integer_count', '=', 'code2'),
                      'high_band': ('integer_count', '=', 'code3')}),
    'rsi_ceiling': dict(
        binding='mixed',
        l1_l3=tuple(('overbought_oversold', 'RSI' + str(n)) for n in (6, 12, 14, 24)),
        recipe='native_rsi_ceiling_v1', unit='maximum_window_rsi_threshold_code',
        outcomes=('above_extreme', 'high_band', 'mid_band', 'low_band'),
        cutoff_id=None,
        baked_cutoff_ids=('S_rsi_extreme_high', 'C224_rsi_ceiling__scalar60',
                          'C225_rsi_ceiling__scalar50'),
        baked_map={'S_rsi_extreme_high': 'rsi_t1',
                   'C224_rsi_ceiling__scalar60': 'rsi_t2',
                   'C225_rsi_ceiling__scalar50': 'rsi_t3'},
        l3_map={'RSI6': {'rsi_period': '6'}, 'RSI12': {'rsi_period': '12'},
                'RSI14': {'rsi_period': '14'}, 'RSI24': {'rsi_period': '24'}},
        outcome_spec={'above_extreme': ('integer_count', '=', 'code3'),
                      'high_band': ('integer_count', '=', 'code2'),
                      'mid_band': ('integer_count', '=', 'code1'),
                      'low_band': ('integer_count', '=', 'code0')}),
    'fresh_cross': dict(
        binding='mixed',
        l1_l3=(('moving_averages', 'SMA20'), ('moving_averages', 'SMA50'),
               ('moving_averages', 'SMA200'), ('moving_averages', 'EMA21')),
        recipe='native_ma_cross_v1', unit='close_ma_cross_events_in_window',
        outcomes=('up', 'down', 'both', 'none'), cutoff_id=None,
        l3_map={'SMA20': {'ma_kind': 'SMA', 'ma_period': '20'},
                'SMA50': {'ma_kind': 'SMA', 'ma_period': '50'},
                'SMA200': {'ma_kind': 'SMA', 'ma_period': '200'},
                'EMA21': {'ma_kind': 'EMA', 'ma_period': '21'}},
        outcome_spec={'up': ('boolean', '=', 'one'), 'down': ('boolean', '=', 'one'),
                      'both': ('boolean', '=', 'one'), 'none': ('boolean', '=', 'one')}),
    'flip': dict(
        binding='mixed', l1_l3=(('volume', 'up_down_volume'),),
        recipe='native_volume_dominance_flip_v1',
        unit='up_down_volume_dominance_flip_in_window',
        outcomes=('to_up', 'to_down', 'none'), cutoff_id=None,
        outcome_spec={'to_up': ('boolean', '=', 'one'),
                      'to_down': ('boolean', '=', 'one'),
                      'none': ('boolean', '=', 'one')}),
}

for _spec in FACETS.values():
    _spec.setdefault('l1_l3', (('candles', 'OHLC'),))
    _spec.setdefault('baked_cutoff_ids', ())
    _spec.setdefault('baked_map', {})

NOT_EVALUABLE = ('Fewer completed native sessions than lookback*candle_days (+1 prior candle where a '
                 'candle pair is required, +14 for the ATR14 base of run_biggest_move), a missing/late '
                 'native bar, a non-positive or non-finite price, a zero total body on both sides '
                 '(colour-balance facets), a missing green or red bar (last_green_vs_red, down_vs_up_moves), '
                 'an all-zero-range window (wick_body), no monochromatic body run (run_biggest_move), '
                 'or a 0/0 ratio (zero body AND zero ATR14) -> NOT_EVALUABLE (excluded, never NO). '
                 'Volume facets add: a missing/negative/non-finite native volume or dollar field, '
                 'all-zero window volume on both sides (dominance), a zero 50-bar median volume '
                 '(dry_up_at_low), or a zero baseline mean with zero window mean (vs_own_past).')
KNOWABLE = ('Uses only native candles with available_from <= setup date D and end < D '
            '(last completed candle = D-1); D open is execution only. Bars are strict '
            + BAR_DEFINITION + ' slot groups; no day-D candle.')
VIEWPORT = ('Purple recolour of the D-1 native candle if YES; ratio/scalar value printed on the '
            'item pane header; no circles.')


def _ratio_thresholds(spec, v):
    """Exact decimal band thresholds; mirror bands take the lower side as 1/v."""
    if not spec['mirror']:
        high = canonical_number(v)
        return high, '-' + high
    high = canonical_number(v)
    low = canonical_number(str(Decimal(1) / Decimal(v)))
    return high, low


def _definition(spec, timeframe, lookback, outcome, transform, operator, threshold,
                feature_kind, source_variant_id, source_question_id, expression_suffix='',
                feature_extra=None):
    scalar = dict(recipe=spec['recipe'], candle_days=timeframe, lookback=lookback,
                  transform=transform, bar_definition=BAR_DEFINITION,
                  price_basis=PRICE_BASIS, numeric_contract=CONTRACT)
    scalar.update(feature_extra or {})
    # The outcome is part of the question's meaning: several outcomes can share
    # one measurement (same feature, comparator and threshold) yet ask different
    # questions (e.g. fresh_cross up/down/both/none all boolean ==1 on the same
    # cross-event dict). Without it in the semantic identity, the build's
    # question_id dedupe silently kept only the first outcome of such facets.
    semantic = dict(feature=scalar, comparator=operator, comparison_threshold=threshold,
                    outcome=outcome)
    expression = (spec['recipe'] + '(' + str(timeframe) + 'd,N=' + str(lookback) + ')'
                  + expression_suffix)
    return dict(
        question_id='BM1-' + identity(semantic), feature_id='BF1-' + identity(scalar),
        feature=scalar, feature_expression=expression, feature_kind=feature_kind,
        formula='(' + expression + ') ' + operator + ' ' + threshold,
        answer_set=['NO', 'YES'], comparator=operator, comparison_threshold=threshold,
        feature_unit=spec['unit'], source_question_id=source_question_id,
        source_variant_id=source_variant_id, source_outcome=outcome,
        expression='NOT_YET', missing='tested_master_binding;pending_renderer_and_derive',
        definition_status='BOUND', chart_status='PENDING', derive_status='PENDING',
        mine_status='PENDING')


def _bind_facet(tree_row, variant, spec):
    settings = dict(variant.settings)
    timeframe, lookback = map(int, tree_row['L2_timeframe'].split('x'))
    if timeframe not in range(1, 22) or lookback < 1:
        raise ValueError('registered native timeframe/lookback required')

    # Baked dials are consumed inside the measurement (they shape the feature,
    # not the comparison threshold); every registered dial must be accounted
    # for by exactly one of the threshold dial or the baked map. A None
    # cutoff_id means the facet has no threshold dial (all-boolean outcomes).
    allowed = ({spec['cutoff_id']} | set(spec['baked_cutoff_ids'])) - {None}
    if spec['binding'] == 'bool3':
        if settings:
            raise ValueError('bool3 binding takes no registered cutoff: ' + str(sorted(settings)))
        feature_extra = {}
    elif set(settings) != allowed:
        raise ValueError('master binding cannot silently ignore a cutoff: ' + str(sorted(settings)))
    else:
        feature_extra = {key: settings[dial] for dial, key in spec['baked_map'].items()}
    if 'volume_source_by_l3' in spec:
        feature_extra['volume_source'] = spec['volume_source_by_l3'][tree_row['L3_derivative']]
    if 'l3_map' in spec:
        feature_extra.update(spec['l3_map'][tree_row['L3_derivative']])

    if spec['binding'] == 'bool3':
        return [_definition(spec, timeframe, lookback, outcome, 'identity', '=', '1',
                            'boolean', variant.variant_id, variant.source_question_id,
                            ';' + outcome, feature_extra)
                for outcome in spec['outcomes']]

    if spec['binding'] == 'mixed':
        v = settings[spec['cutoff_id']] if spec['cutoff_id'] is not None else None
        result = []
        for outcome in spec['outcomes']:
            kind, operator, tsource = spec['outcome_spec'][outcome]
            if tsource == 'cutoff':
                threshold = canonical_number(v)
            elif tsource.startswith('code'):
                threshold = tsource[4:]
            else:
                threshold = '1'
            suffix = ';max_inside_run' if tsource == 'cutoff' else ';' + outcome
            result.append(_definition(spec, timeframe, lookback, outcome, 'identity',
                                      operator, threshold, kind, variant.variant_id,
                                      variant.source_question_id, suffix, feature_extra))
        return result

    # binding == 'splitband': one measured dict, two ratio slots (bull/bear);
    # per-outcome ratio_key selects the slot; thresholds mirror the band dial.
    if spec['binding'] == 'splitband':
        v = settings[spec['cutoff_id']]
        high, low = _ratio_thresholds(spec, v)
        result = []
        for outcome in spec['outcomes']:
            transform = spec['transform_by_outcome'][outcome]
            operator = spec['comparator_by_outcome'][outcome]
            if operator == '>':
                threshold = high
            elif operator == '<':
                threshold = low
            else:
                threshold = low if spec['mirror'] else high
            extra = dict(feature_extra)
            extra['ratio_key'] = spec['feature_key_by_outcome'][outcome]
            suffix = (';mirror_min' if transform == 'mirror_min' else '')
            suffix += ';' + extra['ratio_key']
            result.append(_definition(spec, timeframe, lookback, outcome, transform,
                                      operator, threshold, 'continuous', variant.variant_id,
                                      variant.source_question_id, suffix, extra))
        return result

    # binding == 'band'
    v = settings[spec['cutoff_id']]
    high, low = _ratio_thresholds(spec, v)
    result = []
    for outcome in spec['outcomes']:
        transform = spec['transform_by_outcome'][outcome]
        operator = spec['comparator_by_outcome'][outcome]
        if operator == '>':
            threshold = high
        elif operator == '<':
            threshold = low
        else:  # '>=' band edge: ratio facets use the mirror side; signed facets reuse high
            threshold = low if spec['mirror'] else high
        suffix = (';mirror_min' if transform == 'mirror_min'
                  else ';abs' if transform == 'abs' else '')
        result.append(_definition(spec, timeframe, lookback, outcome, transform,
                                  operator, threshold, 'continuous', variant.variant_id,
                                  variant.source_question_id, suffix, feature_extra))
    return result


def bind_master_question(tree_row, variant):
    """Bind a canonical source question+variant to strict binary definitions.

    Kimi candle/volume facets bind here; everything else falls through to the
    reference price binders, which raise NotImplementedError when unbound.
    """
    spec = FACETS.get(tree_row['L4_analysis'])
    if (tree_row['part'] == 'base' and spec is not None
            and (tree_row['L1_type'], tree_row['L3_derivative']) in spec['l1_l3']):
        if tree_row['question_id'] != variant.source_question_id:
            raise ValueError('source tree and variant question differ')
        return _bind_facet(tree_row, variant, spec)
    return _bind_gpt_price(tree_row, variant)


_MASTER_RECIPES = {spec['recipe'] for spec in FACETS.values()}
# Recipes that compare each window candle with its predecessor need one extra
# native candle before the window (gaps, inside/outside, ATR14 warmup); the
# 50-bar median volume recipes need 49 prior bars; vs_own_past reads its
# baseline length from the feature (baked S_baseline_bars dial).
_EXTRA_PRIOR = {'native_gap_up_fate_v1': 1, 'native_gap_down_fate_v1': 1,
                'native_inside_outside_seq_v1': 1, 'native_run_biggest_move_ratio_v1': 1,
                'native_volume_dry_up_at_low_v1': 49, 'native_maxvol_wick_v1': 1}
_CATEGORICAL_RECIPES = {'native_gap_up_fate_v1', 'native_gap_down_fate_v1',
                        'native_inside_outside_seq_v1', 'native_volume_dry_up_at_low_v1',
                        'native_max_vol_position_v1', 'native_volume_spike_v1',
                        'native_maxvol_wick_v1', 'native_volume_dominance_flip_v1',
                        'native_ma_cross_v1'}


def evaluate_master(definition, bars, setup_date, expected_slot):
    feature = definition['feature']
    if feature['recipe'] in _MASTER_RECIPES:
        extra = _EXTRA_PRIOR.get(feature['recipe'], 0)
        if feature['recipe'] == 'native_volume_vs_own_past_v1':
            extra = int(feature['baseline_bars'])  # baked S_baseline_bars dial
        if feature['recipe'] == 'native_volume_spike_v1':
            extra = int(feature['spike_baseline_bars']) - 1  # baked C031 dial
        if feature['recipe'] in ('native_rsi_floor_v1', 'native_rsi_ceiling_v1'):
            extra = int(feature['rsi_period'])               # RSI seed warmup
        if feature['recipe'] == 'native_ma_cross_v1':
            extra = int(feature['ma_period'])                # MA warmup
        lookback = feature['lookback'] + extra
        candles = _tf_window(bars, setup_date, expected_slot, lookback, feature['candle_days'])
        measured = None if candles is None else _measure(feature['recipe'], candles, feature)
        if feature['recipe'] in _CATEGORICAL_RECIPES:
            if measured is None:
                value = None
            else:
                outcome = definition['source_outcome']
                if feature['recipe'] == 'native_inside_outside_seq_v1' and outcome == 'inside_cluster_ge':
                    value = measured['inside_max_run']
                else:
                    value = bool(measured[outcome])
            return evaluate_binary(value, definition['comparator'],
                                   definition['comparison_threshold'],
                                   feature_kind=definition['feature_kind'])
        raw = measured
        if 'ratio_key' in feature:
            raw = None if measured is None else measured[feature['ratio_key']]
        value = None if raw is None else _apply_transform(raw, feature['transform'])
        return evaluate_binary(value, definition['comparator'],
                               definition['comparison_threshold'],
                               feature_kind=definition['feature_kind'])
    # GPT integration fix (PR #179, ported): the reference fallback measures
    # native candles on the fixed slot//k calendar, not daily slots; adapt.
    if feature['recipe'] not in ('native_intraday_change_fraction_v1',
                                 'native_interday_change_fraction_v1',
                                 'native_close_streak_balance_v1'):
        raise NotImplementedError('unbound canonical master feature: ' + feature['recipe'])
    needed = feature['lookback'] + (feature['recipe'] == 'native_close_streak_balance_v1')
    candles = _tf_window(bars, setup_date, expected_slot, needed, feature['candle_days'])
    if candles is None:
        return evaluate_binary(None, definition['comparator'],
                               definition['comparison_threshold'],
                               feature_kind=definition['feature_kind'])
    last_native = (expected_slot + 1) // feature['candle_days'] - 1
    native = {last_native - len(candles) + 1 + i: bar for i, bar in enumerate(candles)}
    return _eval_gpt_price(definition, native, setup_date, last_native)

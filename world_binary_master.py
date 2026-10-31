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
from numbers import Integral, Real
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


def _ma_series(feature, close):
    """Registered native TA-Lib SMA/EMA over the supplied source history.

    Match world_timeframes.parameter_variants, including initialization and
    float64 operation order. Entry k corresponds to candle index p-1+k.
    The facet window is selected only after calculating the native series.
    """
    import talib
    period = int(feature['ma_period'])
    if len(close) < period:
        return None
    kind = feature['ma_kind']
    if kind not in ('SMA', 'EMA'):
        raise NotImplementedError('unregistered moving average: ' + kind)
    return getattr(talib, kind)(np.asarray(close, dtype=np.float64), timeperiod=period)[period - 1:]


def _native_ma_history(bars, setup_date, expected_slot, candle_days):
    """Complete native groups from supplied history, aligned to shared slots.

    As in frozen world_timeframes.completed_candles, omit partial IPO/halt
    groups. A present but unavailable/invalid history bar cannot become known
    indicator state. Nothing after the requested completed group is read.
    """
    last = ((expected_slot + 1) // candle_days) * candle_days - 1
    groups = sorted({int(slot) // candle_days for slot in bars
                     if isinstance(slot, Integral) and not isinstance(slot, (bool, np.bool_))
                     and 0 <= slot <= last})
    complete = [g for g in groups if all(slot in bars for slot in
                range(g * candle_days, (g + 1) * candle_days))]
    # Validate/aggregate contiguous runs in bulk, preserving the existing raw
    # bar checks without a separate NumPy allocation for every daily candle.
    runs = []
    for group in complete:
        if runs and group == runs[-1][1] + 1:
            runs[-1][1] = group
        else:
            runs.append([group, group])
    history = []
    for first, end in runs:
        candles = _tf_window(bars, setup_date, (end + 1) * candle_days - 1,
                             end - first + 1, candle_days)
        if candles is None:
            return None
        if history and candles[0].end <= history[-1].end:
            raise ValueError('native history ends must increase with shared slot')
        history.extend(candles)
    return history or None


def _ema_series(values, period):
    alpha = 2.0 / (period + 1)
    out = np.empty(len(values) - period + 1, dtype=np.float64)
    out[0] = float(values[:period].mean(dtype=np.float64))
    for j in range(period, len(values)):
        out[j - period + 1] = alpha * values[j] + (1 - alpha) * out[j - period]
    return out


def _osc_series(feature, close, high, low):
    """Oscillator series per the L3 derivative (documented seeding per kind)
    and its comparison line, as equal-length float arrays covering the LAST
    len(series) fetched bars. The line is the definitional constant
    (midline for RSI/Stoch/WillR/ROC) or the MACD signal series.
    None -> NOT_EVALUABLE (a zero 14-bar range or flat RSI is undefined,
    never invented)."""
    kind = feature['osc_kind']
    if kind == 'RSI':
        period = int(feature['osc_period'])
        changes = np.diff(close)
        if len(changes) < period:
            return None
        gains = np.maximum(changes, 0.0)
        losses = np.maximum(-changes, 0.0)
        avg_g = float(gains[:period].mean(dtype=np.float64))
        avg_l = float(losses[:period].mean(dtype=np.float64))

        def rsi(ag, al):
            if al == 0:
                return 100.0 if ag > 0 else None
            return 100.0 - 100.0 / (1.0 + ag / al)

        vals = [rsi(avg_g, avg_l)]
        for j in range(period, len(changes)):
            avg_g = (avg_g * (period - 1) + gains[j]) / period
            avg_l = (avg_l * (period - 1) + losses[j]) / period
            vals.append(rsi(avg_g, avg_l))
        if any(v is None for v in vals):
            return None
        series = np.asarray(vals, dtype=np.float64)
        line = np.full(series.shape, float(feature['cross_line']))
    elif kind == 'STOCH':
        period = int(feature['osc_period'])
        slow = int(feature['osc_slow'])
        t0 = period - 1
        raw = np.empty(len(close) - t0, dtype=np.float64)
        for t in range(t0, len(close)):
            hh = float(high[t - period + 1:t + 1].max())
            ll = float(low[t - period + 1:t + 1].min())
            if hh == ll:
                return None
            raw[t - t0] = 100.0 * (close[t] - ll) / (hh - ll)
        if len(raw) < slow:
            return None
        kernel = np.ones(slow) / slow
        series = np.convolve(raw, kernel, mode='valid')
        line = np.full(series.shape, float(feature['cross_line']))
    elif kind == 'WILLR':
        import talib
        period = int(feature['osc_period'])
        if len(close) < period:
            return None
        t0 = period - 1
        for t in range(t0, len(close)):
            hh = float(high[t - period + 1:t + 1].max())
            ll = float(low[t - period + 1:t + 1].min())
            if hh == ll:
                return None
        # Match the registered negative-valued WILLR field, including the
        # native operation order. Keep the declared zero-range NI policy.
        series = talib.WILLR(np.asarray(high, dtype=np.float64),
                             np.asarray(low, dtype=np.float64),
                             np.asarray(close, dtype=np.float64),
                             timeperiod=period)[t0:]
        line = np.full(series.shape, float(feature['cross_line']))
    elif kind == 'ROC':
        period = int(feature['osc_period'])
        if len(close) <= period:
            return None
        base = close[:-period]
        if (base <= 0).any():
            return None
        series = (close[period:] / base - 1.0) * 100.0
        line = np.full(series.shape, float(feature['cross_line']))
    elif kind == 'MACD':
        fast = _ema_series(close, int(feature['osc_fast']))
        slow = _ema_series(close, int(feature['osc_slow']))
        macd = fast[-len(slow):] - slow     # bars slow_p-1 .. end
        if len(macd) < int(feature['osc_signal']):
            return None
        line = _ema_series(macd, int(feature['osc_signal']))
        series = macd[-len(line):]
    else:
        raise NotImplementedError('unregistered oscillator kind: ' + kind)
    return series, line


def _split_segments(close):
    """Split a window at its FIRST lowest close (argmin; on a plateau the
    earliest lowest bar). The pivot bar belongs to BOTH legs: the decline
    into it and the rally out of it. Returns (decline_slice, rally_slice)."""
    k = int(np.argmin(close))
    return slice(0, k + 1), slice(k, len(close))


def _rsi_at(close, period, idx):
    """Wilder RSI(period) at absolute bar idx, seeded with the simple average
    of the first `period` changes (same seeding as the L3 RSI recipes).
    Needs idx >= period; None when the seeding window is all-flat (0/0)."""
    changes = np.diff(close[:idx + 1])
    if len(changes) < period:
        return None
    gains = np.maximum(changes, 0.0)
    losses = np.maximum(-changes, 0.0)
    ag = float(gains[:period].mean(dtype=np.float64))
    al = float(losses[:period].mean(dtype=np.float64))
    if al == 0:
        if ag == 0:
            return None
        val = 100.0
    else:
        val = 100.0 - 100.0 / (1.0 + ag / al)
    for j in range(period, len(changes)):
        ag = (ag * (period - 1) + gains[j]) / period
        al = (al * (period - 1) + losses[j]) / period
        if al == 0:
            if ag == 0:
                return None
            val = 100.0
        else:
            val = 100.0 - 100.0 / (1.0 + ag / al)
    return val


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
            # Native MA state uses supplied history; only the last lookback
            # candles plus the prior anchor participate in the facet.
            period = int(feature['ma_period'])
            ma = _ma_series(feature, close)
            count = int(feature['lookback']) + 1
            if ma is None or len(ma) < count:
                return None
            diff = (close[period - 1:] - ma)[-count:]
            if not np.isfinite(diff).all():
                return None
            up_cross = bool(any(diff[k - 1] <= 0 and diff[k] > 0
                                for k in range(1, len(diff))))
            down_cross = bool(any(diff[k - 1] >= 0 and diff[k] < 0
                                  for k in range(1, len(diff))))
            return {'up': bool(up_cross and not down_cross),
                    'down': bool(down_cross and not up_cross),
                    'both': bool(up_cross and down_cross),
                    'none': bool(not up_cross and not down_cross)}
        if recipe == 'native_ma_slope_v1':
            # Percent change from first to last WINDOW native MA, excluding
            # its prior anchor. Earlier history initializes the series only.
            period = int(feature['ma_period'])
            ma = _ma_series(feature, close)
            count = int(feature['lookback'])
            if count < 2 or ma is None or len(ma) < count:
                return None
            ma = ma[-count:]
            first, last = float(ma[0]), float(ma[-1])
            if first <= 0 or not np.isfinite(first) or not np.isfinite(last):
                return None
            return (last / first - 1.0) * 100.0
        if recipe == 'native_osc_cross_v1':
            # Oscillator from the L3 derivative crosses its definitional
            # midline/signal within the window (the prior bar anchors the
            # first check). All bars end <= D-1.
            lb = int(feature['lookback'])
            osc = _osc_series(feature, close, high, low)
            if osc is None:
                return None
            series, line_series = osc
            if len(series) < lb + 1:
                return None
            a = series[-(lb + 1):]
            b = line_series[-(lb + 1):]
            up_cross = bool(any(a[k - 1] <= b[k - 1] and a[k] > b[k]
                                for k in range(1, len(a))))
            down_cross = bool(any(a[k - 1] >= b[k - 1] and a[k] < b[k]
                                  for k in range(1, len(a))))
            return {'up': bool(up_cross and not down_cross),
                    'down': bool(down_cross and not up_cross),
                    'both': bool(up_cross and down_cross),
                    'none': bool(not up_cross and not down_cross)}
        if recipe == 'native_ma_cross_count_v1':
            # Number of times price crossed the L3 MA within the window (the
            # prior bar anchors the first check). Bucket edges are the two
            # baked scalar dials: code 0 = no cross; 1 = 1..t1; 2 = t1+1..t2;
            # 3 = more than t2. A degenerate pairing (t2 < t1) leaves bucket 2
            # empty -> NOT_EVALUABLE rather than a invented bucket.
            period = int(feature['ma_period'])
            ma = _ma_series(feature, close)
            size = int(feature['lookback']) + 1
            if ma is None or len(ma) < size:
                return None
            diff = (close[period - 1:] - ma)[-size:]
            if not np.isfinite(diff).all():
                return None
            count = 0
            for k in range(1, len(diff)):
                if ((diff[k - 1] <= 0 and diff[k] > 0)
                        or (diff[k - 1] >= 0 and diff[k] < 0)):
                    count += 1
            t1 = int(feature['cross_low_edge'])
            t2 = int(feature['cross_high_edge'])
            if t2 < t1:
                return None
            if count == 0:
                return 0
            return 1 + int(count > t1) + int(count > t2)
        if recipe == 'native_shock_v1':
            # candles[0:base_n] are the prior bars backing the baseline median
            # bar range; window = candles[base_n:]. Bucket edges are the two
            # baked dials: none = biggest window range < t1 x median; mid =
            # t1..t2 inclusive; big = above t2. Timing = position of the
            # first max-range window bar (early = first half). A zero median
            # baseline range is undefined -> NOT_EVALUABLE.
            base_n = int(feature['baseline_bars'])
            if len(candles) <= base_n:
                return None
            med = float(np.median((high - low)[:base_n]))
            if med <= 0:
                return None
            win = (high - low)[base_n:]
            i = int(np.argmax(win))              # first max on tie
            ratio = float(win[i]) / med
            t1 = float(feature['shock_low_mult'])
            t2 = float(feature['shock_high_mult'])
            if t2 < t1:
                return None
            early = i < len(win) // 2
            mid = t1 <= ratio <= t2
            big = ratio > t2
            return {'none': bool(ratio < t1),
                    'mid_early': bool(mid and early),
                    'mid_late': bool(mid and not early),
                    'big_early': bool(big and early),
                    'big_late': bool(big and not early)}
        if recipe == 'native_osc_zone_share_v1':
            # Share of window bars with the L3 oscillator in its canonical
            # zone (zone edges are definitional constants of the oscillator,
            # declared in the feature). A category wins when its share is
            # strictly above the baked majority_pct dial (">60% rule" at the
            # default); if several categories pass (only possible below 50%)
            # precedence is high > low > mid; otherwise mixed.
            lb = int(feature['lookback'])
            osc = _osc_series(feature, close, high, low)
            if osc is None:
                return None
            series, _line = osc
            if len(series) < lb:
                return None
            win = series[-lb:]
            zh = float(feature['zone_high'])
            zl = float(feature['zone_low'])
            pct = float(feature['majority_pct'])
            hi = float((win >= zh).sum(dtype=np.float64)) * 100.0 / lb
            lo = float((win <= zl).sum(dtype=np.float64)) * 100.0 / lb
            mid = 100.0 - hi - lo
            if hi > pct:
                winner = 'mostly_high'
            elif lo > pct:
                winner = 'mostly_low'
            elif mid > pct:
                winner = 'mostly_mid'
            else:
                winner = 'mixed'
            return {'mostly_high': winner == 'mostly_high',
                    'mostly_low': winner == 'mostly_low',
                    'mostly_mid': winner == 'mostly_mid',
                    'mixed': winner == 'mixed'}
        if recipe == 'native_full_stack_streak_v1':
            # Longest run of consecutive WINDOW bars in full bull order
            # (close > SMA10 > SMA20 > SMA50 > SMA200, all strict) and in
            # full bear order (mirrored). Bucket edges are the four baked
            # scalar dials, read as contiguous ranges {0} | [1, e1] |
            # [e_lo, e_hi] | [e2, inf); a non-contiguous OAT pairing
            # (e_lo != e1+1 or e2 != e_hi+1) -> NOT_EVALUABLE.
            lb = int(feature['lookback'])
            e1 = int(feature['streak_low_edge'])
            e_lo = int(feature['streak_mid_lo'])
            e_hi = int(feature['streak_mid_hi'])
            e2 = int(feature['streak_high_edge'])
            if e_lo != e1 + 1 or e2 != e_hi + 1:
                return None
            mas = {}
            for p in (10, 20, 50, 200):
                mas[p] = _ma_series(dict(feature, ma_kind='SMA', ma_period=str(p)),
                                    close)
            if any(mas[p] is None for p in mas) or len(mas[200]) < lb:
                return None
            idx = np.arange(199, len(close))[-lb:]
            aligned = {p: mas[p][idx - p + 1] for p in (10, 20, 50, 200)}
            if not all(np.isfinite(a).all() for a in aligned.values()):
                return None
            c = close[idx]
            bull = ((c > aligned[10]) & (aligned[10] > aligned[20])
                    & (aligned[20] > aligned[50]) & (aligned[50] > aligned[200]))
            bear = ((c < aligned[10]) & (aligned[10] < aligned[20])
                    & (aligned[20] < aligned[50]) & (aligned[50] < aligned[200]))

            def _longest_run(mask):
                best = cur = 0
                for v in mask:
                    cur = cur + 1 if v else 0
                    best = max(best, cur)
                return best

            def _bucket(s):
                if s == 0:
                    return 0
                if s <= e1:
                    return 1
                if s <= e_hi:
                    return 2
                return 3

            names = ('zero', 'low', 'mid', 'high')
            out = {}
            for direction, mask in (('bull', bull), ('bear', bear)):
                code = _bucket(_longest_run(mask))
                for i, name in enumerate(names):
                    out[direction + '_' + name] = code == i
            return out
        if recipe == 'native_ma30_side_streak_v1':
            # Current run of closes above (bull) or below (bear) SMA30 at the
            # window end, bucketed by the two baked scalar edges, crossed with
            # record = current run strictly longer than the longest above/below
            # run in the baked prior history. The current run may extend into
            # the prior bars (it is "as of D-1"); a last close exactly on the
            # SMA30, or fewer prior bars than the baked history, ->
            # NOT_EVALUABLE.
            lb = int(feature['lookback'])
            hist = int(feature['long_history_bars'])
            e1 = int(feature['streak_short_edge'])
            e2 = int(feature['streak_long_edge'])
            ma = _ma_series(dict(feature, ma_kind='SMA', ma_period='30'), close)
            if ma is None or len(ma) < hist + lb:
                return None
            # The current run can extend into earlier supplied history. Only
            # its record comparator is limited to the baked H prior bars.
            aligned = ma
            c = close[29:]
            if not np.isfinite(aligned).all():
                return None
            side = c > aligned                 # True = above, False = below
            if c[-1] == aligned[-1]:
                return None
            above = bool(c[-1] > aligned[-1])
            run = 0
            for v in reversed(side):
                if bool(v) == above:
                    run += 1
                else:
                    break
            prior = side[-(hist + lb):-lb]
            best = cur = 0
            for v in prior:
                if v:
                    cur += 1
                    best = max(best, cur)
                else:
                    cur = 0
            cur = 0
            for v in prior:
                if not v:
                    cur += 1
                    best = max(best, cur)
                else:
                    cur = 0
            record = run > best
            if run < e1:
                band = 'short'
            elif run <= e2:
                band = 'mid'
            else:
                band = 'long'
            key = ('above' if above else 'below') + '_' + band + (
                '_record' if record else '_not')
            outcomes = tuple(s + '_' + b + r for s in ('above', 'below')
                             for b in ('short', 'mid', 'long')
                             for r in ('_record', '_not'))
            return {o: o == key for o in outcomes}
        if recipe == 'native_osc_swing_speed_v1':
            # Latest COMPLETE cross-zone swing of the L3 oscillator inside the
            # window: bear = a bar >= zone_high with a LATER bar <= zone_low
            # (bull mirrored). Take the latest ending touch j, then the latest
            # starting touch i before j; swing length = j - i (0 = same-bar
            # round trip). The three baked scalar dials read as contiguous
            # ranges: <=e1 short | [e_lo,e_hi] mid | >e_hi long, requiring
            # e_lo == e1+1 (a non-contiguous OAT pairing -> NOT_EVALUABLE);
            # no complete swing in the window -> none. Both directions are
            # measured independently and may both fire.
            lb = int(feature['lookback'])
            e1 = int(feature['swing_low_edge'])
            e_lo = int(feature['swing_mid_lo'])
            e_hi = int(feature['swing_mid_hi'])
            if e_lo != e1 + 1:
                return None
            osc = _osc_series(feature, close, high, low)
            if osc is None:
                return None
            series, _line = osc
            if len(series) < lb:
                return None
            win = series[-lb:]
            zh = float(feature['zone_high'])
            zl = float(feature['zone_low'])
            n = len(win)
            out = {}
            for direction, start_cond, end_cond in (
                    ('bear', lambda v: v >= zh, lambda v: v <= zl),
                    ('bull', lambda v: v <= zl, lambda v: v >= zh)):
                length = None
                ends = [j for j in range(n) if end_cond(win[j])]
                if ends:
                    j = ends[-1]
                    starts = [i for i in range(j) if start_cond(win[i])]
                    if starts:
                        length = j - starts[-1]
                if length is None:
                    band = 'none'
                elif length <= e1:
                    band = 'short'
                elif length <= e_hi:
                    band = 'mid'
                else:
                    band = 'long'
                for b in ('short', 'mid', 'long', 'none'):
                    out[direction + '_' + b] = band == b
            return out
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
        if recipe == 'native_segment_volume_compare_v1':
            # Window split at its first lowest close (decline into the pivot
            # vs rally out of it; the pivot bar counts on both sides).
            # Ratio = mean rally volume / mean decline volume (mirror band).
            vol = _nonnegative([b.volume for b in candles], 'native volume')
            if vol is None:
                return None
            lb = int(feature['lookback'])
            if len(candles) < lb:
                return None
            win_close = close[-lb:]
            win_vol = vol[-lb:]
            decline, rally = _split_segments(win_close)
            d = float(win_vol[decline].mean(dtype=np.float64))
            r = float(win_vol[rally].mean(dtype=np.float64))
            if d == 0:
                if r == 0:
                    return None      # both legs zero volume: 0/0 undefined
                return math.inf      # KNOWN signed infinity per ratio rule
            return r / d
        if recipe == 'native_segment_return_compare_v1':
            # Leg magnitudes around the first lowest close, both >= 0 because
            # the pivot is the window minimum. Ratio = rally magnitude /
            # decline magnitude (mirror band).
            lb = int(feature['lookback'])
            if len(candles) < lb:
                return None
            win_close = close[-lb:]
            decline, rally = _split_segments(win_close)
            k = decline.stop - 1
            d_mag = float(win_close[0] / win_close[k] - 1.0)
            r_mag = float(win_close[-1] / win_close[k] - 1.0)
            if d_mag == 0:
                if r_mag == 0:
                    return None      # perfectly flat window: 0/0 undefined
                return math.inf      # rally out of a zero decline: KNOWN infinity
            return r_mag / d_mag
        if recipe == 'native_segment_atr_compare_v1':
            # Mean ATR14 of the rally leg vs the decline leg around the first
            # lowest close, as a SIGNED percent expansion:
            #   (mean_rally_atr14 / mean_decline_atr14 - 1) * 100
            # Additive +/-pct band (no mirror). ATR14[t] = mean(TR) over the
            # 14 bars ending at t, TR needing the prior close; evaluate_master
            # fetches lookback+14 candles so every window bar has an ATR14.
            lb = int(feature['lookback'])
            n = len(candles)
            if n < lb + 14:
                return None
            prev_close = np.concatenate(([close[0]], close[:-1]))
            tr = np.maximum(high - low, np.maximum(np.abs(high - prev_close),
                                                   np.abs(low - prev_close)))
            atr = np.convolve(tr, np.ones(14) / 14, mode='valid')  # entry j = bar j+13
            win_atr = atr[n - lb - 13:]
            win_close = close[n - lb:]
            decline, rally = _split_segments(win_close)
            d = float(win_atr[decline].mean(dtype=np.float64))
            r = float(win_atr[rally].mean(dtype=np.float64))
            if d == 0:
                if r == 0:
                    return None      # both legs zero range: 0/0 undefined
                return math.inf      # expansion out of zero: KNOWN infinity
            return (r / d - 1.0) * 100.0
        if recipe == 'native_absorption_day_v1':
            # Latest absorption day in the window (dial definitions): RVOL >
            # S_vol_spike_mult (volume vs the 50-bar median ending at the
            # bar, the registered "RVOL" rule) while the bar's move is tiny:
            # |C/Cprev-1| < C039 * ATR14/Cprev (both on the prev-close
            # basis). Direction: close C041 bars before the day strictly
            # above the day's close = after_decline (mirror after_rise);
            # exact equality classifies nothing (documented: a flat lookback
            # is neither a decline nor a rise) and the day is skipped; if no
            # strictly classifiable day exists -> none. Age = window-end
            # bars since the day: <=recent / (recent,old] / >old.
            lb = int(feature['lookback'])
            vol = _nonnegative([b.volume for b in candles], 'native volume')
            if vol is None:
                return None
            n = len(candles)
            if n < lb + 49:
                return None
            prev_close = np.concatenate(([close[0]], close[:-1]))
            tr = np.maximum(high - low, np.maximum(np.abs(high - prev_close),
                                                    np.abs(low - prev_close)))
            atr = np.convolve(tr, np.ones(14) / 14, mode='valid')  # entry j = bar j+13
            w0 = n - lb
            win_vol = vol[w0:]
            win_med = np.array([np.median(vol[i - 49:i + 1]) for i in range(w0, n)])
            win_atr = atr[w0 - 13:]
            win_prev = prev_close[w0:]
            win_c = close[w0:]
            mult = float(feature['spike_mult'])
            frac = float(feature['atr_frac'])
            day = ((win_med > 0) & (win_vol > mult * win_med)
                   & (np.abs(win_c / win_prev - 1.0) < frac * win_atr / win_prev))
            idxs = np.nonzero(day)[0]
            out = {o: False for o in tuple(
                d + '_' + a for d in ('after_decline', 'after_rise')
                for a in ('ageR', 'ageM', 'ageO')) + ('none',)}
            picked = None
            for j in reversed(idxs):
                k = w0 + j - int(feature['dir_lookback'])
                if close[k] > win_c[j]:
                    picked = (j, 'after_decline')
                    break
                if close[k] < win_c[j]:
                    picked = (j, 'after_rise')
                    break
            if picked is None:
                out['none'] = True
                return out
            j, direction = picked
            age = lb - 1 - j
            recent = int(feature['age_recent'])
            old = int(feature['age_old'])
            band = 'ageR' if age <= recent else 'ageM' if age <= old else 'ageO'
            out[direction + '_' + band] = True
            return out
        if recipe == 'native_capitulation_bar_v1':
            # Latest capitulation bar (range > S_shock_atr*ATR14, RVOL >
            # S_vol_spike_mult, close in the outer C156% of its range) else
            # latest blow-off bar (mirror, close in the top C156%), else
            # none. Crossed with: age (<recent / <=old / else, "age<5,5-20,
            # >20" style), size (range/ATR14 <= C160 -> sizeS, else sizeL),
            # record volume (bar volume >= every window bar's volume;
            # documented interpretation of "record"), and close shape:
            # long_reversal_wick = reversal-side wick >= 2x body AND >=
            # 0.5*ATR14 (documented thresholds); else close_near_far_end =
            # close in the outer C156/2% (i.e. the middle of the qualifying
            # zone counts as close_mid); else close_mid.
            lb = int(feature['lookback'])
            vol = _nonnegative([b.volume for b in candles], 'native volume')
            if vol is None:
                return None
            n = len(candles)
            if n < lb + 49:
                return None
            prev_close = np.concatenate(([close[0]], close[:-1]))
            tr = np.maximum(high - low, np.maximum(np.abs(high - prev_close),
                                                    np.abs(low - prev_close)))
            atr = np.convolve(tr, np.ones(14) / 14, mode='valid')
            w0 = n - lb
            win_vol = vol[w0:]
            win_med = np.array([np.median(vol[i - 49:i + 1]) for i in range(w0, n)])
            win_atr = atr[w0 - 13:]
            win_o = opened[w0:]
            win_h = high[w0:]
            win_l = low[w0:]
            win_c = close[w0:]
            mult = float(feature['spike_mult'])
            shock = float(feature['shock_atr'])
            pct = float(feature['close_pct']) / 100.0
            big = float(feature['big_atr'])
            recent = int(feature['age_recent'])
            old = int(feature['age_old'])
            rng = win_h - win_l
            valid = (win_med > 0) & (rng > shock * win_atr) & (win_vol > mult * win_med)
            with np.errstate(all='ignore'):
                loc = np.where(rng > 0, (win_c - win_l) / rng, 0.5)
            caps = np.nonzero(valid & (loc <= pct))[0]
            blows = np.nonzero(valid & (loc >= 1.0 - pct))[0]
            t = None
            direction = None
            if caps.size:
                t = int(caps[-1])
                direction = 'capitulation'
            elif blows.size:
                t = int(blows[-1])
                direction = 'blowoff'
            out = {o: False for o in tuple(
                d + '_age' + b + '_' + s + '_' + r + '_' + sh
                for d in ('capitulation', 'blowoff')
                for b in ('R', 'M', 'O')
                for s in ('sizeS', 'sizeL')
                for r in ('recY', 'recN')
                for sh in ('end', 'mid', 'wk')) + ('none',)}
            if t is None:
                out['none'] = True
                return out
            age = lb - 1 - t
            band = 'R' if age < recent else 'M' if age <= old else 'O'
            size = 'sizeS' if rng[t] <= big * win_atr[t] else 'sizeL'
            rec = 'recY' if win_vol[t] >= win_vol.max() else 'recN'
            wick = (win_c[t] - win_l[t]) if direction == 'capitulation' else (
                win_h[t] - win_c[t])
            body = abs(win_c[t] - win_o[t])
            if wick >= 2.0 * body and wick >= 0.5 * win_atr[t]:
                shape = 'wk'
            elif (direction == 'capitulation' and loc[t] <= pct / 2.0) or (
                    direction == 'blowoff' and loc[t] >= 1.0 - pct / 2.0):
                shape = 'end'
            else:
                shape = 'mid'
            out[direction + '_age' + band + '_' + size + '_' + rec + '_' + shape] = True
            return out
        if recipe == 'native_hl_base_breakout_v1':
            # Higher-low base breakout (mirror lower-high top breakdown):
            # strict swing pivots (min/max of +-k window bars, k =
            # max(S_pivot_k_min, N//S_pivot_k_divisor)); scan consecutive
            # pivot-low pairs from the latest, first pair with a higher
            # second low whose later first bar closes above EVERY earlier
            # window high = breakout (window-high reading, breakout bar
            # excluded from its own max; documented). Bars HL->breakout
            # bucketed <recent / recent..old / >old. RSI6/12/24 on the
            # breakout bar all > S_rsi_extreme_high (up) or all < low (down)
            # = extreme. Up takes precedence when both somehow qualify.
            lb = int(feature['lookback'])
            k = max(int(feature['pivot_k_min']),
                    lb // int(feature['pivot_k_divisor']))
            recent = int(feature['age_recent'])
            old = int(feature['age_old'])
            n = len(candles)
            if n < lb + 25 or k < 1 or 2 * k >= lb:
                return None
            w0 = n - lb
            win_c = close[w0:]
            win_h = high[w0:]
            win_l = low[w0:]
            piv_lo = [i for i in range(k, lb - k)
                      if win_l[i] < min(win_l[i - k:i]) and win_l[i] < min(win_l[i + 1:i + k + 1])]
            piv_hi = [i for i in range(k, lb - k)
                      if win_h[i] > max(win_h[i - k:i]) and win_h[i] > max(win_h[i + 1:i + k + 1])]

            def rsi_all(idx, cmp_hi):
                for period, edge in ((6, feature['rsi_high']), (12, feature['rsi_high']),
                                     (24, feature['rsi_high'])) if cmp_hi else (
                        (6, feature['rsi_low']), (12, feature['rsi_low']),
                        (24, feature['rsi_low'])):
                    v = _rsi_at(close, period, w0 + idx)
                    if v is None:
                        return None
                    if cmp_hi and not v > float(edge):
                        return False
                    if not cmp_hi and not v < float(edge):
                        return False
                return True

            found = None
            for i2 in reversed(piv_lo[1:]):
                i1 = piv_lo[piv_lo.index(i2) - 1]
                if not win_l[i2] > win_l[i1]:
                    continue
                for t in range(i2 + 1, lb):
                    if win_c[t] > float(np.max(win_h[:t])):
                        found = ('up', t - i2, t)
                        break
                if found:
                    break
            if found is None:
                for i2 in reversed(piv_hi[1:]):
                    i1 = piv_hi[piv_hi.index(i2) - 1]
                    if not win_h[i2] < win_h[i1]:
                        continue
                    for t in range(i2 + 1, lb):
                        if win_c[t] < float(np.min(win_l[:t])):
                            found = ('down', t - i2, t)
                            break
                    if found:
                        break
            out = {o: False for o in tuple(
                d + '_' + b + '_' + r for d in ('up', 'down')
                for b in ('lt5', 'b5_20', 'gt20')
                for r in ('extreme', 'not')) + ('none',)}
            if found is None:
                out['none'] = True
                return out
            direction, dist, t = found
            band = 'lt5' if dist < recent else 'b5_20' if dist <= old else 'gt20'
            extreme = rsi_all(t, direction == 'up')
            if extreme is None:
                return None
            out[direction + '_' + band + ('_extreme' if extreme else '_not')] = True
            return out
        if recipe == 'native_high_then_low_v1':
            # Sequence facet: which came first, the window high or the window
            # low? First-occurrence index of the window max high vs the window
            # min low (numpy argmax/argmin take the FIRST occurrence). A bar
            # that is simultaneously both (tie, e.g. an outside spike in a
            # flat window) counts as high_first — documented, the answer set
            # {high_first,low_first} has no same_bar outcome.
            lb = int(feature['lookback'])
            if len(candles) < lb:
                return None
            w0 = len(candles) - lb
            i_h = int(np.argmax(high[w0:]))
            i_l = int(np.argmin(low[w0:]))
            return {'high_first': i_h <= i_l, 'low_first': i_l < i_h}
        if recipe == 'native_intraday_change_mean_v1':
            # Mean intraday body fraction across the window, in PERCENT:
            # mean((C-O)/O)*100. Band dial C001 is a percent threshold.
            lb = int(feature['lookback'])
            if len(candles) < lb:
                return None
            w0 = len(candles) - lb
            frac = (close[w0:] - opened[w0:]) / opened[w0:]
            return float(frac.mean(dtype=np.float64) * 100.0)
        if recipe == 'native_interday_change_total_v1':
            # Total close-to-close change across the window, in PERCENT:
            # (C[last]/C[first] - 1)*100, anchored at the first window close.
            # Band dial C002 is a percent threshold.
            lb = int(feature['lookback'])
            if len(candles) < lb:
                return None
            w0 = len(candles) - lb
            first = float(close[w0])
            last = float(close[-1])
            if not np.isfinite(first) or first <= 0:
                return None
            return (last / first - 1.0) * 100.0
        if recipe == 'native_run_structure_v1':
            # Longest same-colour body run in the window: green (C>O) vs red
            # (C<O). A doji (C==O) breaks any run (documented). equal covers
            # ties including both-zero (all-doji window).
            lb = int(feature['lookback'])
            if len(candles) < lb:
                return None
            w0 = len(candles) - lb
            body = close[w0:] - opened[w0:]
            best = {1: 0, -1: 0}
            run = 0
            sign = 0
            for b in body:
                s = 1 if b > 0 else -1 if b < 0 else 0
                if s == 0:
                    run = 0
                    sign = 0
                    continue
                if s == sign:
                    run += 1
                else:
                    sign = s
                    run = 1
                if run > best[sign]:
                    best[sign] = run
            g, r = best[1], best[-1]
            return {'green_longer': g > r, 'red_longer': r > g, 'equal': g == r}
        if recipe == 'native_weekly_trend_v1':
            # Big-picture trend on the k-day candle stream (5x = the spec's
            # "weekly"). Slope = percent change of the close from the first
            # to the last WINDOW bar (same slope convention as
            # native_ma_slope_v1). Documented flat constant: |slope| <= 1.0%
            # -> flat (no dial is registered on this family; amendable).
            lb = int(feature['lookback'])
            if len(candles) < lb:
                return None
            w0 = len(candles) - lb
            first = float(close[w0])
            last = float(close[-1])
            if first <= 0 or not np.isfinite(first) or not np.isfinite(last):
                return None
            slope = (last / first - 1.0) * 100.0
            return {'rising': slope > 1.0,
                    'falling': slope < -1.0,
                    'flat': abs(slope) <= 1.0}
        if recipe == 'native_weekly_stack_v1':
            # Big-picture stack on the k-day candle stream: last close vs two
            # baked SMA periods (C174 fast / C175 slow), same full-window SMA
            # construction as _ma_series, read at the last fetched bar.
            # bull = close > SMA_fast > SMA_slow (strict); bear mirror;
            # anything else mixed. A degenerate pairing (fast >= slow) is
            # NOT_EVALUABLE rather than an invented order.
            lb = int(feature['lookback'])
            fast = int(feature['ma_fast'])
            slow = int(feature['ma_slow'])
            if len(candles) < lb or fast >= slow or len(candles) < slow:
                return None
            ma_f = _ma_series(dict(feature, ma_kind='SMA', ma_period=str(fast)), close)
            ma_s = _ma_series(dict(feature, ma_kind='SMA', ma_period=str(slow)), close)
            if ma_f is None or ma_s is None or not np.isfinite([ma_f[-1], ma_s[-1]]).all():
                return None
            c = float(close[-1])
            f = float(ma_f[-1])
            s = float(ma_s[-1])
            bull = c > f > s
            bear = c < f < s
            return {'bull': bull, 'bear': bear, 'mixed': not bull and not bear}
        if recipe == 'native_extreme_position_v1':
            # Where the L3 oscillator's window MAX and MIN sit. early = first
            # half of the window [0, lb//2), late = second half; ties use the
            # FIRST occurrence (numpy argmax/argmin). A flat window (max ==
            # min on one bar) lands both on that bar's half -> both_early or
            # both_late (documented; the four outcomes still partition).
            lb = int(feature['lookback'])
            osc = _osc_series(feature, close, high, low)
            if osc is None:
                return None
            series, _line = osc
            if len(series) < lb:
                return None
            win = series[-lb:]
            i_max = int(np.argmax(win))
            i_min = int(np.argmin(win))
            half = lb // 2
            max_early = i_max < half
            min_early = i_min < half
            return {'max_early_min_late': max_early and not min_early,
                    'min_early_max_late': min_early and not max_early,
                    'both_early': max_early and min_early,
                    'both_late': not max_early and not min_early}
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
    'slope': dict(
        binding='band', mirror=False,
        l1_l3=(('moving_averages', 'SMA20'), ('moving_averages', 'SMA50'),
               ('moving_averages', 'SMA200'), ('moving_averages', 'EMA21')),
        recipe='native_ma_slope_v1',
        unit='ma_pct_change_from_window_first_bar_to_last_bar',
        outcomes=('up', 'down', 'flat'), cutoff_id='C091_slope__pct1',
        l3_map={'SMA20': {'ma_kind': 'SMA', 'ma_period': '20'},
                'SMA50': {'ma_kind': 'SMA', 'ma_period': '50'},
                'SMA200': {'ma_kind': 'SMA', 'ma_period': '200'},
                'EMA21': {'ma_kind': 'EMA', 'ma_period': '21'}},
        transform_by_outcome={'up': 'identity', 'down': 'identity', 'flat': 'abs'},
        comparator_by_outcome={'up': '>', 'down': '<', 'flat': '<='}),
    'cross_event': dict(
        binding='mixed',
        l1_l3=(('overbought_oversold', 'RSI6'), ('overbought_oversold', 'RSI12'),
               ('overbought_oversold', 'RSI14'), ('overbought_oversold', 'RSI24'),
               ('overbought_oversold', 'Stoch14_3'),
               ('overbought_oversold', 'WilliamsR14'),
               ('momentum', 'MACD12_26_9'), ('momentum', 'ROC20')),
        recipe='native_osc_cross_v1', unit='oscillator_midline_or_signal_cross_in_window',
        outcomes=('up', 'down', 'both', 'none'), cutoff_id=None,
        l3_map={'RSI6': {'osc_kind': 'RSI', 'osc_period': '6', 'cross_line': '50',
                         'osc_warmup': '7'},
                'RSI12': {'osc_kind': 'RSI', 'osc_period': '12', 'cross_line': '50',
                          'osc_warmup': '13'},
                'RSI14': {'osc_kind': 'RSI', 'osc_period': '14', 'cross_line': '50',
                          'osc_warmup': '15'},
                'RSI24': {'osc_kind': 'RSI', 'osc_period': '24', 'cross_line': '50',
                          'osc_warmup': '25'},
                'Stoch14_3': {'osc_kind': 'STOCH', 'osc_period': '14', 'osc_slow': '3',
                              'cross_line': '50', 'osc_warmup': '16'},
                'WilliamsR14': {'osc_kind': 'WILLR', 'osc_period': '14',
                                'cross_line': '-50', 'osc_warmup': '14'},
                'MACD12_26_9': {'osc_kind': 'MACD', 'osc_fast': '12', 'osc_slow': '26',
                                'osc_signal': '9', 'cross_line': 'signal',
                                'osc_warmup': '34'},
                'ROC20': {'osc_kind': 'ROC', 'osc_period': '20', 'cross_line': '0',
                          'osc_warmup': '21'}},
        outcome_spec={'up': ('boolean', '=', 'one'), 'down': ('boolean', '=', 'one'),
                      'both': ('boolean', '=', 'one'), 'none': ('boolean', '=', 'one')}),
    'cross_count': dict(
        binding='mixed',
        l1_l3=(('moving_averages', 'SMA20'), ('moving_averages', 'SMA50'),
               ('moving_averages', 'SMA200'), ('moving_averages', 'EMA21')),
        recipe='native_ma_cross_count_v1', unit='price_ma_cross_count_window_bucket_code',
        outcomes=('zero', 'low_band', 'mid_band', 'high_band'), cutoff_id=None,
        baked_cutoff_ids=('C087_cross_count__scalar2', 'C089_cross_count__scalar5'),
        baked_map={'C087_cross_count__scalar2': 'cross_low_edge',
                   'C089_cross_count__scalar5': 'cross_high_edge'},
        l3_map={'SMA20': {'ma_kind': 'SMA', 'ma_period': '20'},
                'SMA50': {'ma_kind': 'SMA', 'ma_period': '50'},
                'SMA200': {'ma_kind': 'SMA', 'ma_period': '200'},
                'EMA21': {'ma_kind': 'EMA', 'ma_period': '21'}},
        outcome_spec={'zero': ('integer_count', '=', 'code0'),
                      'low_band': ('integer_count', '=', 'code1'),
                      'mid_band': ('integer_count', '=', 'code2'),
                      'high_band': ('integer_count', '=', 'code3')}),
    'shock': dict(
        binding='mixed', l1_l3=(('volatility', 'ATR14'),),
        recipe='native_shock_v1',
        unit='biggest_window_range_over_baseline_median_range_bucket_and_timing',
        outcomes=('none', 'mid_early', 'mid_late', 'big_early', 'big_late'),
        cutoff_id=None,
        baked_cutoff_ids=('S_baseline_bars', 'C242_shock__scalar3',
                          'C243_shock__mult5'),
        baked_map={'S_baseline_bars': 'baseline_bars',
                   'C242_shock__scalar3': 'shock_low_mult',
                   'C243_shock__mult5': 'shock_high_mult'},
        outcome_spec={'none': ('boolean', '=', 'one'),
                      'mid_early': ('boolean', '=', 'one'),
                      'mid_late': ('boolean', '=', 'one'),
                      'big_early': ('boolean', '=', 'one'),
                      'big_late': ('boolean', '=', 'one')}),
    'time_in_zone': dict(
        binding='mixed',
        l1_l3=(('overbought_oversold', 'RSI6'), ('overbought_oversold', 'RSI12'),
               ('overbought_oversold', 'RSI14'), ('overbought_oversold', 'RSI24'),
               ('overbought_oversold', 'Stoch14_3'),
               ('overbought_oversold', 'WilliamsR14')),
        recipe='native_osc_zone_share_v1', unit='window_zone_share_majority_bucket',
        outcomes=('mostly_high', 'mostly_low', 'mostly_mid', 'mixed'), cutoff_id=None,
        baked_cutoff_ids=('S_majority_share_pct',),
        baked_map={'S_majority_share_pct': 'majority_pct'},
        l3_map={'RSI6': {'osc_kind': 'RSI', 'osc_period': '6', 'cross_line': '50',
                         'osc_warmup': '7', 'zone_high': '70', 'zone_low': '30'},
                'RSI12': {'osc_kind': 'RSI', 'osc_period': '12', 'cross_line': '50',
                          'osc_warmup': '13', 'zone_high': '70', 'zone_low': '30'},
                'RSI14': {'osc_kind': 'RSI', 'osc_period': '14', 'cross_line': '50',
                          'osc_warmup': '15', 'zone_high': '70', 'zone_low': '30'},
                'RSI24': {'osc_kind': 'RSI', 'osc_period': '24', 'cross_line': '50',
                          'osc_warmup': '25', 'zone_high': '70', 'zone_low': '30'},
                'Stoch14_3': {'osc_kind': 'STOCH', 'osc_period': '14', 'osc_slow': '3',
                              'cross_line': '50', 'osc_warmup': '16',
                              'zone_high': '80', 'zone_low': '20'},
                'WilliamsR14': {'osc_kind': 'WILLR', 'osc_period': '14',
                                'cross_line': '-50', 'osc_warmup': '14',
                                'zone_high': '-20', 'zone_low': '-80'}},
        outcome_spec={'mostly_high': ('boolean', '=', 'one'),
                      'mostly_low': ('boolean', '=', 'one'),
                      'mostly_mid': ('boolean', '=', 'one'),
                      'mixed': ('boolean', '=', 'one')}),
    'full_stack_streak': dict(
        binding='mixed',
        l1_l3=(('moving_averages', 'MA_group(10/20/50/200)'),),
        recipe='native_full_stack_streak_v1',
        unit='longest_run_of_full_ma_order_window_bars_bucket',
        outcomes=('bull_zero', 'bull_low', 'bull_mid', 'bull_high',
                  'bear_zero', 'bear_low', 'bear_mid', 'bear_high'),
        cutoff_id=None,
        baked_cutoff_ids=('C101_full_stack_streak__scalar4',
                          'C102_full_stack_streak__scalar5',
                          'C103_full_stack_streak__scalar19',
                          'C104_full_stack_streak__scalar20'),
        baked_map={'C101_full_stack_streak__scalar4': 'streak_low_edge',
                   'C102_full_stack_streak__scalar5': 'streak_mid_lo',
                   'C103_full_stack_streak__scalar19': 'streak_mid_hi',
                   'C104_full_stack_streak__scalar20': 'streak_high_edge'},
        outcome_spec={o: ('boolean', '=', 'one')
                      for o in ('bull_zero', 'bull_low', 'bull_mid', 'bull_high',
                                'bear_zero', 'bear_low', 'bear_mid', 'bear_high')}),
    'ma30_side_streak': dict(
        binding='mixed',
        l1_l3=(('moving_averages', 'MA_group(10/20/50/200)'),),
        recipe='native_ma30_side_streak_v1',
        unit='current_sma30_side_run_bucket_vs_own_history_record',
        outcomes=tuple(s + '_' + b + r for s in ('above', 'below')
                       for b in ('short', 'mid', 'long')
                       for r in ('_record', '_not')),
        cutoff_id=None,
        baked_cutoff_ids=('C107_ma30_side_streak__scalar10',
                          'C108_ma30_side_streak__scalar30',
                          'S_long_history_bars'),
        baked_map={'C107_ma30_side_streak__scalar10': 'streak_short_edge',
                   'C108_ma30_side_streak__scalar30': 'streak_long_edge',
                   'S_long_history_bars': 'long_history_bars'},
        outcome_spec={o: ('boolean', '=', 'one')
                      for o in tuple(s + '_' + b + r for s in ('above', 'below')
                                     for b in ('short', 'mid', 'long')
                                     for r in ('_record', '_not'))}),
    'flip': dict(
        binding='mixed', l1_l3=(('volume', 'up_down_volume'),),
        recipe='native_volume_dominance_flip_v1',
        unit='up_down_volume_dominance_flip_in_window',
        outcomes=('to_up', 'to_down', 'none'), cutoff_id=None,
        outcome_spec={'to_up': ('boolean', '=', 'one'),
                      'to_down': ('boolean', '=', 'one'),
                      'none': ('boolean', '=', 'one')}),
    # ---- batch 9: oscillator swing speed + two-segment compare. The
    # segment_compare family holds a LIST of sub-specs: one L4 analysis name
    # with three different (L1,L3) recipes; bind picks the sub-spec whose
    # l1_l3 matches the tree row. ----
    'osc_swing_speed': dict(
        binding='mixed',
        l1_l3=(('overbought_oversold', 'RSI6'),),
        recipe='native_osc_swing_speed_v1',
        unit='latest_complete_rsi6_cross_zone_swing_length_bucket',
        outcomes=('bull_short', 'bull_mid', 'bull_long', 'bull_none',
                  'bear_short', 'bear_mid', 'bear_long', 'bear_none'),
        cutoff_id=None,
        baked_cutoff_ids=('S_osc_zone_high', 'S_osc_zone_low',
                          'C228_osc_swing_speed__scalar5',
                          'C229_osc_swing_speed__scalar6',
                          'C230_osc_swing_speed__scalar15'),
        baked_map={'S_osc_zone_high': 'zone_high',
                   'S_osc_zone_low': 'zone_low',
                   'C228_osc_swing_speed__scalar5': 'swing_low_edge',
                   'C229_osc_swing_speed__scalar6': 'swing_mid_lo',
                   'C230_osc_swing_speed__scalar15': 'swing_mid_hi'},
        l3_map={'RSI6': {'osc_kind': 'RSI', 'osc_period': '6', 'cross_line': '50',
                         'osc_warmup': '7'}},
        outcome_spec={o: ('boolean', '=', 'one')
                      for o in ('bull_short', 'bull_mid', 'bull_long', 'bull_none',
                                'bear_short', 'bear_mid', 'bear_long', 'bear_none')}),
    'segment_compare': [
        dict(
            binding='band', mirror=True,
            l1_l3=(('volume', 'RVOL20'),),
            recipe='native_segment_volume_compare_v1',
            unit='mean_rally_volume_over_mean_decline_volume',
            outcomes=('rally_heavier', 'decline_heavier', 'similar'),
            cutoff_id='S_ratio_band_1p25',
            transform_by_outcome={'rally_heavier': 'identity',
                                  'decline_heavier': 'identity',
                                  'similar': 'mirror_min'},
            comparator_by_outcome={'rally_heavier': '>', 'decline_heavier': '<',
                                   'similar': '>='}),
        dict(
            binding='band', mirror=True,
            l1_l3=(('return_path', 'daily_returns'),),
            recipe='native_segment_return_compare_v1',
            unit='rally_magnitude_over_decline_magnitude',
            outcomes=('rally_steeper', 'decline_steeper', 'similar'),
            cutoff_id='S_ratio_band_1p5',
            transform_by_outcome={'rally_steeper': 'identity',
                                  'decline_steeper': 'identity',
                                  'similar': 'mirror_min'},
            comparator_by_outcome={'rally_steeper': '>', 'decline_steeper': '<',
                                   'similar': '>='}),
        dict(
            binding='band', mirror=False,
            l1_l3=(('volatility', 'ATR14'),),
            recipe='native_segment_atr_compare_v1',
            unit='signed_pct_expansion_of_mean_atr14_rally_over_decline',
            outcomes=('expanded', 'contracted', 'similar'),
            cutoff_id='C244_segment_compare__pct20',
            transform_by_outcome={'expanded': 'identity', 'contracted': 'identity',
                                  'similar': 'abs'},
            comparator_by_outcome={'expanded': '>', 'contracted': '<',
                                   'similar': '<='}),
    ],
    # ---- batch 10: absorption day + capitulation/blow-off bar (both use the
    # registered 50-bar-median RVOL rule; S_vol_spike_mult is the multiple).
    # Two thresholds (wick >= 2x body and >= 0.5*ATR14 for long_reversal_wick,
    # window-max for record_vol, flat-lookback -> none) are DOCUMENTED
    # INTERPRETATIONS of the dial text, flagged for James in PR #177. ----
    'absorption_day': dict(
        binding='mixed', l1_l3=(('volume', 'RVOL20'),),
        recipe='native_absorption_day_v1',
        unit='latest_rvol_spike_tiny_move_day_direction_and_age',
        outcomes=tuple(d + '_' + a for d in ('after_decline', 'after_rise')
                       for a in ('ageR', 'ageM', 'ageO')) + ('none',),
        cutoff_id=None,
        baked_cutoff_ids=('S_vol_spike_mult', 'C039_absorption_day__atr0p5',
                          'C041_absorption_day__scalar6',
                          'S_age_recent_bars', 'S_age_old_bars'),
        baked_map={'S_vol_spike_mult': 'spike_mult',
                   'C039_absorption_day__atr0p5': 'atr_frac',
                   'C041_absorption_day__scalar6': 'dir_lookback',
                   'S_age_recent_bars': 'age_recent',
                   'S_age_old_bars': 'age_old'},
        outcome_spec={o: ('boolean', '=', 'one')
                      for o in tuple(d + '_' + a
                                     for d in ('after_decline', 'after_rise')
                                     for a in ('ageR', 'ageM', 'ageO')) + ('none',)}),
    'capitulation_bar': dict(
        binding='mixed', l1_l3=(('extremes', 'drawdown'),),
        recipe='native_capitulation_bar_v1',
        unit='latest_capitulation_or_blowoff_bar_age_size_record_shape',
        outcomes=tuple(d + '_age' + b + '_' + s + '_' + r + '_' + sh
                       for d in ('capitulation', 'blowoff')
                       for b in ('R', 'M', 'O')
                       for s in ('sizeS', 'sizeL')
                       for r in ('recY', 'recN')
                       for sh in ('end', 'mid', 'wk')) + ('none',),
        cutoff_id=None,
        baked_cutoff_ids=('S_vol_spike_mult', 'S_shock_atr',
                          'C156_capitulation_bar__pct20',
                          'C160_capitulation_bar__atr5',
                          'S_age_recent_bars', 'S_age_old_bars'),
        baked_map={'S_vol_spike_mult': 'spike_mult',
                   'S_shock_atr': 'shock_atr',
                   'C156_capitulation_bar__pct20': 'close_pct',
                   'C160_capitulation_bar__atr5': 'big_atr',
                   'S_age_recent_bars': 'age_recent',
                   'S_age_old_bars': 'age_old'},
        outcome_spec={o: ('boolean', '=', 'one')
                      for o in tuple(d + '_age' + b + '_' + s + '_' + r + '_' + sh
                                     for d in ('capitulation', 'blowoff')
                                     for b in ('R', 'M', 'O')
                                     for s in ('sizeS', 'sizeL')
                                     for r in ('recY', 'recN')
                                     for sh in ('end', 'mid', 'wk')) + ('none',)}),
    'hl_base_breakout': dict(
        binding='mixed', l1_l3=(('extremes', 'new_highs_lows'),),
        recipe='native_hl_base_breakout_v1',
        unit='higher_low_base_breakout_direction_age_rsi_extreme',
        outcomes=tuple(d + '_' + b + '_' + r for d in ('up', 'down')
                       for b in ('lt5', 'b5_20', 'gt20')
                       for r in ('extreme', 'not')) + ('none',),
        cutoff_id=None,
        baked_cutoff_ids=('S_pivot_k_min', 'S_pivot_k_divisor',
                          'S_age_recent_bars', 'S_age_old_bars',
                          'S_rsi_extreme_high', 'S_rsi_extreme_low'),
        baked_map={'S_pivot_k_min': 'pivot_k_min',
                   'S_pivot_k_divisor': 'pivot_k_divisor',
                   'S_age_recent_bars': 'age_recent',
                   'S_age_old_bars': 'age_old',
                   'S_rsi_extreme_high': 'rsi_high',
                   'S_rsi_extreme_low': 'rsi_low'},
        outcome_spec={o: ('boolean', '=', 'one')
                      for o in tuple(d + '_' + b + '_' + r
                                     for d in ('up', 'down')
                                     for b in ('lt5', 'b5_20', 'gt20')
                                     for r in ('extreme', 'not')) + ('none',)}),
    'high_then_low': dict(
        binding='mixed', l1_l3=(('extremes', 'new_highs_lows'),),
        recipe='native_high_then_low_v1',
        unit='window_high_low_first_occurrence_order',
        outcomes=('high_first', 'low_first'),
        cutoff_id=None, baked_cutoff_ids=(), baked_map={},
        outcome_spec={'high_first': ('boolean', '=', 'one'),
                      'low_first': ('boolean', '=', 'one')}),
    'intraday_change': dict(
        binding='band', mirror=False, l1_l3=(('candles', 'OHLC'),),
        recipe='native_intraday_change_mean_v1',
        unit='mean_intraday_body_fraction_pct',
        outcomes=('up', 'down', 'flat'), cutoff_id='C001_intraday_change__pct1',
        transform_by_outcome={'up': 'identity', 'down': 'identity', 'flat': 'abs'},
        comparator_by_outcome={'up': '>', 'down': '<', 'flat': '<='}),
    'interday_change': dict(
        binding='band', mirror=False, l1_l3=(('candles', 'OHLC'),),
        recipe='native_interday_change_total_v1',
        unit='window_close_to_close_change_pct',
        outcomes=('up', 'down', 'flat'), cutoff_id='C002_interday_change__pct5',
        transform_by_outcome={'up': 'identity', 'down': 'identity', 'flat': 'abs'},
        comparator_by_outcome={'up': '>', 'down': '<', 'flat': '<='}),
    'run_structure': dict(
        binding='mixed', l1_l3=(('candles', 'OHLC'),),
        recipe='native_run_structure_v1',
        unit='longest_same_colour_body_run_comparison',
        outcomes=('green_longer', 'red_longer', 'equal'),
        cutoff_id=None, baked_cutoff_ids=(), baked_map={},
        outcome_spec={'green_longer': ('boolean', '=', 'one'),
                      'red_longer': ('boolean', '=', 'one'),
                      'equal': ('boolean', '=', 'one')}),
    # ---- batch 14: big_picture weekly families + oscillator extreme
    # position. weekly_* measure the k-day candle stream (5x = the spec's
    # "weekly"); extreme_position reuses the documented Wilder-RSI series. ----
    'weekly_trend': dict(
        binding='mixed', l1_l3=(('extremes', 'big_picture'),),
        recipe='native_weekly_trend_v1',
        unit='window_kday_close_slope_pct_bucket',
        outcomes=('rising', 'falling', 'flat'),
        cutoff_id=None, baked_cutoff_ids=(), baked_map={},
        outcome_spec={'rising': ('boolean', '=', 'one'),
                      'falling': ('boolean', '=', 'one'),
                      'flat': ('boolean', '=', 'one')}),
    'weekly_stack': dict(
        binding='mixed', l1_l3=(('extremes', 'big_picture'),),
        recipe='native_weekly_stack_v1',
        unit='kday_close_vs_two_baked_sma_stack_order',
        outcomes=('bull', 'bear', 'mixed'),
        cutoff_id=None,
        baked_cutoff_ids=('C174_weekly_stack__scalar10',
                          'C175_weekly_stack__scalar40'),
        baked_map={'C174_weekly_stack__scalar10': 'ma_fast',
                   'C175_weekly_stack__scalar40': 'ma_slow'},
        outcome_spec={'bull': ('boolean', '=', 'one'),
                      'bear': ('boolean', '=', 'one'),
                      'mixed': ('boolean', '=', 'one')}),
    'extreme_position': dict(
        binding='mixed',
        l1_l3=(('overbought_oversold', 'RSI6'), ('overbought_oversold', 'RSI12'),
               ('overbought_oversold', 'RSI14'), ('overbought_oversold', 'RSI24')),
        recipe='native_extreme_position_v1',
        unit='window_oscillator_max_min_half_position',
        outcomes=('max_early_min_late', 'min_early_max_late',
                  'both_early', 'both_late'),
        cutoff_id=None, baked_cutoff_ids=(), baked_map={},
        l3_map={'RSI6': {'osc_kind': 'RSI', 'osc_period': '6', 'cross_line': '50',
                         'osc_warmup': '7'},
                'RSI12': {'osc_kind': 'RSI', 'osc_period': '12', 'cross_line': '50',
                          'osc_warmup': '13'},
                'RSI14': {'osc_kind': 'RSI', 'osc_period': '14', 'cross_line': '50',
                          'osc_warmup': '15'},
                'RSI24': {'osc_kind': 'RSI', 'osc_period': '24', 'cross_line': '50',
                          'osc_warmup': '25'}},
        outcome_spec={o: ('boolean', '=', 'one')
                      for o in ('max_early_min_late', 'min_early_max_late',
                                'both_early', 'both_late')}),
}

def _iter_specs():
    """Flatten FACETS values: a facet holds one spec dict, or a LIST of
    sub-specs when one L4 analysis name maps to several (L1,L3) recipes
    (segment_compare: volume/returns/ATR)."""
    for facet, entry in FACETS.items():
        specs = entry if isinstance(entry, list) else (entry,)
        for spec in specs:
            yield facet, spec


for _facet, _spec in _iter_specs():
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
                 '(dry_up_at_low), or a zero baseline mean with zero window mean (vs_own_past). '
                 'Swing/segment facets add: a non-contiguous OAT scalar pairing '
                 '(swing_mid_lo != swing_low_edge+1), no complete cross-zone swing in the window '
                 '(both *_none outcomes answer NO; the question is still evaluable), or a zero '
                 'decline-leg mean with zero rally-leg mean (all three segment recipes).')
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
    # A recipe can return several scalar components. The cache identity must
    # distinguish their expressions and types even when their raw recipe is
    # shared (e.g. inside-run count versus the three boolean sequence outcomes).
    feature_identity=dict(feature=scalar,expression=expression,kind=feature_kind,unit=spec['unit'])
    return dict(
        question_id='BM1-' + identity(semantic), feature_id='BF1-' + identity(feature_identity),
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


def _facet_spec(tree_row):
    """The sub-spec binding this tree row, or None when the facet does not
    cover the row's (L1, L3) (falls through to the reference price binders)."""
    entry = FACETS.get(tree_row['L4_analysis'])
    if entry is None:
        return None
    specs = entry if isinstance(entry, list) else (entry,)
    key = (tree_row['L1_type'], tree_row['L3_derivative'])
    return next((spec for spec in specs if key in spec['l1_l3']), None)


def bind_master_question(tree_row, variant):
    """Bind a canonical source question+variant to strict binary definitions.

    Kimi candle/volume facets bind here; everything else falls through to the
    reference price binders, which raise NotImplementedError when unbound.
    """
    spec = _facet_spec(tree_row)
    if tree_row['part'] == 'base' and spec is not None:
        if tree_row['question_id'] != variant.source_question_id:
            raise ValueError('source tree and variant question differ')
        return _bind_facet(tree_row, variant, spec)
    return _bind_gpt_price(tree_row, variant)


_MASTER_RECIPES = {spec['recipe'] for _facet, spec in _iter_specs()}
# Recipes that compare each window candle with its predecessor need one extra
# native candle before the window (gaps, inside/outside, ATR14 warmup); the
# 50-bar median volume recipes need 49 prior bars; vs_own_past reads its
# baseline length from the feature (baked S_baseline_bars dial).
_EXTRA_PRIOR = {'native_gap_up_fate_v1': 1, 'native_gap_down_fate_v1': 1,
                'native_inside_outside_seq_v1': 1, 'native_run_biggest_move_ratio_v1': 1,
                'native_volume_dry_up_at_low_v1': 49, 'native_maxvol_wick_v1': 1,
                'native_segment_atr_compare_v1': 14,
                'native_absorption_day_v1': 49, 'native_capitulation_bar_v1': 49,
                'native_hl_base_breakout_v1': 30}
_CATEGORICAL_RECIPES = {'native_gap_up_fate_v1', 'native_gap_down_fate_v1',
                        'native_inside_outside_seq_v1', 'native_volume_dry_up_at_low_v1',
                        'native_max_vol_position_v1', 'native_volume_spike_v1',
                        'native_maxvol_wick_v1', 'native_volume_dominance_flip_v1',
                        'native_ma_cross_v1', 'native_osc_cross_v1',
                        'native_shock_v1', 'native_osc_zone_share_v1',
                        'native_full_stack_streak_v1',
                        'native_ma30_side_streak_v1',
                        'native_osc_swing_speed_v1',
                        'native_absorption_day_v1', 'native_capitulation_bar_v1',
                        'native_hl_base_breakout_v1', 'native_high_then_low_v1',
                        'native_run_structure_v1', 'native_weekly_trend_v1',
                        'native_weekly_stack_v1', 'native_extreme_position_v1'}


def evaluate_master(definition, bars, setup_date, expected_slot):
    """Evaluate from supplied source history; do not pre-trim MA history to N.

    Native MA state uses all supplied complete candles before setup. The facet
    alone uses N candles. The derivation caller must supply its complete source
    prefix, with the same shared-calendar slots and availability as the world.
    """
    feature = definition['feature']
    if feature['recipe'] in _MASTER_RECIPES:
        extra = _EXTRA_PRIOR.get(feature['recipe'], 0)
        if feature['recipe'] == 'native_volume_vs_own_past_v1':
            extra = int(feature['baseline_bars'])  # baked S_baseline_bars dial
        if feature['recipe'] == 'native_volume_spike_v1':
            extra = int(feature['spike_baseline_bars']) - 1  # baked C031 dial
        if feature['recipe'] in ('native_rsi_floor_v1', 'native_rsi_ceiling_v1'):
            extra = int(feature['rsi_period'])               # RSI seed warmup
        if feature['recipe'] in ('native_osc_cross_v1', 'native_osc_zone_share_v1',
                                 'native_osc_swing_speed_v1',
                                 'native_extreme_position_v1'):
            extra = int(feature['osc_warmup'])               # oscillator seed warmup
        if feature['recipe'] == 'native_shock_v1':
            extra = int(feature['baseline_bars'])            # median-range baseline
        if feature['recipe'] in ('native_ma_cross_v1', 'native_ma_slope_v1',
                                 'native_ma_cross_count_v1', 'native_full_stack_streak_v1',
                                 'native_ma30_side_streak_v1', 'native_weekly_stack_v1'):
            # Required facet/history groups must be present; an old halt/IPO
            # partial group is omitted only from indicator initialization.
            required = feature['lookback']
            if feature['recipe'] in ('native_ma_cross_v1', 'native_ma_cross_count_v1'):
                required += 1
            if feature['recipe'] == 'native_ma30_side_streak_v1':
                required += int(feature['long_history_bars'])
            window = _tf_window(bars, setup_date, expected_slot,
                                required, feature['candle_days'])
            candles = None if window is None else _native_ma_history(
                bars, setup_date, expected_slot, feature['candle_days'])
        else:
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

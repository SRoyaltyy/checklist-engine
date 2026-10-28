"""Shared contexts on the same completed-candle grid as stock inputs.

Keep native blocks factored on disk; attach requested columns to each stock-day
by their proven availability. Missing source intervals remain explicit blanks.
"""
import numpy as np
import pandas as pd

from world_timeframes import TIMEFRAMES, PRICE_COLS, completed_candles, align_features
from world_fred import columns as fred_columns


KEYS = ("candle_start", "source_candle_end", "available_from")


def _dates(values, name):
    dates = pd.DatetimeIndex(pd.to_datetime(values)).as_unit("ns")
    if dates.tz is not None or dates.hasnans or dates.has_duplicates or not dates.is_monotonic_increasing:
        raise ValueError(name + " must be unique ordered timezone-naive dates")
    return dates


def native_intervals(calendar, timeframe):
    cal = _dates(calendar, "shared calendar")
    if not len(cal):
        raise ValueError("empty shared calendar")
    if timeframe not in TIMEFRAMES:
        raise ValueError("unknown timeframe")
    rows = []
    if timeframe == "monthly":
        for period, dates in pd.Series(cal, index=cal).groupby(cal.to_period("M")):
            if period < cal[-1].to_period("M"):
                rows.append((dates.iloc[0], dates.iloc[-1], (period + 1).start_time, len(dates)))
    else:
        k = int(timeframe[:-1])
        for start in range(0, len(cal) - k, k):
            rows.append((cal[start], cal[start + k - 1], cal[start + k], k))
    frame = pd.DataFrame(rows, columns=[*KEYS, "expected_sessions"])
    for column in KEYS:
        frame[column] = pd.to_datetime(frame[column]).astype("datetime64[ns]")
    return frame


def fred_native(calendar, timeframe, timelines, required_series=()):
    missing = set(required_series) - set(timelines)
    if missing:
        raise ValueError("required ALFRED timelines absent: " + ",".join(sorted(missing)))
    bounds = native_intervals(calendar, timeframe)
    # ALFRED uses vintage_date < D, including on the exact release date.
    values = pd.DataFrame(fred_columns(bounds.available_from, timelines), index=bounds.index)
    changes = {}
    for column in values:
        if not column.endswith(("_odays", "_vintage_days")):
            for window in (20, 60):
                changes[column + "_change" + str(window)] = values[column].diff(window)
    return pd.concat([bounds[list(KEYS)], values, pd.DataFrame(changes, index=bounds.index)], axis=1)


def index_native(history, calendar, timeframe, prefix):
    """Aggregate verified index OHLC, or a truly close-only source such as VVIX.

    Every expected session must be present and finite. An incomplete interval
    has a row with unavailable values, preventing an as-of join from hiding it.
    """
    bounds = native_intervals(calendar, timeframe)
    if not {"DATE", "CLOSE"} <= set(history):
        raise ValueError("index DATE and CLOSE required explicitly")
    source = history.copy().sort_values("DATE")
    source["DATE"] = _dates(source.DATE, "index dates")
    ohlc = {"OPEN", "HIGH", "LOW", "CLOSE"}
    true_ohlc = ohlc <= set(source)
    if (ohlc - {"CLOSE"}) & set(source) and not true_ohlc:
        raise ValueError("incomplete OHLC schema is not a close-only source")
    selected = ["OPEN", "HIGH", "LOW", "CLOSE"] if true_ohlc else ["CLOSE"]
    source = source.set_index("DATE")
    cal = _dates(calendar, "shared calendar")
    interval = source.reindex(cal)
    valid = pd.Series(np.isfinite(interval[selected].to_numpy(dtype=float)).all(axis=1), index=cal)
    if timeframe == "monthly":
        groups = cal.to_period("M")
        wanted = pd.DatetimeIndex(bounds.candle_start).to_period("M")
    else:
        k = int(timeframe[:-1])
        groups = np.arange(len(cal)) // k
        wanted = cal.get_indexer(bounds.candle_start) // k
    aggregations = {"CLOSE": "last"}
    if true_ohlc:
        aggregations.update(OPEN="first", HIGH="max", LOW="min")
    aggregated = interval[selected].groupby(groups).agg(aggregations)
    aggregated = aggregated.where(valid.groupby(groups).all(), np.nan).reindex(wanted)
    values = aggregated[selected].reset_index(drop=True).rename(columns=lambda c: prefix + "_" + c.lower())
    for window in (20, 60):
        values[prefix + "_close_change" + str(window)] = values[prefix + "_close"].diff(window)
    return pd.concat([bounds[list(KEYS)], values], axis=1)


def price_native(bars, calendar, timeframe, prefix, feature_builder=None):
    """True ETF OHLCV and native return/trend lenses, with optional full indicators."""
    bounds = native_intervals(calendar, timeframe)
    candles = completed_candles(bars, timeframe, session_calendar=calendar)
    candles = candles.rename(columns={"date": "source_candle_end"})
    for column in KEYS:
        candles[column] = pd.to_datetime(candles[column]).astype("datetime64[ns]")
    grid = bounds[list(KEYS)].merge(candles, on=list(KEYS), how="left", validate="one_to_one")
    close = grid.close
    values = {prefix + "_" + c: grid[c].to_numpy(dtype=float) for c in PRICE_COLS}
    for window in (1, 5, 20):
        prior = close.shift(window)
        values[prefix + "_r" + str(window)] = (close / prior.where(prior > 0) - 1).to_numpy()
    for window in (50, 200):
        average = close.rolling(window).mean()
        values[prefix + "_d" + str(window)] = (close / average.where(average > 0) - 1).to_numpy()
    if feature_builder is not None:
        feature_input = grid.rename(columns={"source_candle_end": "date"})
        features = feature_builder(feature_input)
        if not features.available_from.equals(grid.available_from):
            raise ValueError("context indicator availability differs")
        for column in features:
            if column not in (*KEYS, "date", *PRICE_COLS):
                values[prefix + "_" + column] = features[column].to_numpy()
    return pd.concat([bounds[list(KEYS)], pd.DataFrame(values, index=bounds.index)], axis=1)


def combine_contexts(frames):
    if not frames:
        raise ValueError("no context blocks")
    result = frames[0].copy()
    for frame in frames[1:]:
        if not result[list(KEYS)].equals(frame[list(KEYS)]):
            raise ValueError("context candle boundaries differ")
        columns = [c for c in frame if c not in KEYS]
        if set(columns) & set(result):
            raise ValueError("duplicate context column")
        result = pd.concat([result, frame[columns]], axis=1)
    for numerator, denominator, name in (
        ("cboe_vix9d_close", "cboe_vix_close", "vix9d_vix_term_ratio"),
        ("cboe_vix3m_close", "cboe_vix_close", "vix3m_vix_term_ratio"),
    ):
        if {numerator, denominator} <= set(result):
            result[name] = result[numerator] / result[denominator].where(result[denominator] > 0)
    return result


def attach_context(query_dates, native, timeframe, columns=None):
    """Attach at availability <= D; each source candle must end strictly < D."""
    if timeframe not in TIMEFRAMES:
        raise ValueError("unknown timeframe")
    _dates(query_dates, "stock query dates")
    _dates(native.available_from, "context availability")
    if not (native.source_candle_end < native.available_from).all():
        raise ValueError("context candle exposed before completion")
    selected = [c for c in native if c not in KEYS] if columns is None else list(columns)
    if not set(selected) <= (set(native) - set(KEYS)):
        raise ValueError("requested context columns missing or not features")
    native=native.copy()
    for key in KEYS:
        native[key]=pd.to_datetime(native[key]).astype('datetime64[ns]')
    if native.empty:
        result = pd.DataFrame({"date": pd.to_datetime(query_dates).astype("datetime64[ns]")})
        for column in selected:
            result[column + "__" + timeframe] = np.nan
        return result
    return align_features(query_dates, native[["available_from", *selected]], timeframe)


def membership_at(ticker, query_dates, mapping, role):
    """Select a dated sector/industry assignment known strictly before D.

    A current label first captured in 2026 cannot populate 2020. The caller must
    retain the source evidence for known_from; this helper never invents dates.
    """
    if role not in ("sector", "industry"):
        raise ValueError("unknown membership role")
    target = role + "_etf"
    required = {"ticker", "known_from", target}
    if not required <= set(mapping):
        raise ValueError("membership needs ticker, known_from and " + target)
    dates = _dates(query_dates, "stock query dates")
    rows = mapping.loc[mapping.ticker == ticker, ["known_from", target]].copy()
    rows["known_from"] = pd.to_datetime(rows.known_from).astype("datetime64[ns]")
    if rows.known_from.isna().any():
        raise ValueError("membership knowledge date missing")
    if rows.groupby("known_from", dropna=False)[target].nunique(dropna=False).gt(1).any():
        raise ValueError("conflicting membership at the same knowledge date")
    rows = rows.drop_duplicates("known_from").sort_values("known_from")
    result = pd.merge_asof(pd.DataFrame({"date": dates}), rows,
                           left_on="date", right_on="known_from", direction="backward",
                           allow_exact_matches=False)
    return result.rename(columns={target: "benchmark"})


def attach_mapped_context(ticker, query_dates, mapping, candidates, timeframe, role):
    """Attach the stock's PIT benchmark, returning its dated lineage separately.

    Candidate frames must use a shared role schema (e.g. sector_close) instead
    of ticker-specific names. Missing classification remains unavailable.
    """
    lineage = membership_at(ticker, query_dates, mapping, role)
    if not candidates:
        raise ValueError("no candidate benchmark contexts")
    schemas = [{c for c in frame if c not in KEYS} for frame in candidates.values()]
    if any(schema != schemas[0] for schema in schemas[1:]):
        raise ValueError("candidate benchmark schemas differ")
    selected = set(lineage.benchmark.dropna())
    if not selected <= set(candidates):
        raise ValueError("mapped benchmark source missing: " + ",".join(sorted(selected-set(candidates))))
    columns = sorted(schemas[0])
    result = pd.DataFrame({"date": lineage.date})
    for column in columns:
        result[column + "__" + timeframe] = np.nan
    for symbol in sorted(selected):
        attached = attach_context(query_dates, candidates[symbol], timeframe, columns)
        mask = lineage.benchmark == symbol
        result.loc[mask, attached.columns.drop("date")] = attached.loc[mask, attached.columns.drop("date")].to_numpy()
    return result, lineage


def relative_native(stock, benchmark, role, stock_column="stock_close", benchmark_column=None):
    """Dictionary RS, beta/correlation and Mansfield on matching native intervals."""
    from world_bar_statistics import relative_statistics
    benchmark_column = benchmark_column or role + "_close"
    if not stock[list(KEYS)].equals(benchmark[list(KEYS)]):
        raise ValueError("relative context candle boundaries differ")
    def inputs(frame, column):
        return frame[["candle_start", "source_candle_end", column]].rename(
            columns={"source_candle_end": "date", column: "close"})
    values = relative_statistics(inputs(stock, stock_column), inputs(benchmark, benchmark_column), role)
    a = stock[stock_column].reset_index(drop=True)
    b = benchmark[benchmark_column].reset_index(drop=True)
    ratio = (a / b.where(b > 0)).where(a > 0)
    values["RS_LOG_" + role] = np.log(ratio).to_numpy()
    for window in (5, 10, 20, 60):
        previous_a = a.shift(window);previous_b = b.shift(window)
        values[f"RS_RETURN_{role}_{window}"] = (
            a / previous_a.where(previous_a > 0) - b / previous_b.where(previous_b > 0)
        ).to_numpy()
    return pd.concat([stock[list(KEYS)], pd.DataFrame(values, index=stock.index)], axis=1)

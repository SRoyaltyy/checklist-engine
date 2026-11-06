"""Synthetic clocks/values only. Real-market probes run on GitHub runners."""
import csv
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from world_price_availability import CONTRACT, TIMEFRAMES, PriceColumnView, load_contract
from world_timeframes import completed_candles


@pytest.fixture
def calendar():
    # Deliberately omit a holiday; calendar positions, not weekdays, govern reads.
    days = pd.bdate_range('2019-12-16', '2020-07-10')
    return days.difference(pd.DatetimeIndex(['2020-01-01', '2020-01-20', '2020-02-17']))


def synthetic(calendar, timeframe='1d'):
    close = 100.0 + np.arange(len(calendar), dtype='float64') / 8
    bars = pd.DataFrame(dict(date=calendar, open=close, high=close + 1,
                             low=close - 1, close=close, volume=close * 100))
    native = completed_candles(bars, timeframe, session_calendar=calendar)
    fields = load_contract().fields
    values = np.arange(len(native), dtype='float64')[:, None] + np.arange(len(fields))[None, :] / 4096
    features = pd.DataFrame(values, columns=fields)
    features['available_from'] = native['available_from']
    return native, features


@pytest.mark.parametrize('timeframe', TIMEFRAMES)
def test_every_registered_column_has_its_own_guarded_clock(calendar, timeframe):
    native, features = synthetic(calendar, timeframe)
    query = calendar[[0, -1]]
    aligned = PriceColumnView(native, features, timeframe, calendar).align(query)
    assert len(aligned.values.columns) == 1045
    # Independent eligibility lookup, rather than another asof/searchsorted call.
    eligible = [i for i, row in native.iterrows()
                if row.available_from <= query[-1] and row.date < query[-1]]
    last = eligible[-1]
    for field in load_contract().fields:
        column = aligned.column(field)
        assert pd.isna(column.value.iloc[0]) and pd.isna(column.available_from.iloc[0])
        assert column.value.iloc[-1] == features[field].iloc[last]
        assert column.available_from.iloc[-1] == native.available_from.iloc[last]
        assert column.source_candle_end.iloc[-1] == native.date.iloc[last]
        assert column.source_candle_end.iloc[-1] < query[-1]


def test_future_values_cannot_change_any_earlier_column(calendar):
    native, features = synthetic(calendar)
    cut = calendar[65]
    before = PriceColumnView(native, features, '1d', calendar).align(calendar[:66])
    altered = features.copy()
    altered.loc[altered.available_from > cut, list(load_contract().fields)] *= 1e100
    after = PriceColumnView(native, altered, '1d', calendar).align(calendar[:66])
    np.testing.assert_array_equal(before.values.iloc[:, 1:].to_numpy().view('uint64'),
                                  after.values.iloc[:, 1:].to_numpy().view('uint64'))
    pd.testing.assert_frame_equal(before.clocks, after.clocks)


def test_warmup_missing_infinity_and_signed_zero_keep_distinct_semantics(calendar):
    native, features = synthetic(calendar)
    fields = load_contract().fields
    features.loc[features.index[-1], fields[0]] = np.nan
    features.loc[features.index[-1], fields[1]] = np.inf
    features.loc[features.index[-1], fields[2]] = -0.0
    view = PriceColumnView(native, features, '1d', calendar)
    missing = view.read(fields[0], calendar[-1:])
    assert missing.value.isna().all() and missing.available_from.isna().all()
    assert missing.source_candle_end.isna().all()  # never backfill the older known value
    infinite = view.read(fields[1], calendar[-1:])
    assert np.isposinf(infinite.value.iloc[0]) and infinite.available_from.notna().all()
    zero = view.read(fields[2], calendar[-1:])
    assert zero.value.iloc[0] == 0 and np.signbit(zero.value.iloc[0])


def test_view_copies_input_and_returns_no_reference_to_mutable_source(calendar):
    native, features = synthetic(calendar)
    field = load_contract().fields[0]
    view = PriceColumnView(native, features, '1d', calendar)
    expected = view.read(field, calendar[-1:])
    features.loc[:, field] = 999999.0
    native.loc[:, 'date'] = calendar[-1]
    pd.testing.assert_frame_equal(view.read(field, calendar[-1:]), expected)


def test_empty_native_output_keeps_all_registered_columns_unknown(calendar):
    native, features = synthetic(calendar)
    aligned = PriceColumnView(native.iloc[:0], features.iloc[:0], '1d', calendar).align(calendar[:3])
    assert aligned.values.shape == (3, 1045)
    assert aligned.values.iloc[:, 1:].isna().all().all()
    column = aligned.column(load_contract().fields[-1])
    assert column[['available_from', 'source_candle_end']].isna().all().all()


def test_empty_recipe_schema_can_be_object_typed_without_inventing_values(calendar):
    native, _ = synthetic(calendar)
    features = pd.DataFrame(columns=[*load_contract().fields, 'available_from'])
    result = PriceColumnView(native.iloc[:0], features, '1d', calendar).align(calendar[:1])
    assert result.values.iloc[:, 1:].isna().all().all()


@pytest.mark.parametrize('damage', ['future_end', 'backdated_clock', 'different_clock',
                                  'incomplete_start', 'missing_field', 'extra_field',
                                  'duplicate_field', 'float32_value'])
def test_malformed_native_source_cannot_expose_columns(calendar, damage):
    native, features = synthetic(calendar, '5d')
    field = load_contract().fields[0]
    if damage == 'future_end':
        native.loc[0, 'date'] = native.available_from.iloc[0]
    elif damage == 'backdated_clock':
        native.loc[0, 'available_from'] = native.date.iloc[0]
        features.loc[0, 'available_from'] = native.date.iloc[0]
    elif damage == 'different_clock':
        features.loc[0, 'available_from'] = calendar[6]
    elif damage == 'incomplete_start':
        native.loc[0, 'candle_start'] = calendar[1]
    elif damage == 'missing_field':
        features = features.drop(columns=field)
    elif damage == 'extra_field':
        features['UNREGISTERED'] = 1.0
    elif damage == 'duplicate_field':
        features = pd.concat([features, features[[field]]], axis=1)
    elif damage == 'float32_value':
        features[field] = features[field].astype('float32')
    with pytest.raises(ValueError):
        PriceColumnView(native, features, '5d', calendar)


def test_calendar_holiday_is_not_replaced_by_a_weekday_guess(calendar):
    native, features = synthetic(calendar)
    row = native.index[native.date == pd.Timestamp('2020-01-17')][0]
    assert native.available_from.iloc[row] == pd.Timestamp('2020-01-21')
    native.loc[row, 'available_from'] = pd.Timestamp('2020-01-20')
    features.loc[row, 'available_from'] = pd.Timestamp('2020-01-20')
    with pytest.raises(ValueError, match='next bound trading session'):
        PriceColumnView(native, features, '1d', calendar)


def test_partial_final_month_cannot_be_declared_available(calendar):
    native, features = synthetic(calendar, 'monthly')
    native.loc[native.index[-1], 'date'] = calendar[-1]
    native.loc[native.index[-1], 'available_from'] = pd.Timestamp('2020-08-01')
    features.loc[features.index[-1], 'available_from'] = pd.Timestamp('2020-08-01')
    with pytest.raises(ValueError, match='monthly'):
        PriceColumnView(native, features, 'monthly', calendar)


@pytest.mark.parametrize('query', [pd.to_datetime(['2020-01-03', '2020-01-02']),
    pd.to_datetime(['2020-01-02', '2020-01-02']), pd.to_datetime(['2020-01-02', None]),
    pd.to_datetime(['2020-01-02 10:00']), pd.to_datetime(['2020-01-02'], utc=True),
    pd.to_datetime(['2020-01-20'])])
def test_ambiguous_or_non_session_setup_keys_are_rejected(calendar, query):
    native, features = synthetic(calendar)
    with pytest.raises(ValueError):
        PriceColumnView(native, features, '1d', calendar).align(query)


def test_unknown_columns_and_timeframes_cannot_bypass_registration(calendar):
    native, features = synthetic(calendar)
    with pytest.raises(ValueError, match='timeframe'):
        PriceColumnView(native, features, '2w', calendar)
    view = PriceColumnView(native, features, '1d', calendar)
    with pytest.raises(ValueError, match='unregistered'):
        view.read('not_a_price_column', calendar[-1:])


@pytest.mark.parametrize('damage', ['missing_pair', 'duplicate_pair', 'altered_clock', 'different_field'])
def test_contract_cannot_omit_or_rebind_any_produced_column(tmp_path, damage):
    meta = json.loads(CONTRACT.read_bytes())
    rows = list(csv.DictReader(io.StringIO((CONTRACT.parent / meta['columns_file']).read_text())))
    if damage == 'missing_pair':
        rows.pop()
    elif damage == 'duplicate_pair':
        rows.append(rows[0])
    elif damage == 'altered_clock':
        rows[0]['available_from'] = 'setup_date'
    else:
        rows[0]['native_field'] = 'invented'
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=rows[0].keys(), lineterminator='\n')
    writer.writeheader(); writer.writerows(rows)
    body = stream.getvalue().encode()
    (tmp_path / meta['columns_file']).write_bytes(body)
    meta['columns_lf_sha256'] = hashlib.sha256(body).hexdigest()
    path = tmp_path / CONTRACT.name
    path.write_text(json.dumps(meta), encoding='utf-8')
    with pytest.raises(ValueError):
        load_contract(path)

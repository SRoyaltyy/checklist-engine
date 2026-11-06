"""Explicit clocks for every produced #203 price column; no price calculation.

The shared native clock is referenced by each registered column. A column read
returns a value and its own masked clock, so a missing value has no available
date. Published source/recipe bytes and numeric values are never rewritten.
"""
import csv
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / 'dictionary/PRICE_COLUMN_AVAILABILITY_V1.json'
TIMEFRAMES = tuple(f'{i}d' for i in range(1, 22)) + ('monthly',)
PLAN_SHA = '18e12eed42099647d598931868547c85f99731b14b6f6138fece0fd87a43043d'
REPORT_SHA = 'a40b5279a017f5d08af7e32577e6663ac3d295067525ef3480dfaec6648b3734'
FIELDS_SHA = '773bd59b5e7190083a9051fe7aa8c0b569d2e071ec85f52309ac51027cfffccd'
CALENDAR_SHA = '3904f3115c180d40f230e36facad6b585efed861f0e8af13225e4dfb8513d074'
RECIPE = '40ea182cf6fb377d12710ccbfccd7ab2b5f17b9e6e6f07df08cf4399956ca0c3'
CSV_FIELDS = ('column', 'timeframe', 'native_field', 'available_from', 'source_candle_end', 'missing_rule')
PATTERN_TRANSPORT = dict(field_prefix='CDL', native_dtype='float32', read_dtype='float64',
                         conversion='exact IEEE value promotion; no rounding')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def binding(field, timeframe):
    return dict(column=field + '__' + timeframe, timeframe=timeframe, native_field=field,
                available_from='features.available_from', source_candle_end='candles.date',
                missing_rule='NaN_is_unknown;infinity_is_known')


@dataclass(frozen=True)
class PriceColumnContract:
    fields: tuple
    columns_sha256: str
    metadata_sha256: str


@lru_cache(maxsize=4)
def load_contract(path=CONTRACT):
    path = Path(path)
    raw = path.read_bytes().replace(b'\r\n', b'\n')
    meta = json.loads(raw)
    if (meta['format'] != 'PRICE_COLUMN_AVAILABILITY_V1' or meta['version'] != 1
            or meta['source_plan']['sha256'] != PLAN_SHA or meta['measurement']['sha256'] != REPORT_SHA
            or meta['source_fields_sha256'] != FIELDS_SHA or meta['calendar_sha256'] != CALENDAR_SHA
            or meta['recipe_fingerprint'] != RECIPE or meta['timeframes'] != list(TIMEFRAMES)
            or meta['native_fields'] != 1044 or meta['columns'] != 22968
            or meta.get('pattern_code_transport') != PATTERN_TRANSPORT or meta['scoring_gate'] != 'CLOSED'):
        raise ValueError('price column contract changes its measured source or scope')
    name = meta['columns_file']
    if Path(name).name != name or not name.endswith('.csv'):
        raise ValueError('unsafe column contract path')
    body = (path.parent / name).read_bytes().replace(b'\r\n', b'\n')
    if digest(body) != meta['columns_lf_sha256']:
        raise ValueError('column contract fingerprint differs')
    reader = csv.DictReader(io.StringIO(body.decode('utf-8')))
    if tuple(reader.fieldnames or ()) != CSV_FIELDS:
        raise ValueError('column contract header differs')
    rows = list(reader)
    fields = tuple(sorted({row['native_field'] for row in rows}))
    if len(fields) != 1044 or digest(json.dumps(list(fields), separators=(',', ':')).encode()) != FIELDS_SHA:
        raise ValueError('column contract changes the produced field set')
    expected = [binding(field, tf) for tf in TIMEFRAMES for field in fields]
    if rows != expected:
        raise ValueError('missing, repeated or altered column availability binding')
    return PriceColumnContract(fields, digest(body), digest(raw))


def date_keys(values, label, *, allow_empty=True):
    keys = pd.DatetimeIndex(pd.to_datetime(values)).as_unit('ns')
    if (keys.tz is not None or keys.hasnans or keys.has_duplicates
            or not keys.is_monotonic_increasing or not keys.equals(keys.normalize())
            or (not allow_empty and not len(keys))):
        raise ValueError(label + ' must contain ordered unique known date keys')
    return keys


def validate_candle_keys(candles, timeframe, calendar):
    """Certify complete global-calendar buckets, including IPO/halt boundaries."""
    if timeframe not in TIMEFRAMES:
        raise ValueError('unregistered price timeframe')
    start = date_keys(candles['candle_start'], 'candle starts')
    end = date_keys(candles['date'], 'candle ends')
    available = date_keys(candles['available_from'], 'native availability')
    if not len(end):
        return end, available
    positions = calendar.get_indexer(end)
    starts = calendar.get_indexer(start)
    if (np.any(positions < 0) or np.any(starts < 0)
            or np.any(start.asi8 > end.asi8) or np.any(end.asi8 >= available.asi8)):
        raise ValueError('price candle source must end before availability on the bound calendar')
    if timeframe == 'monthly':
        months = calendar.to_period('M')
        first = {p: calendar[months == p][0] for p in months.unique()}
        last = {p: calendar[months == p][-1] for p in months.unique()}
        for left, right, stamp in zip(start, end, available):
            period = right.to_period('M')
            if (period >= months[-1] or left != first[period] or right != last[period]
                    or stamp != (period + 1).start_time):
                raise ValueError('incomplete or backdated monthly price candle')
    else:
        size = int(timeframe[:-1])
        if (np.any(starts % size != 0) or np.any(positions != starts + size - 1)
                or np.any(positions + 1 >= len(calendar))):
            raise ValueError('incomplete global-session price candle')
        if not available.equals(calendar[positions + 1]):
            raise ValueError('price availability must be the next bound trading session')
    return end, available


@dataclass
class AlignedPriceColumns:
    values: pd.DataFrame
    clocks: pd.DataFrame
    fields: tuple
    timeframe: str
    contract_sha256: str

    def column(self, field):
        if field not in self.fields:
            raise ValueError('unregistered or unselected price column')
        name = field + '__' + self.timeframe
        value = self.values[name]
        known = value.notna()  # infinities and signed zero remain known, unchanged
        result = pd.DataFrame(dict(date=self.values['date'], value=value,
            available_from=self.clocks['available_from'].where(known),
            source_candle_end=self.clocks['source_candle_end'].where(known)))
        result.attrs['column'] = name
        result.attrs['column_contract_sha256'] = self.contract_sha256
        return result


class PriceColumnView:
    """Guarded read-only view over native output from the frozen price recipe."""

    def __init__(self, candles, features, timeframe, session_calendar):
        self.contract = load_contract()
        self.timeframe = timeframe
        self.calendar = date_keys(session_calendar, 'session calendar', allow_empty=False).copy()
        if (features.columns.has_duplicates or set(features) != set(self.contract.fields) | {'available_from'}
                or len(features) != len(candles)):
            raise ValueError('price columns differ from the complete measured schema')
        unsupported = {name: str(features[name].dtype) for name in self.contract.fields
            if len(features) and features[name].dtype != np.dtype('float64')
            and not (name.startswith('CDL') and features[name].dtype == np.dtype('float32'))}
        if unsupported:
            raise ValueError('unsupported frozen price transport: ' + json.dumps(unsupported, sort_keys=True))
        self.end, self.available = validate_candle_keys(candles, timeframe, self.calendar)
        feature_clock = date_keys(features['available_from'], 'feature availability')
        if not feature_clock.equals(self.available):
            raise ValueError('feature clocks differ from their source candles')
        self.end = self.end.copy()
        self.available = self.available.copy()
        self.features = features.loc[:, list(self.contract.fields)].copy(deep=True).reset_index(drop=True)
        if not len(self.features):
            self.features = self.features.astype('float64')
        else:
            # The bound recipe deliberately transports TA-Lib pattern codes as
            # float32. Promotion is exact, matching the existing PIT float64
            # matrix interpretation; indicator floats still require float64.
            for name in self.contract.fields:
                if self.features[name].dtype == np.dtype('float32'):
                    self.features[name] = self.features[name].astype('float64')

    def _align(self, query_dates, fields):
        query = date_keys(query_dates, 'setup dates')
        if np.any(self.calendar.get_indexer(query) < 0):
            raise ValueError('setup date is outside the bound trading calendar')
        positions = self.available.searchsorted(query, side='right') - 1
        present = positions >= 0
        selected = positions[present]
        if len(selected) and (np.any(self.available.asi8[selected] > query.asi8[present])
                or np.any(self.end.asi8[selected] >= query.asi8[present])):
            raise ValueError('price source is not known before the setup open')
        values = np.full((len(query), len(fields)), np.nan, dtype='float64')
        stamps = np.full(len(query), np.datetime64('NaT'), dtype='datetime64[ns]')
        ends = stamps.copy()
        if len(selected):
            values[present] = self.features.loc[:, fields].to_numpy(copy=False)[selected]
            stamps[present] = self.available.to_numpy()[selected]
            ends[present] = self.end.to_numpy()[selected]
        frame = pd.DataFrame(values, columns=[field + '__' + self.timeframe for field in fields])
        frame.insert(0, 'date', query)
        clocks = pd.DataFrame(dict(date=query, available_from=stamps, source_candle_end=ends))
        return AlignedPriceColumns(frame, clocks, tuple(fields), self.timeframe, self.contract.columns_sha256)

    def align(self, query_dates):
        return self._align(query_dates, list(self.contract.fields))

    def read(self, field, query_dates):
        if field not in self.contract.fields:
            raise ValueError('unregistered price column')
        return self._align(query_dates, [field]).column(field)

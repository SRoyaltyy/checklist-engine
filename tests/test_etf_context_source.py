import io
import json

import numpy as np
import pandas as pd
import pytest

from ci import etf_context_source as source
from world_timeframes import TIMEFRAMES


def bars():
    calendar = pd.bdate_range('2019-01-02', periods=320)
    close = np.arange(len(calendar), dtype=float) + 100
    return pd.DataFrame(dict(ticker='SPY', date=calendar, open=close,
                             high=close + 2, low=close - 2, close=close + 1, volume=1000.))


def test_native_source_future_truncation_all_timeframes_and_preipo_blanks():
    frame = bars()
    ipo = frame.iloc[170:].copy().assign(ticker='IBIT')
    sources = {'SPY': frame, 'IBIT': ipo}
    full = source.contexts(sources, pd.DatetimeIndex(frame.date))
    checks = source.prefix_checks(full, sources, pd.DatetimeIndex(frame.date),
                                  cuts=(str(frame.date.iloc[150].date()), str(frame.date.iloc[250].date())))
    assert len(checks) == 2 * len(TIMEFRAMES)
    assert all(c['mismatches'] == 0 for c in checks)
    daily = full['1d']
    assert daily.etf_ibit_close.iloc[:170].isna().all()
    assert daily.etf_ibit_close.iloc[170] == ipo.close.iloc[0]
    assert daily.etf_ibit_d200.isna().all()
    # A five-candle return on 5d is a 25-session price change.
    assert full['5d'].etf_spy_r5.iloc[5] == pytest.approx(frame.close.iloc[29] / frame.close.iloc[4] - 1)


@pytest.mark.parametrize('change', ['ticker', 'order', 'calendar'])
def test_verified_member_still_requires_correct_ticker_dates_and_calendar(change):
    frame = bars()
    calendar = pd.DatetimeIndex(frame.date).copy(deep=True)
    if change == 'ticker':
        frame.loc[0, 'ticker'] = 'QQQ'
    elif change == 'order':
        frame = frame.iloc[::-1]
    else:
        frame.loc[0, 'date'] = pd.Timestamp('1900-01-01')
    raw = io.BytesIO()
    frame.to_parquet(raw, index=False)
    with pytest.raises(ValueError, match='ETF source'):
        source.validated_bars(raw.getvalue(), 'SPY', calendar)


def test_partial_compact_shard_reports_missing_target_without_substitution(tmp_path, monkeypatch):
    inputs = {'records': [dict(ticker='SPY', ordinal=0), dict(ticker='QQQ', ordinal=16)]}
    original_download = source.base.download

    def complete_parts(tag, inputs, selected, directory):
        assert selected == {'SPY', 'QQQ'}
        directory.mkdir(parents=True)
        (directory / 'base_0000.json').write_text(json.dumps({'members': []}))
        return [dict(part='base_0000', release=tag, tickers=['SPY'])], []

    monkeypatch.setattr(source.base, 'recover_base_parts', complete_parts)
    parts, missing = source.target_parts(inputs, ['SPY', 'QQQ', 'ABSENT'], tmp_path, 'compact')
    assert parts[0][2] == ['SPY']
    assert missing == ['ABSENT', 'QQQ']
    assert source.base.download is original_download


def test_explicit_missing_etf_reconciliation_preserves_old_prices_and_rejects_stale_or_incompatible_source():
    dates = pd.bdate_range(end='2026-10-23', periods=140)
    close = 50 + np.arange(140) * .05
    new = pd.DataFrame(dict(ticker='XLI', date=dates, open=close, high=close + 1,
                            low=close - 1, close=close, volume=1000.))
    old = new.iloc[20:110].copy()
    old[['open', 'high', 'low', 'close']] *= 3
    out, bridge = source.reconcile_etf('XLI', old, new, None, dates)
    np.testing.assert_allclose(out.close, new.close * 3)
    assert bridge['frozen_values_unchanged']
    assert not bridge['nominal_historical_price_verified']
    with pytest.raises(ValueError, match='rejected/stale'):
        source.reconcile_etf('XLI', old, new.iloc[:-1], None, dates)
    with pytest.raises(ValueError, match='RECONCILIATION_FAIL'):
        source.reconcile_etf('XLI', old, new.assign(volume=100000.), None, dates)


def test_missing_etf_fallback_rejects_changed_recipe_before_source_io(tmp_path, monkeypatch):
    monkeypatch.setattr(source.frozen, 'recipe_fingerprint', lambda: ('changed', {}))
    with pytest.raises(ValueError, match='unchanged frozen recipe'):
        source.missing_etf_sources(dict(price_source_release=source.frozen.PRICE_TAG,
                                       recipe_fingerprint='original'), ['XLI'], tmp_path, [])


def test_daily_source_retains_final_session_separately_from_completed_native_features(tmp_path):
    frame=bars();calendar=pd.DatetimeIndex(frame.date)
    inputs=dict(inputs_tag='frozen',recipe_fingerprint='recipe',calendar_sha256='calendar',
                as_of_completed_session=str(frame.date.max().date()))
    files,records=source.daily_source_proof({'SPY':frame},inputs,calendar,tmp_path)
    saved=pd.read_parquet(next(f for f in files if f.suffix=='.parquet'))
    assert saved.date.max()==frame.date.max()
    assert source.contexts({'SPY':frame},calendar)['1d'].source_candle_end.max()<saved.date.max()
    assert records[0]['missing_sessions_after_first_source_date']==[]
    with pytest.raises(ValueError,match='stock cutoff'):
        source.daily_source_proof({'SPY':frame.iloc[:-1]},inputs,calendar,tmp_path)

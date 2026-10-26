import pandas as pd
import pytest
import facets_world as fw


def frame(ticker,dates,closes):
    return pd.DataFrame(dict(ticker=ticker,date=pd.to_datetime(dates),open=closes,high=closes,low=closes,close=closes,volume=1000.))


def test_authoritative_prices_override_post_2020_updown_and_keep_universe_only_names(tmp_path,monkeypatch):
    canonical=pd.concat([frame('A',['2020-01-02'],[20.]),frame('UNIVERSE_ONLY',['2020-01-02'],[30.])],ignore_index=True)
    legacy=frame('A',['2019-12-31','2020-01-02'],[10.,999.])
    canonical.to_parquet(tmp_path/'universe_2020_survivors.parquet',index=False)
    legacy.to_parquet(tmp_path/'bars_all.parquet',index=False)
    from pathlib import PurePosixPath
    monkeypatch.setattr(fw,'D',lambda p:tmp_path/PurePosixPath(p).name)
    actual=fw.load_bars()
    assert set(actual.ticker)=={'A','UNIVERSE_ONLY'}
    assert list(actual[actual.ticker=='A'].close)==[10.,20.]
    assert str(actual.date.dtype)=='datetime64[ns]'
    assert list(fw.load_bars({'UNIVERSE_ONLY'}).close)==[30.]

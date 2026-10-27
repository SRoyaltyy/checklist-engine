import numpy as np
import pandas as pd
import pytest
from fetch.fetch_event_history import normalize_rows


def test_analyst_actions_keep_canonical_identity_and_provider_time_without_backdating():
    frame=pd.DataFrame({"Firm":["A","B"],"FromGrade":["Hold","Buy"],"ToGrade":["Buy","Hold"],"Action":["up","down"]},
                       index=pd.to_datetime(["2020-01-02T01:00:00Z","2020-01-03T15:00:00Z"]))
    out=normalize_rows("NA",frame,"analyst")
    assert out.ticker.tolist()==["NA","NA"] and out.direction.tolist()==[1,-1]
    assert out.event_date.tolist()==["2020-01-01","2020-01-03"]
    assert set(out.source_timezone)=={"UTC"}


def test_earnings_keeps_reported_eps_missing_surprise_and_unproven_naive_timezone():
    frame=pd.DataFrame({"EPS Estimate":[1.],"Reported EPS":[1.2]},index=pd.to_datetime(["2020-01-02"]))
    row=normalize_rows("A",frame,"earnings").iloc[0]
    assert row.eps_actual==1.2 and np.isnan(row.surprise_pct)
    assert row.source_timezone=="PROVIDER_NAIVE_TIMEZONE_UNPROVEN"
    assert normalize_rows("A",None,"earnings").empty
    with pytest.raises(ValueError,match="schema differs"):normalize_rows("A",frame,"analyst")

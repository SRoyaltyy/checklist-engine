import pandas as pd

import cursor_session_factors as factors
from world_context_native import attach_context
from world_context_store import validate_factor


def test_calendar_flag_is_numeric_and_hidden_until_the_next_session():
    frame = pd.DataFrame({
        "timeframe": ["1d", "1d"],
        "candle_start": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        "available_from": pd.to_datetime(["2024-01-03", "2024-01-04"]),
        "is_fomc": [True, False],
    })
    native = factors.to_native_factor(frame, "calendar_")
    columns = validate_factor(native)
    assert columns == ["calendar_is_fomc"]
    attached = attach_context(pd.to_datetime(["2024-01-02", "2024-01-03"]), native, "1d")
    assert pd.isna(attached["calendar_is_fomc__1d"].iloc[0])
    assert attached["calendar_is_fomc__1d"].iloc[1] == 1

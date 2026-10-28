"""Scheduled market calendar flags. No prices.

FOMC days come from the Federal Reserve's public calendar. CPI and jobs-report
days are the first ALFRED vintage of CPIAUCSL and UNRATE, which is the morning
release. Month-end, turn-of-month, and monthly options expiry are rules on the
NYSE session calendar. A row on day D does not read prices. A release dated
after D is not flagged on D. Candle rows repeat the end session's facts.
They are not a count or an average of the sessions inside the candle.
"""

from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

FRED_RELEASE = "fred-structured-v3-40266650669-1"
FRED_ARCHIVE = "fred_structured_source.tar.gz"
FRED_ARCHIVE_SHA256 = "16a60d96ccbc0f9e5424bc9dc5057e3a72327a48b8036078072cca4bfbedb5d8"
FOMC_CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
FOMC_2020_URL = "https://www.federalreserve.gov/monetarypolicy/fomchistorical2020.htm"
WINDOW_START = pd.Timestamp("2020-01-02")
MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
FLAG_COLUMNS = (
    "is_fomc", "is_fomc_notation", "is_cpi", "is_jobs", "is_month_start",
    "is_month_end", "is_turn_of_month", "is_opex",
)
CANDLE_NOTE = (
    "Each candle row repeats the calendar facts of its end session. "
    "The flags are not counted, averaged, or otherwise combined across the sessions inside the candle. "
    "They are calendar facts, not resampled prices. "
    "available_from is the next session after the candle completes, so a candle that contains day D is not visible on D."
)


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_sha256(path, expected):
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError("archive bytes differ: " + Path(path).name)
    return actual


def _clean(html):
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def _month_number(name):
    key = name.strip().lower()
    if key not in MONTHS:
        raise ValueError("unknown month: " + name)
    return MONTHS[key]


def _expand_days(year, month_text, day_text):
    """Turn 'Apr/May' and '30-1' into concrete dates. A wrap uses the next month."""
    parts = [part.strip() for part in month_text.split("/") if part.strip()]
    start_month = _month_number(parts[0])
    end_month = _month_number(parts[-1])
    numbers = [int(piece) for piece in re.findall(r"\d{1,2}", day_text)]
    if not numbers:
        raise ValueError("no day in " + day_text)
    if len(numbers) == 1:
        return [pd.Timestamp(year=year, month=start_month, day=numbers[0])]
    start_day, end_day = numbers[0], numbers[1]
    start = pd.Timestamp(year=year, month=start_month, day=start_day)
    if end_day < start_day or end_month != start_month:
        end_year = year + 1 if end_month < start_month else year
        end = pd.Timestamp(year=end_year, month=end_month, day=end_day)
    else:
        end = pd.Timestamp(year=year, month=start_month, day=end_day)
    return list(pd.date_range(start, end, freq="D"))


def parse_fomc_historical(html, year):
    """Headings such as 'March 15 (unscheduled) Meeting - 2020'. Cancelled meetings are skipped."""
    rows = []
    for raw in re.findall(r"<h5[^>]*>(.*?)</h5>", html, flags=re.S):
        heading = _clean(raw)
        if str(year) not in heading:
            continue
        if "cancelled" in heading.lower():
            continue
        match = re.search(
            r"(January|February|March|April|May|June|July|August|September|October|November|December)"
            r"\s+(\d{1,2})(?:\s*[-–]\s*(\d{1,2}))?",
            heading,
        )
        if not match:
            continue
        kind = "notation" if "notation" in heading.lower() else "meeting" if "meeting" in heading.lower() else ""
        if not kind:
            continue
        month = _month_number(match.group(1))
        start = int(match.group(2))
        end = int(match.group(3) or start)
        for day in range(start, end + 1):
            rows.append(dict(date=pd.Timestamp(year=int(year), month=month, day=day), kind=kind))
    return pd.DataFrame(rows, columns=["date", "kind"])


def parse_fomc_calendars(html):
    """The current Fed calendar page, one section per year, newest section first in the file."""
    marks = [(match.start(), int(match.group(1))) for match in re.finditer(r"(20\d\d) FOMC Meetings", html)]
    marks.sort()
    rows = []
    for index, (start, year) in enumerate(marks):
        stop = marks[index + 1][0] if index + 1 < len(marks) else len(html)
        chunk = html[start:stop]
        months = re.findall(r"fomc-meeting__month[^>]*>(.*?)</div>", chunk, flags=re.S)
        dates = re.findall(r"fomc-meeting__date[^>]*>(.*?)</div>", chunk, flags=re.S)
        for month_html, date_html in zip(months, dates):
            month_text = _clean(month_html)
            day_text = _clean(date_html)
            if "cancelled" in day_text.lower() or "cancelled" in month_text.lower():
                continue
            kind = "notation" if "notation" in day_text.lower() else "meeting"
            for day in _expand_days(year, month_text, day_text):
                rows.append(dict(date=day, kind=kind))
    return pd.DataFrame(rows, columns=["date", "kind"]).drop_duplicates(["date", "kind"])


def first_release_dates(vintages):
    """The first vintage of each observation is the release. Later revisions are not new days."""
    frame = vintages.loc[:, ["obs_date", "vintage_date"]].copy()
    frame["obs_date"] = pd.to_datetime(frame["obs_date"])
    frame["vintage_date"] = pd.to_datetime(frame["vintage_date"])
    frame = frame.dropna().sort_values("vintage_date")
    first = frame.groupby("obs_date", as_index=False).first()
    return pd.DatetimeIndex(first["vintage_date"].drop_duplicates().sort_values())


def session_or_next(dates, sessions):
    """A weekend or holiday announcement is flagged on the next NYSE session."""
    sessions = pd.DatetimeIndex(pd.to_datetime(sessions)).sort_values()
    chosen = []
    for day in pd.to_datetime(dates):
        day = pd.Timestamp(day).normalize()
        if day in sessions:
            chosen.append(day)
            continue
        later = sessions[sessions > day]
        if len(later):
            chosen.append(pd.Timestamp(later[0]))
    return pd.DatetimeIndex(pd.to_datetime(chosen)).unique().sort_values()


def monthly_opex(sessions):
    """Third Friday, or the previous session when that Friday is not a session."""
    sessions = pd.DatetimeIndex(pd.to_datetime(sessions)).sort_values()
    fridays = pd.date_range(sessions[0], sessions[-1], freq="W-FRI")
    third = [day for day in fridays if 15 <= day.day <= 21]
    chosen = []
    for day in third:
        if day in sessions:
            chosen.append(pd.Timestamp(day))
            continue
        earlier = sessions[sessions < day]
        if len(earlier) and (day - earlier[-1]).days <= 4:
            chosen.append(pd.Timestamp(earlier[-1]))
    return pd.DatetimeIndex(chosen).unique().sort_values()


def _distance(sessions, events, forward):
    sessions = pd.DatetimeIndex(pd.to_datetime(sessions))
    events = pd.DatetimeIndex(pd.to_datetime(events)).sort_values().unique()
    out = np.full(len(sessions), np.nan)
    if not len(events):
        return out
    positions = {pd.Timestamp(day): index for index, day in enumerate(sessions)}
    event_positions = [positions[pd.Timestamp(day)] for day in events if pd.Timestamp(day) in positions]
    if not event_positions:
        return out
    event_positions = np.array(sorted(event_positions))
    for index in range(len(sessions)):
        if forward:
            later = event_positions[event_positions >= index]
            if len(later):
                out[index] = later[0] - index
        else:
            earlier = event_positions[event_positions <= index]
            if len(earlier):
                out[index] = index - earlier[-1]
    return out


def build_calendar(sessions, fomc, cpi_dates, jobs_dates, as_of):
    """One row per completed session. Forward counts may see a published later date."""
    sessions = pd.DatetimeIndex(pd.to_datetime(sessions)).sort_values().unique()
    as_of = pd.Timestamp(as_of)
    fomc = fomc.copy()
    fomc["date"] = pd.to_datetime(fomc["date"])
    meetings = session_or_next(fomc.loc[fomc.kind == "meeting", "date"], sessions)
    notations = session_or_next(fomc.loc[fomc.kind == "notation", "date"], sessions)
    cpi = session_or_next(pd.to_datetime(cpi_dates), sessions)
    jobs = session_or_next(pd.to_datetime(jobs_dates), sessions)
    # A release after as_of has not happened. Do not flag it and do not count toward it.
    meetings = meetings[meetings <= as_of]
    notations = notations[notations <= as_of]
    cpi = cpi[cpi <= as_of]
    jobs = jobs[jobs <= as_of]
    opex = monthly_opex(sessions)
    rows = sessions[(sessions >= WINDOW_START) & (sessions <= as_of)]
    frame = pd.DataFrame({"date": rows})
    frame["is_fomc"] = frame["date"].isin(meetings)
    frame["is_fomc_notation"] = frame["date"].isin(notations)
    frame["is_cpi"] = frame["date"].isin(cpi)
    frame["is_jobs"] = frame["date"].isin(jobs)
    frame["is_opex"] = frame["date"].isin(opex)
    month = frame["date"].dt.to_period("M")
    rank = frame.groupby(month).cumcount() + 1
    size = frame.groupby(month)["date"].transform("size")
    frame["is_month_start"] = rank == 1
    frame["is_month_end"] = rank == size
    frame["is_turn_of_month"] = frame["is_month_end"] | (rank <= 3)
    frame["day_of_week"] = frame["date"].dt.dayofweek.astype("int16")
    frame["day_of_month"] = frame["date"].dt.day.astype("int16")
    # Third Friday is a rule, so the count may see an expiry after as_of.
    # The flag itself stays off until that session is in the panel.
    to_opex = pd.Series(_distance(sessions, opex, True), index=sessions)
    since_opex = pd.Series(_distance(sessions, opex, False), index=sessions)
    frame["days_to_opex"] = frame["date"].map(to_opex).to_numpy()
    frame["days_since_opex"] = frame["date"].map(since_opex).to_numpy()
    frame["days_to_fomc"] = _distance(rows, meetings, True)
    frame["days_since_fomc"] = _distance(rows, meetings, False)
    frame["days_to_cpi"] = _distance(rows, cpi, True)
    frame["days_since_cpi"] = _distance(rows, cpi, False)
    frame["days_to_jobs"] = _distance(rows, jobs, True)
    frame["days_since_jobs"] = _distance(rows, jobs, False)
    # These facts are public before the open: the Fed/BLS calendar, or an 8:30 release.
    frame["available_from"] = frame["date"]
    if frame["date"].duplicated().any() or (frame["date"] > as_of).any():
        raise ValueError("calendar row is duplicated or after as_of")
    return frame


def carry_onto_candles(daily, sessions, as_of):
    """Put the daily facts on each completed candle. The value is the end session's value."""
    from world_timeframes import PRICE_COLS, TIMEFRAMES, completed_candles

    as_of = pd.Timestamp(as_of)
    sessions = pd.DatetimeIndex(pd.to_datetime(sessions)).tz_localize(None)
    sessions = sessions.sort_values().unique()
    facts = daily.copy()
    facts["date"] = pd.to_datetime(facts["date"]).astype("datetime64[ns]")
    facts = facts.loc[facts["date"] <= as_of].sort_values("date").reset_index(drop=True)
    fact_columns = [column for column in facts.columns if column not in ("date", "available_from")]
    bars = pd.DataFrame({
        "date": facts["date"].to_numpy(),
        "open": np.ones(len(facts)),
        "high": np.ones(len(facts)),
        "low": np.ones(len(facts)),
        "close": np.ones(len(facts)),
        "volume": np.zeros(len(facts)),
    })
    lookup = facts.set_index("date")
    frames = []
    for timeframe in TIMEFRAMES:
        candles = completed_candles(bars, timeframe, sessions)
        candles = candles.loc[candles["date"] <= as_of]
        if candles.empty:
            continue
        piece = candles.loc[:, ["candle_start", "date", "available_from"]].copy()
        piece.insert(0, "timeframe", timeframe)
        aligned = lookup.reindex(pd.DatetimeIndex(piece["date"]))
        if not pd.DatetimeIndex(piece["date"]).isin(lookup.index).all():
            raise ValueError("candle end date has no calendar row: " + timeframe)
        for column in fact_columns:
            piece[column] = aligned[column].to_numpy()
        frames.append(piece)
    if not frames:
        raise ValueError("no completed calendar candles")
    out = pd.concat(frames, ignore_index=True)
    if set(PRICE_COLS) & set(out.columns):
        raise ValueError("calendar candles stored a price")
    if (pd.to_datetime(out["available_from"]) <= pd.to_datetime(out["date"])).any():
        raise ValueError("calendar candle is visible on its end session")
    return out


def candle_summary(candles):
    from world_timeframes import TIMEFRAMES

    counts = candles.groupby("timeframe", sort=False).size()
    ordered = [timeframe for timeframe in TIMEFRAMES if timeframe in counts.index]
    return dict(
        note=CANDLE_NOTE,
        timeframes=ordered,
        rows_by_timeframe={timeframe: int(counts[timeframe]) for timeframe in ordered},
        rows=int(len(candles)),
    )


def coverage_table(frame):
    rows = []
    for column in list(FLAG_COLUMNS) + [
        "day_of_week", "day_of_month", "days_to_opex", "days_since_opex",
        "days_to_fomc", "days_since_fomc", "days_to_cpi", "days_since_cpi",
        "days_to_jobs", "days_since_jobs",
    ]:
        present = frame[column].notna()
        missing = int((~present).sum())
        percent = float(present.mean()) if len(frame) else 0.0
        rows.append(dict(
            series=column, status="PASS" if percent >= 0.95 else "EXCLUDED",
            reason="" if percent >= 0.95 else "COVERAGE_BELOW_95",
            coverage_percent=round(percent * 100, 4),
            rows=int(present.sum()), expected_sessions=int(len(frame)),
            missing_sessions=missing,
        ))
    return rows


def assert_calendar_coverage(rows):
    failed = [row["series"] for row in rows if row["status"] != "PASS"]
    if failed:
        raise ValueError("calendar coverage below 95 percent: " + ",".join(failed))
    return dict(series_passed=len(rows), excluded=[])


def write_lossless(frame, path):
    """Bool flags are parquet bit-packed. Day counts are delta-encoded."""
    path = Path(path)
    sort_on = [column for column in ("timeframe", "date") if column in frame.columns]
    stored = frame.sort_values(sort_on).reset_index(drop=True)
    counts = [column for column in stored.columns if column.startswith("days_") or column.startswith("day_")]
    for column in counts:
        if stored[column].notna().all():
            stored[column] = stored[column].astype("int16")
    encodings = {column: "DELTA_BINARY_PACKED" for column in counts if stored[column].notna().all()}
    dictionaries = ["timeframe"] if "timeframe" in stored.columns else False
    table = pa.Table.from_pandas(stored, preserve_index=False)
    pq.write_table(
        table, path, compression="zstd", compression_level=19,
        use_dictionary=dictionaries, column_encoding=encodings or None, data_page_version="2.0",
    )
    return dict(rows=len(stored), sha256=sha256_file(path),
                encoding="bool_bit_packed_and_int16_delta_zstd19")

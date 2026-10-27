import copy
import pandas as pd
import pytest
from ci.event_source_audit import validate_status, validate_part, field_counts


def status():
    return dict(kind='analyst', source_commit='source', status='REQUESTED_TICKERS_ATTEMPTED_SOURCE_ONLY',
                requested_tickers=['A', 'B'], attempts=[dict(ticker='A', status='ROWS_RETURNED', rows=1),
                dict(ticker='B', status='NO_ROWS_RETURNED_HISTORY_UNPROVEN', rows=0)],
                parts=[dict(file='events_0000.parquet', rows=1)], source_rows=1)


def test_audit_retains_empty_responses_as_unproven_not_full_history():
    counts = validate_status(status(), 'analyst', ['A', 'B'], 'source')
    assert counts['NO_ROWS_RETURNED_HISTORY_UNPROVEN'] == 1
    for key, value in [('requested_tickers', ['A']), ('source_rows', 2), ('source_commit', 'wrong')]:
        report = copy.deepcopy(status())
        report[key] = value
        with pytest.raises(ValueError):
            validate_status(report, 'analyst', ['A', 'B'], 'source')


def test_audit_verifies_actual_row_identity_counts_and_local_event_date():
    frame = pd.DataFrame([dict(ticker='A', event_timestamp='2020-01-03T01:00:00+00:00',
        event_date='2020-01-02', source_timezone='UTC', firm='F', from_grade='Hold',
        to_grade='Buy', action='up', direction=1)])
    receipt = dict(rows=1, attempts=status()['attempts'])
    validate_part(frame, 'analyst', receipt, ['A', 'B'])
    with pytest.raises(ValueError, match='timestamp/date'):
        validate_part(frame.assign(event_date='2020-01-03'), 'analyst', receipt, ['A', 'B'])
    with pytest.raises(ValueError, match='unrequested'):
        validate_part(frame.assign(ticker='OTHER'), 'analyst', receipt, ['A', 'B'])
    with pytest.raises(ValueError, match='per-ticker'):
        validate_part(frame, 'analyst', dict(rows=1, attempts=[dict(ticker='B', rows=1)]), ['A', 'B'])


def test_field_coverage_distinguishes_blank_categories_from_real_zero_and_ticker_na():
    frame=pd.DataFrame(dict(ticker=['NA','A','B'],grade=[None,'  ','Buy'],number=[0.,None,2.]))
    raw,meaningful,blanks=field_counts(frame)
    assert raw['grade']==2 and meaningful['grade']==1 and blanks['grade']==1
    assert meaningful['ticker']==3 and blanks['ticker']==0
    assert meaningful['number']==2 and blanks['number']==0

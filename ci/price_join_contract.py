"""Export and check read-only price join metadata; never calculate market features."""
import argparse
import csv
from datetime import date
import hashlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDENTITY = ROOT / 'docs/SEC_RETAINED_IDENTITY_MAP_V1.json'
KEYS = ROOT / 'dictionary/PRICE_WORLD_JOIN_KEYS_V1.csv'
SESSIONS = ROOT / 'dictionary/PRICE_WORLD_SESSIONS_V1.csv'
META = ROOT / 'docs/PRICE_WORLD_JOIN_CONTRACT_V1.json'
PLAN_SHA = '18e12eed42099647d598931868547c85f99731b14b6f6138fece0fd87a43043d'
CALENDAR_SHA = '3904f3115c180d40f230e36facad6b585efed861f0e8af13225e4dfb8513d074'
IDENTITY_SHA = '50323efcd9855061501d88010d8e812371fda7c9dd48d3a54c0f5f19cdad97ce'
FIELDS = ['price_ticker', 'candidate_cik', 'mapping_status', 'observed_first_filed',
          'observed_last_filed', 'valid_from', 'valid_to_exclusive',
          'historical_identity_status', 'historical_join_allowed', 'setup_rows', 'raw_sha256']


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def lf(path):
    return path.read_bytes().replace(b'\r\n', b'\n')


def csv_bytes(fields, rows):
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode()


def identity_rows():
    assert sha(lf(IDENTITY)) == IDENTITY_SHA, 'identity source changed; version the contract'
    return json.loads(IDENTITY.read_bytes())['records']


def identity_columns(record):
    unique = record['status'] == 'UNIQUE_CIK'
    candidates = record['candidates']
    if unique:
        assert len(candidates) == 1 and not candidates[0].get('quarantined')
        assert not candidates[0].get('quarantined_for_join')
    return dict(price_ticker=record['ticker'],
        candidate_cik=str(candidates[0]['cik']).zfill(10) if unique else '',
        mapping_status=record['status'], observed_first_filed=record['shares_first_filed'] or '',
        observed_last_filed=record['shares_last_filed'] or '', valid_from='', valid_to_exclusive='',
        historical_identity_status='NO_FORMAL_OWNERSHIP_INTERVAL', historical_join_allowed='false')


def build(plan_path, calendar_path):
    # Decode only authenticated session metadata, never OHLCV or feature arrays.
    import pandas as pd
    assert sha(plan_path.read_bytes()) == PLAN_SHA
    assert sha(calendar_path.read_bytes()) == CALENDAR_SHA
    plan = json.loads(plan_path.read_bytes())
    references = {r['ticker']: r for r in plan['references']}
    records = identity_rows()
    assert len(references) == 8439 and set(references) == {r['ticker'] for r in records}
    rows = []
    for record in sorted(records, key=lambda r: r['ticker']):
        reference = references[record['ticker']]
        rows.append(dict(**identity_columns(record), setup_rows=reference['query_rows'],
                         raw_sha256=reference['raw_sha256']))
    calendar = pd.DatetimeIndex(pd.read_parquet(calendar_path).date)
    assert calendar.is_unique and calendar.is_monotonic_increasing and not calendar.isna().any()
    assert (calendar == calendar.normalize()).all() and calendar.tz is None
    days = [d.strftime('%Y-%m-%d') for d in calendar]
    session_rows = [dict(session_date=d, previous_session=days[i-1] if i else '',
                         next_session=days[i+1] if i+1 < len(days) else '') for i,d in enumerate(days)]
    KEYS.write_bytes(csv_bytes(FIELDS, rows))
    SESSIONS.write_bytes(csv_bytes(['session_date','previous_session','next_session'], session_rows))
    metadata = dict(format='PRICE_WORLD_JOIN_CONTRACT_V1', version=1,
        status='PUBLISHED_READ_ONLY_KEYS_AND_DATE_CONVENTIONS',
        source_plan_sha256=PLAN_SHA, identity_map_lf_sha256=IDENTITY_SHA,
        source_calendar=dict(release=plan['frozen_build_request']['inputs_tag'],
                             asset='market_sessions.parquet', sha256=CALENDAR_SHA),
        keys=dict(path=str(KEYS.relative_to(ROOT)).replace('\\','/'), lf_sha256=sha(lf(KEYS)),
                  rows=8439, setup_rows=sum(r['setup_rows'] for r in rows), candidate_ciks=3996,
                  unresolved=4419, quarantined_product_aliases=24, formal_ownership_intervals=0),
        sessions=dict(path=str(SESSIONS.relative_to(ROOT)).replace('\\','/'), lf_sha256=sha(lf(SESSIONS)),
                      rows=len(days), first=days[0], last=days[-1]),
        primary_key=['price_ticker','setup_session_date'], setup_minimum='2020-01-01',
        membership='Intersect the bound calendar with authenticated per-stock setup rows; calendar membership alone is insufficient.',
        historical_identity='BLOCKED_WITHOUT_FORMAL_VALID_FROM_VALID_TO_EVIDENCE',
        observed_filing_dates='Observations only; never interpret as ownership interval endpoints.',
        sec_join='CIK + independently established dated identity; acceptance/filed date strictly before setup date.',
        options_join='Exact dated underlying mapping + source session; publication availability strictly before setup open.',
        calendar_extension='Outside the frozen calendar is unsupported; publish a new version before extending.',
        world_gate='NOT_PROVEN', scoring_gate='CLOSED')
    META.write_bytes((json.dumps(metadata, indent=2)+'\n').encode())
    check()


def check():
    m = json.loads(META.read_bytes())
    assert m['source_plan_sha256'] == PLAN_SHA and m['identity_map_lf_sha256'] == IDENTITY_SHA
    assert m['source_calendar']['sha256'] == CALENDAR_SHA
    assert m['world_gate'] == 'NOT_PROVEN' and m['scoring_gate'] == 'CLOSED'
    assert sha(lf(KEYS)) == m['keys']['lf_sha256'] and sha(lf(SESSIONS)) == m['sessions']['lf_sha256']
    reader = csv.DictReader(io.StringIO(lf(KEYS).decode()))
    assert reader.fieldnames == FIELDS
    rows = list(reader)
    records = identity_rows()
    assert len(rows) == len(records) == m['keys']['rows'] == 8439
    assert [r['price_ticker'] for r in rows] == sorted(r['ticker'] for r in records)
    by_ticker = {r['ticker']:r for r in records}
    for row in rows:
        assert {k:row[k] for k in identity_columns(by_ticker[row['price_ticker']])} == identity_columns(by_ticker[row['price_ticker']])
        assert int(row['setup_rows']) > 0 and len(bytes.fromhex(row['raw_sha256'])) == 32
    assert sum(int(r['setup_rows']) for r in rows) == m['keys']['setup_rows'] == 12547288
    assert sum(bool(r['candidate_cik']) for r in rows) == m['keys']['candidate_ciks'] == 3996
    assert sum(r['mapping_status']=='NO_CIK' for r in rows) == m['keys']['unresolved'] == 4419
    assert sum(r['mapping_status']=='QUARANTINED_ISSUER_PRODUCT_ALIAS' for r in rows) == 24
    assert m['keys']['formal_ownership_intervals'] == 0
    sessions = list(csv.DictReader(io.StringIO(lf(SESSIONS).decode())))
    days = [r['session_date'] for r in sessions]
    assert len(days) == len(set(days)) == m['sessions']['rows'] == 9271
    assert days == sorted(days) and (days[0],days[-1]) == ('1990-01-02','2026-10-23')
    for i,row in enumerate(sessions):
        assert date.fromisoformat(row['session_date']).isoformat() == row['session_date']
        assert row['previous_session'] == (days[i-1] if i else '')
        assert row['next_session'] == (days[i+1] if i+1 < len(days) else '')
    print('PASS: 8439 keys / 12547288 setup rows / 9271 frozen sessions / 0 formal ownership intervals')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['build','check'])
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--calendar', type=Path)
    args = parser.parse_args()
    if args.mode == 'build':
        if not args.plan or not args.calendar:
            parser.error('build requires authenticated --plan and --calendar')
        build(args.plan, args.calendar)
    else:
        check()

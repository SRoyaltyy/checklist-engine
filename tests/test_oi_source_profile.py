import json
from pathlib import Path
import tempfile
import unittest
import pyarrow as pa
import pyarrow.parquet as pq
from ci.oi_source_profile import inspect_bytes,legacy_profile,validate_request


class ProfileTests(unittest.TestCase):
    def test_scope_and_boolean_are_explicit(self):
        value=dict(version=1,execute=False,scope='OI_CURRENT_SOURCES_AND_FROZEN_LEGACY_OBSERVATION')
        self.assertIs(validate_request(value)['execute'],False)
        with self.assertRaises(ValueError):validate_request(dict(value,execute='false'))
        with self.assertRaises(ValueError):validate_request(dict(value,scope='ALL_OPTIONS_HISTORY'))

    def test_html_shell_cannot_be_a_successful_chain(self):
        with self.assertRaises((ValueError,KeyError)):inspect_bytes('cboe_chain_AAPL',b'<html>Open Interest</html>')
        raw=json.dumps(dict(timestamp='uninterpreted source timestamp',data=dict(symbol='AAPL',options=[dict(option='AAPL...',open_interest=0)]))).encode()
        self.assertEqual(inspect_bytes('cboe_chain_AAPL',raw)['open_interest_null'],0)

    def test_legacy_date_label_never_becomes_a_proven_history_session(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'synthetic.parquet'
            pq.write_table(pa.Table.from_pylist([dict(ticker='TEST',product='TEST',expiry='2027-01-01',strike=10.0,
                call_oi=0,put_oi=2,snapshot_utc='20261102')]),path)
            report=legacy_profile(path)
            self.assertEqual(report['rows'],1);self.assertEqual(report['invalid_oi_rows'],0)
            self.assertEqual(report['historical_oi_session'],'UNKNOWN');self.assertFalse(report['backfill_proof'])


if __name__=='__main__':unittest.main()

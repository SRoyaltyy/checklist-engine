import unittest
import json
from pathlib import Path
from ci.sec_quarterly_fields import TABLES,filing_date_iso,value_unit_13f


class FieldTests(unittest.TestCase):
    def test_every_selected_field_matches_all_54_observed_archive_headers(self):
        root=Path(__file__).resolve().parents[1]/'docs'
        for kind in ('form345','form13f'):
            report=json.loads((root/f'SEC_QUARTERLY_{kind.upper()}_PROFILE_42392401389_V2.json').read_bytes())
            self.assertEqual(report['status'],'PASS_PUBLISHED_SOURCE_CATALOG_ONLY')
            self.assertEqual(len(report['windows']),27)
            for window in report['windows']:
                actual={t['table']:t for t in window['profile']['tables']}
                self.assertTrue(set(TABLES[kind])<=set(actual))
                for table,spec in TABLES[kind].items():
                    absent=set(spec['columns'])-set(actual[table]['columns'])
                    allowed={'AFF10B5ONE'} if kind=='form345' and window['window']['label']<'2023Q1' else set()
                    if table!='SUBMISSION':allowed=set()
                    self.assertEqual(absent,allowed,(kind,window['window']['label'],table))
                    self.assertEqual(actual[table]['ragged_rows'],0)

    def test_sec_dates_and_13f_value_unit_boundary_are_explicit(self):
        self.assertEqual(filing_date_iso('03-JAN-2023'),'2023-01-03')
        self.assertEqual(filing_date_iso('29-FEB-2024'),'2024-02-29')
        self.assertEqual(value_unit_13f('02-JAN-2023'),'USD_THOUSANDS')
        self.assertEqual(value_unit_13f('03-JAN-2023'),'USD')
        self.assertEqual(value_unit_13f(None),'UNKNOWN_FILING_DATE')
        for bad in ('31-FEB-2024','20230103','03/01/2023'):
            with self.assertRaises(ValueError):filing_date_iso(bad)

    def test_transactions_holdings_and_all_owners_are_retained_without_prose_fields(self):
        insider=TABLES['form345']
        self.assertTrue({'NONDERIV_TRANS','DERIV_TRANS','NONDERIV_HOLDING','DERIV_HOLDING','REPORTINGOWNER'}<=set(insider))
        self.assertIn('RPTOWNERCIK',insider['REPORTINGOWNER']['required'])
        self.assertIn('NONDERIV_TRANS_SK',insider['NONDERIV_TRANS']['columns'])
        self.assertIn('DERIV_TRANS_SK',insider['DERIV_TRANS']['columns'])
        excluded={'ISSUERNAME','REMARKS','RPTOWNERNAME','RPTOWNER_TITLE','RPTOWNER_TXT','NATURE_OF_OWNERSHIP',
                  'SECURITY_TITLE','UNDLYNG_SEC_TITLE','NAMEOFISSUER','TITLEOFCLASS','ADDITIONALINFORMATION'}
        for tables in TABLES.values():
            for spec in tables.values():self.assertFalse(excluded&set(spec['columns']))
        self.assertIn('CUSIP',TABLES['form13f']['INFOTABLE']['required'])
        self.assertNotIn('CIK',TABLES['form13f']['INFOTABLE']['columns'])


if __name__=='__main__':unittest.main()

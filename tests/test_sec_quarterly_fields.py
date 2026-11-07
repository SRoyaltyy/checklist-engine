import unittest
from ci.sec_quarterly_fields import TABLES,filing_date_iso,value_unit_13f


class FieldTests(unittest.TestCase):
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

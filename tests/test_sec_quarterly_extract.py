import hashlib
import io
from pathlib import Path
import tempfile
import unittest
import zipfile
import pyarrow as pa
import pyarrow.parquet as pq
from ci.sec_quarterly_extract import annotate,extract_zip


class Capture:
    def __init__(self,root):self.root=root;self.data={};self.assets=[]
    def emit(self,path,kind,**metadata):
        raw=path.read_bytes();self.data[path.name]=raw
        result=dict(name=path.name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),kind=kind,**metadata)
        self.assets.append(result);path.unlink();return result
    def rows(self,table):
        result=[]
        for asset in self.assets:
            if asset['table']==table:result.extend(pq.read_table(pa.BufferReader(self.data[asset['name']])).to_pylist())
        return result


class ExtractTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.publisher=Capture(self.root)
    def source(self,tables):
        path=self.root/'synthetic.zip'
        with zipfile.ZipFile(path,'w') as archive:
            for name,text in tables.items():archive.writestr(name+'.tsv',text)
        return path

    def test_every_owner_and_both_transaction_kinds_keep_exact_source_values(self):
        tables=dict(SUBMISSION='ACCESSION_NUMBER\tFILING_DATE\tDOCUMENT_TYPE\tISSUERCIK\tPERIOD_OF_REPORT\nA\t03-JAN-2023\t4\t0000000123\t01-JAN-2023\n',
            REPORTINGOWNER='ACCESSION_NUMBER\tRPTOWNERCIK\tRPTOWNER_RELATIONSHIP\tRPTOWNERNAME\nA\t456\tDIRECTOR\tExcluded name\nA\t789\tOFFICER\tAnother name\n',
            NONDERIV_TRANS='ACCESSION_NUMBER\tNONDERIV_TRANS_SK\tTRANS_DATE\tTRANS_ACQUIRED_DISP_CD\tTRANS_SHARES\tTRANS_PRICEPERSHARE\nA\t900719925474099300000000001\t02-JAN-2023\tA\t10.25\t9007199254740993.01\n',
            DERIV_TRANS='ACCESSION_NUMBER\tDERIV_TRANS_SK\tTRANS_DATE\tTRANS_ACQUIRED_DISP_CD\tTRANS_PRICEPERSHARE\nA\t99\t02-JAN-2023\tD\t0.1\n')
        report=extract_zip(self.source(tables),'form345','2023Q1',self.publisher,{123})
        owners=self.publisher.rows('REPORTINGOWNER');non=self.publisher.rows('NONDERIV_TRANS');deriv=self.publisher.rows('DERIV_TRANS')
        self.assertEqual([r['RPTOWNERCIK'] for r in owners],['456','789'])
        self.assertTrue(all('RPTOWNERNAME' not in r for r in owners))
        self.assertEqual(non[0]['TRANS_PRICEPERSHARE'],'9007199254740993.01')
        self.assertEqual(non[0]['NONDERIV_TRANS_SK'],'900719925474099300000000001')
        self.assertEqual(deriv[0]['TRANS_PRICEPERSHARE'],'0.1')
        self.assertEqual(non[0]['filing_date_iso'],'2023-01-03');self.assertEqual(non[0]['period_of_report_raw'],'01-JAN-2023')
        self.assertTrue(non[0]['retained_retrieval_candidate']);self.assertEqual(non[0]['issuer_cik'],123)
        self.assertEqual(report['tables']['REPORTINGOWNER']['output_rows'],2)

    def test_13f_manager_is_not_used_as_held_issuer_and_units_use_filing_date(self):
        source=self.source(dict(SUBMISSION='ACCESSION_NUMBER\tFILING_DATE\tSUBMISSIONTYPE\tCIK\tPERIODOFREPORT\nA\t03-JAN-2023\t13F-HR/A\t111\t31-DEC-2020\n',
            INFOTABLE='ACCESSION_NUMBER\tINFOTABLE_SK\tCUSIP\tVALUE\tSSHPRNAMT\tSSHPRNAMTTYPE\tNAMEOFISSUER\nA\t1\t012345678\t9007199254740993\t100\tSH\tExcluded name\n'))
        extract_zip(source,'form13f','2023Q1',self.publisher,{111})
        row=self.publisher.rows('INFOTABLE')[0]
        self.assertEqual(row['filing_manager_cik'],111);self.assertNotIn('issuer_cik',row)
        self.assertEqual(row['reported_market_value_unit'],'USD');self.assertEqual(row['VALUE'],'9007199254740993')
        self.assertEqual(row['period_of_report_raw'],'31-DEC-2020');self.assertNotIn('NAMEOFISSUER',row)

    def test_orphans_and_bad_dates_remain_unknown_without_period_date_substitution(self):
        row=annotate(dict(source_member='x',source_row=1),None,'form13f','INFOTABLE','window','source.zip',set())
        self.assertEqual(row['parent_link_status'],'SOURCE_SUBMISSION_MISSING')
        self.assertIsNone(row['filing_date_iso']);self.assertEqual(row['reported_market_value_unit'],'UNKNOWN_FILING_DATE')
        row=annotate({},dict(FILING_DATE='31-FEB-2024',PERIOD_OF_REPORT='01-JAN-2024',ISSUERCIK='bad'),
                     'form345','NONDERIV_TRANS','window','source.zip',{123})
        self.assertEqual(row['filing_date_status'],'INVALID_SOURCE_DATE');self.assertIsNone(row['filing_date_iso'])
        self.assertIsNone(row['issuer_cik']);self.assertIsNone(row['retained_retrieval_candidate'])

    def test_duplicate_parent_accessions_fail_without_first_row_selection(self):
        path=self.source(dict(SUBMISSION='ACCESSION_NUMBER\tFILING_DATE\tDOCUMENT_TYPE\tISSUERCIK\nA\t01-JAN-2020\t4\t123\nA\t02-JAN-2020\t4\t456\n'))
        with self.assertRaisesRegex(ValueError,'duplicate source submission'):extract_zip(path,'form345','2020Q1',self.publisher,{123})


if __name__=='__main__':unittest.main()

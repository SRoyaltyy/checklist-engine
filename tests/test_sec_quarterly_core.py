"""Synthetic index and strict source-cell preservation tests; no vendor reads."""
import io
import unittest
import zipfile
from ci.sec_quarterly_core import filename_label,fixed_rows,source_catalog,table_members


class QuarterlyCoreTests(unittest.TestCase):
    def test_calendar_labels_and_shifted_windows_do_not_invent_filing_bounds(self):
        quarter=filename_label('2020q1_form13f.zip','form13f')
        self.assertEqual(quarter['label'],'2020Q1');self.assertIsNone(quarter['filename_start_date'])
        shifted=filename_label('01dec2025-28feb2026_form13f.zip','form13f')
        self.assertEqual((shifted['filename_start_date'],shifted['filename_end_date']),('2025-12-01','2026-02-28'))
        with self.assertRaises(ValueError):filename_label('31feb2026-31mar2026_form13f.zip','form13f')

    def test_source_catalog_is_official_and_exhaustive_without_guessing_quarter_urls(self):
        html=''.join('<a href="'+u+'">data</a>' for u in ['/files/2019q4_form345.zip',
            '/files/2020q1_form345.zip','/files/2026q3_form345.zip','https://other.test/2020q2_form345.zip',
            '/files/2020q1_form13f.zip','/files/2020q1_form345.zip'])
        rows=source_catalog(html,'form345',end_year=2026)
        self.assertEqual([r['label'] for r in rows],['2020Q1','2026Q3'])
        # A source gap stays a gap; there is no fabricated Q2 download URL.
        self.assertEqual(len(rows),2)
        with self.assertRaises(ValueError):source_catalog('<a href="/files/2020q1_form345.zip?secret=x">x</a>','form345')
        with self.assertRaisesRegex(ValueError,'duplicate ZIP basename'):
            source_catalog('<a href="/old/2020q1_form345.zip">x</a><a href="/new/2020q1_form345.zip">x</a>','form345')

    def zip(self,body,name='SUBMISSION.tsv'):
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as archive:archive.writestr(name,body)
        return zipfile.ZipFile(io.BytesIO(stream.getvalue()))

    def test_fixed_cells_preserve_exact_numbers_and_nulls_without_prose_features(self):
        with self.zip('ACCESSION_NUMBER\tVALUE\tNAME\n0000000123-20-000001\t9007199254740993\tprose excluded\n0000000123-20-000002\t\tmore prose\n') as archive:
            member=table_members(archive)['SUBMISSION'];metadata={}
            rows=list(fixed_rows(archive,member,['ACCESSION_NUMBER','VALUE','FIGI'],['ACCESSION_NUMBER'],metadata))
            self.assertEqual(rows[0]['VALUE'],'9007199254740993');self.assertIsNone(rows[1]['VALUE'])
            self.assertNotIn('NAME',rows[0]);self.assertEqual(metadata['optional_columns_absent'],['FIGI'])
            self.assertEqual([r['source_row'] for r in rows],[1,2]);self.assertEqual(metadata['rows'],2)

    def test_ragged_rows_missing_required_fields_and_duplicate_tables_fail(self):
        with self.zip('A\tB\n1\t2\n3\n') as archive:
            with self.assertRaisesRegex(ValueError,'ragged TSV row 2'):
                list(fixed_rows(archive,table_members(archive)['SUBMISSION'],['A'],['A'],{}))
        with self.zip('A\tB\n1\t2\n') as archive:
            with self.assertRaisesRegex(ValueError,'columns absent'):
                list(fixed_rows(archive,table_members(archive)['SUBMISSION'],['A','CIK'],['CIK'],{}))
        with self.zip('A\tB\n1\t2','../SUBMISSION.tsv') as archive:
            with self.assertRaisesRegex(ValueError,'unsafe'):table_members(archive)


if __name__=='__main__':unittest.main()

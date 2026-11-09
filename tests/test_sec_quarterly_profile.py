"""Synthetic profile evidence, including malformed-row reporting and CRC failure."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from ci.sec_quarterly_profile import bulk_prerequisite,profile_zip,validate_request


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)

    def test_profile_records_all_rows_and_malformed_line_fingerprints(self):
        body=b'ACCESSION_NUMBER\tVALUE\n0000000123-20-000001\t9007199254740993\nragged\n'
        path=self.root/'synthetic.zip'
        with zipfile.ZipFile(path,'w') as archive:
            archive.writestr('INFOTABLE.tsv',body);archive.writestr('README.txt','Prose is not a feature')
        result=profile_zip(path);table=result['tables'][0]
        self.assertEqual(table['rows'],2);self.assertEqual(table['ragged_rows'],1)
        self.assertEqual(table['sha256'],hashlib.sha256(body).hexdigest())
        self.assertEqual(table['ragged_row_examples'][0]['sha256'],hashlib.sha256(b'ragged\n').hexdigest())
        self.assertEqual(result['non_tabular_members'],['README.txt']);self.assertFalse(result['free_text_features'])

    def test_changed_zip_member_crc_cannot_pass_profile(self):
        path=self.root/'source.zip';body=b'A\tB\n1\t2\n'
        with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_STORED) as archive:archive.writestr('SUBMISSION.tsv',body)
        raw=path.read_bytes();self.assertIn(body,raw);path.write_bytes(raw.replace(body,b'A\tB\n9\t2\n',1))
        with self.assertRaises(zipfile.BadZipFile):profile_zip(path)

    def test_request_boolean_and_year_scope_are_bound(self):
        value=dict(version=1,scope='SEC_QUARTERLY_OFFICIAL_SOURCE_PROFILE_2020_LATEST',start_year=2020,execute=False,bulk_readback=None)
        self.assertEqual(validate_request(value),value)
        for changed in [dict(value,execute='false'),dict(value,start_year=2024)]:
            with self.assertRaises(ValueError):validate_request(changed)
        with self.assertRaisesRegex(ValueError,'frozen successful bulk readback'):validate_request(dict(value,execute=True))

    def test_public_bulk_prerequisite_requires_exact_receipt_and_successful_actual_runner(self):
        report=dict(format='SEC_BULK_PUBLIC_READBACK_V1',status='PASS',reader_commit='a'*40,
            coverage=dict(retained_names=8439),actual_run_id='123',actual_attempt='1',source=dict(run='111',attempt='1'),
            verification_scope='ALL_PUBLISHED_RETAINED_RAW_MEMBERS_AND_ALL_PARQUET_ROW_VALUES',
            unfiltered_zip_readback_kinds=['companyfacts'])
        path=self.root/'readback.json';raw=json.dumps(report).encode();path.write_bytes(raw)
        proof=dict(release='sec-bulk-readback-v1-123-1',commit='a'*40,receipt_sha256=hashlib.sha256(raw).hexdigest())
        run=dict(status='completed',conclusion='failure',head_sha='a'*40,path='.github/workflows/sec_bulk_readback.yml')
        with patch.dict('os.environ',GITHUB_REPOSITORY='SRoyaltyy/checklist-engine'),\
                patch('ci.sec_quarterly_profile.releases.release_info',return_value=dict(draft=False,target_commitish='a'*40)),\
                patch('ci.sec_quarterly_profile.releases.download_asset',return_value=path),\
                patch('ci.sec_quarterly_profile.releases._read',side_effect=lambda *args:json.dumps(run)):
            with self.assertRaisesRegex(ValueError,'runner result'):bulk_prerequisite(proof,self.root)
            run['conclusion']='success';result=bulk_prerequisite(proof,self.root)
            self.assertEqual(result['verification_status'],'PASS');path.write_bytes(raw+b' ')
            with self.assertRaisesRegex(ValueError,'receipt differs'):bulk_prerequisite(proof,self.root)


if __name__=='__main__':unittest.main()

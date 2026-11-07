"""Synthetic immutable reuse checks; never retrieve market inputs locally."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from ci.sec_bulk_recovery import checked_receipt,companyfacts,submissions


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.spec=dict(release='old-synthetic-source',commit='a'*40,receipt_sha256='b'*64)

    def test_checked_receipt_rejects_wrong_fingerprint_and_release_commit(self):
        path=self.root/'receipt.json';path.write_text(json.dumps(dict(release=self.spec['release'],source_commit=self.spec['commit'])))
        with patch('ci.sec_bulk_recovery.releases.release_info',return_value=dict(draft=False,target_commitish='a'*40)),\
                patch('ci.sec_bulk_recovery.releases.download_asset',return_value=path):
            with self.assertRaisesRegex(ValueError,'fingerprint'):checked_receipt(self.spec,'receipt.json',self.root)
            self.spec['receipt_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(checked_receipt(self.spec,'receipt.json',self.root)['source_commit'],'a'*40)
            self.spec['commit']='c'*40
            with self.assertRaisesRegex(ValueError,'commit differs'):checked_receipt(self.spec,'receipt.json',self.root)

    def test_only_a_complete_matching_submissions_stage_can_be_reused(self):
        old=dict(retained_names=8439,scoring_gate='CLOSED',
            identity_map_lf_sha256='50323efcd9855061501d88010d8e812371fda7c9dd48d3a54c0f5f19cdad97ce',
            join_keys_lf_sha256='5e6d83f56bdb2a765ad5a9bf76219f82fdbe76ff2b93acd3f9ca12fa2e3233e2',
            filing_record_model='SOURCE_OBSERVATIONS_NOT_CANONICAL_ACCESSIONS',
            stages=dict(submissions=dict(status='PASS_RETAINED_SOURCE_EXTRACTION',
                filing_record_model='SOURCE_OBSERVATIONS_WITH_CONFLICT_FIELDS',populated_ciks=[123],
                missing_archive_ciks=[456],ciks_without_output_rows=[],rows=1,entity_rows=1,source_members=1)),coverage=dict(retrieval_ciks=2),
            inputs=dict(submissions=dict(url='https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip',
                                         started_at='original acquisition',sha256='c'*64)),assets=[])
        paths={}
        for name,kind,meta in [('sec_submissions_raw-00000.json','raw_member_ledger',{}),
                ('sec_submissions_raw-00000.tar.gz','retained_raw_archive',dict(members=1)),
                ('sec_submissions_filings_retained-00000.parquet','parquet',dict(rows=1)),
                ('sec_submissions_entities_retained-00000.parquet','parquet',dict(rows=1))]:
            path=self.root/name;path.write_bytes(b'synthetic immutable bytes');paths[name]=path
            old['assets'].append(dict(name=name,kind=kind,bytes=path.stat().st_size,
                                     sha256=hashlib.sha256(path.read_bytes()).hexdigest(),**meta))
        class Publisher:
            def emit(self,path,kind,**metadata):
                return dict(name=path.name,kind=kind,bytes=path.stat().st_size,
                            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),**metadata)
        with patch('ci.sec_bulk_recovery.checked_receipt',return_value=old),\
                patch('ci.sec_bulk_recovery.releases.download_asset',side_effect=lambda release,name,root:paths[name]):
            source,stage=submissions(self.spec,self.root,{123,456},Publisher())
            self.assertEqual(source['started_at'],'original acquisition')
            self.assertEqual(source['reused_from']['scope'],'COMPLETE_SUBMISSIONS_STAGE_FROM_EXPLICIT_PARTIAL_RUN')
            with self.assertRaisesRegex(ValueError,'matching retrieval stage'):
                submissions(self.spec,self.root,{123,789},Publisher())
            old['stages']['submissions']['status']='INCOMPLETE'
            with self.assertRaisesRegex(ValueError,'matching retrieval stage'):
                submissions(self.spec,self.root,{123,456},Publisher())

    def test_cached_zip_preserves_original_source_bytes_and_acquisition_time(self):
        path=self.root/'companyfacts.zip';path.write_bytes(b'synthetic ZIP payload')
        source=dict(url='https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip',
            bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),started_at='original time')
        old=dict(status='PASS_EXACT_SOURCE_DIAGNOSTIC_NOT_DATA_EXTRACTION',source=source,
            assets=[dict(name='companyfacts.zip',kind='official_unfiltered_source_zip',
                         bytes=source['bytes'],sha256=source['sha256'])])
        with patch('ci.sec_bulk_recovery.checked_receipt',return_value=old),\
                patch('ci.sec_bulk_recovery.releases.download_asset',return_value=path):
            result,receipt=companyfacts(self.spec,self.root)
            self.assertEqual(result,path);self.assertEqual(receipt['started_at'],'original time')
            self.assertEqual(receipt['reused_from']['scope'],'EXACT_OFFICIAL_UNFILTERED_SOURCE_ZIP')
            path.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'bytes differ'):companyfacts(self.spec,self.root)


if __name__=='__main__':unittest.main()

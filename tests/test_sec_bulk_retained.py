"""Synthetic SEC mapping, source/archive and actual parquet round-trip tests."""
from collections import defaultdict
from decimal import Decimal
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from ci.sec_bulk_retained_core import (cik_number,companyfact_rows,decode_source,live_candidates,
    members_by_cik,annotate_filing_observations,resolve_identities,submission_rows)
from ci.sec_bulk_retained import (ParquetSink,Publisher,downloaded,encoded,load_cohort,process_archive,
                                 reused_identity,run,schemas,validate_request,wait_seconds)
from scripts.nai.common import SourceError


def record(ticker,cik=None,status=None):
    return dict(ticker=ticker,status=status or ('UNIQUE_CIK' if cik else 'NO_CIK'),
        candidates=[dict(cik=cik,quarantined=False)] if cik else [],
        shares_first_filed='2020-02-03' if cik else None,shares_last_filed='2024-11-01' if cik else None)


class CapturePublisher:
    def __init__(self,root):
        self.root=Path(root);self.assets=[];self.bodies={}
    def emit(self,path,kind,**metadata):
        raw=path.read_bytes();self.bodies[path.name]=raw
        binding=dict(name=path.name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),kind=kind,**metadata)
        self.assets.append(binding);path.unlink();return binding
    def json(self,name,value,kind):
        path=self.root/name;path.write_bytes(encoded(value));return self.emit(path,kind)


class IdentityTests(unittest.TestCase):
    def test_bound_complete_cohort_reads_only_committed_metadata(self):
        records=load_cohort()
        self.assertEqual(len(records),8439)
        self.assertEqual(len({r['ticker'] for r in records}),8439)

    def test_exact_symbols_do_not_silently_merge_dot_dash(self):
        current=live_candidates({'0':dict(ticker='BRK-B',cik_str=123)},
            dict(fields=['cik','ticker','exchange'],data=[[123,'BRK-B','NYSE']]))
        rows=resolve_identities([record('BRK.B'),record('BRK-B')],current)
        by={r['ticker']:r for r in rows}
        self.assertIsNone(by['BRK.B']['cik']);self.assertEqual(by['BRK-B']['cik'],123)
        self.assertTrue(all(r['historical_join_allowed'] is False and r['valid_from'] is None for r in rows))

    def test_current_and_archived_conflict_preserves_both_not_false_unique(self):
        row=resolve_identities([record('TEST',123)],{'TEST':{456}})[0]
        self.assertEqual(row['status'],'ARCHIVED_CURRENT_CONFLICT')
        self.assertEqual(row['candidate_ciks'],[123,456]);self.assertIsNone(row['cik'])

    def test_product_and_integrity_quarantines_are_not_resurrected(self):
        rows=resolve_identities([record('ETN',123,'QUARANTINED_ISSUER_PRODUCT_ALIAS'),record('BAD',1790169)],
                               {'ETN':{123},'BAD':{1790169}})
        self.assertTrue(all(not r['candidate_ciks'] and r['cik'] is None for r in rows))
        self.assertEqual(rows[0]['withheld_ciks'],[1790169])

    def test_live_ambiguity_and_missing_names_remain_explicit(self):
        rows=resolve_identities([record('AMB'),record('NONE')],{'AMB':{123,456}})
        self.assertEqual([r['status'] for r in rows],['AMBIGUOUS_CURRENT','NO_CIK'])
        self.assertEqual(rows[0]['candidate_ciks'],[123,456])

    def test_bad_map_shape_and_cik_are_rejected(self):
        for value in [True,0,-1,'12x',1.5]:
            with self.subTest(value=value),self.assertRaises(ValueError):cik_number(value)
        with self.assertRaises(ValueError):live_candidates({'0':dict(ticker='T',cik_str=1)},
            dict(fields=['cik','ticker','exchange'],data=[[1,'T']]))

    def test_request_scope_and_local_runner_guard(self):
        from ci.sec_bulk_retained import REQUEST
        request=validate_request(json.loads(REQUEST.read_bytes()))
        with self.assertRaises(ValueError):validate_request(dict(request,retained_names=8438))
        with patch.dict(os.environ,{},clear=True),patch('ci.sec_bulk_retained.common.get') as network:
            with self.assertRaisesRegex(ValueError,'only on the authorized'):run(Path('unused'))
        network.assert_not_called()


class TransformTests(unittest.TestCase):
    def test_history_members_group_with_root_and_foreign_ciks_excluded(self):
        names=['CIK0000000123-submissions-001.json','CIK0000000123.json','CIK0000000999.json']
        self.assertEqual(members_by_cik(names,{123},'submissions'),
            {123:['CIK0000000123.json','CIK0000000123-submissions-001.json']})
        with self.assertRaises(ValueError):members_by_cik(['../CIK0000000123.json'],{123},'submissions')
        with self.assertRaises(ValueError):members_by_cik(['CIK0000000123.json']*2,{123},'companyfacts')

    def test_missing_columns_preserve_unknown_and_reject_ragged_arrays(self):
        payload=dict(accessionNumber=['0000000123-20-000001'])
        row=list(submission_rows(payload,123))[0]
        self.assertIsNone(row['filing_date']);self.assertIsNone(row['acceptance_datetime'])
        with self.assertRaises(ValueError):list(submission_rows(dict(payload,form=[]),123))

    def test_duplicate_accession_observations_preserve_unknowns_and_disputed_clocks(self):
        row=list(submission_rows(dict(accessionNumber=['0000000123-20-000001'],filingDate=['2020-02-03']),123))[0]
        observations=[dict(row,source_member='root',source_row=1),
            dict(row,acceptance_datetime='2020-02-03T20:30:00Z',source_member='history1',source_row=1),
            dict(row,acceptance_datetime='2020-02-03T20:31:00Z',source_member='history2',source_row=1)]
        rows,counts,examples=annotate_filing_observations({row['accession_number']:observations})
        self.assertEqual(len(rows),3);self.assertEqual(counts['distinct_accessions'],1)
        self.assertEqual(counts['accessions_with_conflicting_metadata'],1)
        self.assertEqual({r['acceptance_datetime'] for r in rows},{None,'2020-02-03T20:30:00Z','2020-02-03T20:31:00Z'})
        self.assertTrue(all(r['conflict_fields']==['acceptance_datetime'] for r in rows))
        self.assertEqual(examples[0]['reported_values']['acceptance_datetime'],['2020-02-03T20:30:00Z','2020-02-03T20:31:00Z'])

    def test_exact_decimal_and_large_integer_are_preserved(self):
        raw=b'{"cik":123,"facts":{"us-gaap":{"Assets":{"units":{"USD":[{"val":9007199254740993,"filed":"2020-02-03"},{"val":0.1,"filed":null}]}}}}}'
        counters=defaultdict(int);rows=list(companyfact_rows(decode_source(raw),123,counters))
        self.assertEqual([r['val_text'] for r in rows],['9007199254740993','0.1'])
        self.assertTrue(all(not r['float64_exact'] for r in rows))
        self.assertEqual(counters['numeric_facts_without_filed_date'],1)
        self.assertIsNone(rows[1]['filed'])

    def test_cik_mismatch_invalid_dates_and_non_numeric_are_explicit(self):
        with self.assertRaises(ValueError):list(submission_rows(dict(cik=456,filings=dict(recent={})),123))
        counters=defaultdict(int)
        payload=dict(cik=123,facts={'us-gaap':{'X':{'units':{'pure':[dict(val='free text'),dict(val=1,filed='bad')]}}}})
        with self.assertRaises(ValueError):list(companyfact_rows(payload,123,counters))
        self.assertEqual(counters['non_numeric_fact_values'],1)


class ParquetIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.publisher=CapturePublisher(self.root)

    def source_zip(self,names):
        path=self.root/'fixture.zip'
        with zipfile.ZipFile(path,'w') as archive:
            for name,payload in names.items():archive.writestr(name,encoded(payload))
        return path

    def parquet_rows(self,prefix):
        import pyarrow as pa
        import pyarrow.parquet as pq
        result=[]
        for name,raw in self.publisher.bodies.items():
            if name.startswith(prefix) and name.endswith('.parquet'):
                result.extend(pq.read_table(pa.BufferReader(raw)).to_pylist())
        return result

    def test_submissions_history_null_schema_observations_and_raw_byte_lineage(self):
        root=dict(cik=123,tickers=['TEST'],exchanges=['NYSE'],sic='1234',
            filings=dict(recent=dict(accessionNumber=['0000000123-20-000001'],filingDate=['2020-02-03'],
                acceptanceDateTime=['2020-02-03T20:30:00Z'],form=['10-K'],isXBRL=[1])))
        history=dict(accessionNumber=['0000000123-20-000001','0000000123-19-000001'],
                     filingDate=['2020-02-03','2019-02-01'],form=['10-K','10-K'],
                     acceptanceDateTime=['2020-02-03T20:31:00Z',None])
        sources={'CIK0000000123.json':root,'CIK0000000123-submissions-001.json':history,
                 'CIK0000000999.json':dict(cik=999,filings=dict(recent={}))}
        report=process_archive('submissions',self.source_zip(sources),{123,456},self.publisher)
        rows=self.parquet_rows('sec_submissions_filings')
        self.assertEqual(report['rows'],3);self.assertEqual(report['duplicate_accession_observations'],1)
        self.assertEqual(report['distinct_accessions'],2)
        self.assertEqual(report['missing_archive_ciks'],[456])
        self.assertEqual({r['cik'] for r in rows},{123})
        self.assertEqual(sum(r['acceptance_datetime'] is None for r in rows),1)
        self.assertEqual(report['accessions_with_conflicting_metadata'],1)
        disputed=[r for r in rows if r['accession_number']=='0000000123-20-000001']
        self.assertEqual({r['acceptance_datetime'] for r in disputed},{'2020-02-03T20:30:00Z','2020-02-03T20:31:00Z'})
        self.assertTrue(all(r['conflict_fields']==['acceptance_datetime'] for r in disputed))
        ledger=json.loads(self.publisher.bodies['sec_submissions_raw-00000.json'])
        with tarfile.open(fileobj=io.BytesIO(self.publisher.bodies[ledger['archive']['name']]),mode='r:gz') as archive:
            for member in ledger['members']:
                raw=archive.extractfile(member['member']).read()
                self.assertEqual(raw,encoded(sources[member['zip_member']]))
                self.assertEqual(hashlib.sha256(raw).hexdigest(),member['sha256'])

    def test_companyfacts_parquet_roundtrip_preserves_exact_values_and_dates(self):
        payload=dict(cik=123,facts={'us-gaap':{'Assets':{'units':{'USD':[dict(val=9007199254740993,
            filed='2020-02-03',end='2019-12-31',accn='0000000123-20-000001',fy=2019)]}}}})
        report=process_archive('companyfacts',self.source_zip({'CIK0000000123.json':payload}),{123},self.publisher)
        rows=self.parquet_rows('sec_companyfacts')
        self.assertEqual(report['rows'],1)
        self.assertEqual(rows[0]['val_text'],'9007199254740993');self.assertFalse(rows[0]['float64_exact'])
        self.assertEqual((rows[0]['filed'],rows[0]['end']),('2020-02-03','2019-12-31'))
        self.assertNotIn('label',rows[0]);self.assertNotIn('description',rows[0])

    def test_empty_members_and_filename_only_facts_are_preserved_explicitly(self):
        source={'CIK0000000123.json':{},
            'CIK0000000456.json':dict(entityName='excluded prose',facts={'cef':{'Shares':{'units':{'shares':[
                dict(val=10,filed='2026-07-01')]}}}}),
            'CIK0000000789.json':dict(cik=789,facts={'us-gaap':{'Assets':{'units':{'USD':[
                dict(val=20,filed='2026-07-02')]}}}})}
        report=process_archive('companyfacts',self.source_zip(source),{123,456,789,999},self.publisher)
        rows=self.parquet_rows('sec_companyfacts');self.assertEqual(len(rows),2)
        self.assertEqual(report['empty_companyfacts_ciks'],[123])
        self.assertEqual(report['companyfacts_ciks_without_body_cik'],[123,456])
        self.assertEqual(report['fact_rows_without_body_cik'],1)
        self.assertEqual(report['ciks_without_output_rows'],[123]);self.assertEqual(report['missing_archive_ciks'],[999])
        self.assertEqual(rows[0]['cik'],456);self.assertIsNone(rows[0]['body_cik'])
        self.assertEqual(rows[0]['cik_evidence'],'FILENAME_ONLY_BODY_CIK_ABSENT')
        self.assertEqual(rows[1]['body_cik'],789);self.assertEqual(rows[1]['cik_evidence'],'BODY_AND_FILENAME_AGREE')
        self.assertEqual(rows[0]['val_text'],'10');self.assertNotIn('entityName',rows[0])
        counters=defaultdict(int)
        with self.assertRaisesRegex(ValueError,'filename/body CIK differs'):
            list(companyfact_rows(dict(cik=999,facts={}),456,counters))

    def test_actual_parquet_cik_membership_and_chunk_counts(self):
        sink=ParquetSink(self.publisher,'chunk',schemas()['filings'],{123},limit=1)
        row=list(submission_rows(dict(accessionNumber=['0000000123-20-000001']),123))[0]
        sink.write([row]);sink.write([row]);sink.close()
        self.assertEqual(len([a for a in self.publisher.assets if a['kind']=='parquet']),2)
        self.assertEqual(sum(a['rows'] for a in self.publisher.assets),2)
        with self.assertRaises(ValueError):sink.write([dict(row,cik=456)])

    def test_bad_source_failure_closes_partial_output_handles(self):
        path=self.source_zip({'CIK0000000123.json':dict(cik=456,filings=dict(recent={}))})
        with self.assertRaisesRegex(ValueError,'CIK differs'):process_archive('submissions',path,{123},self.publisher)
        self.assertFalse(list(self.root.glob('*.tar.gz')))

    def test_publication_uses_immutable_helper_not_clobber(self):
        with patch.dict(os.environ,{'GITHUB_SHA':'a'*40}),patch('ci.sec_bulk_retained.releases.gh_retry') as gh,\
                patch('ci.sec_bulk_retained.releases.publish_assets') as upload:
            publisher=Publisher(self.root,'unique-run-tag')
            path=self.root/'data.json';path.write_bytes(b'{}')
            publisher.emit(path,'test')
        self.assertIn('--draft',gh.call_args.args)
        upload.assert_called_once_with('unique-run-tag',path)
        self.assertFalse(path.exists())

    def test_rate_limit_waits_then_retries_same_source_once(self):
        attempts=[]
        def fetch(url,destination,**kwargs):
            attempts.append((url,destination))
            if len(attempts)==1:raise SourceError(dict(http_status=429,retry_after_seconds=900))
            Path(destination).write_bytes(b'synthetic download')
        with patch('ci.sec_bulk_retained.common.get',side_effect=fetch),patch('ci.sec_bulk_retained.wait_seconds') as wait:
            path,receipt=downloaded('submissions',self.root,1000)
        self.assertEqual(attempts[0],attempts[1]);wait.assert_called_once_with(900)
        self.assertEqual(len(receipt['rate_limit_history']),1)
        self.assertEqual(path.read_bytes(),b'synthetic download')

    def test_repeated_rate_limit_is_bounded_and_403_is_not_retried(self):
        for code,expected_calls in [(429,2),(403,1)]:
            with self.subTest(code=code),patch('ci.sec_bulk_retained.common.get',
                    side_effect=SourceError(dict(http_status=code))) as network,\
                    patch('ci.sec_bulk_retained.wait_seconds') as wait:
                with self.assertRaises(SourceError):downloaded('submissions',self.root,1000)
            self.assertEqual(network.call_count,expected_calls)
            self.assertEqual(wait.call_count,1 if code==429 else 0)

    def test_cooldown_is_chunked_and_reuse_makes_no_vendor_request(self):
        with patch('ci.sec_bulk_retained.time.sleep') as sleep,patch('sys.stdout',new_callable=io.StringIO):
            wait_seconds(601)
        self.assertEqual([c.args[0] for c in sleep.call_args_list],[60]*10+[1])
        from ci.sec_bulk_retained import IDENTITY_INPUT_COMMIT,URLS
        raw=b'{"0":{"ticker":"TEST","cik_str":123}}';raw_sha=hashlib.sha256(raw).hexdigest()
        source=self.root/'source.json';source.write_bytes(raw)
        receipt=self.root/'source-receipt.json'
        receipt.write_bytes(encoded(dict(kind='tickers',source_commit=IDENTITY_INPUT_COMMIT,
            source=dict(url=URLS['tickers'],sha256=raw_sha,bytes=len(raw),started_at='2026-11-06T17:43:00Z',finished_at='2026-11-06T17:43:01Z'))))
        pins=dict(tickers=(raw_sha,hashlib.sha256(receipt.read_bytes()).hexdigest()))
        with patch('ci.sec_bulk_retained.IDENTITY_INPUT_PINS',pins),\
                patch('ci.sec_bulk_retained.releases.download_asset',side_effect=[source,receipt]),\
                patch('ci.sec_bulk_retained.common.get') as vendor:
            destination,binding=reused_identity('tickers',self.root)
        vendor.assert_not_called();self.assertEqual(destination.read_bytes(),raw)
        self.assertEqual(binding['reused_from']['source_commit'],IDENTITY_INPUT_COMMIT)

    def test_second_archive_failure_publishes_honest_partial_receipt(self):
        source=self.source_zip({'CIK0000000123.json':dict(cik=123,
            filings=dict(recent=dict(accessionNumber=['0000000123-20-000001'],filingDate=['2020-02-03'])))})
        def fetch(kind,root,max_bytes):
            if kind=='companyfacts':raise RuntimeError('synthetic second archive failure')
            if kind=='submissions':return source,dict(url='https://www.sec.gov/example.zip',bytes=source.stat().st_size,sha256='a'*64)
            value={'0':dict(ticker='TEST',cik_str=123)} if kind=='tickers' else dict(fields=['cik','ticker','exchange'],data=[[123,'TEST','NYSE']])
            path=self.root/(kind+'.json');path.write_bytes(encoded(value))
            return path,dict(url='https://www.sec.gov/'+kind,bytes=path.stat().st_size,sha256='b'*64)
        with patch.dict(os.environ,dict(GITHUB_ACTIONS='true',GITHUB_REPOSITORY='SRoyaltyy/checklist-engine',
                GITHUB_RUN_ID='123',GITHUB_RUN_ATTEMPT='1',GITHUB_SHA='a'*40,GITHUB_EVENT_NAME='push')),\
                patch('ci.sec_bulk_retained.validate_request',return_value=dict(execute=True)),\
                patch('ci.sec_bulk_retained.relay_configuration',return_value=dict(matches_inspected_production_worker=True)),\
                patch('ci.sec_bulk_retained.load_cohort',return_value=[record('TEST',123)]),\
                patch('ci.sec_bulk_retained.Publisher',return_value=self.publisher),\
                patch('ci.sec_bulk_retained.downloaded',side_effect=fetch),\
                patch('ci.sec_bulk_retained.shutil.disk_usage',return_value=type('Disk',(),dict(free=20*1024**3))()),\
                patch('ci.sec_bulk_retained.releases.publish_assets') as upload,\
                patch('ci.sec_bulk_retained.releases.gh_retry'):
            with self.assertRaisesRegex(RuntimeError,'second archive failure'):run(self.root)
        receipt=json.loads((self.root/'SEC_BULK_COVERAGE_V2.json').read_bytes())
        self.assertEqual(receipt['status'],'FAIL_PARTIAL_SOURCE_SNAPSHOT')
        self.assertEqual(receipt['failed_stage'],'companyfacts_download')
        self.assertEqual(receipt['stages']['submissions']['rows'],1)
        self.assertNotIn('companyfacts',receipt['stages'])
        self.assertTrue(receipt['assets']);upload.assert_called_once()

    def test_recovery_run_makes_no_vendor_request_and_keeps_source_acquisition_times(self):
        facts=self.source_zip({'CIK0000000123.json':dict(cik=123,facts={'us-gaap':{'X':{'units':{'pure':[
            dict(val=1,filed='2020-02-03')]}}}})})
        def identity(kind,root):
            value={'0':dict(ticker='TEST',cik_str=123)} if kind=='tickers' else dict(fields=['cik','ticker','exchange'],data=[[123,'TEST','NYSE']])
            path=self.root/(kind+'.json');path.write_bytes(encoded(value))
            return path,dict(url='synthetic identity',sha256='b'*64,bytes=path.stat().st_size)
        source=dict(url='synthetic cached source',sha256='c'*64,bytes=facts.stat().st_size,started_at='original source time')
        stage=dict(status='PASS_RETAINED_SOURCE_EXTRACTION',rows=1,populated_ciks=[123])
        with patch.dict(os.environ,dict(GITHUB_ACTIONS='true',GITHUB_REPOSITORY='SRoyaltyy/checklist-engine',
                GITHUB_RUN_ID='123',GITHUB_RUN_ATTEMPT='1',GITHUB_SHA='a'*40,GITHUB_EVENT_NAME='push')),\
                patch('ci.sec_bulk_retained.validate_request',return_value=dict(execute=True,reuse_identity_inputs=True,
                    recovery_sources=dict(submissions={},companyfacts={}))),\
                patch('ci.sec_bulk_retained.relay_configuration',return_value=dict(matches_inspected_production_worker=True)),\
                patch('ci.sec_bulk_retained.load_cohort',return_value=[record('TEST',123)]),\
                patch('ci.sec_bulk_retained.Publisher',return_value=self.publisher),\
                patch('ci.sec_bulk_retained.reused_identity',side_effect=identity),\
                patch('ci.sec_bulk_retained.downloaded') as vendor,\
                patch('ci.sec_bulk_recovery.submissions',return_value=(source,stage)) as cached_stage,\
                patch('ci.sec_bulk_recovery.companyfacts',return_value=(facts,source)) as cached_zip,\
                patch('ci.sec_bulk_retained.shutil.disk_usage',return_value=type('Disk',(),dict(free=20*1024**3))()),\
                patch('ci.sec_bulk_retained.releases.publish_assets'),patch('ci.sec_bulk_retained.releases.gh_retry'):
            report=run(self.root)
        vendor.assert_not_called();cached_stage.assert_called_once();cached_zip.assert_called_once()
        self.assertEqual(report['status'],'PASS_BOTH_BULK_SOURCES_RETAINED_EXTRACTION')
        self.assertEqual(report['inputs']['companyfacts']['started_at'],'original source time')
        self.assertEqual(report['coverage']['submissions_unique_ticker_matches'],1)

    def test_complete_run_counts_unique_and_conflicting_candidate_coverage_separately(self):
        source=self.source_zip({'CIK0000000123.json':dict(cik=123,
            filings=dict(recent=dict(accessionNumber=['0000000123-20-000001'],filingDate=['2020-02-03'])))})
        facts=self.root/'facts.zip'
        with zipfile.ZipFile(facts,'w') as archive:
            archive.writestr('CIK0000000123.json',encoded(dict(cik=123,facts={'us-gaap':{'X':{'units':{'pure':[dict(val=1,filed='2020-02-03')]}}}})))
        def fetch(kind,root,max_bytes):
            if kind in ('submissions','companyfacts'):
                path=source if kind=='submissions' else facts
            else:
                value={'0':dict(ticker='NEW',cik_str=123),'1':dict(ticker='CONFLICT',cik_str=456)} if kind=='tickers' else dict(fields=['cik','ticker','exchange'],data=[[123,'NEW','NYSE'],[456,'CONFLICT','NYSE']])
                path=self.root/(kind+'.json');path.write_bytes(encoded(value))
            return path,dict(url='https://www.sec.gov/'+kind,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        with patch.dict(os.environ,dict(GITHUB_ACTIONS='true',GITHUB_REPOSITORY='SRoyaltyy/checklist-engine',
                GITHUB_RUN_ID='123',GITHUB_RUN_ATTEMPT='1',GITHUB_SHA='a'*40,GITHUB_EVENT_NAME='push')),\
                patch('ci.sec_bulk_retained.validate_request',return_value=dict(execute=True)),\
                patch('ci.sec_bulk_retained.relay_configuration',return_value=dict(matches_inspected_production_worker=True)),\
                patch('ci.sec_bulk_retained.load_cohort',return_value=[record('NEW'),record('CONFLICT',123),record('NONE')]),\
                patch('ci.sec_bulk_retained.Publisher',return_value=self.publisher),\
                patch('ci.sec_bulk_retained.downloaded',side_effect=fetch),\
                patch('ci.sec_bulk_retained.shutil.disk_usage',return_value=type('Disk',(),dict(free=20*1024**3))()),\
                patch('ci.sec_bulk_retained.releases.publish_assets'),patch('ci.sec_bulk_retained.releases.gh_retry'):
            report=run(self.root)
        self.assertEqual(report['status'],'PASS_BOTH_BULK_SOURCES_RETAINED_EXTRACTION')
        self.assertEqual(report['coverage']['with_unique_cik'],1)
        self.assertEqual(report['coverage']['with_retrieval_candidates'],2)
        self.assertEqual(report['coverage']['companyfacts_unique_ticker_matches'],1)
        self.assertEqual(report['coverage']['companyfacts_candidate_ticker_matches'],2)
        self.assertEqual(report['coverage']['historical_ownership_intervals'],0)
        self.assertEqual(report['stages']['companyfacts']['missing_archive_ciks'],[456])


if __name__=='__main__':unittest.main()

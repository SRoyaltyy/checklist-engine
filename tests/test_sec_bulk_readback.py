"""Synthetic end-to-end public bundle checks and deliberate evidence corruption."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq
from ci.sec_bulk_readback import Bundle,audit_bundle,json_bytes,schema,validate_request
from ci.sec_bulk_readback_core import FIELDS,RawAudit,RowDigests,identities


class ReadbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)

    def test_request_requires_exact_terminal_source_fingerprints(self):
        self.assertFalse(validate_request(dict(version=1,execute=False,source=None))['execute'])
        with self.assertRaises(ValueError):validate_request(dict(version=1,execute=True,source=None))
        value=dict(version=1,execute=True,source=dict(run='123',attempt='1',commit='a'*40,receipt_sha256='b'*64))
        self.assertEqual(validate_request(value),value)
        for bad in [dict(value,extra=True),dict(value,source=dict(value['source'],receipt_sha256='bad'))]:
            with self.assertRaises(ValueError):validate_request(bad)

    def test_identity_conflicts_quarantines_exact_symbols_and_unknown_ownership(self):
        def old(ticker,cik=None,status=None):
            return dict(ticker=ticker,status=status or ('UNIQUE_CIK' if cik else 'NO_CIK'),
                        candidates=[dict(cik=cik)] if cik else [])
        archived=[old('BRK.B'),old('CONFLICT',123),old('ETN',123,'QUARANTINED_ISSUER_PRODUCT_ALIAS'),
                  old('BAD'),old('OLD',789),old('NEW'),old('AMB')]
        live={'0':dict(ticker='BRK-B',cik_str=123),'1':dict(ticker='CONFLICT',cik_str=456),
              '2':dict(ticker='ETN',cik_str=123),'3':dict(ticker='BAD',cik_str=1790169),
              '4':dict(ticker='NEW',cik_str=555),'5':dict(ticker='AMB',cik_str=111)}
        exchange=dict(fields=['ticker','cik','exchange'],data=[['AMB',222,'NYSE']])
        rows={r['ticker']:r for r in identities(archived,live,exchange)}
        self.assertEqual(rows['BRK.B']['status'],'NO_CIK')
        self.assertEqual(rows['CONFLICT']['candidate_ciks'],[123,456]);self.assertIsNone(rows['CONFLICT']['cik'])
        self.assertEqual(rows['ETN']['candidate_ciks'],[]);self.assertEqual(rows['BAD']['withheld_ciks'],[1790169])
        self.assertEqual(rows['AMB']['status'],'AMBIGUOUS_CURRENT');self.assertEqual(rows['OLD']['cik'],789)
        self.assertEqual(rows['NEW']['cik'],555)
        self.assertTrue(all(not r['historical_join_allowed'] and r['valid_from'] is None for r in rows.values()))

    def filing_audit(self):
        audit=RawAudit('submissions');root='CIK0000000123.json';history='CIK0000000123-submissions-001.json'
        audit.member(123,root,json.dumps(dict(cik=123,sic='7372',tickers=['TEST'],exchanges=['NYSE'],
            stateOfIncorporation='DE',filings=dict(recent=dict(accessionNumber=['0000000123-20-000001'],
                filingDate=['2020-02-03'],acceptanceDateTime=['2020-02-03T12:00:00Z'],form=['10-K'])))).encode())
        audit.member(123,history,json.dumps(dict(accessionNumber=['0000000123-20-000001','0000000123-20-000001'],
            filingDate=['2020-02-03','2020-02-03'],acceptanceDateTime=['2020-02-03T13:00:00Z',''],
            form=['10-K','10-K'])).encode())
        stage=audit.finish({123,456});return audit,stage

    def test_every_source_observation_and_disputed_clock_is_hashed(self):
        audit,stage=self.filing_audit()
        self.assertEqual(stage['rows'],3);self.assertEqual(stage['distinct_accessions'],1)
        self.assertEqual(stage['duplicate_accession_observations'],2)
        self.assertEqual(stage['accessions_with_conflicting_metadata'],1)
        self.assertEqual(stage['filings_without_acceptance_timestamp'],1)
        self.assertEqual(stage['missing_archive_ciks'],[456]);self.assertEqual(stage['entity_rows'],1)
        self.assertEqual(stage['conflict_examples'][0]['reported_values'],
                         {'acceptance_datetime':['2020-02-03T12:00:00Z','2020-02-03T13:00:00Z']})
        # Retaining the same counts while changing one source value must change the digest.
        one=dict.fromkeys(FIELDS['filings']);one.update(cik=123,source_row=1,source_member='one',
            conflict_fields=['acceptance_datetime'],accession_number='0000000123-20-000001')
        a=RowDigests('filings');a.add(one)
        b=RowDigests('filings');b.add(dict(one,acceptance_datetime='invented'))
        self.assertNotEqual(a.summary(),b.summary())

    def test_exact_numeric_source_order_and_skipped_values(self):
        raw=b'{"cik":123,"facts":{"us-gaap":{"X":{"units":{"USD":[{"val":9007199254740993,"filed":"2020-02-03"},{"val":0.1},{"val":true},{"val":"7"},{"val":2.0,"filed":"2020-02-04"}]}}}}}'
        audit=RawAudit('companyfacts');captured=[]
        original=audit.add_row
        def collect(row):captured.append(row);original(row)
        audit.add_row=collect;audit.member(123,'CIK0000000123.json',raw);stage=audit.finish({123})
        self.assertEqual([r['val_text'] for r in captured],['9007199254740993','0.1','2.0'])
        self.assertEqual([r['float64_exact'] for r in captured],[False,False,True])
        self.assertEqual([r['source_sequence'] for r in captured],[1,2,5])
        self.assertEqual(stage['source_fact_values'],5);self.assertEqual(stage['non_numeric_fact_values'],2)
        self.assertEqual(stage['numeric_facts_without_filed_date'],1)
        self.assertEqual((stage['first_filed_date'],stage['last_filed_date']),('2020-02-03','2020-02-04'))

    def fake_bundle(self,files,bindings):
        bundle=Bundle.__new__(Bundle);bundle.root=self.root;bundle.bindings=bindings;bundle.checked=set()
        def get(name):bundle.checked.add(name);return files[name]
        bundle.get=get;return bundle

    def test_actual_parquet_full_row_read_and_binding_corruption(self):
        row=dict(cik=123,sic=7372,current_tickers=['TEST'],current_exchanges=['NYSE'],
            state_of_incorporation='DE',identity_scope='CURRENT_ENTITY_METADATA_NOT_HISTORICAL_OWNERSHIP')
        name='sec_submissions_entities_retained-00000.parquet';path=self.root/name
        pq.write_table(pa.Table.from_pylist([row],schema=schema('entities')),path)
        with pq.ParquetFile(path) as file:signature=hashlib.sha256(str(file.schema_arrow).encode()).hexdigest()
        binding=dict(rows=1,ciks=[123],schema_sha256=signature)
        bundle=self.fake_bundle({name:path},{name:binding})
        self.assertEqual(list(bundle.parquet('entities')),[row]);self.assertFalse(path.exists())
        pq.write_table(pa.Table.from_pylist([row],schema=schema('entities')),path)
        binding['ciks']=[456]
        with self.assertRaisesRegex(ValueError,'rows/CIKs'):list(bundle.parquet('entities'))

    def test_raw_tar_hash_ledger_and_path_corruption(self):
        name='sec_companyfacts_raw-00000.tar.gz';path=self.root/name;raw=b'{"cik":123,"facts":{}}'
        with tarfile.open(path,'w:gz') as archive:
            member=tarfile.TarInfo('0000000123/CIK0000000123.json');member.size=len(raw);archive.addfile(member,io.BytesIO(raw))
        binding=dict(name=name,members=1)
        entry=dict(cik=123,member='0000000123/CIK0000000123.json',zip_member='CIK0000000123.json',
                   bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        ledger=dict(archive=binding,source_kind='companyfacts',members=[entry])
        bundle=self.fake_bundle({name:path},{name:binding})
        bundle.json=lambda name:ledger
        entry['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'SHA'):bundle.raw('companyfacts',RawAudit('companyfacts'),{123})
        entry['sha256']=hashlib.sha256(raw).hexdigest();entry['zip_member']='../CIK0000000123.json'
        with self.assertRaisesRegex(ValueError,'unsafe'):bundle.raw('companyfacts',RawAudit('companyfacts'),{123})
        entry['zip_member']='CIK0000000123.json';audit=RawAudit('companyfacts');bundle.raw('companyfacts',audit,{123})
        self.assertEqual(audit.finish({123})['source_members'],1);self.assertFalse(path.exists())

    def test_public_reader_cannot_import_producer_transforms(self):
        import ast
        from ci import sec_bulk_readback,sec_bulk_readback_core
        for module in (sec_bulk_readback,sec_bulk_readback_core):
            tree=ast.parse(Path(module.__file__).read_text())
            imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
            self.assertNotIn('ci.sec_bulk_retained',imports);self.assertNotIn('ci.sec_bulk_retained_core',imports)

    def test_complete_public_bundle_and_corrupted_values_with_unchanged_counts(self):
        """Exercise the whole reader using synthetic 8,439-name cohort metadata."""
        fixture=self.root/'fixture';fixture.mkdir();(fixture/'docs').mkdir();(fixture/'dictionary').mkdir()
        archived=[dict(ticker=f'T{i:04d}',status='UNIQUE_CIK' if i==0 else 'NO_CIK',
                       candidates=[dict(cik=123)] if i==0 else []) for i in range(8439)]
        identity_raw=json_bytes(dict(records=archived));keys=('price_ticker\n'+'\n'.join(r['ticker'] for r in archived)+'\n').encode()
        (fixture/'docs/SEC_RETAINED_IDENTITY_MAP_V1.json').write_bytes(identity_raw)
        (fixture/'dictionary/PRICE_WORLD_JOIN_KEYS_V1.csv').write_bytes(keys)
        source=dict(run='123',attempt='1',commit='a'*40,receipt_sha256='b'*64)
        maps=[{'0':dict(ticker='T0000',cik_str=123)},dict(fields=['ticker','cik','exchange'],data=[['T0000',123,'NYSE']])]
        identity_rows=identities(archived,*maps)
        raw_sub=json_bytes(dict(cik=123,filings=dict(recent=dict(accessionNumber=['0000000123-20-000001'],
            filingDate=['2020-02-03'],acceptanceDateTime=['2020-02-03T12:00:00Z']))))
        raw_fact=b'{"cik":123,"facts":{"us-gaap":{"X":{"units":{"pure":[{"val":0.1,"filed":"2020-02-03"}]}}}}}'
        audits={};rows={};stages={}
        for kind,raw in [('submissions',raw_sub),('companyfacts',raw_fact)]:
            audit=RawAudit(kind);captured=[];original=audit.add_row
            def capture(row,original=original,captured=captured):captured.append(row);original(row)
            audit.add_row=capture;audit.member(123,'CIK0000000123.json',raw);stages[kind]=audit.finish({123});audits[kind]=audit
            rows['filings' if kind=='submissions' else 'facts']=captured
        rows['identity']=identity_rows
        rows['entities']=[dict(cik=123,sic=None,current_tickers=[],current_exchanges=[],state_of_incorporation=None,
                              identity_scope='CURRENT_ENTITY_METADATA_NOT_HISTORICAL_OWNERSHIP')]
        coverage=dict(retained_names=8439,with_unique_cik=1,with_retrieval_candidates=1,retrieval_ciks=1,
            unique_cik_percent=round(100/8439,2),archived_unique_baseline=1,new_current_only=0,
            historical_ownership_intervals=0,status_counts={'ARCHIVED_AND_CURRENT_AGREE':1,'NO_CIK':8438})
        complete_coverage=dict(coverage,submissions_unique_ticker_matches=1,submissions_candidate_ticker_matches=1,
                              companyfacts_unique_ticker_matches=1,companyfacts_candidate_ticker_matches=1)
        raw_assets={'company_tickers.json':maps[0],'company_tickers_exchange.json':maps[1]}
        bindings={name:dict(sha256=hashlib.sha256(json_bytes(body)).hexdigest(),bytes=len(json_bytes(body)))
                  for name,body in raw_assets.items()}
        inputs={}
        for kind,name in [('tickers','company_tickers.json'),('exchanges','company_tickers_exchange.json')]:
            inputs[kind]=dict(url='https://www.sec.gov/'+name,**bindings[name])
        for kind in ('submissions','companyfacts'):inputs[kind]=dict(url='https://www.sec.gov/'+kind+'.zip',bytes=123,sha256='c'*64)
        report=dict(stages=stages,coverage=complete_coverage,inputs=inputs)
        json_assets=dict(raw_assets,SEC_IDENTITY_COVERAGE_V2=coverage)
        json_assets['SEC_IDENTITY_COVERAGE_V2.json']=json_assets.pop('SEC_IDENTITY_COVERAGE_V2')
        for kind in inputs:
            json_assets[f'SEC_{kind.upper()}_SOURCE_V2.json']=dict(kind=kind,source=inputs[kind],source_commit=source['commit'])
        identity_sha=hashlib.sha256(identity_raw).hexdigest()
        for kind in stages:
            json_assets[f'SEC_{kind.upper()}_EXTRACTION_V2.json']=dict(kind=kind,source=inputs[kind],result=stages[kind],
                source_commit=source['commit'],identity_map_lf_sha256=identity_sha)
        class SyntheticBundle:
            def __init__(self):
                self.source=source;self.report=report;self.bindings=bindings;self.checked=set()
                self.inventory=set(json_assets)|{'RAW:submissions','RAW:companyfacts'}|set(rows)
            def json(self,name):self.checked.add(name);return json_assets[name]
            def parquet(self,kind):self.checked.add(kind);return iter(rows[kind])
            def raw(self,kind,audit,selected):
                self.checked.add('RAW:'+kind);audit.member(123,'CIK0000000123.json',raw_sub if kind=='submissions' else raw_fact)
        with patch('ci.sec_bulk_readback.ROOT',fixture),patch('ci.sec_bulk_readback.IDENTITY_SHA',identity_sha),\
             patch('ci.sec_bulk_readback.KEYS_SHA',hashlib.sha256(keys).hexdigest()):
            result=audit_bundle(SyntheticBundle())
            self.assertEqual(result['coverage'],complete_coverage)
            self.assertFalse(result['full_unfiltered_zip_readback'])
            self.assertEqual(result['stages']['companyfacts']['row_digests']['facts']['123']['rows'],1)
            rows['facts'][0]['val_text']='0.2'
            with self.assertRaisesRegex(ValueError,'row values differ: facts'):audit_bundle(SyntheticBundle())
            rows['facts'][0]['val_text']='0.1';identity_rows[0]['historical_join_allowed']=True
            with self.assertRaisesRegex(ValueError,'identity rows differ'):audit_bundle(SyntheticBundle())


if __name__=='__main__':unittest.main()

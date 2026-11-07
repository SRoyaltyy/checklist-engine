"""Independent reader reconstructions against synthetic actual parquet files."""
import ast
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import pyarrow.parquet as pq
from ci.sec_quarterly_extract import extract_zip
from ci.sec_quarterly_readback_core import RowHash,columns,raw_window
from ci import sec_quarterly_readback as reader


class DiskPublisher:
    def __init__(self,root):self.root=root;self.assets=[]
    def emit(self,path,kind,**metadata):self.assets.append(dict(name=path.name,kind=kind,**metadata));return self.assets[-1]


class ReadbackTests(unittest.TestCase):
    def fixture(self,root,kind):
        if kind=='form345':
            tables=dict(SUBMISSION='ACCESSION_NUMBER\tFILING_DATE\tDOCUMENT_TYPE\tISSUERCIK\nA\t03-JAN-2023\t4\t123\n',
                REPORTINGOWNER='ACCESSION_NUMBER\tRPTOWNERCIK\tRPTOWNER_RELATIONSHIP\nA\t456\tDIRECTOR\nA\t789\tOFFICER\n',
                DERIV_TRANS='ACCESSION_NUMBER\tDERIV_TRANS_SK\tTRANS_DATE\tTRANS_ACQUIRED_DISP_CD\tTRANS_PRICEPERSHARE\tEXCERCISE_DATE\nA\t99\t02-JAN-2023\tA\t9007199254740993.01\t03-JAN-2024\n')
        else:
            tables=dict(SUBMISSION='ACCESSION_NUMBER\tFILING_DATE\tSUBMISSIONTYPE\tCIK\tPERIODOFREPORT\nA\t03-JAN-2023\t13F-HR/A\t123\t31-DEC-2020\n',
                INFOTABLE='ACCESSION_NUMBER\tINFOTABLE_SK\tCUSIP\tVALUE\tSSHPRNAMT\tSSHPRNAMTTYPE\nA\t90071992547409930000000001\t012345678\t9007199254740993\t100\tSH\nORPHAN\t2\t000000001\t2\t3\tSH\n')
        path=root/(kind+'.zip')
        with zipfile.ZipFile(path,'w') as archive:
            for table,text in tables.items():archive.writestr(table+'.tsv',text)
        return path

    def test_independent_full_raw_values_match_every_written_parquet_field(self):
        for kind in ('form345','form13f'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);path=self.fixture(root,kind);publisher=DiskPublisher(root)
                actual_report=extract_zip(path,kind,'2023Q1',publisher,{123})
                expected_report,expected_hashes=raw_window(path,kind,'2023Q1',{123})
                self.assertEqual(actual_report,expected_report)
                hashes={table:RowHash() for table in expected_hashes}
                stored={}
                for asset in publisher.assets:
                    table=asset['table'];rows=pq.read_table(root/asset['name']).to_pylist();stored[table]=rows
                    for row in rows:hashes[table].add([row[k] for k in columns(kind,table)])
                self.assertEqual({k:v.result() for k,v in hashes.items()},expected_hashes)
                if kind=='form345':
                    self.assertEqual(len(stored['REPORTINGOWNER']),2)
                    bad=RowHash();row=dict(stored['DERIV_TRANS'][0],TRANS_PRICEPERSHARE='9007199254740993.02')
                    bad.add([row[k] for k in columns(kind,'DERIV_TRANS')])
                    self.assertNotEqual(bad.result(),expected_hashes['DERIV_TRANS'])
                else:
                    row=stored['INFOTABLE'][0];self.assertEqual(row['reported_market_value_unit'],'USD')
                    self.assertEqual(row['filing_manager_cik'],123);self.assertNotIn('issuer_cik',row)
                    self.assertEqual(stored['INFOTABLE'][1]['parent_link_status'],'SOURCE_SUBMISSION_MISSING')

    def test_independent_core_has_no_producer_import(self):
        from ci import sec_quarterly_readback_core
        tree=ast.parse(Path(sec_quarterly_readback_core.__file__).read_text())
        imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        self.assertFalse(any(n and n.startswith('ci.') for n in imports))

    def test_request_requires_both_kinds_and_explicit_boolean(self):
        spec=dict(run='123',attempt='1',commit='a'*40,receipt_sha256='b'*64)
        self.assertEqual(reader.validate_request(dict(version=1,execute=False,sources={} ))['execute'],False)
        with self.assertRaisesRegex(ValueError,'both complete'):
            reader.validate_request(dict(version=1,execute=True,sources={'form345':spec}))
        with self.assertRaisesRegex(ValueError,'request differs'):
            reader.validate_request(dict(version=1,execute='false',sources={}))

    def test_catalog_preserves_actual_shifted_windows_and_rejects_ambiguous_names(self):
        html='<a href="/files/2020q1_form13f.zip">a</a><a href="/files/01jun2026-31aug2026_form13f.zip">b</a>'
        windows=reader.catalog(html,'form13f',2026)
        self.assertEqual([w['label'] for w in windows],['2020Q1','2026-06-01_2026-08-31'])
        with self.assertRaisesRegex(ValueError,'ambiguous'):
            reader.catalog(html+'<a href="/other/2020q1_form13f.zip">c</a>','form13f',2026)

    def test_complete_public_release_readback_and_corruptions(self):
        # Actual synthetic ZIP + parquet bytes pass through the outer reader,
        # manifest validation, original profile lineage and every-field hash.
        from ci.sec_quarterly_profile import profile_zip
        for kind in ('form345','form13f'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);storage=root/'storage';storage.mkdir()
                raw=self.fixture(storage,kind);name='2023q1_'+kind+'.zip';raw=raw.rename(storage/name)
                window=reader.catalog('<a href="/files/'+name+'">source</a>',kind,2026)[0]
                profile=profile_zip(raw);source=dict(url=window['url'],bytes=raw.stat().st_size,
                    sha256=reader.digest(raw),started_at='2026-11-07T00:00:00+00:00',finished_at='2026-11-07T00:01:00+00:00')
                original=dict(window=window,source=source,profile=profile,source_commit='b'*40)
                ptag='sec-quarterly-profile-v2-'+kind+'-122-1';dtag='nai-sec-quarterly-v2-'+kind+'-123-1'
                stores={ptag:{},dtag:{}}
                def put(tag,name,value):
                    data=value if isinstance(value,bytes) else json.dumps(value).encode()
                    stores[tag][name]=data
                    return dict(name=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
                index=(kind+'_official_index.html');index_bytes=('<a href="/files/'+name+'">source</a>').encode()
                index_meta=dict(url=reader.PAGES[kind],bytes=len(index_bytes),sha256=hashlib.sha256(index_bytes).hexdigest(),finished_at='2026-11-07T00:01:00+00:00')
                pbindings=[put(ptag,index,index_bytes),put(ptag,name,raw.read_bytes()),put(ptag,name+'.json',original),
                    put(ptag,name+'.source.json',dict(window=window,source=source,source_commit='b'*40))]
                pfinal=put(ptag,'SEC_QUARTERLY_SOURCE_PROFILE_V2.json',dict(status='PASS_PUBLISHED_SOURCE_CATALOG_ONLY',
                    kind=kind,source_commit='b'*40,release=ptag,actual_run_id='122',actual_attempt='1',
                    windows=[original],published_catalog=[window],index=index_meta,assets=pbindings))
                lineage=dict(release=ptag,asset=name,profile_receipt='SEC_QUARTERLY_SOURCE_PROFILE_V2.json',
                    profile_receipt_sha256=pfinal['sha256'],schema_receipt=name+'.json',
                    schema_receipt_sha256=pbindings[2]['sha256'],source_commit='b'*40)
                publisher=DiskPublisher(storage);extraction=extract_zip(raw,kind,'2023Q1',publisher,{123})
                dbindings=[]
                for asset in publisher.assets:
                    binding=put(dtag,asset['name'],(storage/asset['name']).read_bytes());dbindings.append(dict(asset,**binding))
                reused=dict(source,reused_from=lineage)
                entry=dict(window=window,source=reused,profile=profile,extraction=extraction,source_commit='a'*40)
                dbindings.extend([dict(put(dtag,name+'.source.json',dict(window=window,source=reused,source_commit='a'*40)),kind='quarterly_source_acquisition_receipt'),
                    dict(put(dtag,name+'.fixed.json',entry),kind='quarterly_fixed_field_receipt')])
                report=dict(status='PASS_ALL_PUBLISHED_QUARTERLY_FIXED_FIELDS_SOURCE_ONLY',kind=kind,actual_run_id='123',
                    actual_attempt='1',source_commit='a'*40,release=dtag,scoring_gate='CLOSED',world_gate='NOT_PROVEN',free_text_features=False,
                    scope='ALL_FIXED_SOURCE_ROWS_NOT_A_HISTORICAL_TICKER_OR_STOCK_DATE_JOIN',assets=dbindings,
                    profile_source=dict(run='122',attempt='1',commit='b'*40,receipt_sha256=pfinal['sha256']),index=index_meta,
                    index_lineage=dict(release=ptag,receipt_sha256=pfinal['sha256'],source_commit='b'*40),published_catalog=[window],windows=[entry])
                dfinal=put(dtag,reader.FINAL,report)
                spec=dict(run='123',attempt='1',commit='a'*40,receipt_sha256=dfinal['sha256'])
                def asset_inventory(tag):
                    return [dict(name=n,size=len(data),digest='sha256:'+hashlib.sha256(data).hexdigest(),state='uploaded') for n,data in stores[tag].items()]
                def release(tag):return dict(id=1 if tag==ptag else 2,draft=False,target_commitish=('b' if tag==ptag else 'a')*40)
                def api(path):
                    if path.startswith('releases/'):
                        return asset_inventory(ptag if path.split('/')[1]=='1' else dtag)
                    profile_run='/122/' in path
                    return dict(status='completed',conclusion='success',head_sha=('b' if profile_run else 'a')*40,
                        path='.github/workflows/sec_quarterly_profile.yml' if profile_run else '.github/workflows/nai_sec_quarterly_v2.yml')
                def download(tag,name,directory):
                    directory.mkdir(parents=True,exist_ok=True);path=directory/name;path.write_bytes(stores[tag][name]);return path
                with patch.object(reader.releases,'release_info',side_effect=release),patch.object(reader,'api',side_effect=api),\
                        patch.object(reader.releases,'download_asset',side_effect=download),patch.object(reader,'selected_ciks',return_value={123}):
                    result=reader.audit_kind(kind,spec,root/'audit')
                    self.assertEqual(result['status'],'PASS');self.assertEqual(result['windows_verified'],1)
                    self.assertEqual(result['data_assets_checked'],len(stores[dtag]))
                    stores[dtag]['unbound.parquet']=b'unexpected'
                    with self.assertRaisesRegex(ValueError,'unbound/missing'):
                        reader.audit_kind(kind,spec,root/'audit-extra')
                    del stores[dtag]['unbound.parquet']
                    # Change a financial value and consistently re-sign manifests;
                    # the independent ZIP comparison must still reject it.
                    asset=next(a for a in dbindings if a.get('table') in ('DERIV_TRANS','INFOTABLE'))
                    path=storage/asset['name'];table=pq.read_table(path);rows=table.to_pylist()
                    key='VALUE' if kind=='form13f' else 'TRANS_PRICEPERSHARE';rows[0][key]='12345'
                    import pyarrow as pa
                    pq.write_table(pa.Table.from_pylist(rows,schema=table.schema),path,compression='zstd')
                    asset.update(put(dtag,path.name,path.read_bytes()))
                    spec['receipt_sha256']=put(dtag,reader.FINAL,report)['sha256']
                    with self.assertRaisesRegex(ValueError,'full source/parquet values differ'):
                        reader.audit_kind(kind,spec,root/'audit-changed')


if __name__=='__main__':unittest.main()

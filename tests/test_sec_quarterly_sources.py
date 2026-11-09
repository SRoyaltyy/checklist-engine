import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from ci.sec_quarterly_sources import ProfileCache


class CacheTests(unittest.TestCase):
    def test_only_complete_bound_profile_catalog_can_supply_exact_cached_zip(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);spec=dict(run='123',attempt='1',commit='a'*40,receipt_sha256='b'*64)
            tag='sec-quarterly-profile-v2-form345-123-1'
            raw_path=root/'2020q1_form345.zip';raw_path.write_bytes(b'synthetic official ZIP bytes')
            window=dict(name=raw_path.name,url='https://www.sec.gov/files/2020q1_form345.zip',label='2020Q1')
            source=dict(url=window['url'],bytes=raw_path.stat().st_size,sha256=hashlib.sha256(raw_path.read_bytes()).hexdigest(),
                        started_at='original source time')
            receipt=dict(window=window,source=source,profile=dict(tables=[]),source_commit='a'*40)
            schema_path=root/(raw_path.name+'.json');schema_path.write_text(json.dumps(receipt))
            def binding(path):return dict(name=path.name,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            report=dict(status='PASS_PUBLISHED_SOURCE_CATALOG_ONLY',kind='form345',source_commit='a'*40,
                release=tag,actual_run_id='123',actual_attempt='1',windows=[receipt],published_catalog=[window],
                assets=[binding(raw_path),binding(schema_path)])
            root_path=root/'SEC_QUARTERLY_SOURCE_PROFILE_V2.json';root_bytes=json.dumps(report).encode();root_path.write_bytes(root_bytes)
            spec['receipt_sha256']=hashlib.sha256(root_bytes).hexdigest()
            paths={raw_path.name:raw_path,schema_path.name:schema_path,root_path.name:root_path}
            run=dict(status='completed',conclusion='success',head_sha='a'*40,path='.github/workflows/sec_quarterly_profile.yml')
            with patch('ci.sec_quarterly_sources.verified_release'),\
                    patch('ci.sec_quarterly_sources.api',return_value=run),\
                    patch('ci.sec_quarterly_sources.releases.download_asset',side_effect=lambda tag,name,root:paths[name]):
                cache=ProfileCache('form345',spec,root);path,restored,profile=cache.get(receipt)
                self.assertEqual(path,raw_path);self.assertEqual(restored['started_at'],'original source time')
                self.assertEqual(restored['reused_from']['profile_receipt_sha256'],spec['receipt_sha256'])
                raw_path.write_bytes(b'changed');schema_path.write_text(json.dumps(receipt))
                with self.assertRaisesRegex(ValueError,'source bytes differ'):cache.get(receipt)
                report['windows']=[];root_path.write_text(json.dumps(report));spec['receipt_sha256']=hashlib.sha256(root_path.read_bytes()).hexdigest()
                with self.assertRaisesRegex(ValueError,'omitted published'):ProfileCache('form345',spec,root)


if __name__=='__main__':unittest.main()

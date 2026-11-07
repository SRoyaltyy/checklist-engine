"""Synthetic archive evidence for empty, missing and mismatched body identities."""
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from ci.sec_companyfacts_diagnostic import EXPECTED_SHA,inspect_archive,validate_request


class DiagnosticTests(unittest.TestCase):
    def test_only_the_exact_failing_source_can_be_requested(self):
        for execute in (False,True):
            self.assertEqual(validate_request(dict(version=1,execute=execute,source_sha256=EXPECTED_SHA))['execute'],execute)
        for value in [dict(version=1,execute='false',source_sha256=EXPECTED_SHA),
                      dict(version=1,execute=True,source_sha256='0'*64)]:
            with self.assertRaises(ValueError):validate_request(value)

    def test_all_bad_source_members_are_explicit_and_exact_bytes_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'source.zip'
            bodies={123:b'{}',456:b'{"facts":{}}',789:b'{"cik":999,"facts":{}}',
                    111:b'{"cik":111,"facts":{}}',222:b'{"cik":222,"facts":[]}',444:b'{invalid'}
            with zipfile.ZipFile(path,'w') as archive:
                for cik,raw in bodies.items():archive.writestr(f'CIK{cik:010d}.json',raw)
            retained={}
            result=inspect_archive(path,set(bodies)|{333},lambda entry,raw:retained.update({entry['cik']:raw}))
            self.assertEqual(result['missing_archive_ciks'],[333]);self.assertEqual(result['archive_ciks'],6)
            statuses={r['cik']:r['status'] for r in result['members']}
            self.assertEqual(statuses[123],'EMPTY_OBJECT_NO_BODY_IDENTITY_OR_FACTS')
            self.assertEqual(statuses[456],'MISSING_BODY_CIK_NONEMPTY_PAYLOAD')
            self.assertEqual(statuses[789],'MISMATCHED_BODY_CIK')
            self.assertEqual(statuses[111],'BODY_IDENTITY_VERIFIED')
            self.assertEqual(statuses[222],'INVALID_FACTS_CONTAINER')
            self.assertEqual(statuses[444],'INVALID_JSON')
            self.assertEqual(retained,{c:raw for c,raw in bodies.items() if c!=111})


if __name__=='__main__':unittest.main()

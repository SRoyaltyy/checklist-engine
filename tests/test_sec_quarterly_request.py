import unittest
from ci.sec_quarterly_retained import validate_request


class RequestTests(unittest.TestCase):
    def test_quarterly_scope_and_cache_anchors_are_bound(self):
        value=dict(version=2,scope='SEC_QUARTERLY_FIXED_FIELDS_2020_LATEST',execute=False,
                   bulk_readback=None,profile_sources={})
        self.assertEqual(validate_request(value),value)
        for bad in [dict(value,scope='narrow subset'),dict(value,profile_sources={'other':{}}),
                    dict(value,profile_sources={'form345':dict(run='1',attempt='1',commit='bad',receipt_sha256='a'*64)})]:
            with self.assertRaises(ValueError):validate_request(bad)
        with self.assertRaisesRegex(ValueError,'frozen successful bulk readback'):
            validate_request(dict(value,execute=True))


if __name__=='__main__':unittest.main()

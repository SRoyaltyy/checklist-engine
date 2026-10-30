import copy
import unittest
from ci.rebuild_checkpoint_probe import reconcile


class PartialCheckpointTest(unittest.TestCase):
    def fixture(self):
        request=dict(run=41078405278,job=124141406844,release_id=429178716,index=0,processed_checkpoint_rows=2,
                     source_commit='source',plan={'release':'inputs'},checkpoint={'release':'partial'})
        part={'tickers':['A','B','C']};plan=dict(parts=[part],request=dict(corrected_recipe_fingerprint='recipe',registry_sha256='registry'))
        row=dict(ticker='A',release='partial',asset='a',diagnostic_questions=68904,roundtrip='ALL_CELLS_EXACT_WITH_MISSING_DISTINCT',
                 shared_registry_sha256='registry',answer_container_bytes=3,answer_container_sha256='answer')
        state=dict(source_part=part,inputs_release='inputs',source_commit='source',recipe_fingerprint='recipe',completed=[row],excluded=[dict(ticker='B',reason='STOCK_ERROR',error='transport detail')])
        inventory=dict(id=429178716,tag_name='partial',assets=[dict(name='a',state='uploaded',size=3,digest='sha256:answer')])
        return plan,state,inventory,request

    def test_preserves_exact_completed_record_and_retries_only_missing(self):
        args=self.fixture();result=reconcile(*args)
        self.assertEqual(result['completed'],args[1]['completed'])
        self.assertIsNot(result['completed'][0],args[1]['completed'][0])
        self.assertEqual(result['missing_names'],['B','C'])
        self.assertEqual(result['verified_completed_names'],1)
        self.assertEqual(result['checkpoint_excluded'][0]['error'],'transport detail')
        self.assertEqual(result['original_source_mutations'],'NONE')

    def test_unverified_asset_does_not_count_as_durable(self):
        for key,value in [('state','starter'),('size',4),('digest','sha256:other')]:
            args=self.fixture();args[2]['assets'][0][key]=value
            with self.assertRaises(ValueError):reconcile(*args)

    def test_changed_recipe_or_membership_fails(self):
        args=self.fixture();args[1]['recipe_fingerprint']='other'
        with self.assertRaises(ValueError):reconcile(*args)
        args=self.fixture();args[1]['excluded'][0]['ticker']='OUTSIDE'
        with self.assertRaises(ValueError):reconcile(*args)
        args=self.fixture();args[1]['excluded'][0]['ticker']='A'
        with self.assertRaises(ValueError):reconcile(*args)

    def test_wrong_checkpoint_progress_or_source_fails(self):
        args=self.fixture();args[3]['processed_checkpoint_rows']=3
        with self.assertRaises(ValueError):reconcile(*args)
        args=self.fixture();args[1]['source_commit']='other'
        with self.assertRaises(ValueError):reconcile(*args)

    def test_protected_resources_never_become_recovery_targets(self):
        args=self.fixture();args[3]['run']=40621517496
        with self.assertRaises(ValueError):reconcile(*args)
        args=self.fixture();args[3]['release_id']=427402982
        with self.assertRaises(ValueError):reconcile(*args)

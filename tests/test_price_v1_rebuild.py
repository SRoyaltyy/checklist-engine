import copy
import unittest
from ci.price_v1_rebuild import validate
from ci.price_v1_sample_gate import scope


class PriceV1RebuildTest(unittest.TestCase):
    def fixture(self):
        policy=scope();request=dict(corrected_recipe_fingerprint='frozen',replay_quarantine={'lf_sha256':'quarantine'})
        sample=['S'+str(i) for i in range(100)]
        plan=dict(scope=policy,source_commit='measured',request=request,original_universe=8727,source_coverage_pct=100*8439/8727,
                  sample=sample,price_fields=list(range(1044)),timeframes=list(range(22)))
        binding=dict(gate={'sha256':'gate'},sample_plan={'sha256':'plan'})
        gate=dict(format='ROW0_PRICE_WORLD_GATE_V2',price_v1_gate='PASS',authority_commit=policy['authority_commit'],
            plan_sha256='plan',source_commit='measured',retained_names=8439,source_coverage_pct=plan['source_coverage_pct'],
            sample_names=sample,sample_stocks=100,stock_bindings=[{'ticker':t} for t in sample],price_columns_per_timeframe=1044,
            native_timeframes=22,cut_checks=4400,compared_cells=10000,prefix_mismatch_blocks=0,prefix_failures=[],
            deferred_fields={f:'DEFERRED_V2_FIELD' for f in policy['deferred_fields']},scoring_gate='CLOSED',protected_source_mutations='NONE')
        return gate,plan,binding,request,policy

    def test_scoped_pass_only_authorizes_rebuild(self):
        result=validate(*self.fixture())
        self.assertEqual(result['price_v1_row0_gate'],'PASS_SAMPLE_ONLY')
        self.assertEqual(result['full_world_and_scoring'],'NOT_APPROVED_BY_SAMPLE_GATE')
        self.assertEqual(result['max_parallel'],20)

    def test_fail_or_unmeasured_gate_cannot_authorize_rebuild(self):
        for status in ('FAIL','UNMEASURED'):
            args=self.fixture();args[0]['price_v1_gate']=status
            with self.assertRaises(ValueError):validate(*args)

    def test_different_plan_recipe_or_duplicate_sample_cannot_authorize(self):
        args=self.fixture();args[0]['plan_sha256']='other'
        with self.assertRaises(ValueError):validate(*args)
        args=self.fixture();args[1]['request']=copy.deepcopy(args[3]);args[1]['request']['corrected_recipe_fingerprint']='other'
        with self.assertRaises(ValueError):validate(*args)
        args=self.fixture();args[0]['stock_bindings'][0]=args[0]['stock_bindings'][1]
        with self.assertRaises(ValueError):validate(*args)

    def test_observed_prefix_failure_or_wrong_scope_cannot_authorize(self):
        args=self.fixture();args[0]['prefix_failures']=[{'field':'leak'}]
        with self.assertRaises(ValueError):validate(*args)
        args=self.fixture();args[0]['deferred_fields']={}
        with self.assertRaises(ValueError):validate(*args)


if __name__=='__main__':unittest.main()

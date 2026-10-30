import copy
import unittest
import numpy as np
from ci.price_v1_sample_gate import compare,select,scope,verdict,align_prefix


class PriceV1SampleGateTest(unittest.TestCase):
    def test_empty_prelisting_prefix_and_real_availability_difference(self):
        import pandas as pd
        a=pd.DataFrame({'available_from':pd.Series(dtype='datetime64[ns]'),'close':pd.Series(dtype=float)})
        b=pd.DataFrame(columns=['available_from'])
        left,right,differences=align_prefix(a,b)
        self.assertEqual(differences,[])
        self.assertEqual(len(left),0)
        self.assertEqual(len(right),0)
        a=pd.DataFrame({'available_from':pd.to_datetime(['2023-01-03','2023-01-04']),'close':[1.,2.]})
        left,right,differences=align_prefix(a,a.iloc[:1])
        self.assertEqual(len(left),1)
        self.assertEqual(len(right),1)
        self.assertEqual(differences[0]['different_cells'],1)

    def test_predeclared_selection_is_order_independent(self):
        names=[str(i) for i in range(8439)];policy=scope()
        self.assertEqual(select(names,policy),select(names[::-1],policy))
        self.assertEqual(len(set(select(names,policy))),100)
        with self.assertRaises(ValueError):select(names[:-1],policy)

    def test_exact_bits_missing_and_infinity(self):
        x=np.array([1.,np.nan,np.inf,0.,-np.inf])
        y=x.copy();y[0]=np.nextafter(1.,2.);y[1]=0.;y[3]=-0.
        result=compare(x,y)
        self.assertEqual(result['different_cells'],3)
        self.assertEqual(result['missing_differences'],1)
        self.assertEqual(compare(x,x.copy())['different_cells'],0)

    def test_only_the_nine_owner_authorized_fields_are_deferred(self):
        policy=scope()
        self.assertEqual(len(set(policy['deferred_fields'])),9)
        self.assertEqual(policy['deferred_fields_reason'],'DEFERRED_V2_FIELD')
        self.assertEqual(policy['authority_commit'],'0b57c0939e56c1611874e01b45f98cf2cd994aee')

    def fixtures(self):
        names=[str(i) for i in range(100)]
        plan=dict(sample=names,price_fields=['close'],timeframes=['1d'],source_coverage_pct=96.7,scope=scope())
        stock=dict(coverage=[dict(timeframe='1d',field='close')],checks=[dict(timeframe='1d',cut=cut,rows=2,columns=1,cells=2,differences=[]) for cut in plan['scope']['prefix_cuts']])
        return plan,[dict(copy.deepcopy(stock),ticker=t) for t in names]

    def test_observed_leak_fails_but_full_cohort_unmeasured_is_reported(self):
        plan,stocks=self.fixtures();result=verdict(plan,stocks)
        self.assertEqual(result['price_v1_gate'],'PASS')
        self.assertEqual(result['scoring_gate'],'CLOSED')
        self.assertIn('UNMEASURED',result['full_cohort_price_PIT'])
        stocks[0]['checks'][0]['differences']=[dict(field='close',different_cells=1)]
        self.assertEqual(verdict(plan,stocks)['price_v1_gate'],'FAIL')

    def test_incomplete_sample_or_field_grid_cannot_pass(self):
        plan,stocks=self.fixtures()
        with self.assertRaises(ValueError):verdict(plan,stocks[:-1])
        stocks[0]['coverage']=[]
        with self.assertRaises(ValueError):verdict(plan,stocks)
        plan,stocks=self.fixtures();stocks[0]['checks'].pop()
        with self.assertRaises(ValueError):verdict(plan,stocks)
        plan,stocks=self.fixtures();stocks[0]['checks'][0]['cells']=0
        with self.assertRaises(ValueError):verdict(plan,stocks)


if __name__=='__main__':unittest.main()

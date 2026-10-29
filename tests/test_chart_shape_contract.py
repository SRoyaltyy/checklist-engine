from datetime import date
import csv
import json
import math
from pathlib import Path
import unittest
import tempfile

from ci.audit_inventory_catalog import audit
from world_chart_shape import HORIZONS, TIMEFRAMES, WINDOWS, known_forward_return, match_state, normalise_closes, shape_similarity


class ShapeContract(unittest.TestCase):
    def test_normalization_is_close_only_and_constant_or_missing_is_unknown(self):
        self.assertEqual(normalise_closes([10.,20.,10.]), (0.,1.,0.))
        for bad in ([5.]*10, [None]+[5.]*9, [math.inf]+[5.]*9, [0.]+[5.]*9):
            self.assertIsNone(normalise_closes(bad))

    def test_affine_shape_and_reversed_shape_have_correct_correlation(self):
        a=[float(v) for v in range(1,11)]
        self.assertAlmostEqual(shape_similarity(a,[2*v+100 for v in a]),1.,places=14)
        self.assertAlmostEqual(shape_similarity(a,list(reversed(a))),-1.,places=14)

    def test_threshold_is_strict_and_unknown_is_not_no(self):
        self.assertFalse(match_state(.90))
        self.assertTrue(match_state(math.nextafter(.90,1.)))
        self.assertIsNone(match_state(None))
        with self.assertRaises(ValueError): match_state(1.1)

    def test_outcome_uses_exact_trading_session_endpoint_not_calendar_days(self):
        cal=[date(2020,1,d) for d in (2,3,6,7,8)]
        prices={cal[0]:10.,cal[1]:11.,cal[2]:12.,cal[3]:13.}
        self.assertAlmostEqual(known_forward_return(cal,prices,cal[0],cal[4],2),.2)
        self.assertIsNone(known_forward_return(cal,{cal[0]:10.,cal[3]:13.},cal[0],cal[4],2))

    def test_never_reads_setup_day_or_later_outcome(self):
        cal=[date(2020,1,d) for d in (2,3,6,7,8)]
        class NoRead(dict):
            def get(self,key): raise AssertionError('unmatured outcome price was read')
        self.assertIsNone(known_forward_return(cal,NoRead(),cal[0],cal[2],2))
        self.assertIsNone(known_forward_return(cal,NoRead(),cal[0],cal[2],21))

    def test_candidate_and_setup_must_be_real_sessions_with_candidate_strictly_earlier(self):
        cal=[date(2020,1,d) for d in (2,3,6)]
        for end,setup,k in ((cal[1],cal[1],1),(cal[0],date(2020,1,4),1),(cal[0],cal[2],True)):
            with self.assertRaises(ValueError): known_forward_return(cal,{},end,setup,k)

    def test_registered_axes_are_complete_and_k_independent_outputs_are_not_duplicated(self):
        spec=json.loads(Path('dictionary/CHART_SHAPE_REGISTRY_V1.json').read_text(encoding='utf-8'))
        self.assertEqual(spec['grid'],dict(N=list(WINDOWS),Y=list(TIMEFRAMES),K=list(HORIZONS)))
        self.assertEqual(spec['defaults'],dict(N=20,Y='1d',K=5))
        self.assertEqual({item['id'] for item in spec['items']},{'I227','I228'})
        for item in spec['items']:
            for output in item['outputs']:
                self.assertTrue(output['viewport_draw'] and output['units'] and output['definition'])
                if output['name'] in ('match_count','top5_geometry','shape_correlation'):
                    self.assertNotIn('K',output['axes'])
        self.assertEqual(spec['fixed_similarity_rule']['operator'],'>')
        self.assertEqual(spec['fixed_similarity_rule']['threshold'],.90)

    def catalog(self,root):
        ids=['C01','I227','I228']
        def write(name,fields,rows):
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('w',encoding='utf-8',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
        write('dictionary/WORLD_SNAPSHOT_DICTIONARY.csv',['id'],[dict(id=i) for i in ids])
        write('dictionary/DATA_SOURCES.csv',['id','fetch_test'],[
            dict(id=i,fetch_test='legacy' if i=='C01' else 'REGISTERED_DERIVED_SOURCE_NOT_MEASURED') for i in ids])
        write('dictionary/world_coverage_map.csv',['item_id'],[dict(item_id=i) for i in ids])
        fields=['namespace','item_id','timeframe','status','reason']
        rows=[dict(namespace='dictionary',item_id=i,timeframe=tf,status='PENDING',reason='not measured') for i in ids for tf in TIMEFRAMES]
        write('docs/WORLD_COVERAGE.csv',fields,rows)
        return write,fields,rows

    def test_catalog_gate_detects_silent_source_and_timeframe_omissions(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            root=Path(directory);write,fields,rows=self.catalog(root)
            self.assertEqual(audit(root)['required_inventory_timeframe_rows'],66)
            write('docs/WORLD_COVERAGE.csv',fields,rows[:-1])
            with self.assertRaisesRegex(ValueError,'omitted'):audit(root)
            write('docs/WORLD_COVERAGE.csv',fields,rows)
            write('dictionary/DATA_SOURCES.csv',['id','fetch_test'],[dict(id='C01',fetch_test='legacy')])
            with self.assertRaisesRegex(ValueError,'missing'):audit(root)

    def test_new_pending_reason_required_and_legacy_missing_reasons_reported_not_approved(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            root=Path(directory);write,fields,rows=self.catalog(root)
            rows[0]['reason']=''
            write('docs/WORLD_COVERAGE.csv',fields,rows)
            report=audit(root)
            self.assertEqual(report['legacy_pending_rows_without_reason'],1)
            self.assertEqual(report['full_world_gate'],'NOT_PROVEN')
            rows[-1]['reason']=''
            write('docs/WORLD_COVERAGE.csv',fields,rows)
            with self.assertRaisesRegex(ValueError,'PENDING reason'):audit(root)


if __name__=='__main__': unittest.main()

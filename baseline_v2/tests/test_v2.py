import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from parser_v2 import run,normalize_amount,read_lines
from evaluate import read_gold,measure
from benchmark import make_variant,make_two_page,raster_only,remove_one_cell,remove_negative_marker

class FinancialTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=run(ROOT/'source.pdf');cls.gold=read_gold(ROOT/'tests/gold_rows.tsv')
        cls.variants={
         'scaled':make_variant('scaled_79',scale=.79,offset=(100,45)),
         'large':make_variant('scaled_123',scale=1.23,offset=(34,60)),
         'translated':make_variant('translated',scale=1,offset=(180,15)),
         'noisy':make_variant('distractor_footer',scale=.91,offset=(90,33),with_noise=True),
         'two':make_two_page(),'missing':remove_one_cell(),'sign':remove_negative_marker(),'raster':raster_only()}
    def get(self,label):return next(x for x in self.data['rows'] if x['label']==label)
    def test_01_all_monetary_rows(self):self.assertEqual(self.data['stats']['monetary_rows'],37)
    def test_02_sections(self):self.assertEqual(self.data['stats']['sections'],6)
    def test_03_raw_cell_gold(self):self.assertEqual(measure(self.data['rows'],self.gold)['raw_cell_exact'],74)
    def test_04_hierarchy_gold(self):self.assertEqual(measure(self.data['rows'],self.gold)['path_exact'],43)
    def test_05_dates(self):self.assertEqual(self.data['pages'][0]['periods'],['2025-03-31','2026-03-31'])
    def test_06_unit(self):self.assertEqual(self.data['pages'][0]['unit'],'thousand_JPY')
    def test_07_anchors(self):
        x=self.data['pages'][0]['column_anchors'];self.assertAlmostEqual(x[0],397.51,places=1);self.assertAlmostEqual(x[1],522.55,places=1)
    def test_08_negative(self):self.assertEqual(normalize_amount('△3,634,165'),(-3634165,'observed'))
    def test_09_negative_zero(self):self.assertEqual(normalize_amount('△0'),(0,'negative_zero'))
    def test_10_missing_dash(self):self.assertEqual(normalize_amount('－'),(None,'not_reported'))
    def test_11_numeric_total(self):self.assertEqual([c['value'] for c in self.get('資産合計')['cells']],[7534110,5135249])
    def test_12_local_depreciation_associations(self):
        dep=[x for x in self.data['rows'] if x['label']=='減価償却累計額']
        self.assertEqual(len(dep),4);self.assertEqual(len({tuple(x['path']) for x in dep}),4)
    def test_13_hierarchy_fixed_assets_total(self):self.assertEqual(self.get('固定資産合計')['path'],['資産の部','固定資産合計'])
    def test_14_negative_amount_evidence_box(self):
        r=self.get('貸倒引当金');self.assertEqual(r['cells'][0]['raw'],'△2,979');self.assertTrue(r['cells'][0]['bbox'])
    def test_15_nonzero_small_reconciliations_reported(self):
        self.assertTrue(any(c['difference']!=0 for c in self.data['checks']))
        self.assertTrue(all(c['plausibly_rounded'] for c in self.data['checks']))
    def test_16_scale_down(self):self.assertEqual(measure(run(self.variants['scaled'])['rows'],self.gold)['raw_cell_exact'],74)
    def test_17_scale_up(self):self.assertEqual(measure(run(self.variants['large'])['rows'],self.gold)['raw_cell_exact'],74)
    def test_18_horizontal_translate(self):self.assertEqual(measure(run(self.variants['translated'])['rows'],self.gold)['raw_cell_exact'],74)
    def test_19_distractor_footer(self):self.assertEqual(measure(run(self.variants['noisy'])['rows'],self.gold)['raw_cell_exact'],74)
    def test_20_multipage(self):self.assertEqual(run(self.variants['two'])['stats']['reported_cell_count'],148)
    def test_21_one_deleted_cell_flagged(self):
        x=run(self.variants['missing'])
        self.assertEqual(x['stats']['reported_cell_count'],73)
        self.assertTrue(any(i['code']=='partial_data_row' for i in x['issues']))
        self.assertEqual(next(r for r in x['rows'] if r['label']=='売掛金')['cells'][0]['status'],'absent_text_cell')
    def test_22_lost_sign_accounting_alarm(self):
        x=run(self.variants['sign'])
        self.assertTrue(any(i['code']=='financial_reconciliation_failure' for i in x['issues']))
    def test_23_raster_fails_closed(self):
        x=run(self.variants['raster'])
        self.assertEqual(x['stats']['monetary_rows'],0)
        self.assertEqual(x['issues'][0]['code'],'needs_visual_fallback')
    def test_24_cells_include_source_coordinates(self):
        for r in self.data['rows']:
            self.assertTrue(r['label_bbox'])
            if r['type']!='section':self.assertTrue(all(c['bbox'] for c in r['cells']))
    def test_25_all_issues_empty_on_original(self):self.assertEqual(self.data['issues'],[])

if __name__=='__main__':unittest.main()

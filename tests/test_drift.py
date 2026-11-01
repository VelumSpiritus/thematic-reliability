import unittest
from thematic_reliability import (measure_drift, cohen_kappa, krippendorff_alpha,
    Codebook, Code, ThematicNetwork, BasicTheme, OrganizingTheme, GlobalTheme, drift_impact)
from thematic_reliability.drift import _per_code_agreement

class DriftRegressionTests(unittest.TestCase):
    def setUp(self):
        self.base = dict(zip(range(4), ['A','A','B','B']))
    def test_expanding_code_and_omitted_code_are_both_flagged(self):
        report=measure_drift(self.base,[self.base,dict.fromkeys(self.base,'A')])
        self.assertEqual(set(dict(report.drifting_codes())),{'A','B'})
        a=report.windows[1].per_code_metrics['A'];b=report.windows[1].per_code_metrics['B']
        self.assertEqual((a.true_positive,a.false_positive,a.false_negative,a.true_negative),(2,2,0,0))
        self.assertEqual((a.baseline_count,a.recoding_count),(2,4))
        self.assertEqual(a.recall,1);self.assertEqual(a.precision,.5);self.assertAlmostEqual(a.agreement,2/3)
        self.assertEqual(a.overuse_rate,1);self.assertEqual(a.omission_rate,0);self.assertEqual(a.prevalence_delta,.5)
        self.assertIsNone(b.precision);self.assertEqual(b.recall,0);self.assertEqual(b.agreement,0);self.assertEqual(b.omission_rate,1)
        self.assertEqual(report.kappas,[1.,0.]);self.assertEqual(report.windows[1].p_observed,.5);self.assertEqual(report.windows[1].p_expected,.5)
    def test_stable_coding_and_absent_categories(self):
        report=measure_drift(self.base,[self.base,self.base],['A','B','C'])
        self.assertEqual(report.drifting_codes(),[])
        for window in report.windows:
            self.assertEqual(window.per_code['A'],1);self.assertIsNone(window.per_code['C'])
            stats=window.per_code_metrics['C'];self.assertIsNone(stats.precision);self.assertIsNone(stats.recall)
            self.assertEqual(stats.overuse_rate,0)
    def test_new_code_appearance_is_detected_without_imputed_positive_agreement(self):
        changed={**self.base,2:'C'};report=measure_drift(self.base,[self.base,changed])
        self.assertIsNone(report.windows[0].per_code['C']);self.assertEqual(report.windows[1].per_code['C'],0)
        self.assertIn('C',dict(report.drifting_codes()));self.assertGreater(report.per_code_trends()['C']['overuse_rate'],0)
    def test_balanced_swaps_have_zero_prevalence_change_and_nonzero_drift(self):
        changed=dict(zip(range(4),['B','B','A','A']));report=measure_drift(self.base,[self.base,changed])
        self.assertEqual(set(dict(report.drifting_codes())),{'A','B'})
        self.assertTrue(all(s.prevalence_delta==0 for s in report.windows[1].per_code_metrics.values()))
    def test_changing_subsets_use_a_common_panel_for_trends(self):
        first={0:'A',1:'A',3:'B'};second={0:'A',2:'A',3:'B'}
        report=measure_drift(self.base,[first,second])
        self.assertEqual(report.common_units,(0,3));self.assertEqual(report.drifting_codes(),[])
        self.assertEqual(report.windows[0].per_code['A'],1);self.assertAlmostEqual(report.windows[1].per_code['A'],2/3)
        self.assertIn('calibration subsets vary',report.summary())
        for window,current in zip(report.windows,[first,second]):
            units=window.unit_ids
            self.assertEqual((window.kappa,window.p_observed,window.p_expected),cohen_kappa([self.base[u] for u in units],[current[u] for u in units],report.categories))
    def test_disjoint_subsets_make_trend_unavailable(self):
        report=measure_drift(self.base,[{0:'A',1:'A'},{2:'B',3:'B'}])
        self.assertEqual(report.common_units,());self.assertEqual(report.drifting_codes(),[])
        self.assertIsNone(report.per_code_trends()['A']['agreement']);self.assertIn('trends unavailable',report.summary())
    def test_skipped_rounds_keep_original_indices(self):
        report=measure_drift(self.base,[self.base,{0:'A'},dict.fromkeys(self.base,'A')])
        self.assertEqual([w.window_index for w in report.windows],[0,2]);self.assertAlmostEqual(report.per_code_trends()['A']['agreement'],-1/6)
    def test_single_window_has_no_trend(self):
        report=measure_drift(self.base,[self.base]);self.assertIsNone(report.trend);self.assertEqual(report.drifting_codes(),[])
    def test_explicit_category_contract_is_complete_and_unique(self):
        with self.assertRaises(ValueError):measure_drift(self.base,[self.base],['A'])
        with self.assertRaises(ValueError):measure_drift(self.base,[self.base],['A','A','B'])
        with self.assertRaises(ValueError):_per_code_agreement(['A'],[],['A'])
    def test_all_eight_components_flow_through_codebook_metrics_and_network(self):
        axes=['WHAT','HOW','WHO','HOWMUCH','WHEREWHEN','WHY','WHETHER','WHICH']
        cb=Codebook('Components')
        for axis in axes:cb.add(Code(axis,axis+' component'))
        self.assertEqual(set(Codebook.from_dict(cb.to_dict()).categories()),set(axes))
        baseline=dict(enumerate(axes));current={**baseline,7:'WHAT'};report=measure_drift(baseline,[baseline,current],categories=axes)
        self.assertEqual(set(report.windows[1].per_code_metrics),set(axes));self.assertEqual(set(dict(report.drifting_codes())),{'WHAT','WHICH'})
        network=ThematicNetwork();network.add_basic(BasicTheme('Referents',['WHAT']));network.add_basic(BasicTheme('Selection',['WHICH']))
        network.add_organizing(OrganizingTheme('Components',['Referents','Selection']));network.add_global(GlobalTheme('Whole',['Components']))
        impact=drift_impact(network,report)
        self.assertEqual(next(row for row in impact if row['name']=='Whole')['drifting_codes'],['WHAT','WHICH'])
    def test_original_overall_coefficients_are_preserved(self):
        self.assertEqual(cohen_kappa(['A','A','B','B'],['A','A','A','A']),(0.,.5,.5))
        self.assertAlmostEqual(krippendorff_alpha([['A','A'],['A','B'],['B','B']])[0],4/9)
    def test_extra_recoding_units_do_not_enter_calibration_counts(self):
        report=measure_drift(self.base,[{**self.base,99:'C'},self.base])
        self.assertEqual(report.windows[0].n_units,4);self.assertIsNone(report.windows[0].per_code['C']);self.assertEqual(report.drifting_codes(),[])

if __name__=='__main__':unittest.main()

import os, unittest
from profit_doctor.intake.workbook import semantic_map_workbook,generic_reconciliations,canonical_extract,intake_assessment
class TestIntelligentIntakeV224(unittest.TestCase):
 def setUp(self):
  self.s1=os.environ.get('PD_UWB1','/mnt/data/v223/scenario1.xlsx'); self.s2=os.environ.get('PD_UWB2','/mnt/data/v223/scenario2.xlsx')
 def test_semantic_columns_and_units(self):
  m={x['sheet']:x for x in semantic_map_workbook(self.s2)}
  ar={x['semantic']:x for x in m['AR Customer Ledger']['columns'] if x['semantic']}
  self.assertEqual(ar['metric.ar_balance']['unit'],'GBP'); self.assertEqual(ar['metric.debtor_days']['unit'],'DAYS'); self.assertGreater(m['AR Customer Ledger']['mapping_confidence'],.5)
 def test_canonical_handoff_without_invention(self):
  c=canonical_extract(self.s2)
  self.assertGreater(len(c['D04_AR']),20); self.assertGreater(len(c['D05_AP']),10); self.assertEqual(len(c['D11_WORKFORCE']),25); self.assertGreater(len(c['D16_OPERATIONS']),3)
  self.assertIn('metric.ar_balance',c['D04_AR'][0]); self.assertNotIn('invoice_id',c['D04_AR'][0])
 def test_generic_controls(self):
  r={x['control']:x for x in generic_reconciliations(self.s2)}
  self.assertEqual(r['AR_TO_TB']['status'],'FAIL'); self.assertEqual(r['AP_TO_TB']['status'],'FAIL')
  self.assertIn('INVENTORY_TO_SUPPORT',r); self.assertEqual(r['INVENTORY_TO_SUPPORT']['status'],'FAIL')
 def test_assessment_fail_closed(self):
  a=intake_assessment(self.s2)
  self.assertEqual(a['integrity_state'],'MATERIALLY_CONSTRAINED'); self.assertIn('D11_WORKFORCE',a['available_domains']); self.assertIn('D16_OPERATIONS',a['available_domains'])
  self.assertIn('AR_TO_TB',a['failed_controls'])
 def test_scenario1_bad_capacity_is_preserved_not_repaired(self):
  c=canonical_extract(self.s1)['D16_OPERATIONS']; vals=[x.get('metric.utilisation_pct') for x in c if x.get('metric.utilisation_pct') is not None]
  self.assertTrue(any(float(v)>100 for v in vals))
if __name__=='__main__': unittest.main()

import os, unittest
from profit_doctor.intake.bridge import execute_unknown_workbook
class TestUnknownWorkbookBridgeV225(unittest.TestCase):
 def setUp(self):
  self.s1=os.environ.get('PD_UWB1','/mnt/data/v225/scenario1.xlsx'); self.s2=os.environ.get('PD_UWB2','/mnt/data/v225/scenario2.xlsx')
 def test_scenario1_end_to_end(self):
  r=execute_unknown_workbook(self.s1)
  self.assertGreater(r['canonical']['pnl_rows'],30); self.assertGreater(r['canonical']['tb_rows'],20); self.assertEqual(r['canonical']['workforce_rows'],25)
  self.assertEqual(r['diagnostics']['total'],56); self.assertGreaterEqual(r['diagnostics']['completed'],5)
  self.assertTrue(any(x['control']=='AR_TO_TB' and x['status']=='FAIL' for x in r['controls']))
 def test_scenario2_end_to_end(self):
  r=execute_unknown_workbook(self.s2)
  self.assertEqual(r['diagnostics']['total'],56); self.assertGreaterEqual(r['diagnostics']['completed'],5)
  controls={x['control']:x['status'] for x in r['controls']}
  self.assertEqual(controls['AR_TO_TB'],'FAIL'); self.assertEqual(controls['AP_TO_TB'],'FAIL'); self.assertEqual(controls['INVENTORY_TO_SUPPORT'],'FAIL')
 def test_no_fake_invoice_level_handoff(self):
  r=execute_unknown_workbook(self.s2)
  # Aggregate AR/AP schedules must not unlock invoice-level customer payment diagnostics.
  e={x['test_id']:x for x in r['executions']}
  self.assertEqual(e['CUS-06']['execution_status'],'NOT_RUN')
  self.assertIn(e['WC-02']['execution_status'],('COMPLETED','NOT_RUN'))
if __name__=='__main__': unittest.main()

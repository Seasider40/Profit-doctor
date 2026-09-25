import os, unittest
from profit_doctor.intake.bridge import execute_unknown_workbook
class TestGranularityHandoffV226(unittest.TestCase):
 def setUp(self):
  self.s1=os.environ.get('PD_UWB1','/mnt/data/v225/scenario1.xlsx'); self.s2=os.environ.get('PD_UWB2','/mnt/data/v225/scenario2.xlsx')
 def test_s1_customer_summary_unlocks_without_fake_invoice(self):
  r=execute_unknown_workbook(self.s1); e={x['test_id']:x for x in r['executions']}
  self.assertEqual(e['CUS-01']['execution_status'],'COMPLETED'); self.assertEqual(e['CUS-02']['execution_status'],'COMPLETED'); self.assertEqual(e['CUS-07']['execution_status'],'COMPLETED')
  self.assertEqual(e['CUS-06']['execution_status'],'NOT_RUN'); self.assertEqual(r['aggregate_handoff']['capacity_rows_accepted'],0); self.assertGreater(r['aggregate_handoff']['capacity_rows_refused'],0); self.assertEqual(e['PEO-04']['execution_status'],'NOT_RUN')
 def test_s2_customer_supplier_capacity_unlocks(self):
  r=execute_unknown_workbook(self.s2); e={x['test_id']:x for x in r['executions']}
  for t in ('CUS-01','CUS-02','CUS-07','SUP-01','SUP-03','PEO-04'): self.assertEqual(e[t]['execution_status'],'COMPLETED',t)
  self.assertEqual(e['CUS-06']['execution_status'],'NOT_RUN'); self.assertGreater(r['aggregate_handoff']['capacity_rows_accepted'],0)
 def test_no_opportunity_from_discrepancy(self):
  r=execute_unknown_workbook(self.s2)
  # Reconciliation discrepancies remain control evidence, not monetised opportunity.
  self.assertTrue(all(x['status']=='FAIL' for x in r['controls'] if x['control'] in ('AR_TO_TB','AP_TO_TB','INVENTORY_TO_SUPPORT','DEBT_TO_SUPPORT')))
if __name__=='__main__': unittest.main()

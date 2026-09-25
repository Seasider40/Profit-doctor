import os,sqlite3,tempfile,unittest
from profit_doctor.intake.bridge import execute_unknown_workbook
from profit_doctor.api import get_priority_detail,get_diagnostic_detail
class TestInteractiveDrilldownV236(unittest.TestCase):
 def setUp(self):
  p=os.environ.get('PD_UWB2','/mnt/data/v227/scenario2.xlsx'); f=tempfile.NamedTemporaryFile(suffix='.db',delete=False); f.close(); self.r=execute_unknown_workbook(p,f.name); self.c=sqlite3.connect(f.name); self.c.row_factory=sqlite3.Row; self.client=self.c.execute('select client_id from engine_run where run_id=?',(self.r['run_id'],)).fetchone()['client_id']
 def tearDown(self): self.c.close()
 def test_priority_lineage(self):
  d=get_priority_detail(self.c,self.r['run_id'],self.client,'FINANCIAL_INTEGRITY')
  self.assertEqual(d.rank,1); self.assertGreater(len(d.supporting_evidence),0); self.assertTrue(all(x.test_id in d.diagnostic_ids for x in d.supporting_evidence)); self.assertGreater(len(d.recommended_actions),0); self.assertGreater(len(d.opportunities),0)
 def test_working_capital_drilldown(self):
  d=get_priority_detail(self.c,self.r['run_id'],self.client,'WORKING_CAPITAL'); self.assertTrue(any(x.test_id.startswith('WC-') for x in d.supporting_evidence)); self.assertIsNone(d.opportunities[0].expected)
 def test_diagnostic_core_question_and_signals(self):
  p=get_priority_detail(self.c,self.r['run_id'],self.client,'CUSTOMER_ECONOMICS'); tid=p.diagnostic_ids[0]; d=get_diagnostic_detail(self.c,self.r['run_id'],self.client,tid); self.assertTrue(d.core_question); self.assertEqual(d.test_id,tid); self.assertGreater(len(d.signals),0)
 def test_wrong_client_fails_closed(self):
  with self.assertRaises(ValueError): get_priority_detail(self.c,self.r['run_id'],'wrong','WORKING_CAPITAL')
  with self.assertRaises(ValueError): get_diagnostic_detail(self.c,self.r['run_id'],'wrong','WC-06')
 def test_unknown_objects_refused(self):
  with self.assertRaises(KeyError): get_priority_detail(self.c,self.r['run_id'],self.client,'NOT_A_THEME')
  with self.assertRaises(KeyError): get_diagnostic_detail(self.c,self.r['run_id'],self.client,'NOT-A-TEST')
if __name__=='__main__': unittest.main()

import os,tempfile,sqlite3,unittest
from profit_doctor.intake.bridge import execute_unknown_workbook
from profit_doctor.management.output_spec import build_management_output,SECTIONS
class TestManagementOutputSpecV233(unittest.TestCase):
 def setUp(self):
  self.s1=os.environ.get('PD_UWB1','/mnt/data/v227/scenario1.xlsx'); self.s2=os.environ.get('PD_UWB2','/mnt/data/v227/scenario2.xlsx')
 def run_case(self,p):
  f=tempfile.NamedTemporaryFile(suffix='.db',delete=False); f.close(); r=execute_unknown_workbook(p,f.name); c=sqlite3.connect(f.name); c.row_factory=sqlite3.Row; return r,c
 def test_contract_has_all_sections_and_compact_attention(self):
  r,c=self.run_case(self.s2); o=build_management_output(c,r['run_id'],c.execute('select client_id from engine_run where run_id=?',(r['run_id'],)).fetchone()['client_id'])
  self.assertEqual(o['section_order'],list(SECTIONS)); self.assertGreaterEqual(len(o['management_attention']),3); self.assertLessEqual(len(o['management_attention']),7); c.close()
 def test_no_universal_health_score(self):
  r,c=self.run_case(self.s2); client=c.execute('select client_id from engine_run where run_id=?',(r['run_id'],)).fetchone()['client_id']; o=build_management_output(c,r['run_id'],client)
  self.assertNotIn('score',o['executive_health_check']); self.assertIn('not a universal score',o['executive_health_check']['guardrail']); c.close()
 def test_profit_cash_never_combined(self):
  r,c=self.run_case(self.s2); client=c.execute('select client_id from engine_run where run_id=?',(r['run_id'],)).fetchone()['client_id']; o=build_management_output(c,r['run_id'],client)
  self.assertIsNone(o['opportunity_register']['portfolio_headline']['combined_total']); self.assertIn('non-additive',o['opportunity_register']['portfolio_headline']['rule']); c.close()
 def test_control_residual_remains_control_evidence(self):
  r,c=self.run_case(self.s2); client=c.execute('select client_id from engine_run where run_id=?',(r['run_id'],)).fetchone()['client_id']; o=build_management_output(c,r['run_id'],client)
  x=next(x for x in o['opportunity_register']['items'] if x['theme']=='FINANCIAL_INTEGRITY'); self.assertIsNone(x['expected']); self.assertIn('not losses',x['limitation']); c.close()
 def test_benefit_not_inferred_from_opportunity(self):
  r,c=self.run_case(self.s1); client=c.execute('select client_id from engine_run where run_id=?',(r['run_id'],)).fetchone()['client_id']; o=build_management_output(c,r['run_id'],client)
  self.assertIsNone(o['benefit_progress']['realised']); self.assertIn('not inferred',o['benefit_progress']['rule']); c.close()
 def test_wrong_client_fails_closed(self):
  r,c=self.run_case(self.s2)
  with self.assertRaises(ValueError): build_management_output(c,r['run_id'],'wrong-client')
  c.close()
if __name__=='__main__': unittest.main()

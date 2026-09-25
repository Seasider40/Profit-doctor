import os,tempfile,sqlite3,unittest
from profit_doctor.intake.bridge import execute_unknown_workbook
class TestV228(unittest.TestCase):
 def setUp(self):
  self.s1=os.environ.get('PD_UWB1','/mnt/data/v228/scenario1.xlsx'); self.s2=os.environ.get('PD_UWB2','/mnt/data/v228/scenario2.xlsx')
 def run_case(self,p):
  f=tempfile.NamedTemporaryFile(suffix='.db',delete=False); f.close(); r=execute_unknown_workbook(p,f.name); c=sqlite3.connect(f.name); c.row_factory=sqlite3.Row; return r,c
 def test_register_matches_attention(self):
  r,c=self.run_case(self.s2); self.assertEqual(r['opportunity_register']['count'],r['management_attention']['selected']); self.assertEqual(c.execute('select count(*) n from management_action_candidate where run_id=?',(r['run_id'],)).fetchone()['n'],r['management_attention']['selected']); c.close()
 def test_control_residual_not_opportunity(self):
  r,c=self.run_case(self.s2); x=next(x for x in r['opportunity_register']['items'] if x['theme']=='FINANCIAL_INTEGRITY'); self.assertIsNone(x['theoretical_amount']); self.assertIsNone(x['addressable_amount']); self.assertIsNone(x['expected_amount']); self.assertIn('not losses',x['limitation']); c.close()
 def test_capacity_not_saving(self):
  r,c=self.run_case(self.s2); x=next(x for x in r['opportunity_register']['items'] if x['theme']=='CAPACITY_CONSTRAINT'); self.assertIsNone(x['expected_amount']); self.assertIn('not a saving',x['limitation']); c.close()
 def test_bad_capacity_data_is_action_not_money(self):
  r,c=self.run_case(self.s1); x=next(x for x in r['opportunity_register']['items'] if x['theme']=='DATA_CAPACITY'); self.assertEqual(x['economic_state'],'EVIDENCE_REQUIRED'); self.assertIsNone(x['theoretical_amount']); c.close()
 def test_no_priority_gets_addressable_without_qualification(self):
  r,c=self.run_case(self.s2); self.assertEqual(r['opportunity_register']['quantified_supported'],0); self.assertTrue(all(x['addressable_amount'] is None for x in r['opportunity_register']['items'])); c.close()
if __name__=='__main__': unittest.main()

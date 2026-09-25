import os, tempfile, sqlite3, unittest
from profit_doctor.intake.bridge import execute_unknown_workbook
class TestManagementAttentionV227(unittest.TestCase):
 def setUp(self):
  self.s1=os.environ.get('PD_UWB1','/mnt/data/v227/scenario1.xlsx'); self.s2=os.environ.get('PD_UWB2','/mnt/data/v227/scenario2.xlsx')
 def run_case(self,p):
  f=tempfile.NamedTemporaryFile(suffix='.db',delete=False); f.close(); r=execute_unknown_workbook(p,f.name); c=sqlite3.connect(f.name); c.row_factory=sqlite3.Row; return r,c
 def test_s1_compacts_to_management_agenda_and_flags_bad_capacity_data(self):
  r,c=self.run_case(self.s1); a=r['management_attention']; self.assertGreaterEqual(a['selected'],3); self.assertLessEqual(a['selected'],7)
  themes={x['theme'] for x in a['items']}; self.assertIn('FINANCIAL_INTEGRITY',themes); self.assertIn('CUSTOMER_ECONOMICS',themes); self.assertIn('DATA_CAPACITY',themes)
  self.assertEqual(c.execute('select count(*) n from fd_review_queue where run_id=?',(r['run_id'],)).fetchone()['n'],a['selected']); c.close()
 def test_s2_compacts_duplicates_into_distinct_fd_themes(self):
  r,c=self.run_case(self.s2); a=r['management_attention']; self.assertGreaterEqual(a['selected'],3); self.assertLessEqual(a['selected'],7)
  themes=[x['theme'] for x in a['items']]; self.assertEqual(len(themes),len(set(themes)))
  for t in ('FINANCIAL_INTEGRITY','CUSTOMER_ECONOMICS','SUPPLIER_DEPENDENCY','CAPACITY_CONSTRAINT'): self.assertIn(t,themes)
  integ=next(x for x in a['items'] if x['theme']=='FINANCIAL_INTEGRITY'); self.assertIn('not assumed losses',integ['rationale']); self.assertGreaterEqual(integ['evidence_count'],4); c.close()
 def test_attention_does_not_create_opportunity_value(self):
  r,c=self.run_case(self.s2)
  # Attention compression is narrative/decision prioritisation only.
  for x in r['management_attention']['items']: self.assertIn('No causal or monetised opportunity',x['limitation'])
  c.close()
 def test_priority_not_raw_pound_sort(self):
  r,c=self.run_case(self.s2); items=r['management_attention']['items']
  self.assertEqual(items[0]['theme'],'FINANCIAL_INTEGRITY'); c.close()
if __name__=='__main__': unittest.main()

import tempfile,unittest
from pathlib import Path
from profit_doctor.qualification_level3 import build_level3_case
class Level3Qualification(unittest.TestCase):
 def run_case(self,d): return build_level3_case(Path(d)/'l3.db',Path(__file__).parent/'fixtures'/'northstar',Path(d)/'store')
 def test_complete_56_test_estate_executes(self):
  with tempfile.TemporaryDirectory() as d:
   c,s=self.run_case(d); self.assertEqual(s['diagnostics_total'],56); self.assertEqual(s['completed'],56); self.assertEqual(s['not_run'],[]); c.close()
 def test_level3_evidence_activates_key_domains(self):
  with tempfile.TemporaryDirectory() as d:
   c,s=self.run_case(d)
   for tid in ['CUS-06','PEO-04','SUP-05','WC-07','FCST-04','RISK-04']:
    r=c.execute('select * from test_execution where run_id=? and test_id=?',(s['run_id'],tid)).fetchone(); self.assertEqual(r['execution_status'],'COMPLETED'); self.assertGreater(r['signal_count'],0)
   c.close()
 def test_guardrails_survive_rich_evidence(self):
  with tempfile.TemporaryDirectory() as d:
   c,s=self.run_case(d); ev=' '.join((r['evidence_summary'] or '') for r in c.execute('select * from signal where run_id=?',(s['run_id'],)))
   self.assertIn('Cash release is not profit',ev); self.assertIn('not probabilities or predictions',ev); self.assertIn('not proof of duplicate payment',ev); c.close()
if __name__=='__main__':unittest.main()

import tempfile, unittest
from pathlib import Path
from profit_doctor.core.db import connect
from profit_doctor.crm import ingest_crm, analyse_crm
from profit_doctor.qualification_level3 import build_level3_case

class CRMV240(unittest.TestCase):
 def base(self,d):
  c=connect(Path(d)/'x.db'); c.execute("insert into client values ('c','Client','GBP','SERVICES','t')"); c.execute("insert into engine_run values ('r','c','Q','t',null,'RUNNING',null,'r','2.40')"); c.commit(); return c
 def test_canonical_crm_and_guardrails(self):
  with tempfile.TemporaryDirectory() as d:
   c=self.base(d); ingest_crm(c,'c',[{'source_opportunity_key':'1','opportunity_name':'Deal','created_date':'2026-01-01','expected_close_date':'2026-08-01','stage':'PROPOSAL','status':'OPEN','amount':'100000','probability_pct':'60'}]); x=analyse_crm(c,'r','c'); self.assertTrue(x['available']); self.assertIn('Weighted pipeline is not a forecast.',x['guardrails']); self.assertEqual(x['metrics'][0]['metric_code'],'OPEN_PIPELINE_VALUE'); c.close()
 def test_invalid_probability_fails_closed(self):
  with tempfile.TemporaryDirectory() as d:
   c=self.base(d)
   with self.assertRaises(ValueError): ingest_crm(c,'c',[{'source_opportunity_key':'1','opportunity_name':'Deal','created_date':'2026-01-01','stage':'X','status':'OPEN','amount':'1','probability_pct':'120'}])
   c.close()
 def test_closed_requires_close_date(self):
  with tempfile.TemporaryDirectory() as d:
   c=self.base(d)
   with self.assertRaises(ValueError): ingest_crm(c,'c',[{'source_opportunity_key':'1','opportunity_name':'Deal','created_date':'2026-01-01','stage':'WON','status':'WON','amount':'1'}])
   c.close()
 def test_level3_now_contains_qualified_d15(self):
  with tempfile.TemporaryDirectory() as d:
   c,s=build_level3_case(Path(d)/'l3.db',Path(__file__).parent/'fixtures'/'northstar',Path(d)/'store'); self.assertTrue(s['crm']['available']); self.assertEqual(s['diagnostics_total'],56); self.assertEqual(s['completed'],56); self.assertGreaterEqual(len(s['crm']['metrics']),3); c.close()
 def test_tenant_isolation(self):
  with tempfile.TemporaryDirectory() as d:
   c=self.base(d); c.execute("insert into client values ('c2','Other','GBP','SERVICES','t')"); c.execute("insert into engine_run values ('r2','c2','Q','t',null,'RUNNING',null,'r2','2.40')"); c.commit(); ingest_crm(c,'c',[{'source_opportunity_key':'1','opportunity_name':'Deal','created_date':'2026-01-01','stage':'X','status':'OPEN','amount':'100'}]); self.assertFalse(analyse_crm(c,'r2','c2')['available']); c.close()
if __name__=='__main__': unittest.main()

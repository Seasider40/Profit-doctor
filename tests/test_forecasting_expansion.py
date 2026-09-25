import tempfile, unittest
from datetime import datetime, timezone
from profit_doctor.core.db import connect
from profit_doctor.diagnostic.engine import seed_registry, forecasting_diagnostics

def now(): return datetime.now(timezone.utc).isoformat()
class ForecastTests(unittest.TestCase):
 def setUp(self):
  self.f=tempfile.NamedTemporaryFile(suffix='.db',delete=False); self.f.close(); self.c=connect(self.f.name); self.client='c'; self.run='r'
  self.c.execute('INSERT INTO client VALUES (?,?,?,?,?)',(self.client,'PlanCo','GBP','SERVICES',now())); self.c.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(self.run,self.client,'TEST',now(),None,'RUNNING',None,None,'2.2')); seed_registry(self.c)
  self.c.execute('INSERT INTO plan_version VALUES (?,?,?,?,?,?,?,?,?)',('pv1',self.client,'BUDGET','FY26 Original','2025-12-01','2026-01-01','2026-12-31','ACTIVE','board approved'))
  for i,(m,p,a) in enumerate([('2026-01',100,90),('2026-02',100,110),('2026-03',100,80)]):
   self.c.execute('INSERT INTO plan_line VALUES (?,?,?,?,?,?,?,?,?,?)',(f'pl{i}','pv1',self.client,m,'REVENUE',None,None,str(p),'GBP','approved budget'))
   self.c.execute('INSERT INTO actual_metric VALUES (?,?,?,?,?,?,?)',(f'a{i}',self.client,m,'REVENUE',str(a),'GBP','accounts'))
   self.c.execute('INSERT INTO forecast_vintage VALUES (?,?,?,?,?,?,?,?)',(f'fv{i}',self.client,'2025-12-15',m,'REVENUE',str(p),'GBP','forecast'))
  self.c.execute('INSERT INTO kpi_observation VALUES (?,?,?,?,?,?,?,?,?,?)',('k1',self.client,'2026-03','UTIL','Utilisation','78','PCT','LEADING','REVENUE','ops'))
  self.c.commit()
 def test_registry_complete(self):
  ids={r['test_id'] for r in self.c.execute("SELECT * FROM test_registry WHERE test_id LIKE 'FCST-%'")}; self.assertEqual(ids,{f'FCST-0{i}' for i in range(1,5)})
 def test_variance_not_explanation(self):
  forecasting_diagnostics(self.c,self.run,self.client); s=self.c.execute("SELECT * FROM signal WHERE test_id='FCST-01'").fetchone(); self.assertIn('not an explanation',s['evidence_summary'])
 def test_forecast_accuracy_not_certainty(self):
  forecasting_diagnostics(self.c,self.run,self.client); ss=self.c.execute("SELECT * FROM signal WHERE test_id='FCST-02'").fetchall(); self.assertTrue(any('not a future prediction' in x['evidence_summary'] or 'does not establish future certainty' in x['evidence_summary'] for x in ss))
 def test_kpi_does_not_claim_causality(self):
  forecasting_diagnostics(self.c,self.run,self.client); s=self.c.execute("SELECT * FROM signal WHERE test_id='FCST-03'").fetchone(); self.assertIn('does not by itself prove causality',s['evidence_summary'])
 def test_scenario_not_prediction_or_probability(self):
  forecasting_diagnostics(self.c,self.run,self.client); s=self.c.execute("SELECT * FROM signal WHERE test_id='FCST-04'").fetchone(); self.assertIn('not probabilities or predictions',s['evidence_summary'])
 def test_original_plan_preserved(self):
  forecasting_diagnostics(self.c,self.run,self.client); self.assertEqual(self.c.execute("SELECT COUNT(*) n FROM plan_version WHERE plan_version_id='pv1'").fetchone()['n'],1)
if __name__=='__main__': unittest.main()

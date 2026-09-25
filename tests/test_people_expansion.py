import tempfile, unittest
from datetime import datetime, timezone
from profit_doctor.core.db import connect
from profit_doctor.diagnostic.engine import seed_registry, workforce_diagnostics

def now(): return datetime.now(timezone.utc).isoformat()
class PeopleExpansionTests(unittest.TestCase):
 def setUp(self):
  self.f=tempfile.NamedTemporaryFile(suffix='.db',delete=False); self.f.close(); self.c=connect(self.f.name)
  self.client='c'; self.run='r'; self.c.execute('INSERT INTO client VALUES (?,?,?,?,?)',(self.client,'PeopleCo','GBP','PROFESSIONAL_SERVICES',now())); self.c.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(self.run,self.client,'TEST',now(),None,'RUNNING',None,None,'1.9')); seed_registry(self.c)
  for tid in ['PEO-01','PEO-02','PEO-03','PEO-04','PEO-05']:
   self.c.execute('INSERT INTO test_eligibility VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(tid,self.run,self.client,tid,'APPLICABLE','FULL','D11_WORKFORCE_SNAPSHOT','Reliable','Reliable','100',None,now()))
  rows=[('w1','E1','Sales','AE','1','50000','8000','12000','0','0','1600','1200'),('w2','E2','Delivery','Consultant','1','45000','7000','0','2000','0','1600','1500')]
  for x in rows:self.c.execute('INSERT INTO workforce_snapshot VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(x[0],self.client,'2026-09-30',*x[1:], 'synthetic payroll/capacity evidence'))
  self.c.commit()
 def test_registry_has_all_people_tests(self):
  ids={r['test_id'] for r in self.c.execute("SELECT * FROM test_registry WHERE test_id LIKE 'PEO-%'")}; self.assertEqual(ids,{f'PEO-0{i}' for i in range(1,6)})
 def test_people_cost_includes_variable_pay(self):
  workforce_diagnostics(self.c,self.run,self.client); s=self.c.execute("SELECT * FROM signal WHERE test_id='PEO-01' AND signal_type='TOTAL_PEOPLE_COST'").fetchone(); self.assertEqual(s['observed_value'],'124000')
 def test_capacity_is_not_money(self):
  workforce_diagnostics(self.c,self.run,self.client); s=self.c.execute("SELECT * FROM signal WHERE test_id='PEO-05'").fetchone(); self.assertEqual(s['unit'],'HOURS'); self.assertIn('financial benefit remains £0',s['evidence_summary'])
 def test_department_does_not_rank_productivity(self):
  workforce_diagnostics(self.c,self.run,self.client); s=self.c.execute("SELECT * FROM signal WHERE test_id='PEO-03' LIMIT 1").fetchone(); self.assertIn('does not rank departments',s['evidence_summary'])
 def test_no_capacity_evidence_refuses_utilisation(self):
  self.c.execute('UPDATE workforce_snapshot SET practical_capacity_hours=NULL, utilised_hours=NULL'); self.c.commit(); workforce_diagnostics(self.c,self.run,self.client); x=self.c.execute("SELECT * FROM test_execution WHERE test_id='PEO-04' ORDER BY completed_at DESC LIMIT 1").fetchone(); self.assertEqual(x['execution_status'],'NOT_RUN'); self.assertIn('utilisation refused',x['limitation'])
 def test_commission_structure_does_not_claim_roi(self):
  self.c.execute("INSERT INTO commission_plan VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",('cp',self.client,'AE Plan','COMMISSION','REVENUE','0.05',None,None,'Sales','AE','synthetic plan',1)); self.c.commit(); workforce_diagnostics(self.c,self.run,self.client); s=self.c.execute("SELECT * FROM signal WHERE test_id='PEO-01' AND signal_type='COMMISSION_PLAN_STRUCTURE'").fetchone(); self.assertIn('do not by themselves prove incentive effectiveness',s['evidence_summary'])
if __name__=='__main__': unittest.main()

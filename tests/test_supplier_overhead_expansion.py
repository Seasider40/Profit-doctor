import tempfile, unittest
from datetime import datetime, timezone
from profit_doctor.core.db import connect
from profit_doctor.diagnostic.engine import seed_registry, supplier_overhead_diagnostics

def now(): return datetime.now(timezone.utc).isoformat()
class SupplierTests(unittest.TestCase):
 def setUp(self):
  self.f=tempfile.NamedTemporaryFile(suffix='.db',delete=False); self.f.close(); self.c=connect(self.f.name); self.client='c'; self.run='r'
  self.c.execute('INSERT INTO client VALUES (?,?,?,?,?)',(self.client,'SupplyCo','GBP','PRODUCT_DISTRIBUTION',now())); self.c.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(self.run,self.client,'TEST',now(),None,'RUNNING',None,None,'2.0')); seed_registry(self.c)
  for tid in [f'SUP-0{i}' for i in range(1,7)]: self.c.execute('INSERT INTO test_eligibility VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(tid,self.run,self.client,tid,'APPLICABLE','FULL','SUPPLIER_EVIDENCE','Reliable','Reliable','100',None,now()))
  self.c.execute('INSERT INTO supplier_master VALUES (?,?,?,?,?,?,?,?)',('S1',self.client,'Critical Parts','Materials','CRITICAL',45,1,'contract/master evidence'))
  purchases=[('p1','2026-01-10','S1','Materials','A','Part A','100','1000','10','INV1',None),('p2','2026-09-10','S1','Materials','A','Part A','100','1200','12','INV2',None),('p3','2026-09-15','S2','Materials','B','Part B','50','500','10','INV3',None),('p4','2026-09-15','S2','Materials','B','Part B','50','500','10','INV3',None)]
  for x in purchases:self.c.execute('INSERT INTO purchase_transaction VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',(x[0],self.client,*x[1:],'synthetic purchase evidence'))
  overhead=[('o1','2026-01-01','S3','Software','CRM','1000','SW1','CRM'),('o2','2026-02-01','S3','Software','CRM','1000','SW2','CRM'),('o3','2026-08-01','S3','Software','CRM','1600','SW3','CRM'),('o4','2026-09-01','S3','Software','CRM','1600','SW4','CRM')]
  for x in overhead:self.c.execute('INSERT INTO overhead_transaction VALUES (?,?,?,?,?,?,?,?,?,?)',(x[0],self.client,*x[1:],'synthetic overhead evidence'))
  self.c.commit()
 def test_registry_complete(self):
  ids={r['test_id'] for r in self.c.execute("SELECT * FROM test_registry WHERE test_id LIKE 'SUP-%'")}; self.assertEqual(ids,{f'SUP-0{i}' for i in range(1,7)})
 def test_high_spend_not_overspend(self):
  supplier_overhead_diagnostics(self.c,self.run,self.client); s=self.c.execute("SELECT * FROM signal WHERE test_id='SUP-01' ORDER BY CAST(observed_value AS REAL) DESC LIMIT 1").fetchone(); self.assertIn('not evidence of overspend',s['evidence_summary'])
 def test_ppv_not_recoverable(self):
  supplier_overhead_diagnostics(self.c,self.run,self.client); s=self.c.execute("SELECT * FROM signal WHERE test_id='SUP-02' LIMIT 1").fetchone(); self.assertIn('not supplier cause, recoverability',s['evidence_summary'])
 def test_dependency_no_expected_loss(self):
  supplier_overhead_diagnostics(self.c,self.run,self.client); s=self.c.execute("SELECT * FROM signal WHERE test_id='SUP-03' AND entity_id='S1'").fetchone(); self.assertIn('no disruption probability or expected loss',s['evidence_summary'])
 def test_cost_drift_not_waste(self):
  supplier_overhead_diagnostics(self.c,self.run,self.client); s=self.c.execute("SELECT * FROM signal WHERE test_id='SUP-04' LIMIT 1").fetchone(); self.assertIn('not, by itself, waste',s['evidence_summary'])
 def test_duplicate_not_error(self):
  supplier_overhead_diagnostics(self.c,self.run,self.client); s=self.c.execute("SELECT * FROM signal WHERE test_id='SUP-05' LIMIT 1").fetchone(); self.assertIn('not proof of duplicate payment',s['evidence_summary'])
 def test_candidate_unquantified(self):
  supplier_overhead_diagnostics(self.c,self.run,self.client); s=self.c.execute("SELECT * FROM signal WHERE test_id='SUP-06' LIMIT 1").fetchone(); self.assertIsNone(s['observed_value']); self.assertIn('remain unquantified',s['evidence_summary'])
if __name__=='__main__': unittest.main()

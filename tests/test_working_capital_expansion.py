import tempfile, unittest
from datetime import datetime, timezone
from profit_doctor.core.db import connect
from profit_doctor.diagnostic.engine import seed_registry, working_capital_diagnostics
from profit_doctor.calc.primitive_engine import seed_registry as seed_primitives

def now(): return datetime.now(timezone.utc).isoformat()
class WCTests(unittest.TestCase):
 def setUp(self):
  self.f=tempfile.NamedTemporaryFile(suffix='.db',delete=False); self.f.close(); self.c=connect(self.f.name); self.client='c'; self.run='r'
  self.c.execute('INSERT INTO client VALUES (?,?,?,?,?)',(self.client,'CashCo','GBP','PRODUCT_DISTRIBUTION',now())); self.c.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(self.run,self.client,'TEST',now(),None,'RUNNING',None,None,'2.1')); seed_registry(self.c); seed_primitives(self.c)
  # Direct primitive evidence keeps the test focused on diagnostics.
  vals=[('WC_DSO','52','DAYS'),('WC_DIO','70','DAYS'),('WC_DPO','45','DAYS'),('WC_CCC','77','DAYS'),('BS_ACCOUNTS_RECEIVABLE','250000','GBP'),('AR_LEDGER_OUTSTANDING','245000','GBP'),('AR_OVERDUE_OUTSTANDING','90000','GBP'),('BS_ACCOUNTS_PAYABLE','180000','GBP'),('AP_LEDGER_OUTSTANDING','175000','GBP'),('AP_OVERDUE_OUTSTANDING','30000','GBP'),('BS_INVENTORY','400000','GBP'),('AVAILABLE_CASH','120000','GBP')]
  for i,(p,v,u) in enumerate(vals): self.c.execute('INSERT INTO primitive_result VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',(f'pr{i}',self.run,self.client,p,'M',None,None,None,None,v,u,'VALID',now()))
  self.c.commit()
 def test_registry_complete(self):
  ids={r['test_id'] for r in self.c.execute("SELECT * FROM test_registry WHERE test_id LIKE 'WC-%'")}; self.assertEqual(ids,{f'WC-0{i}' for i in range(1,8)})
 def test_payables_delay_not_automatic_opportunity(self):
  working_capital_diagnostics(self.c,self.run,self.client); s=self.c.execute("SELECT * FROM signal WHERE test_id='WC-03' LIMIT 1").fetchone(); self.assertIn('not automatically a cash opportunity',s['evidence_summary'])
 def test_inventory_not_equal_releasable_cash(self):
  working_capital_diagnostics(self.c,self.run,self.client); s=self.c.execute("SELECT * FROM signal WHERE test_id='WC-04' AND signal_type='BS_INVENTORY'").fetchone(); self.assertIn('not the same as safely releasable cash',s['evidence_summary'])
 def test_cash_not_liquidity_without_facility(self):
  working_capital_diagnostics(self.c,self.run,self.client); s=self.c.execute("SELECT * FROM signal WHERE test_id='WC-05'").fetchone(); self.assertIn('not Available Liquidity',s['evidence_summary'])
 def test_release_candidate_unquantified_and_not_profit(self):
  working_capital_diagnostics(self.c,self.run,self.client); s=self.c.execute("SELECT * FROM signal WHERE test_id='WC-06' LIMIT 1").fetchone(); self.assertIsNone(s['observed_value']); self.assertIn('Cash release is not profit',s['evidence_summary'])
 def test_optimisation_does_not_double_count_profit_cash(self):
  working_capital_diagnostics(self.c,self.run,self.client); s=self.c.execute("SELECT * FROM signal WHERE test_id='WC-07' LIMIT 1").fetchone(); self.assertIsNone(s['observed_value']); self.assertIn('must not be double counted',s['evidence_summary'])
if __name__=='__main__': unittest.main()

import tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path
from profit_doctor.core.db import connect
from profit_doctor.diagnostic.engine import seed_registry, working_capital_diagnostics
from profit_doctor.calc.primitive_engine import seed_registry as seed_primitives
from profit_doctor.persistence import Base,Client,EngineRun,DatabaseConfig,build_engine,session_factory,session_scope
from profit_doctor.persistence.diagnostic_migration import migrate_working_capital,canonical_batch_legacy,canonical_batch_v2,BATCH4_TESTS
from profit_doctor.persistence.models import Signal

def now(): return datetime.now(timezone.utc).isoformat()

class WorkingCapitalMigration(unittest.TestCase):
 def legacy(self,d):
  con=connect(Path(d)/'legacy.db'); c='c'; r='r'; t=now()
  con.execute('INSERT INTO client VALUES (?,?,?,?,?)',(c,'Cash Migration Co','GBP','PRODUCT_DISTRIBUTION',t))
  con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(r,c,'TEST',t,None,'RUNNING',None,r,'2.13')); seed_registry(con); seed_primitives(con)
  vals=[('WC_DSO','52','DAYS'),('WC_DIO','70','DAYS'),('WC_DPO','45','DAYS'),('WC_CCC','77','DAYS'),('BS_ACCOUNTS_RECEIVABLE','250000','GBP'),('AR_LEDGER_OUTSTANDING','245000','GBP'),('AR_OVERDUE_OUTSTANDING','90000','GBP'),('BS_ACCOUNTS_PAYABLE','180000','GBP'),('AP_LEDGER_OUTSTANDING','175000','GBP'),('AP_OVERDUE_OUTSTANDING','30000','GBP'),('BS_INVENTORY','400000','GBP'),('AVAILABLE_CASH','120000','GBP')]
  for i,(p,v,u) in enumerate(vals): con.execute('INSERT INTO primitive_result VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',(f'pr{i}',r,c,p,'M',None,None,None,None,v,u,'VALID',t))
  con.commit(); working_capital_diagnostics(con,r,c); return con,c,r
 def target(self,d,c,r):
  e=build_engine(DatabaseConfig(f'sqlite+pysqlite:///{Path(d)/"new.db"}')); Base.metadata.create_all(e); F=session_factory(e); t=now()
  with session_scope(F) as s:
   s.add(Client(client_id=c,client_name='Cash Migration Co',base_currency='GBP',business_model='PRODUCT_DISTRIBUTION',created_at=t))
   s.add(EngineRun(run_id=r,client_id=c,run_type='TEST',started_at=t,status='RUNNING',baseline_run_id=r,engine_version='2.13'))
  return e,F
 def test_all_7_execution_contracts_are_lossless(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=self.legacy(d); e,F=self.target(d,c,r)
   with session_scope(F) as s: counts=migrate_working_capital(con,s,r,c)
   self.assertEqual(counts['executions'],7); self.assertGreater(counts['signals'],0); self.assertGreater(counts['lineage'],0)
   with F() as s: self.assertEqual(canonical_batch_legacy(con,r,c,BATCH4_TESTS),canonical_batch_v2(s,r,c,BATCH4_TESTS))
   e.dispose(); con.close()
 def test_working_capital_economics_exact(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=self.legacy(d); e,F=self.target(d,c,r)
   with session_scope(F) as s: migrate_working_capital(con,s,r,c)
   q=','.join('?' for _ in BATCH4_TESTS)
   old={tuple(x) for x in con.execute(f"SELECT test_id,signal_type,entity_type,entity_id,observed_value,comparison_value,variance_value,unit,evidence_summary FROM signal WHERE run_id=? AND test_id IN ({q})",(r,*BATCH4_TESTS)).fetchall()}
   with F() as s: new={(x.test_id,x.signal_type,x.entity_type,x.entity_id,x.observed_value,x.comparison_value,x.variance_value,x.unit,x.evidence_summary) for x in s.query(Signal).filter(Signal.run_id==r,Signal.test_id.in_(BATCH4_TESTS)).all()}
   self.assertEqual(old,new); e.dispose(); con.close()
 def test_cash_guardrails_survive_migration(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=self.legacy(d); e,F=self.target(d,c,r)
   with session_scope(F) as s: migrate_working_capital(con,s,r,c)
   with F() as s:
    inv=s.query(Signal).filter(Signal.run_id==r,Signal.test_id=='WC-04',Signal.signal_type=='BS_INVENTORY').first(); self.assertIn('not the same as safely releasable cash',inv.evidence_summary)
    cash=s.query(Signal).filter(Signal.run_id==r,Signal.test_id=='WC-05').first(); self.assertIn('not Available Liquidity',cash.evidence_summary)
    rel=s.query(Signal).filter(Signal.run_id==r,Signal.test_id=='WC-06').first(); self.assertIsNone(rel.observed_value); self.assertIn('Cash release is not profit',rel.evidence_summary)
    opt=s.query(Signal).filter(Signal.run_id==r,Signal.test_id=='WC-07').first(); self.assertIsNone(opt.observed_value); self.assertIn('must not be double counted',opt.evidence_summary)
   e.dispose(); con.close()
 def test_scope_refuses_cross_client(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=self.legacy(d); e,F=self.target(d,c,r)
   with session_scope(F) as s: s.add(Client(client_id='evil',client_name='Other',base_currency='GBP',created_at=now()))
   with self.assertRaises(ValueError):
    with session_scope(F) as s: migrate_working_capital(con,s,r,'evil')
   e.dispose(); con.close()
if __name__=='__main__': unittest.main()

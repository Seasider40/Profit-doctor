import tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path
from profit_doctor.core.db import connect
from profit_doctor.diagnostic.engine import seed_registry, forecasting_diagnostics, risk_control_diagnostics
from profit_doctor.persistence import Base,Client,EngineRun,DatabaseConfig,build_engine,session_factory,session_scope
from profit_doctor.persistence.diagnostic_migration import migrate_fcst_risk,canonical_batch_legacy,canonical_batch_v2,BATCH5_TESTS
from profit_doctor.persistence.models import Signal

def now(): return datetime.now(timezone.utc).isoformat()

class FinalDiagnosticMigration(unittest.TestCase):
 def legacy(self,d):
  con=connect(Path(d)/'legacy.db'); c='c'; r='r'; t=now()
  con.execute('INSERT INTO client VALUES (?,?,?,?,?)',(c,'Final Migration Co','GBP','SERVICES',t))
  con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(r,c,'TEST',t,None,'RUNNING',None,r,'2.14')); seed_registry(con)
  con.execute('INSERT INTO plan_version VALUES (?,?,?,?,?,?,?,?,?)',('pv1',c,'BUDGET','FY26 Original','2025-12-01','2026-01-01','2026-12-31','ACTIVE','board approved'))
  for i,(m,p,a) in enumerate([('2026-01',100,90),('2026-02',100,110),('2026-03',100,80)]):
   con.execute('INSERT INTO plan_line VALUES (?,?,?,?,?,?,?,?,?,?)',(f'pl{i}','pv1',c,m,'REVENUE',None,None,str(p),'GBP','approved budget'))
   con.execute('INSERT INTO actual_metric VALUES (?,?,?,?,?,?,?)',(f'a{i}',c,m,'REVENUE',str(a),'GBP','accounts'))
   con.execute('INSERT INTO forecast_vintage VALUES (?,?,?,?,?,?,?,?)',(f'fv{i}',c,'2025-12-15',m,'REVENUE',str(p),'GBP','forecast'))
  con.execute('INSERT INTO kpi_observation VALUES (?,?,?,?,?,?,?,?,?,?)',('k1',c,'2026-03','UTIL','Utilisation','78','PCT','LEADING','REVENUE','ops'))
  con.execute('INSERT INTO financial_integrity VALUES (?,?,?,?,?,?,?,?)',('i1',r,c,'D03_TB_GL','MATERIALLY_CONSTRAINED','TB does not balance','Investigate',t))
  con.execute('INSERT INTO control_exception VALUES (?,?,?,?,?,?,?,?,?,?)',('x1',c,'2026-09-01','AP','DUPLICATE_LOOKING','Two invoices share amount/reference','25000','dup1','AP review','OPEN'))
  con.execute('INSERT INTO financial_exposure_evidence VALUES (?,?,?,?,?,?,?,?,?)',('e1',c,'2026-09-01','SUPPLIER_DEPENDENCY','Single source component','900000','35','NONE','supplier contract'))
  con.commit(); forecasting_diagnostics(con,r,c); risk_control_diagnostics(con,r,c); return con,c,r
 def target(self,d,c,r):
  e=build_engine(DatabaseConfig(f'sqlite+pysqlite:///{Path(d)/"new.db"}')); Base.metadata.create_all(e); F=session_factory(e); t=now()
  with session_scope(F) as s:
   s.add(Client(client_id=c,client_name='Final Migration Co',base_currency='GBP',business_model='SERVICES',created_at=t))
   s.add(EngineRun(run_id=r,client_id=c,run_type='TEST',started_at=t,status='RUNNING',baseline_run_id=r,engine_version='2.14'))
  return e,F
 def test_all_8_execution_contracts_are_lossless(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=self.legacy(d); e,F=self.target(d,c,r)
   with session_scope(F) as s: counts=migrate_fcst_risk(con,s,r,c)
   self.assertEqual(counts['executions'],8); self.assertGreater(counts['signals'],0); self.assertGreater(counts['lineage'],0)
   with F() as s: self.assertEqual(canonical_batch_legacy(con,r,c,BATCH5_TESTS),canonical_batch_v2(s,r,c,BATCH5_TESTS))
   e.dispose(); con.close()
 def test_financially_sensitive_outputs_are_exact(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=self.legacy(d); e,F=self.target(d,c,r)
   with session_scope(F) as s: migrate_fcst_risk(con,s,r,c)
   q=','.join('?' for _ in BATCH5_TESTS)
   old={tuple(x) for x in con.execute(f"SELECT test_id,signal_type,entity_type,entity_id,observed_value,comparison_value,variance_value,unit,evidence_summary FROM signal WHERE run_id=? AND test_id IN ({q})",(r,*BATCH5_TESTS)).fetchall()}
   with F() as s: new={(x.test_id,x.signal_type,x.entity_type,x.entity_id,x.observed_value,x.comparison_value,x.variance_value,x.unit,x.evidence_summary) for x in s.query(Signal).filter(Signal.run_id==r,Signal.test_id.in_(BATCH5_TESTS)).all()}
   self.assertEqual(old,new); e.dispose(); con.close()
 def test_forecast_and_risk_guardrails_survive(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=self.legacy(d); e,F=self.target(d,c,r)
   with session_scope(F) as s: migrate_fcst_risk(con,s,r,c)
   with F() as s:
    f1=s.query(Signal).filter(Signal.run_id==r,Signal.test_id=='FCST-01').first(); self.assertIn('not an explanation',f1.evidence_summary)
    f4=s.query(Signal).filter(Signal.run_id==r,Signal.test_id=='FCST-04').first(); self.assertIn('not probabilities or predictions',f4.evidence_summary)
    r1=s.query(Signal).filter(Signal.run_id==r,Signal.test_id=='RISK-01').first(); self.assertIn('not an audit opinion',r1.evidence_summary)
    r2=s.query(Signal).filter(Signal.run_id==r,Signal.test_id=='RISK-02',Signal.signal_type=='CONTROL_PROCESS_EXCEPTION').first(); self.assertIn('does not establish error, misconduct, fraud or financial loss',r2.evidence_summary)
    r3=s.query(Signal).filter(Signal.run_id==r,Signal.test_id=='RISK-03').first(); self.assertIn('Exposure is not expected loss',r3.evidence_summary)
   e.dispose(); con.close()
 def test_scope_refuses_cross_client(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=self.legacy(d); e,F=self.target(d,c,r)
   with session_scope(F) as s: s.add(Client(client_id='evil',client_name='Other',base_currency='GBP',created_at=now()))
   with self.assertRaises(ValueError):
    with session_scope(F) as s: migrate_fcst_risk(con,s,r,'evil')
   e.dispose(); con.close()
if __name__=='__main__': unittest.main()

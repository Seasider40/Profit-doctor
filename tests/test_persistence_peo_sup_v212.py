import tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from profit_doctor.core.db import connect
from profit_doctor.diagnostic.engine import seed_registry,workforce_diagnostics,supplier_overhead_diagnostics
from profit_doctor.persistence import Base,Client,EngineRun,DatabaseConfig,build_engine,session_factory,session_scope
from profit_doctor.persistence.diagnostic_migration import migrate_peo_sup,canonical_batch_legacy,canonical_batch_v2,BATCH3_TESTS
from profit_doctor.persistence.models import Signal

def now(): return datetime.now(timezone.utc).isoformat()

class PeopleSupplierMigration(unittest.TestCase):
 def legacy(self,d):
  con=connect(Path(d)/'legacy.db'); c='c'; r='r'; t=now()
  con.execute('INSERT INTO client VALUES (?,?,?,?,?)',(c,'People Supply Co','GBP','PRODUCT_DISTRIBUTION',t));con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(r,c,'TEST',t,None,'RUNNING',None,r,'2.12'));seed_registry(con)
  for tid in BATCH3_TESTS: con.execute('INSERT INTO test_eligibility VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(tid,r,c,tid,'APPLICABLE','FULL','MIGRATION_EVIDENCE','Reliable','Reliable','100',None,t))
  people=[('w1','E1','Sales','AE','1','50000','8000','12000','0','0','1600','1200'),('w2','E2','Delivery','Consultant','1','45000','7000','0','2000','0','1600','1500')]
  for x in people: con.execute('INSERT INTO workforce_snapshot VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(x[0],c,'2026-09-30',*x[1:],'migration workforce evidence'))
  con.execute("INSERT INTO commission_plan VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",('cp',c,'AE Plan','COMMISSION','REVENUE','0.05',None,None,'Sales','AE','migration plan evidence',1))
  con.execute('INSERT INTO supplier_master VALUES (?,?,?,?,?,?,?,?)',('S1',c,'Critical Parts','Materials','CRITICAL',45,1,'migration supplier evidence'))
  purchases=[('p1','2026-01-10','S1','Materials','A','Part A','100','1000','10','INV1',None),('p2','2026-09-10','S1','Materials','A','Part A','100','1200','12','INV2',None),('p3','2026-09-15','S2','Materials','B','Part B','50','500','10','INV3',None),('p4','2026-09-15','S2','Materials','B','Part B','50','500','10','INV3',None)]
  for x in purchases: con.execute('INSERT INTO purchase_transaction VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',(x[0],c,*x[1:],'migration purchase evidence'))
  overhead=[('o1','2026-01-01','S3','Software','CRM','1000','SW1','CRM'),('o2','2026-02-01','S3','Software','CRM','1000','SW2','CRM'),('o3','2026-08-01','S3','Software','CRM','1600','SW3','CRM'),('o4','2026-09-01','S3','Software','CRM','1600','SW4','CRM')]
  for x in overhead: con.execute('INSERT INTO overhead_transaction VALUES (?,?,?,?,?,?,?,?,?,?)',(x[0],c,*x[1:],'migration overhead evidence'))
  con.commit();workforce_diagnostics(con,r,c);supplier_overhead_diagnostics(con,r,c);return con,c,r
 def target(self,d,c,r):
  e=build_engine(DatabaseConfig(f'sqlite+pysqlite:///{Path(d)/"new.db"}'));Base.metadata.create_all(e);F=session_factory(e);t=now()
  with session_scope(F) as s:s.add(Client(client_id=c,client_name='People Supply Co',base_currency='GBP',business_model='PRODUCT_DISTRIBUTION',created_at=t));s.add(EngineRun(run_id=r,client_id=c,run_type='TEST',started_at=t,status='RUNNING',baseline_run_id=r,engine_version='2.12'))
  return e,F
 def test_all_11_execution_contracts_are_lossless(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=self.legacy(d);e,F=self.target(d,c,r)
   with session_scope(F) as s: counts=migrate_peo_sup(con,s,r,c)
   self.assertEqual(counts['executions'],11);self.assertGreater(counts['signals'],0);self.assertGreater(counts['lineage'],0)
   with F() as s:self.assertEqual(canonical_batch_legacy(con,r,c,BATCH3_TESTS),canonical_batch_v2(s,r,c,BATCH3_TESTS))
   e.dispose();con.close()
 def test_people_and_supplier_economics_exact(self):
  focus=['PEO-01','PEO-02','PEO-03','PEO-04','PEO-05','SUP-01','SUP-02','SUP-03','SUP-04','SUP-05','SUP-06']
  with tempfile.TemporaryDirectory() as d:
   con,c,r=self.legacy(d);e,F=self.target(d,c,r)
   with session_scope(F) as s:migrate_peo_sup(con,s,r,c)
   q=','.join('?' for _ in focus)
   old={tuple(x) for x in con.execute(f"SELECT test_id,signal_type,entity_type,entity_id,observed_value,comparison_value,variance_value,unit,evidence_summary FROM signal WHERE run_id=? AND test_id IN ({q})",(r,*focus)).fetchall()}
   with F() as s:new={(x.test_id,x.signal_type,x.entity_type,x.entity_id,x.observed_value,x.comparison_value,x.variance_value,x.unit,x.evidence_summary) for x in s.query(Signal).filter(Signal.run_id==r,Signal.test_id.in_(focus)).all()}
   self.assertEqual(old,new);e.dispose();con.close()
 def test_guardrails_survive_migration(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=self.legacy(d);e,F=self.target(d,c,r)
   with session_scope(F) as s:migrate_peo_sup(con,s,r,c)
   with F() as s:
    cap=s.query(Signal).filter(Signal.run_id==r,Signal.test_id=='PEO-05').first();self.assertEqual(cap.unit,'HOURS');self.assertIn('financial benefit remains £0',cap.evidence_summary)
    dup=s.query(Signal).filter(Signal.run_id==r,Signal.test_id=='SUP-05').first();self.assertIn('not proof of duplicate payment',dup.evidence_summary)
    opt=s.query(Signal).filter(Signal.run_id==r,Signal.test_id=='SUP-06').first();self.assertIsNone(opt.observed_value);self.assertIn('remain unquantified',opt.evidence_summary)
   e.dispose();con.close()
 def test_scope_refuses_cross_client(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=self.legacy(d);e,F=self.target(d,c,r)
   with session_scope(F) as s:s.add(Client(client_id='evil',client_name='Other',base_currency='GBP',created_at=now()))
   with self.assertRaises(ValueError):
    with session_scope(F) as s:migrate_peo_sup(con,s,r,'evil')
   e.dispose();con.close()
if __name__=='__main__':unittest.main()

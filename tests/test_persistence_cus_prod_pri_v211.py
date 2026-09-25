import tempfile,unittest,uuid
from pathlib import Path
from profit_doctor.core.db import connect
from profit_doctor.ingestion.northstar import ingest_northstar
from profit_doctor.trust.engine import run_trust_layer
from profit_doctor.diagnostic.engine import run_diagnostic_engine
from profit_doctor.persistence import Base,Client,EngineRun,DatabaseConfig,build_engine,session_factory,session_scope
from profit_doctor.persistence.diagnostic_migration import migrate_cus_prod_pri,canonical_batch_legacy,canonical_batch_v2,BATCH2_TESTS
from profit_doctor.persistence.models import DiagnosticLineage,Signal
T='2026-09-25T10:00:00+00:00'
class CommercialMigration(unittest.TestCase):
 def legacy(self,d):
  root=Path(__file__).resolve().parent/'fixtures'/'northstar'; con=connect(Path(d)/'legacy.db'); c='c_'+uuid.uuid4().hex; r='r_'+uuid.uuid4().hex
  con.execute('INSERT INTO client VALUES (?,?,?,?,?)',(c,'Commercial Migration','GBP','PRODUCT_DISTRIBUTION',T));con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(r,c,'BASELINE',T,None,'RUNNING',None,r,'2.11'));con.commit()
  ing=ingest_northstar(con,c,r,root,Path(d)/'store');run_trust_layer(con,r,c,ing['dataset_version_id']);run_diagnostic_engine(con,r,c,ing['dataset_version_id']);return con,c,r
 def target(self,d,c,r):
  e=build_engine(DatabaseConfig(f'sqlite+pysqlite:///{Path(d)/"new.db"}'));Base.metadata.create_all(e);F=session_factory(e)
  with session_scope(F) as s:s.add(Client(client_id=c,client_name='Commercial Migration',base_currency='GBP',business_model='PRODUCT_DISTRIBUTION',created_at=T));s.add(EngineRun(run_id=r,client_id=c,run_type='BASELINE',started_at=T,status='RUNNING',baseline_run_id=r,engine_version='2.11'))
  return e,F
 def test_all_17_execution_contracts_are_lossless(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=self.legacy(d);e,F=self.target(d,c,r)
   with session_scope(F) as s: counts=migrate_cus_prod_pri(con,s,r,c)
   self.assertEqual(counts['executions'],17);self.assertGreater(counts['signals'],0);self.assertGreater(counts['lineage'],0)
   with F() as s:self.assertEqual(canonical_batch_legacy(con,r,c,BATCH2_TESTS),canonical_batch_v2(s,r,c,BATCH2_TESTS))
   e.dispose();con.close()
 def test_commercial_economics_exact(self):
  focus=['CUS-02','CUS-03','CUS-05','CUS-07','PROD-01','PROD-04','PROD-05','PRI-01','PRI-02','PRI-03','PRI-04','PRI-05']
  with tempfile.TemporaryDirectory() as d:
   con,c,r=self.legacy(d);e,F=self.target(d,c,r)
   with session_scope(F) as s:migrate_cus_prod_pri(con,s,r,c)
   q=','.join('?' for _ in focus)
   old={tuple(x) for x in con.execute(f"SELECT test_id,signal_type,entity_type,entity_id,observed_value,comparison_value,variance_value,unit,evidence_summary FROM signal WHERE run_id=? AND test_id IN ({q})",(r,*focus)).fetchall()}
   with F() as s:new={(x.test_id,x.signal_type,x.entity_type,x.entity_id,x.observed_value,x.comparison_value,x.variance_value,x.unit,x.evidence_summary) for x in s.query(Signal).filter(Signal.run_id==r,Signal.test_id.in_(focus)).all()}
   self.assertEqual(old,new);e.dispose();con.close()
 def test_pricing_does_not_create_supported_opportunity_value(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=self.legacy(d);e,F=self.target(d,c,r)
   with session_scope(F) as s:migrate_cus_prod_pri(con,s,r,c)
   with F() as s:
    rows=s.query(Signal).filter(Signal.run_id==r,Signal.test_id=='PRI-05').all()
    for x in rows:
     ev=(x.evidence_summary or '').lower()
     self.assertFalse('addressable opportunity £' in ev or 'expected opportunity £' in ev)
   e.dispose();con.close()
 def test_scope_refuses_cross_client(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=self.legacy(d);e,F=self.target(d,c,r)
   with session_scope(F) as s:s.add(Client(client_id='evil',client_name='Other',base_currency='GBP',created_at=T))
   with self.assertRaises(ValueError):
    with session_scope(F) as s:migrate_cus_prod_pri(con,s,r,'evil')
   e.dispose();con.close()
if __name__=='__main__':unittest.main()

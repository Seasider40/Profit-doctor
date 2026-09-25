import tempfile,unittest,uuid
from pathlib import Path
from profit_doctor.core.db import connect
from profit_doctor.ingestion.northstar import ingest_northstar
from profit_doctor.trust.engine import run_trust_layer
from profit_doctor.diagnostic.engine import run_diagnostic_engine
from profit_doctor.persistence import Base,Client,EngineRun,DatabaseConfig,build_engine,session_factory,session_scope
from profit_doctor.persistence.diagnostic_migration import migrate_rev_gm,canonical_legacy,canonical_v2,BATCH1_TESTS
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
T='2026-09-25T09:00:00+00:00'
class RevGMMigration(unittest.TestCase):
 def legacy(self,d):
  root=Path(__file__).resolve().parent/'fixtures'/'northstar'; con=connect(Path(d)/'legacy.db'); c='c_'+uuid.uuid4().hex; r='r_'+uuid.uuid4().hex
  con.execute('INSERT INTO client VALUES (?,?,?,?,?)',(c,'Migration Equivalence','GBP','PRODUCT_DISTRIBUTION',T));con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(r,c,'BASELINE',T,None,'RUNNING',None,r,'2.10'));con.commit()
  ing=ingest_northstar(con,c,r,root,Path(d)/'store');run_trust_layer(con,r,c,ing['dataset_version_id']);run_diagnostic_engine(con,r,c,ing['dataset_version_id']);return con,c,r
 def target(self,d,c,r):
  e=build_engine(DatabaseConfig(f'sqlite+pysqlite:///{Path(d)/"new.db"}'));Base.metadata.create_all(e);F=session_factory(e)
  with session_scope(F) as s:s.add(Client(client_id=c,client_name='Migration Equivalence',base_currency='GBP',business_model='PRODUCT_DISTRIBUTION',created_at=T));s.add(EngineRun(run_id=r,client_id=c,run_type='BASELINE',started_at=T,status='RUNNING',baseline_run_id=r,engine_version='2.10'))
  return e,F
 def test_all_13_executions_and_signals_are_lossless(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=self.legacy(d);e,F=self.target(d,c,r)
   with session_scope(F) as s: counts=migrate_rev_gm(con,s,r,c)
   self.assertEqual(counts['executions'],13); self.assertGreater(counts['lineage'],0)
   with F() as s:
    self.assertEqual(canonical_legacy(con,r,c),canonical_v2(s,r,c))
    from profit_doctor.persistence.models import DiagnosticLineage
    new_lin={(x.signal_id,x.source_object_type,x.source_object_id,x.relationship_type,x.scope_definition or '') for x in s.query(DiagnosticLineage).all()}
   old_lin={tuple(x) for x in con.execute("SELECT signal_id,source_object_type,source_object_id,relationship_type,COALESCE(scope_definition,'') FROM diagnostic_lineage WHERE signal_id IN (SELECT signal_id FROM signal WHERE run_id=? AND test_id LIKE 'REV-%' OR run_id=? AND test_id LIKE 'GM-%')",(r,r)).fetchall()}
   self.assertEqual(old_lin,new_lin)
   e.dispose();con.close()
 def test_pvm_and_margin_economics_exact(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=self.legacy(d);e,F=self.target(d,c,r)
   with session_scope(F) as s:migrate_rev_gm(con,s,r,c)
   legacy={tuple(x) for x in con.execute("SELECT test_id,signal_type,observed_value,comparison_value,variance_value FROM signal WHERE run_id=? AND test_id IN ('REV-04','GM-01','GM-02','GM-06','GM-07')",(r,)).fetchall()}
   with F() as s:
    from profit_doctor.persistence.models import Signal
    new={(x.test_id,x.signal_type,x.observed_value,x.comparison_value,x.variance_value) for x in s.query(Signal).filter(Signal.run_id==r,Signal.test_id.in_(['REV-04','GM-01','GM-02','GM-06','GM-07'])).all()}
   self.assertEqual(legacy,new);e.dispose();con.close()
 def test_scope_refuses_cross_client_migration(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=self.legacy(d);e,F=self.target(d,c,r)
   with session_scope(F) as s:s.add(Client(client_id='evil',client_name='Other',base_currency='GBP',created_at=T))
   with self.assertRaises(ValueError):
    with session_scope(F) as s:migrate_rev_gm(con,s,r,'evil')
   e.dispose();con.close()
 def test_alembic_head_has_diagnostic_contract(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'mig.db';cfg=Config(str(Path(__file__).resolve().parents[1]/'alembic.ini'));cfg.set_main_option('sqlalchemy.url',f'sqlite+pysqlite:///{p}');command.upgrade(cfg,'head');e=build_engine(DatabaseConfig(f'sqlite+pysqlite:///{p}'));names=set(inspect(e).get_table_names());self.assertIn('test_execution_v2',names);self.assertIn('diagnostic_lineage_v2',names);cols={x['name'] for x in inspect(e).get_columns('signal_v2')};self.assertTrue({'comparison_value','materiality_state','source_primitive_id'}<=cols);e.dispose()
if __name__=='__main__':unittest.main()

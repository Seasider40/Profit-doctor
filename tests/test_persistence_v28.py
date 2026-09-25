import tempfile, unittest
from pathlib import Path
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from alembic import command
from alembic.config import Config
from profit_doctor.persistence import Base, Client, EngineRun, OpportunityRelationship, DatabaseConfig, build_engine, session_factory, session_scope, ping

class PersistenceV28Tests(unittest.TestCase):
    def make(self):
        f=tempfile.NamedTemporaryFile(suffix='.db',delete=False); f.close(); p=Path(f.name)
        e=build_engine(DatabaseConfig(f"sqlite+pysqlite:///{p}")); Base.metadata.create_all(e); return p,e,session_factory(e)
    def seed(self,F):
        with session_scope(F) as s:
            s.add(Client(client_id='c1',client_name='A',base_currency='GBP',business_model='SERVICES',created_at='2026-09-25T00:00:00Z'))
            s.add(EngineRun(run_id='r1',client_id='c1',run_type='BASELINE',started_at='2026-09-25T00:00:00Z',status='RUNNING',engine_version='2.8'))
    def test_ping_and_commit(self):
        p,e,F=self.make(); self.assertTrue(ping(e)); self.seed(F)
        with F() as s: self.assertEqual(s.scalar(select(Client.client_name).where(Client.client_id=='c1')),'A')
        e.dispose(); p.unlink(missing_ok=True)
    def test_rollback_is_atomic(self):
        p,e,F=self.make()
        try:
            with session_scope(F) as s:
                s.add(Client(client_id='rollback',client_name='X',base_currency='GBP',created_at='x')); raise RuntimeError('boom')
        except RuntimeError: pass
        with F() as s: self.assertIsNone(s.get(Client,'rollback'))
        e.dispose(); p.unlink(missing_ok=True)
    def test_foreign_key_client_isolation_boundary(self):
        p,e,F=self.make(); self.seed(F)
        with self.assertRaises(IntegrityError):
            with session_scope(F) as s: s.add(EngineRun(run_id='bad',client_id='missing',run_type='BASELINE',started_at='x',status='RUNNING',engine_version='2.8'))
        e.dispose(); p.unlink(missing_ok=True)
    def test_symmetric_relationship_duplicate_blocked(self):
        p,e,F=self.make(); self.seed(F); pair='oppA|oppB'
        with session_scope(F) as s: s.add(OpportunityRelationship(relationship_id='x1',client_id='c1',run_id='r1',from_opportunity_id='oppA',to_opportunity_id='oppB',pair_key=pair,relationship_type='OVERLAPPING',overlap_amount='20',evidence_basis='test'))
        with self.assertRaises(IntegrityError):
            with session_scope(F) as s: s.add(OpportunityRelationship(relationship_id='x2',client_id='c1',run_id='r1',from_opportunity_id='oppB',to_opportunity_id='oppA',pair_key=pair,relationship_type='OVERLAPPING',overlap_amount='20',evidence_basis='test'))
        e.dispose(); p.unlink(missing_ok=True)
    def test_alembic_upgrade_and_downgrade(self):
        f=tempfile.NamedTemporaryFile(suffix='.db',delete=False); f.close(); p=Path(f.name)
        cfg=Config(str(Path(__file__).resolve().parents[1]/'alembic.ini')); cfg.set_main_option('sqlalchemy.url',f'sqlite+pysqlite:///{p}')
        command.upgrade(cfg,'head'); e=build_engine(DatabaseConfig(f'sqlite+pysqlite:///{p}'))
        with e.connect() as c: self.assertIn('client',{r[0] for r in c.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))})
        e.dispose(); command.downgrade(cfg,'base'); p.unlink(missing_ok=True)
if __name__=='__main__': unittest.main()

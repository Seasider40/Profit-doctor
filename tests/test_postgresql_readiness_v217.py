import os, unittest
from sqlalchemy import create_mock_engine, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable, CreateIndex
from profit_doctor.persistence import Base, Client, EngineRun, DatabaseConfig, build_engine, session_factory, session_scope, ping

class PostgreSQLStaticReadinessV217(unittest.TestCase):
    def test_all_metadata_compiles_for_postgresql(self):
        dialect=postgresql.dialect()
        for table in Base.metadata.sorted_tables:
            sql=str(CreateTable(table).compile(dialect=dialect))
            self.assertIn('CREATE TABLE', sql)
            for idx in table.indexes:
                self.assertTrue(str(CreateIndex(idx).compile(dialect=dialect)).strip())

    def test_mock_postgresql_create_all_emits_every_table(self):
        emitted=[]
        def executor(sql,*multiparams,**params):
            emitted.append(str(sql.compile(dialect=postgresql.dialect())))
        engine=create_mock_engine('postgresql+psycopg://',executor)
        Base.metadata.create_all(engine)
        ddl='\n'.join(emitted)
        for table in Base.metadata.tables:
            self.assertIn(table, ddl)

    def test_named_unique_constraints_are_not_duplicated(self):
        names=[]
        for table in Base.metadata.tables.values():
            for c in table.constraints:
                if c.name: names.append(c.name)
        self.assertEqual(len(names),len(set(names)))

@unittest.skipUnless(os.getenv('PROFIT_DOCTOR_POSTGRES_TEST_URL'), 'live PostgreSQL URL not supplied')
class PostgreSQLLiveQualificationV217(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.url=os.environ['PROFIT_DOCTOR_POSTGRES_TEST_URL']
        if not cls.url.startswith('postgresql'):
            raise unittest.SkipTest('qualification URL is not PostgreSQL')
        cls.engine=build_engine(DatabaseConfig(cls.url)); cls.F=session_factory(cls.engine)
        self=cls
        with cls.engine.begin() as c:
            Base.metadata.drop_all(c); Base.metadata.create_all(c)
    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()
    def test_live_ping_commit_and_rollback(self):
        self.assertTrue(ping(self.engine))
        with session_scope(self.F) as s:
            s.add(Client(client_id='pg-c1',client_name='PG',base_currency='GBP',created_at='2026-09-25T00:00:00Z'))
        try:
            with session_scope(self.F) as s:
                s.add(Client(client_id='pg-rollback',client_name='X',base_currency='GBP',created_at='x'))
                raise RuntimeError('rollback')
        except RuntimeError: pass
        with self.F() as s:
            self.assertIsNone(s.get(Client,'pg-rollback'))
    def test_live_foreign_key_tenant_boundary(self):
        from sqlalchemy.exc import IntegrityError
        with self.assertRaises(IntegrityError):
            with session_scope(self.F) as s:
                s.add(EngineRun(run_id='pg-bad',client_id='does-not-exist',run_type='BASELINE',started_at='x',status='RUNNING',engine_version='2.17'))

if __name__=='__main__': unittest.main()

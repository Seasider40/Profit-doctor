"""Frozen v2.54 reconstruction, forward ownership DDL and legacy preservation."""
from pathlib import Path
import shutil
import unittest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, insert, select, text
from sqlalchemy.engine import create_mock_engine
from profit_doctor.persistence import Base, DatabaseConfig, build_engine
from tests.preserved_schema_fixture import load_preserved_schema_fixture, reflect_preserved_schema
from tests.test_postgresql_live_qualification_v218 import alembic_config

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/'tests/fixtures/v254_schema.sql'
NEW={'canonical_monthly_measurement','canonical_receivables_absence','canonical_production_evidence_audit'}


class ProductionEvidenceMigrationsV255(unittest.TestCase):
    target_url=None
    def setUp(self):
        self.root=ROOT/'tests/.v255_migration_tmp'
        if self.root.exists():shutil.rmtree(self.root)
        self.root.mkdir();self.addCleanup(shutil.rmtree,self.root)
        self.url=self.target_url or ('sqlite+pysqlite:///'+(self.root/'migration.db').as_posix())
        self.cfg=alembic_config(self.url)
        self.engine=build_engine(DatabaseConfig(self.url));self.addCleanup(self.engine.dispose)
        if self.engine.dialect.name=='postgresql':
            # Live canonical fixtures start at current head; preserved-schema
            # qualification needs an empty target, exactly as inherited suites.
            command.downgrade(self.cfg,'base')
            with self.engine.begin() as connection:
                connection.execute(text('DROP TABLE IF EXISTS alembic_version'))

    def assert_head(self):
        self.assertEqual(set(Base.metadata.tables),set(inspect(self.engine).get_table_names())-{'alembic_version'})
        with self.engine.connect() as connection:
            ctx=MigrationContext.configure(connection,opts={'compare_type':True,'compare_server_default':True})
            self.assertEqual(('0019_production_history',),ctx.get_current_heads())
            self.assertEqual([],compare_metadata(ctx,Base.metadata))

    def test_clean_upgrade_and_repeat_head(self):
        command.upgrade(self.cfg,'head');self.assert_head()
        command.upgrade(self.cfg,'head');self.assert_head()

    def test_frozen_v254_all_rows_preserved_downgrade_reupgrade(self):
        old=load_preserved_schema_fixture(self.engine,FIXTURE)
        self.assertEqual(58,len(old.tables))
        expected={}
        with self.engine.begin() as connection:
            ids={table.name:'frozen-'+table.name for table in old.sorted_tables}
            for table in old.sorted_tables:
                if table.name=='alembic_version':continue
                row={}
                for column in table.columns:
                    if str(column.type)=='INTEGER':value=1
                    elif column.foreign_keys:
                        values=[]
                        for ref in column.foreign_keys:
                            foreign=ref.column
                            values.append(expected[foreign.table.name][foreign.name] if foreign.table.name in expected else
                                ids[foreign.table.name] if foreign.primary_key else 'frozen-client')
                        self.assertEqual(1,len(set(values)))
                        value=values[0]
                    elif column.primary_key:value=ids[table.name]
                    else:value={'document':'{"frozen":"v254-preserved"}','created_at':'2026-10-06T00:00:00+00:00',
                        'currency':'GBP','base_currency':'GBP'}.get(column.name,'frozen')
                    row[column.name]=value
                connection.execute(insert(table).values(**row));expected[table.name]=row
        command.upgrade(self.cfg,'head');self.assert_head()
        with self.engine.begin() as connection:
            client=expected['client']['client_id'];run=expected['engine_run']['run_id']
            connection.execute(Base.metadata.tables['canonical_measurement_context'].insert().values(
                context_id='monthly-context',client_id=client,run_id=run,document='{"qualification":"monthly-owner"}'))
            connection.execute(Base.metadata.tables['canonical_monthly_measurement'].insert().values(
                measurement_id='monthly1',client_id=client,run_id=run,series_id='monthly-series',revision=1,
                context_id='monthly-context',document='{"qualification":"monthly-value"}'))
            connection.execute(Base.metadata.tables['canonical_receivables_absence'].insert().values(
                assessment_id='absence1',client_id=client,run_id=run,series_id='absence-series',revision=1,document='{}'))
            connection.execute(Base.metadata.tables['canonical_production_evidence_audit'].insert().values(
                event_id='audit1',client_id=client,measurement_id='monthly1',created_at='2026-10-06',document='{}'))
        command.downgrade(self.cfg,'0016_temporal_evidence')
        self.assertEqual(set(old.tables),set(inspect(self.engine).get_table_names()))
        with self.engine.connect() as connection:
            for name,row in expected.items():
                self.assertEqual(row,dict(connection.execute(select(old.tables[name])).mappings().one()),name)
        command.upgrade(self.cfg,'head');self.assert_head()
        with self.engine.connect() as connection:
            for name in NEW:self.assertEqual(0,connection.scalar(text('SELECT count(*) FROM '+name)))

    def test_frozen_fixture_postgresql_ddl_equivalence(self):
        old,_=reflect_preserved_schema(FIXTURE)
        statements=[]
        engine=create_mock_engine('postgresql+psycopg://',lambda sql,*a,**kw:statements.append(str(sql.compile(dialect=engine.dialect))))
        old.create_all(engine)
        self.assertEqual(58,sum(s.lstrip().startswith('CREATE TABLE') for s in statements))
        self.assertEqual(sum(len(t.foreign_key_constraints) for t in old.tables.values()),sum(s.count('FOREIGN KEY') for s in statements))
        self.assertEqual(sum(len(t.columns) for t in old.tables.values()),424)
        self.assertEqual(reflect_preserved_schema(FIXTURE)[1]['alembic_version'][0]['version_num'],'0016_temporal_evidence')

    def test_new_ddl_foreign_keys_and_check_retained_on_postgresql(self):
        statements=[]
        engine=create_mock_engine('postgresql+psycopg://',lambda sql,*a,**kw:statements.append(str(sql.compile(dialect=engine.dialect))))
        Base.metadata.create_all(engine)
        selected=[s for s in statements if any('CREATE TABLE '+name+' ' in s for name in NEW)]
        self.assertEqual(len(NEW),len(selected))
        self.assertIn('ck_production_audit_owner','\n'.join(selected))
        self.assertIn('canonical_measurement_context','\n'.join(selected))

    def test_all_revision_ids_fit_version_table(self):
        script=ScriptDirectory.from_config(self.cfg)
        self.assertEqual('0019_production_history',script.get_current_head())
        for rev in script.walk_revisions():self.assertLessEqual(len(rev.revision),32)

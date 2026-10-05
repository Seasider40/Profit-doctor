"""Migration-only frozen v2.53 preservation and temporal-schema parity."""
from pathlib import Path
import shutil
import unittest

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import MetaData, inspect, insert, select, text
from sqlalchemy.engine import create_mock_engine

from profit_doctor.persistence import Base, DatabaseConfig, build_engine
from tests.preserved_schema_fixture import load_preserved_schema_fixture, reflect_preserved_schema
from tests.test_postgresql_live_qualification_v218 import alembic_config

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/'tests/fixtures/v253_schema.sql'
NEW={'canonical_temporal_assessment','canonical_temporal_audit'}


class TemporalMigrationsV254(unittest.TestCase):
    target_url=None

    def setUp(self):
        self.root=ROOT/'tests'/'.v254_temporal_migration_tmp'
        self._remove(self.root)
        self.root.mkdir()
        self.addCleanup(self._remove,self.root)
        self.url=self.target_url or ('sqlite+pysqlite:///'+(self.root/'migration.db').as_posix())
        self.cfg=alembic_config(self.url)
        self.engine=build_engine(DatabaseConfig(self.url))
        self.addCleanup(self.engine.dispose)
        if self.engine.dialect.name=='postgresql':
            command.downgrade(self.cfg,'base')
            with self.engine.begin() as connection:
                connection.execute(text('DROP TABLE IF EXISTS alembic_version'))

    @staticmethod
    def _remove(root):
        if root.exists():
            shutil.rmtree(root)

    def assert_head(self):
        self.assertEqual(set(Base.metadata.tables),set(inspect(self.engine).get_table_names())-{'alembic_version'})
        with self.engine.connect() as connection:
            context=MigrationContext.configure(connection,opts={'compare_type':True,'compare_server_default':True})
            self.assertEqual(('0016_temporal_evidence',),context.get_current_heads())
            self.assertEqual([],compare_metadata(context,Base.metadata))
        for name in NEW:
            actual=inspect(self.engine).get_foreign_keys(name)
            self.assertEqual({(tuple(f.column_keys),tuple(e.column.name for e in f.elements))
                for f in Base.metadata.tables[name].foreign_key_constraints},
                {(tuple(f['constrained_columns']),tuple(f['referred_columns'])) for f in actual})

    def test_clean_creation_and_repeat_head(self):
        command.upgrade(self.cfg,'head');self.assert_head()
        command.upgrade(self.cfg,'head');self.assert_head()

    def test_frozen_v253_rows_preserved_temporal_rows_removed_downgrade_and_reupgrade(self):
        old=load_preserved_schema_fixture(self.engine,FIXTURE)
        self.assertEqual(56,len(old.tables))
        self.assertFalse(NEW & old.tables.keys())
        with self.engine.connect() as connection:
            self.assertEqual(('0015_dataset_comparability',),MigrationContext.configure(connection).get_current_heads())
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
                        for reference in column.foreign_keys:
                            foreign=reference.column
                            values.append(expected[foreign.table.name][foreign.name] if foreign.table.name in expected
                                else ids[foreign.table.name] if foreign.primary_key else 'frozen-client')
                        self.assertEqual(1,len(set(values)),'Frozen FK seeds must reconcile')
                        value=values[0]
                    elif column.primary_key:value=ids[table.name]
                    else:value={'document':'{"frozen":"v253-preserved"}',
                        'created_at':'2026-10-05T00:00:00+00:00','currency':'GBP','base_currency':'GBP'}.get(column.name,'frozen')
                    row[column.name]=value
                connection.execute(insert(table).values(**row));expected[table.name]=row
        command.upgrade(self.cfg,'head');self.assert_head()
        with self.engine.begin() as connection:
            connection.execute(Base.metadata.tables['canonical_temporal_assessment'].insert().values(
                assessment_id='new-assessment',series_id='new-series',subject_id=ids['reasoning_object_v243'],
                client_id=expected['reasoning_object_v243']['client_id'],run_id=ids['engine_run'],revision=1,
                created_at='2026-10-05T00:00:00+00:00',document='{"qualification":"new"}'))
            connection.execute(Base.metadata.tables['canonical_temporal_audit'].insert().values(
                event_id='new-event',assessment_id='new-assessment',client_id=expected['reasoning_object_v243']['client_id'],
                created_at='2026-10-05T00:00:00+00:00',document='{"qualification":"audit"}'))
        command.downgrade(self.cfg,'0015_dataset_comparability')
        self.assertEqual(set(old.tables),set(inspect(self.engine).get_table_names()))
        with self.engine.connect() as connection:
            for name,row in expected.items():
                self.assertEqual(row,dict(connection.execute(select(old.tables[name])).mappings().one()),name)
        command.upgrade(self.cfg,'head');self.assert_head()
        with self.engine.connect() as connection:
            for name in NEW:self.assertEqual(0,connection.scalar(text(f'SELECT count(*) FROM {name}')))

    def test_frozen_fixture_postgresql_construction_retains_dependencies_and_constraints(self):
        metadata,_=reflect_preserved_schema(FIXTURE)
        statements=[]
        mock=create_mock_engine('postgresql+psycopg://',lambda statement,*a,**kw:statements.append(str(statement.compile(dialect=mock.dialect))))
        metadata.create_all(mock)
        self.assertEqual(56,sum(s.lstrip().startswith('CREATE TABLE') for s in statements))
        self.assertEqual(sum(len(t.foreign_key_constraints) for t in metadata.tables.values()),
            sum(s.count('FOREIGN KEY') for s in statements))
        self.assertEqual(sum(type(c).__name__=='UniqueConstraint' for t in metadata.tables.values() for c in t.constraints),
            sum(s.count('UNIQUE (') for s in statements))
        self.assertEqual('0015_dataset_comparability',reflect_preserved_schema(FIXTURE)[1]['alembic_version'][0]['version_num'])

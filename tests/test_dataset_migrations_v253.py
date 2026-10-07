"""Forward migration qualification from the frozen v2.52 schema."""
from pathlib import Path
import shutil
import unittest

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import MetaData, inspect, insert, select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from profit_doctor.persistence import Base, DatabaseConfig, build_engine
from tests.preserved_schema_fixture import load_preserved_schema_fixture
from tests.test_postgresql_live_qualification_v218 import alembic_config

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT/'tests/fixtures/v252_schema.sql'
NEW = {'canonical_dataset_contract', 'canonical_dataset_comparability', 'canonical_dataset_audit'}


class DatasetContractMigrationsV253(unittest.TestCase):
    target_url = None
    @staticmethod
    def _remove(root):
        if root.exists():
            for path in root.rglob('*'):
                if path.is_file():
                    path.chmod(0o666)
            shutil.rmtree(root)

    def setUp(self):
        self.root = ROOT/'tests'/'.v253_dataset_migration_tmp'
        self._remove(self.root)
        self.root.mkdir(parents=True)
        self.addCleanup(self._remove, self.root)
        self.url = self.target_url or ('sqlite+pysqlite:///' + (self.root/'migration.db').as_posix())
        self.cfg = alembic_config(self.url)
        self.engine = build_engine(DatabaseConfig(self.url))
        self.addCleanup(self.engine.dispose)
        if self.engine.dialect.name == 'postgresql':
            command.downgrade(self.cfg, 'base')
            with self.engine.begin() as connection:
                connection.execute(text('DROP TABLE IF EXISTS alembic_version'))

    def assert_head(self):
        self.assertEqual(set(Base.metadata.tables), set(inspect(self.engine).get_table_names())-{'alembic_version'})
        with self.engine.connect() as connection:
            context = MigrationContext.configure(connection, opts={'compare_type':True,'compare_server_default':True})
            self.assertEqual(('0019_production_history',), context.get_current_heads())
            self.assertEqual([], compare_metadata(context, Base.metadata))
        for name in NEW:
            expected = Base.metadata.tables[name]
            actual = inspect(self.engine).get_foreign_keys(name)
            self.assertEqual({(tuple(f.column_keys), tuple(e.column.name for e in f.elements))
                for f in expected.foreign_key_constraints},
                {(tuple(f['constrained_columns']), tuple(f['referred_columns'])) for f in actual})

    def test_all_revision_ids_fit_alembic_version_column(self):
        migration_context = MigrationContext.configure(dialect=postgresql.dialect())
        version_table = migration_context.impl.version_table_impl(
            version_table='alembic_version', version_table_schema=None,
            version_table_pk=True)
        version_limit = version_table.c.version_num.type.length
        self.assertEqual(32, version_limit)
        self.assertIn('VARCHAR(32)', str(CreateTable(version_table).compile(
            dialect=postgresql.dialect())))
        revisions = ScriptDirectory.from_config(self.cfg).walk_revisions()
        oversized = [(revision.revision, len(revision.revision)) for revision in revisions
                     if len(revision.revision) > version_limit]
        self.assertEqual([], oversized,
            'Alembic revision IDs must fit its default PostgreSQL version_num column')

    def test_clean_creation_and_repeat_head(self):
        command.upgrade(self.cfg, 'head')
        self.assert_head()
        command.upgrade(self.cfg, 'head')
        self.assert_head()

    def test_v252_checkpoint_upgrade_preserves_legacy_rows_on_downgrade_and_reupgrade(self):
        load_preserved_schema_fixture(self.engine, FIXTURE)
        old = MetaData()
        old.reflect(self.engine)
        self.assertEqual(52, len(old.tables)-1)
        self.assertFalse(NEW & old.tables.keys())
        with self.engine.connect() as connection:
            self.assertEqual(('0014_priority_decision',),
                MigrationContext.configure(connection).get_current_heads())
        expected = {}
        with self.engine.begin() as connection:
            ids = {table.name:'frozen-'+table.name for table in old.sorted_tables}
            for table in old.sorted_tables:
                if table.name == 'alembic_version':
                    continue
                row = {}
                for column in table.columns:
                    if str(column.type) == 'INTEGER':
                        value = 1
                    elif column.foreign_keys:
                        values = []
                        for reference in column.foreign_keys:
                            foreign = reference.column
                            values.append(expected[foreign.table.name][foreign.name]
                                if foreign.table.name in expected else ids[foreign.table.name]
                                if foreign.primary_key else 'frozen-client')
                        self.assertEqual(1, len(set(values)), 'Frozen foreign-key seed must reconcile')
                        value = values[0]
                    elif column.primary_key:
                        value = ids[table.name]
                    else:
                        value = {'document':'{"frozen":"preserved"}',
                            'created_at':'2026-10-01T00:00:00+00:00','currency':'GBP',
                            'base_currency':'GBP'}.get(column.name, 'frozen')
                    row[column.name] = value
                connection.execute(insert(table).values(**row))
                expected[table.name] = row
        command.upgrade(self.cfg, 'head')
        self.assert_head()
        command.downgrade(self.cfg, '0014_priority_decision')
        self.assertEqual(set(old.tables), set(inspect(self.engine).get_table_names()))
        with self.engine.connect() as connection:
            for name, row in expected.items():
                self.assertEqual(row, dict(connection.execute(select(old.tables[name])).mappings().one()), name)
        command.upgrade(self.cfg, 'head')
        self.assert_head()
        with self.engine.connect() as connection:
            for name in NEW:
                self.assertEqual(0, connection.scalar(text(f'SELECT count(*) FROM {name}')))


if __name__ == '__main__':
    unittest.main()

"""Forward-only workspace schema, inherited data, FK and rollback qualification."""
import unittest
import tempfile
from pathlib import Path
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import create_mock_engine
from tests.test_workspace_v256 import WorkspaceFixture
from tests.test_postgresql_live_qualification_v218 import alembic_config
from profit_doctor.persistence import Base, Client, workspace_schema as t
from tests.preserved_schema_fixture import load_preserved_schema_fixture, reflect_preserved_schema

FIXTURE = Path(__file__).with_name('fixtures') / 'v2551_schema.sql'


class WorkspaceMigrationsV256(WorkspaceFixture, unittest.TestCase):
    def test_clean_head_equals_metadata(self):
        with self.engine.connect() as connection:
            context = MigrationContext.configure(connection, opts={'compare_type': True, 'compare_server_default': True})
            self.assertEqual(context.get_current_heads(), ('0020_engagement_workspace',))
            self.assertEqual(compare_metadata(context, Base.metadata), [])

    def test_upgrade_downgrade_reupgrade_preserves_legacy_clients(self):
        self.receive()
        self.session.commit()
        self.session.close()
        with self.engine.connect() as connection:
            before = list(connection.execute(select(Client.__table__)).mappings())
        command.downgrade(alembic_config(self.url), '0019_production_history')
        self.assertTrue(all(x.name not in inspect(self.engine).get_table_names() for x in t.TABLES))
        command.upgrade(alembic_config(self.url), 'head')
        with self.engine.connect() as connection:
            self.assertEqual(list(connection.execute(select(Client.__table__)).mappings()), before)
            self.assertEqual(list(connection.execute(select(t.receipt))), [])
        self.assertEqual(len(list(self.store.root.iterdir())), 1)

    def test_postgresql_ddl_keeps_all_scoped_constraints(self):
        statements = []
        engine = create_mock_engine('postgresql+psycopg://', lambda sql, *args, **kwargs:
            statements.append(str(sql.compile(dialect=engine.dialect))))
        Base.metadata.create_all(engine)
        for table in t.TABLES:
            ddl = next(x for x in statements if 'CREATE TABLE ' + table.name + ' ' in x)
            self.assertEqual(ddl.count('FOREIGN KEY'), len(table.foreign_key_constraints), table.name)
            self.assertEqual(ddl.count('UNIQUE'), len([c for c in table.constraints if c.__class__.__name__ == 'UniqueConstraint']), table.name)

    def test_frozen_v2551_constructs_and_upgrades_without_schema_drift(self):
        from profit_doctor.persistence import DatabaseConfig, build_engine
        with tempfile.TemporaryDirectory() as root:
            live = self.engine.dialect.name == 'postgresql'
            url = self.url if live else 'sqlite+pysqlite:///' + (Path(root) / 'frozen.db').as_posix()
            engine = self.engine if live else build_engine(DatabaseConfig(url))
            try:
                if live:
                    # Only this destructive qualification fixture, reached after
                    # inherited disposable verification. Never a product route.
                    self.session.close()
                    command.downgrade(alembic_config(url), 'base')
                    with engine.begin() as connection:
                        connection.execute(text('DROP TABLE alembic_version'))
                frozen, rows = reflect_preserved_schema(FIXTURE)
                load_preserved_schema_fixture(engine, FIXTURE)
                with engine.connect() as connection:
                    self.assertEqual(MigrationContext.configure(connection).get_current_heads(), ('0019_production_history',))
                command.upgrade(alembic_config(url), 'head')
                with engine.connect() as connection:
                    self.assertEqual(compare_metadata(MigrationContext.configure(connection), Base.metadata), [])
                    self.assertEqual(set(frozen.tables), set(inspect(engine).get_table_names()) - {x.name for x in t.TABLES})
            finally:
                if not live:
                    engine.dispose()

    def test_frozen_checkpoint_postgresql_ddl_retains_every_fk(self):
        metadata, _ = reflect_preserved_schema(FIXTURE)
        statements = []
        engine = create_mock_engine('postgresql+psycopg://', lambda sql, *args, **kwargs:
            statements.append(str(sql.compile(dialect=engine.dialect))))
        metadata.create_all(engine)
        for table in metadata.tables.values():
            # Cyclic constraints may appear in ALTER TABLE statements.
            own = [sql for sql in statements if 'CREATE TABLE ' + table.name + ' ' in sql or 'ALTER TABLE ' + table.name + ' ' in sql]
            self.assertEqual(sum(sql.count('FOREIGN KEY') for sql in own), len(table.foreign_key_constraints), table.name)

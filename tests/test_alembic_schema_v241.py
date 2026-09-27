"""Local migration/fixture regressions; these are not live PostgreSQL evidence."""
import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import event, inspect, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Engine
from sqlalchemy.schema import CreateColumn, CreateIndex, CreateTable

from profit_doctor.persistence import Base, DatabaseConfig, build_engine
from tests.test_postgresql_live_qualification_v218 import (
    alembic_config, reset_qualification_schema,
)


class AlembicSchemaV241(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.url = f"sqlite+pysqlite:///{Path(directory.name) / 'qualification.db'}"
        self.cfg = alembic_config(self.url)
        self.engine = build_engine(DatabaseConfig(self.url))
        self.addCleanup(self.engine.dispose)

    def assert_schema_matches_metadata(self):
        inspector = inspect(self.engine)
        self.assertEqual(
            set(Base.metadata.tables),
            set(inspector.get_table_names()) - {"alembic_version"},
        )
        with self.engine.connect() as connection:
            context = MigrationContext.configure(connection, opts={
                "compare_type": True, "compare_server_default": True,
            })
            self.assertEqual([], compare_metadata(context, Base.metadata))
            self.assertEqual(
                (ScriptDirectory.from_config(self.cfg).get_current_head(),),
                context.get_current_heads(),
            )
        # Alembic autogenerate does not detect primary-key changes.
        for table in Base.metadata.sorted_tables:
            with self.subTest(table=table.name):
                self.assertEqual(
                    [column.name for column in table.primary_key],
                    inspector.get_pk_constraint(table.name)["constrained_columns"],
                )
                self.assertEqual([], inspector.get_check_constraints(table.name))

    def test_fresh_migrations_match_all_metadata_and_postgresql_ddl(self):
        # Capture the DDL actually executed by the migration chain, then compile
        # its columns, constraints and indexes with the PostgreSQL dialect.
        emitted = []

        def capture(connection, clause, multiparams, params, execution_options):
            if isinstance(clause, (CreateTable, CreateIndex)):
                emitted.append(clause)

        event.listen(Engine, "before_execute", capture)
        try:
            command.upgrade(self.cfg, "head")
        finally:
            event.remove(Engine, "before_execute", capture)
        self.assert_schema_matches_metadata()
        dialect = postgresql.dialect()

        def table_contract(table):
            return (
                tuple(str(CreateColumn(c).compile(dialect=dialect)) for c in table.columns),
                sorted(line.strip().rstrip(",") for line in
                       str(CreateTable(table).compile(dialect=dialect)).splitlines()
                       if line.strip()),
            )

        tables = {
            ddl.element.name: ddl.element for ddl in emitted
            if isinstance(ddl, CreateTable) and ddl.element.name != "alembic_version"
        }
        self.assertEqual(set(Base.metadata.tables), set(tables))
        for name, table in Base.metadata.tables.items():
            with self.subTest(table=name):
                self.assertEqual(table_contract(table), table_contract(tables[name]))
        self.assertEqual(
            {str(CreateIndex(index).compile(dialect=dialect))
             for table in Base.metadata.tables.values() for index in table.indexes},
            {str(ddl.compile(dialect=dialect)) for ddl in emitted if isinstance(ddl, CreateIndex)},
        )

    def test_qualification_reset_replays_migrations_on_repeated_runs(self):
        reset_qualification_schema(self.engine, self.url)
        self.assert_schema_matches_metadata()
        reset_qualification_schema(self.engine, self.url)
        self.assert_schema_matches_metadata()
        # Exercise the exact per-test cleanup which failed on benefit_leg_v2.
        with self.engine.begin() as connection:
            for table in reversed(Base.metadata.sorted_tables):
                connection.execute(table.delete())

    def test_qualification_reset_recovers_missing_tables_with_stale_head(self):
        command.upgrade(self.cfg, "head")
        with self.engine.begin() as connection:
            Base.metadata.drop_all(connection)
        self.assertEqual(["alembic_version"], inspect(self.engine).get_table_names())
        # The old fixture's upgrade is a no-op with the retained revision marker.
        command.upgrade(self.cfg, "head")
        self.assertEqual(["alembic_version"], inspect(self.engine).get_table_names())
        reset_qualification_schema(self.engine, self.url)
        self.assert_schema_matches_metadata()

    def test_downgrade_base_and_reupgrade_match_all_metadata(self):
        command.upgrade(self.cfg, "head")
        command.downgrade(self.cfg, "base")
        self.assertEqual(["alembic_version"], inspect(self.engine).get_table_names())
        with self.engine.connect() as connection:
            self.assertEqual((), MigrationContext.configure(connection).get_current_heads())
        command.upgrade(self.cfg, "head")
        self.assert_schema_matches_metadata()

    def test_upgrade_at_head_preserves_existing_data(self):
        command.upgrade(self.cfg, "head")
        with self.engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO client (client_id, client_name, base_currency, created_at) "
                "VALUES ('existing', 'Existing client', 'GBP', '2026-09-27')"
            ))
        command.upgrade(self.cfg, "head")
        with self.engine.connect() as connection:
            self.assertEqual("Existing client", connection.execute(text(
                "SELECT client_name FROM client WHERE client_id = 'existing'"
            )).scalar_one())
        self.assert_schema_matches_metadata()


if __name__ == "__main__":
    unittest.main()

"""Frozen v2.44 upgrade evidence, independent of current metadata."""
from pathlib import Path
import tempfile
import unittest

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import MetaData, inspect, insert, select, text

from profit_doctor.persistence import Base, DatabaseConfig, build_engine
from tests.test_postgresql_live_qualification_v218 import alembic_config

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/v244_schema.sql'
NEW = {'evidence_graph_record'}


class GraphMigrationsV245(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.url = 'sqlite+pysqlite:///' + (Path(directory.name)/'migration.db').as_posix()
        self.cfg = alembic_config(self.url)
        self.engine = build_engine(DatabaseConfig(self.url))
        self.addCleanup(self.engine.dispose)

    def assert_head(self):
        self.assertEqual(set(Base.metadata.tables), set(inspect(self.engine).get_table_names()) - {'alembic_version'})
        with self.engine.connect() as c:
            context = MigrationContext.configure(c, opts={'compare_type': True, 'compare_server_default': True})
            self.assertEqual(('0008_economic_story',), context.get_current_heads())
            self.assertEqual([], compare_metadata(context, Base.metadata))
        for name in NEW:
            self.assertEqual([], inspect(self.engine).get_check_constraints(name))
            expected = Base.metadata.tables[name]
            actual = inspect(self.engine).get_foreign_keys(name)
            self.assertEqual({(tuple(f.column_keys), tuple(e.column.name for e in f.elements)) for f in expected.foreign_key_constraints},
                {(tuple(f['constrained_columns']), tuple(f['referred_columns'])) for f in actual})

    def test_clean_creation_and_repeat_head(self):
        command.upgrade(self.cfg, 'head')
        self.assert_head()
        command.upgrade(self.cfg, 'head')
        self.assert_head()

    def test_frozen_v244_all_tables_preserved_downgrade_and_reupgrade(self):
        statements = '\n'.join(x for x in FIXTURE.read_text(encoding='utf-8').splitlines() if not x.startswith('--'))
        with self.engine.begin() as c:
            for statement in statements.split(';'):
                if statement.strip():
                    c.exec_driver_sql(statement)
        old = MetaData()
        old.reflect(self.engine)
        self.assertEqual(25, len(old.tables)-1)
        self.assertFalse(NEW & old.tables.keys())
        expected = {}
        with self.engine.begin() as c:
            ids = {t.name: 'old-'+t.name for t in old.sorted_tables}
            for table in old.sorted_tables:
                if table.name == 'alembic_version':
                    continue
                row = {}
                for col in table.columns:
                    if col.foreign_keys:
                        fk = next(iter(col.foreign_keys)).column
                        value = ids[fk.table.name] if fk.primary_key else 'old-client'
                    elif col.primary_key:
                        value = ids[table.name]
                    elif str(col.type) == 'INTEGER':
                        value = 1
                    else:
                        value = {'document':'{"frozen":"preserve exactly"}', 'created_at':'2026-09-28T00:00:00+00:00',
                                 'currency':'GBP','base_currency':'GBP'}.get(col.name, 'legacy')
                    row[col.name] = value
                c.execute(insert(table).values(**row))
                expected[table.name] = row
        command.upgrade(self.cfg, 'head')
        self.assert_head()
        # Payload removal on downgrade is intentional; v2.44 records and foundation links/audits stay.
        with self.engine.begin() as c:
            for name in NEW:
                values = dict(link_id='old-evidence_link_v243', revision=1, client_id='old-client', run_id='old-engine_run', source_id='old-reasoning_object_v243', target_id='old-reasoning_object_v243', document='{"qualification":"payload"}')
                c.execute(insert(Base.metadata.tables[name]).values(**values))
        for revision in ('head', '0005_canonical_facts_findings'):
            if revision != 'head':
                command.downgrade(self.cfg, revision)
            with self.engine.connect() as c:
                for name, row in expected.items():
                    self.assertEqual(row, dict(c.execute(select(old.tables[name])).mappings().one()), name)
        self.assertEqual(set(old.tables), set(inspect(self.engine).get_table_names()))
        command.upgrade(self.cfg, 'head')
        self.assert_head()
        with self.engine.connect() as c:
            for name in NEW:
                self.assertEqual(0, c.scalar(text(f'SELECT count(*) FROM {name}')))

    def test_forward_migration_does_not_import_mutable_models(self):
        source = (ROOT/'alembic/versions/0006_evidence_graph.py').read_text(encoding='utf-8')
        for forbidden in ('profit_doctor', 'metadata', 'create_all'):
            self.assertNotIn(forbidden, source)
        self.assertIn("down_revision = '0005_canonical_facts_findings'", source)


if __name__ == '__main__':
    unittest.main()

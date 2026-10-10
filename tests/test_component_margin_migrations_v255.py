"""0017 preservation, additive margin schema and PostgreSQL DDL parity."""
import unittest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, select
from sqlalchemy.engine import create_mock_engine

from tests import test_component_margin_v255 as fixture
from tests.test_postgresql_live_qualification_v218 import alembic_config
from profit_doctor.persistence import Base, production_evidence_schema as legacy, production_qualification_schema as tables, measurement_schema


class ComponentMarginMigrationsV255(fixture.ComponentFixture, unittest.TestCase):
    def test_current_head_matches_metadata(self):
        with self.engine.connect() as connection:
            ctx = MigrationContext.configure(connection, opts={'compare_type': True, 'compare_server_default': True})
            self.assertEqual(ctx.get_current_heads(), ('0020_engagement_workspace',))
            self.assertEqual(compare_metadata(ctx, Base.metadata), [])

    def test_0017_data_preserved_on_downgrade_and_reupgrade(self):
        margin = self.margin_service.qualify(self.bind().binding_id)
        self.session.commit()
        expected = {}
        with self.engine.connect() as connection:
            for table in (legacy.monthly, legacy.absence, legacy.audit):
                expected[table.name] = [dict(r) for r in connection.execute(select(table)).mappings()]
            contexts = [dict(r) for r in connection.execute(select(measurement_schema.measurement_context).where(
                measurement_schema.measurement_context.c.context_id != margin.context.context_id)).mappings()]
        command.downgrade(alembic_config(self.url), '0017_production_evidence')
        self.assertNotIn(tables.binding.name, inspect(self.engine).get_table_names())
        with self.engine.connect() as connection:
            for table in (legacy.monthly, legacy.absence, legacy.audit):
                self.assertEqual([dict(r) for r in connection.execute(select(table)).mappings()], expected[table.name])
            self.assertEqual([dict(r) for r in connection.execute(select(measurement_schema.measurement_context)).mappings()], contexts)
        command.upgrade(alembic_config(self.url), 'head')
        command.upgrade(alembic_config(self.url), 'head')
        with self.engine.connect() as connection:
            for table in (tables.binding, tables.margin, tables.audit):
                self.assertEqual(list(connection.execute(select(table))), [])
            for table in (legacy.monthly, legacy.absence, legacy.audit):
                self.assertEqual([dict(r) for r in connection.execute(select(table)).mappings()], expected[table.name])

    def test_postgresql_ddl_preserves_all_component_scope_foreign_keys(self):
        statements = []
        engine = create_mock_engine('postgresql+psycopg://', lambda sql, *a, **kw: statements.append(str(sql.compile(dialect=engine.dialect))))
        Base.metadata.create_all(engine)
        for table in (tables.binding, tables.margin, tables.audit):
            ddl = next(s for s in statements if 'CREATE TABLE '+table.name+' ' in s)
            self.assertEqual(ddl.count('FOREIGN KEY'), len(table.foreign_key_constraints))
            self.assertIn('client_id', ddl)
        self.assertIn('CHECK', next(s for s in statements if 'CREATE TABLE '+tables.audit.name+' ' in s))

    def test_refused_margin_downgrade_removes_receipt_without_touching_components(self):
        self.components('3', '2')
        value = self.margin_service.qualify(self.bind().binding_id)
        self.assertIsNone(value.context)
        self.session.commit()
        command.downgrade(alembic_config(self.url), '0017_production_evidence')
        with self.engine.connect() as connection:
            self.assertEqual(len(list(connection.execute(select(legacy.monthly)))), 4)
            self.assertEqual(len(list(connection.execute(select(measurement_schema.measurement_context)))), 4)
        command.upgrade(alembic_config(self.url), 'head')

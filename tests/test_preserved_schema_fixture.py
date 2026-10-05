"""Portability and completeness checks for preserved SQL schema snapshots."""

import re
import unittest
from pathlib import Path

from sqlalchemy import MetaData, create_engine, inspect, select
from sqlalchemy.engine import create_mock_engine

from tests.preserved_schema_fixture import (
    load_preserved_schema_fixture,
    reflect_preserved_schema,
)


ROOT = Path(__file__).resolve().parents[1]
V252_FIXTURE = ROOT / 'tests' / 'fixtures' / 'v252_schema.sql'


def metadata_signature(metadata):
    """Describe all schema features represented by a reflected snapshot."""
    signature = {}
    for table in metadata.sorted_tables:
        signature[table.name] = {
            'columns': tuple((column.name, str(column.type), column.nullable,
                              str(column.default.arg) if column.default else None,
                              str(column.server_default.arg) if column.server_default else None)
                             for column in table.columns),
            'primary_key': (table.primary_key.name,
                            tuple(column.name for column in table.primary_key.columns)),
            'foreign_keys': tuple(sorted((
                tuple(constraint.column_keys),
                tuple(element.target_fullname for element in constraint.elements),
                constraint.name,
                constraint.ondelete,
                constraint.onupdate,
                constraint.deferrable,
                constraint.initially,
            ) for constraint in table.foreign_key_constraints)),
            'unique_constraints': tuple(sorted((
                constraint.name,
                tuple(column.name for column in constraint.columns),
            ) for constraint in table.constraints
                if constraint.__class__.__name__ == 'UniqueConstraint')),
            'checks': tuple(sorted((constraint.name, str(constraint.sqltext))
                                   for constraint in table.constraints
                                   if constraint.__class__.__name__ == 'CheckConstraint')),
            'indexes': tuple(sorted((index.name,
                                     tuple(column.name for column in index.columns),
                                     index.unique)
                                    for index in table.indexes)),
        }
    return signature


class PreservedSchemaFixtureTests(unittest.TestCase):
    def test_full_v252_fixture_reconstructs_equivalent_sqlite_schema_and_rows(self):
        frozen, frozen_rows = reflect_preserved_schema(V252_FIXTURE)
        target = create_engine('sqlite+pysqlite:///:memory:')
        try:
            created = load_preserved_schema_fixture(target, V252_FIXTURE)
            actual = MetaData()
            actual.reflect(bind=target)

            self.assertEqual(53, len(actual.tables))
            self.assertEqual(52, len(set(actual.tables) - {'alembic_version'}))
            self.assertEqual(metadata_signature(frozen), metadata_signature(actual))
            self.assertEqual(122, sum(len(table.foreign_key_constraints)
                                      for table in frozen.tables.values()))
            self.assertEqual(180, sum(len(constraint.elements)
                                      for table in frozen.tables.values()
                                      for constraint in table.foreign_key_constraints))
            self.assertEqual(24, sum(
                constraint.__class__.__name__ == 'UniqueConstraint'
                for table in frozen.tables.values() for constraint in table.constraints))
            self.assertEqual(14, sum(len(table.indexes) for table in frozen.tables.values()))
            with target.connect() as connection:
                for table in actual.sorted_tables:
                    rows = [dict(row) for row in connection.execute(select(table)).mappings()]
                    self.assertEqual(frozen_rows[table.name], rows, table.name)
            self.assertEqual({'alembic_version'},
                             {name for name, rows in frozen_rows.items() if rows})
            self.assertEqual('0014_priority_decision',
                             frozen_rows['alembic_version'][0]['version_num'])
            self.assertEqual(set(frozen.tables), set(created.tables))
        finally:
            target.dispose()

    def test_v252_fixture_compiles_as_complete_postgresql_schema_in_dependency_order(self):
        metadata, _ = reflect_preserved_schema(V252_FIXTURE)
        statements = []

        def capture(statement, *args, **kwargs):
            statements.append(str(statement.compile(dialect=mock.dialect)))

        mock = create_mock_engine('postgresql+psycopg://', capture)
        metadata.create_all(mock)

        create_table_statements = [
            statement for statement in statements
            if statement.lstrip().upper().startswith('CREATE TABLE')
        ]
        self.assertEqual(53, len(create_table_statements))
        created = set()
        postgres_table_ddl = {}
        for statement in statements:
            if statement.lstrip().upper().startswith('CREATE TABLE'):
                name_match = re.match(
                    r'\s*CREATE TABLE\s+"?([\w]+)"?', statement, re.IGNORECASE)
                self.assertIsNotNone(name_match, statement)
                name = name_match.group(1)
                postgres_table_ddl[name] = statement
                references = re.findall(
                    r'\bREFERENCES\s+"?([\w]+)"?', statement, re.IGNORECASE)
                for referenced in references:
                    self.assertIn(referenced, created | {name},
                                  f'{name} references {referenced} before it exists')
                created.add(name)
            elif statement.lstrip().upper().startswith('ALTER TABLE'):
                self.assertEqual(53, len(created),
                                 'deferred FK constraints must follow table creation')

        self.assertEqual(set(metadata.tables), created)
        self.assertEqual(388, sum(len(table.columns) for table in metadata.tables.values()))
        for table in metadata.tables.values():
            ddl = postgres_table_ddl[table.name]
            for column in table.columns:
                column_name = re.escape(column.name)
                type_name = re.escape(column.type.compile(dialect=mock.dialect))
                self.assertRegex(
                    ddl,
                    rf'(?m)^\s*(?:"{column_name}"|{column_name})\s+'
                    rf'{type_name}(?:\s|,|$)',
                    f'{table.name}.{column.name} is absent from PostgreSQL DDL',
                )
        self.assertEqual(122, sum(statement.count('FOREIGN KEY')
                                  for statement in create_table_statements))
        self.assertEqual(24, sum(statement.count('UNIQUE (')
                                 for statement in create_table_statements))
        index_statements = [statement for statement in statements
                            if statement.lstrip().upper().startswith('CREATE INDEX')
                            or statement.lstrip().upper().startswith('CREATE UNIQUE INDEX')]
        self.assertEqual(14, len(index_statements))
        version_ddl = next(statement for statement in create_table_statements
                           if 'CREATE TABLE alembic_version' in statement)
        self.assertIn('version_num VARCHAR(32) NOT NULL', version_ddl)


if __name__ == '__main__':
    unittest.main()

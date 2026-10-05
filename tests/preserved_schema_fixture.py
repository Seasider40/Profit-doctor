"""Construct preserved SQL snapshots portably for migration qualification.

The SQL fixture is the canonical frozen schema.  SQLite is used only as a
parser/reflection staging dialect; the reflected SQLAlchemy metadata is then
created on the requested target dialect so its normal dependency ordering and
cycle handling produce a valid schema without suppressing constraints.
"""

from pathlib import Path

from sqlalchemy import MetaData, inspect, select
from sqlalchemy.engine import Engine


class PreservedSchemaFixtureError(RuntimeError):
    """Raised when a preserved snapshot cannot be safely reconstructed."""


def reflect_preserved_schema(path):
    """Return reflected schema and rows from a canonical SQL snapshot.

    The snapshot is executed by in-memory SQLite, which accepts forward
    references in table DDL.  Foreign-key enforcement is enabled for fixture
    data validation; it is never disabled on the destination database.
    """
    from sqlalchemy import create_engine

    source = create_engine('sqlite+pysqlite:///:memory:')
    try:
        with source.connect() as connection:
            raw = connection.connection.driver_connection
            raw.execute('PRAGMA foreign_keys = ON')
            raw.executescript(Path(path).read_text(encoding='utf-8'))
            violations = raw.execute('PRAGMA foreign_key_check').fetchall()
            if violations:
                raise PreservedSchemaFixtureError(
                    f'Frozen fixture contains foreign-key violations: {violations!r}')

            metadata = MetaData()
            metadata.reflect(bind=connection)
            rows = {
                table.name: [dict(row) for row in connection.execute(select(table)).mappings()]
                for table in metadata.sorted_tables
            }
        return metadata, rows
    finally:
        source.dispose()


def load_preserved_schema_fixture(engine: Engine, path):
    """Reconstruct a frozen SQL fixture on SQLite or PostgreSQL.

    SQLAlchemy creates referenced tables in dependency order and handles
    cyclic foreign-key DDL using its dialect-aware DDL visitor.  The fixture's
    rows are copied after schema creation, retaining its Alembic checkpoint.
    The target must be empty so this cannot silently overlay another schema.
    """
    metadata, rows = reflect_preserved_schema(path)
    existing = inspect(engine).get_table_names()
    if existing:
        raise PreservedSchemaFixtureError(
            f'Refusing to load preserved schema over existing tables: {existing!r}')

    with engine.begin() as connection:
        metadata.create_all(connection)
        for table in metadata.sorted_tables:
            table_rows = rows[table.name]
            if table_rows:
                connection.execute(table.insert(), table_rows)
    return metadata

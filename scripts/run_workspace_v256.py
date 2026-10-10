"""Controlled single-operator launcher. Never reads a PostgreSQL URL or token."""
import argparse
from contextlib import contextmanager
import getpass
from pathlib import Path
import secrets
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from profit_doctor.persistence import DatabaseConfig, build_engine, session_factory
from profit_doctor.workspace.app import create_app
from profit_doctor.workspace.contracts import Operator
from profit_doctor.workspace.readers import production_reader
from profit_doctor.workspace.storage import EvidenceStore


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True, help='Durable local SQLite workflow database')
    parser.add_argument('--store', type=Path, required=True, help='Protected original-evidence directory')
    parser.add_argument('--client', action='append', required=True, help='Explicit authorised client ID; repeat for multiple clients')
    parser.add_argument('--legacy-database', type=Path, help='Existing legacy source registry, opened read-only')
    parser.add_argument('--initialize', action='store_true', help='Upgrade local workspace database through current migrations')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error('Unprivileged loopback port required')
    database = args.database.resolve()
    database.parent.mkdir(parents=True, exist_ok=True)
    url = 'sqlite+pysqlite:///' + database.as_posix()
    if args.initialize:
        cfg = Config(str(ROOT / 'alembic.ini'))
        cfg.set_main_option('script_location', str(ROOT / 'alembic'))
        cfg.set_main_option('sqlalchemy.url', url.replace('%', '%%'))
        command.upgrade(cfg, 'head')
    engine = build_engine(DatabaseConfig(url))
    try:
        with engine.connect() as connection:
            if MigrationContext.configure(connection).get_current_heads() != ('0020_engagement_workspace',):
                raise ValueError('Explicit local --initialize upgrade required before workspace use')
        operator = Operator(getpass.getuser(), frozenset(args.client))
        reader_factory = None
        if args.legacy_database:
            legacy = args.legacy_database.resolve()
            if not legacy.is_file():
                raise ValueError('Existing legacy registry required')
            @contextmanager
            def reader_factory(session):
                connection = sqlite3.connect(legacy.as_uri() + '?mode=ro', uri=True)
                connection.row_factory = sqlite3.Row
                try:
                    yield production_reader(session, connection, operator)
                finally:
                    connection.close()
        code = secrets.token_urlsafe(32)
        app = create_app(session_factory(engine), operator, EvidenceStore(args.store), port=args.port,
            access_code=code, reader_factory=reader_factory)
        print(f'Local workspace: http://127.0.0.1:{args.port}')
        print('One-session local operator access code (not financial-source authentication): ' + code)
        print('Protect this console and data directory. No remote access or production-readiness claim.')
        import uvicorn
        uvicorn.run(app, host='127.0.0.1', port=args.port, access_log=False, proxy_headers=False)
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()

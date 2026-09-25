"""Production persistence foundation for Profit Doctor.

The analytical engine remains sqlite3-compatible during the staged migration, while
new product/runtime persistence uses SQLAlchemy 2.x sessions. PostgreSQL is the
production target; SQLite is permitted only for deterministic local tests.
"""
from __future__ import annotations
from contextlib import contextmanager
from dataclasses import dataclass
import os
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DATABASE_URL = os.getenv("PROFIT_DOCTOR_DATABASE_URL", "sqlite+pysqlite:///:memory:")

@dataclass(frozen=True)
class DatabaseConfig:
    url: str = DEFAULT_DATABASE_URL
    echo: bool = False
    pool_pre_ping: bool = True


def build_engine(config: DatabaseConfig | None = None) -> Engine:
    cfg = config or DatabaseConfig()
    kwargs = {"echo": cfg.echo, "future": True, "pool_pre_ping": cfg.pool_pre_ping}
    if cfg.url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(cfg.url, **kwargs)
    if cfg.url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _sqlite_fk(dbapi_connection, _):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine


def session_factory(engine: Engine):
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False, autoflush=False, future=True)

@contextmanager
def session_scope(factory):
    """Own one transaction. Commit on success; rollback on any exception; always close."""
    session = factory()
    try:
        with session.begin():
            yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ping(engine: Engine) -> bool:
    with engine.connect() as con:
        return con.execute(text("SELECT 1")).scalar_one() == 1

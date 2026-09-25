# PostgreSQL Qualification Gate — v2.17

## Purpose
Convert the remaining live-PostgreSQL release gate into an executable qualification contract without pretending SQLite proves PostgreSQL behaviour.

## Implemented now
- Compile every SQLAlchemy table and index against the PostgreSQL dialect.
- Emit the complete metadata DDL through a PostgreSQL mock engine.
- Reject duplicate named constraints before deployment.
- Provide opt-in live PostgreSQL tests via `PROFIT_DOCTOR_POSTGRES_TEST_URL` for ping, commit, rollback and FK tenant-boundary enforcement.

## Live release gate
Static dialect compatibility is necessary but not sufficient. Production qualification remains OPEN until a real PostgreSQL service is supplied and the live suite is expanded/run for Alembic upgrade/downgrade, concurrent uniqueness races, transaction isolation, pooling/recovery and cross-tenant attacks.

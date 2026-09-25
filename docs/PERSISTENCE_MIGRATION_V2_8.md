# Profit Doctor v2.8 — Production Persistence Migration

## Decision
Production persistence is PostgreSQL + SQLAlchemy 2.x + Alembic. SQLite remains a local deterministic test/dev adapter while the existing 56-diagnostic SQL is migrated in controlled slices.

## Delivered in v2.8
- SQLAlchemy engine/session factory with explicit transaction ownership.
- Commit-on-success, rollback-on-exception, always-close session scope.
- Foreign-key enforcement in SQLite parity tests.
- Alembic migration environment and initial production schema migration.
- ORM foundation for Client, EngineRun and hardened OpportunityRelationship.
- Database-level uniqueness for canonical symmetric opportunity pairs.
- Tests for commit, rollback, FK/client boundary, duplicate relationship refusal, and Alembic upgrade/downgrade.

## Migration rule
Do not rewrite all 56 diagnostics in one high-risk change. Existing deterministic diagnostic calculations remain behaviourally frozen behind the legacy SQLite adapter while persistence is strangled across module boundaries. Every migrated slice must demonstrate result equivalence before legacy access is removed.

## PostgreSQL verification
The package includes the PostgreSQL driver dependency and Alembic configuration. A live PostgreSQL server is not available in this build environment, so live-server DDL/transaction/concurrency behaviour is not claimed as tested here. That is a release gate, not an assumed pass.

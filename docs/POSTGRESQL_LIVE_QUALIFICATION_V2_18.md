# PostgreSQL Live Qualification — v2.18

## Purpose
Turn the remaining database release gate into a fail-closed executable contract. v2.18 does **not** claim PostgreSQL qualification when no PostgreSQL service exists.

## Live attacks now encoded
When `PROFIT_DOCTOR_POSTGRES_TEST_URL` points at a disposable PostgreSQL database, the qualification runner tests:
1. Alembic upgrade to `head` and exact current metadata table presence.
2. Commit and forced rollback atomicity.
3. PostgreSQL FK rejection for an invalid tenant/client reference.
4. A true concurrent two-session uniqueness race for a symmetric overlapping opportunity relationship: exactly one transaction must commit.
5. READ COMMITTED visibility: an uncommitted row must not be visible to another session, then becomes visible after commit.
6. Repeated pool checkout plus dispose/reconnect recovery.
7. Alembic downgrade to `base` and clean re-upgrade to `head`.

The runner exits with code **2** if no PostgreSQL URL is supplied. This prevents CI or a human from interpreting skipped live tests as a PostgreSQL PASS.

## Evidence in this build environment
No PostgreSQL server/client binary or live qualification URL is available here. Therefore the live database gate remains **OPEN**, by design. The new contract tests pass locally and the existing PostgreSQL static-readiness tests continue to pass; live tests are skipped rather than simulated with SQLite.

## Important persistence-hardening observation
The current relational schema uses individual `client_id` and `run_id` foreign keys on many economic objects. Cross-client/run pairing is additionally enforced by controlled application service boundaries rather than composite database foreign keys throughout the whole model. That architecture has existing adversarial coverage, but a future production hardening pass should consider database-level composite tenant/run constraints for defence in depth before exposing uncontrolled write paths.

# Profit Doctor v2.7 — Engineering Attack Pass

## Scope
Pre-v1.0 adversarial engineering pass against v2.6, focused on persistence lifecycle, opportunity economics, relationship aggregation, and regression reliability.

## Changes
1. Added a canonical SQLite connection factory that initializes all 14 schema groups through one explicit runtime path. Historical wrapper definitions remain only for migration traceability.
2. Added defensive SQLite connection cleanup for legacy tests. Explicit close/context management remains the required application discipline.
3. Added a schema-template bootstrap for new ephemeral SQLite databases and retained idempotent schema bootstrap for existing databases.
4. Hardened symmetric opportunity relationships. Reverse duplicates for INDEPENDENT, OVERLAPPING, ALTERNATIVE, SYNERGISTIC and MUTUALLY_EXCLUSIVE are rejected before insertion. This prevents accidental double deductions in portfolio expected-value aggregation.
5. Added an adversarial regression test proving a reversed OVERLAPPING relationship cannot be inserted twice.

## Verification observed
- Economic + Adversarial SME + Risk/Controls selected gate: 28/28 PASS.
- New reverse symmetric relationship adversarial test: PASS.
- Full single-process historical regression remains too slow/non-deterministic in this environment and did not complete inside the extended watchdog window. This is NOT reported as a pass.

## Remaining release blocker
The persistence/test lifecycle is improved but not signed off. The historical suite still has many tests that do not explicitly close connections, and the full one-process suite remains unsuitable as a release gate. Before v1.0, migrate application persistence to the planned PostgreSQL/SQLAlchemy/Alembic layer and make connection/session ownership explicit. Then establish one canonical regression command with deterministic completion and warning-as-error policy.

## Economic invariant strengthened
A symmetric economic relationship may only affect portfolio aggregation once regardless of left/right insertion order. Directional relationships (DEPENDENT, SEQUENTIAL) remain directional and are not deduplicated by reversal.

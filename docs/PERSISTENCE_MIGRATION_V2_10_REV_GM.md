# Profit Doctor v2.10 — Revenue + Gross Margin Persistence Migration

## Scope
First diagnostic persistence batch: REV-01..REV-06 and GM-01..GM-07 (13 tests). Calculation logic is deliberately frozen. Legacy sqlite diagnostic outputs remain the behavioural oracle while the persisted diagnostic contract is moved to SQLAlchemy/Alembic.

## New production persistence contract
- `test_execution_v2` stores method, eligibility, status, limitations and signal count.
- `signal_v2` now preserves the full diagnostic signal contract: entity, period, observed/comparison/variance values, unit, materiality, status, evidence and primitive reference.
- `diagnostic_lineage_v2` preserves source-object lineage.
- Alembic revision `0003_rev_gm_diagnostics` establishes the new contract.
- `diagnostic_migration.migrate_rev_gm()` is tenant-scoped and refuses a run/client mismatch.

## Equivalence gate
The migration test executes the existing Revenue + Gross Margin engine against the portable Northstar fixture, migrates the resulting 13 executions, signals and lineage, then compares canonical legacy and SQLAlchemy representations exactly. High-risk PVM and margin economics are separately compared field-for-field.

Result: dedicated migration suite 4/4 PASS. Wider selected regression gate 50/50 PASS, including Revenue, Margin, v2.8/v2.9 persistence, Economic Engine, adversarial SME and Risk & Controls.

## Financial invariants retained
- PVM reconciliation remains exact and residual explicit.
- Margin movement remains impact, not automatically opportunity.
- Supplier-cost inflation/recovery cannot imply recoverability beyond evidence.
- Negative/abnormal margin signals remain forensic, not accusations.
- Decimal values are persisted losslessly as canonical strings during strangler migration.
- Cross-client diagnostic migration is refused.

## Remaining limits
This is a controlled persistence migration, not yet a calculation rewrite. The legacy diagnostic engine still performs the calculations; v2 persistence stores the resulting diagnostic contract. Live PostgreSQL integration/concurrency testing remains a release gate because no PostgreSQL server is available in this build environment.

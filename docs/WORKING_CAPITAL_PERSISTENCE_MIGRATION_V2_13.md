# Profit Doctor v2.13 — Working Capital & Cash Persistence Migration

## Scope
Migrates WC-01 through WC-07 diagnostic execution contracts, signals and lineage through the SQLAlchemy persistence path while leaving deterministic analytical logic frozen in the legacy reference engine during strangler migration.

## Acceptance gates
- 7/7 Working Capital diagnostic execution contracts migrate losslessly.
- Canonical old-vs-new execution and signal representations are identical.
- Exact signal economics/evidence match across WC-01..WC-07.
- Cross-client migration is refused.
- Cash guardrails survive persistence: inventory balance is not releasable cash; available cash is not available liquidity without evidenced facility headroom; cash release is not profit; profit-to-cash manifestation is not double counted.

## Test evidence
- v2.13 migration suite: 4/4 PASS.
- All diagnostic persistence migration suites through v2.13: 16/16 PASS.
- Working Capital diagnostic suite: 6/6 PASS.
- Economic Engine: 11/11 PASS.
- Adversarial SME Gate: 10/10 PASS.
- Risk & Controls: 7/7 PASS.

## Migration position
48/56 diagnostics have now crossed the production-persistence equivalence gate. Remaining: Forecasting & Performance Management (4) and Financial Risk & Controls (4).

## Known release gate
Live PostgreSQL integration/concurrency testing remains outstanding; equivalence tests use the SQLAlchemy SQLite test adapter. Legacy SQLite paths remain during strangler migration and are not the production target.

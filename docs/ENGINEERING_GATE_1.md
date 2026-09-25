# Engineering Gate 1 — Foundation Hardening

Status: **PASS for progression to Sprint 2 Trust Layer**

This gate was introduced after the v0.1 cold review. The purpose was to prevent the first executable proof from becoming an unsafe foundation merely because its happy path ran.

## Remediated findings
1. Canonical IDs are generated and client-safe; source identifiers are not global primary keys.
2. Financial arithmetic uses `Decimal`; SQLite harness persists financial decimals as text rather than binary float.
3. Transaction sales are correctly named `COMMERCIAL_NET_REVENUE`; accounting `FIN_REVENUE` is not fabricated.
4. Transaction revenue less direct product/service cost is `ECON_CONTRIBUTION_0`; accounting gross profit remains a separate future primitive.
5. Source evidence is copied to hash-addressed controlled storage and hash-verified.
6. Source File / Dataset / Dataset Version / Ingestion Job are distinct.
7. Financial transactions are never silently replaced.
8. Failed ingestion rolls back canonical writes and records a failed ingestion job.
9. Ingestion and audit activity link to the engine run.
10. Primitive queries are client and dataset-version scoped.
11. Primitive lineage records exact dataset version and reproducible input scope.
12. Required-column, decimal, identifier and duplicate-transaction validation is present for the Northstar adapter.
13. Automated regression coverage expanded from 2 tests to 9 substantive foundation tests.
14. Northstar known-answer assertions use exact decimal values.
15. Identical evidence is idempotent; changed evidence creates a new dataset version.
16. Restatement history is preserved rather than overwritten.

## Verified Northstar known answers
- Transactions: 15,087
- Commercial Net Revenue: £14,047,932.56
- Commercial Direct Cost: £9,110,927.70
- Contribution 0: £4,937,004.86
- Contribution 0 Margin: 35.14399602157543387295418508%

## Automated test gate
9 tests pass:
- schema
- hash stability
- client entity isolation
- Northstar exact known answers + lineage
- idempotent reprocessing
- immutable source evidence
- duplicate transaction rollback
- zero-revenue NOT_MEANINGFUL semantics
- restatement version preservation

## Boundary
This PASS means the **foundation is strong enough to build the Trust Layer on top of**. It does not mean production readiness, nor does it mean the 56 diagnostic tests have been implemented or validated.

## Next authorised sprint
**Sprint 2 — Trust Layer:** Availability → Quality → Mapping Coverage → Reconciliation → Financial Integrity → Economic Coverage → Test Eligibility.

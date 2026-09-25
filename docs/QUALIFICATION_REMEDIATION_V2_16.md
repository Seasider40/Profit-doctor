# Profit Doctor v2.16 — Qualification Remediation

## Purpose
Remediate the v1.0 qualification blocker caused by legacy SQLite/test resource lifecycle behaviour without expanding analytical scope.

## Changes
- Fixed unclosed CSV readers in foundation tests.
- Retained explicit SQLite connection ownership as the application contract.
- Added deterministic cleanup for the cached schema-template connection.
- Kept defensive legacy-fixture connection cleanup to prevent test/dev resource leakage.
- No diagnostic, economic, or opportunity logic was expanded.

## Evidence
Resource-warning strict high-risk run:
`python -W error::ResourceWarning -m unittest tests.test_foundation tests.test_economic_engine tests.test_management_benefit_engine tests.test_adversarial_sme_gate`

Result: 37/37 PASS with ResourceWarning promoted to errors.

A monolithic full-estate invocation remains too slow for the execution window; this is now a test-runtime/architecture issue rather than the previously reproduced file/connection warning defect. Production persistence remains PostgreSQL-targeted.

## Outstanding v1.0 gates
1. Live PostgreSQL integration/concurrency/isolation qualification — environment not available here.
2. Real anonymised SME validation — external datasets required.
3. Full estate should be moved to PostgreSQL-backed/partitioned CI and given an authoritative completion gate before production release.

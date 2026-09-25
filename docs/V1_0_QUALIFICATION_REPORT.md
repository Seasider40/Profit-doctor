# Profit Doctor v1.0 Qualification Programme — Gate Report

Date: 2026-09-25
Baseline: v2.14 (56/56 diagnostics migrated)
Hardened candidate produced by qualification: v2.15

## Executive verdict

**CONDITIONAL / NOT YET RELEASE-APPROVED AS v1.0.**

The diagnostic and economic-control architecture passed the targeted high-risk qualification gates after one newly discovered management/benefit integrity defect was fixed. Two external/release gates remain open: (1) clean authoritative whole-suite execution without the legacy SQLite/resource-lifecycle stall, and (2) live PostgreSQL integration/concurrency testing. Real anonymised SME validation also remains required before commercial confidence claims.

## Defect discovered and remediated

Qualification found that management/benefit APIs did not consistently enforce `run_id` ownership. A benefit could potentially be recorded under a new run while referencing an opportunity/action from another run belonging to the same client. Verification and retention also accepted a caller-supplied run without proving the benefit belonged to it. In addition, symmetric benefit relationships such as CASH_MANIFESTATION could be inserted in reverse order and therefore risk double deduction in portfolio aggregation.

v2.15 fixes these issues by:
- requiring opportunity + action + benefit to belong to the same client/run;
- requiring verify/retention operations to match the benefit's run;
- requiring related benefit legs to belong to the same client/run;
- rejecting reverse duplicates for symmetric benefit relationships (INDEPENDENT, CASH_MANIFESTATION, OVERLAPPING).

Three adversarial qualification tests were added and all pass.

## Qualification gates executed

| Gate | Result | Evidence |
|---|---|---|
| Management/benefit run integrity | PASS after remediation | New adversarial qualification tests 3/3 |
| Management & realised-benefit lifecycle | PASS | 7/7 |
| Opportunity economics / anti-double-counting | PASS | Economic Engine 11/11 |
| Adversarial accounting/data integrity | PASS | Adversarial SME Gate 10/10 |
| Financial risk/control restraint | PASS | Risk & Controls 7/7 |
| 56-diagnostic persistence migration contracts | PASS | Five migration suites 20/20 |
| High-risk targeted requalification total | PASS | **58/58** |
| Single-process authoritative whole regression | **RELEASE BLOCKER** | stalls; ResourceWarnings show legacy unclosed file/SQLite lifecycle debt |
| Live PostgreSQL integration/concurrency | **OPEN RELEASE GATE** | no live PostgreSQL service in this build environment |
| Real anonymised SME validation | **OPEN COMMERCIAL QUALIFICATION GATE** | synthetic/adversarial fixtures are not a substitute for real SME data |

## Whole-suite finding

The repository's canonical regression runner promotes `ResourceWarning` to error and attempts all tests in one process. During qualification it again stalled after a sequence of tests and emitted ResourceWarnings from historical test/fixture code. This means there is still no clean, deterministic, one-process PASS for the complete historical estate. Individual targeted suites remain reproducible and pass, but this is not sufficient for final production sign-off.

## Financial invariant assessment

The targeted gates continue to enforce the core economic invariants:
- Impact is not Opportunity.
- Exposure is not Expected Loss.
- Cash release is not Profit.
- Capacity released is not a saving until economic use is evidenced.
- Theoretical >= Addressable >= Expected where a theoretical ceiling exists.
- Addressable/Expected must remain inside a supported recovery envelope.
- Pricing gaps, supplier spend, overhead drift and duplicate-looking transactions do not become automatic savings.
- Profit-to-cash manifestation and overlapping benefits/opportunities are non-additive.
- Unsupported mechanism narrative cannot qualify opportunity economics.
- Cross-client and now cross-run economic writes are rejected at controlled service boundaries.

## v1.0 release decision

Do **not** label the current build production-ready v1.0 yet.

Required before release approval:
1. retire/refactor the remaining legacy raw-SQLite lifecycle path sufficiently that one authoritative regression command completes cleanly with no ResourceWarnings/stalls;
2. run Alembic migrations and persistence/integrity tests against a real PostgreSQL instance, including concurrent writes, uniqueness races, rollback/isolation, connection pooling and tenant separation;
3. rerun the full qualification matrix after those changes;
4. validate against multiple anonymised real SME datasets and compare findings with experienced FD review before making commercial accuracy/value claims.

## Recommended next engineering action

The immediate next action is **qualification remediation**, not new diagnostics: remove the remaining legacy connection/file lifecycle debt and establish one canonical CI regression command. Then provision a live PostgreSQL test environment and execute the database qualification gate.

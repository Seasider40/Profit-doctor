# Profit Doctor Pre-v1.0 Engineering Audit — v2.6

## Verdict
**CONDITIONAL PASS — not yet production-ready.** The financial-control philosophy is strong and the adversarial trust gate passes, but the audit identified one material opportunity-qualification control bypass and persistent database lifecycle/test-runner debt.

## Audit performed
- Replayed standard unittest discovery in one process with a 120s watchdog.
- Replayed Economic Engine, Management/Benefit, Risk/Controls and Adversarial SME suites independently.
- Inspected DB connection/schema construction, test discovery, opportunity qualification, relationship aggregation and unsafe execution patterns.
- Counted current discovered test functions: 145 after the new v2.6 bypass test (the previous v2.5 source contains 144 test functions; historical documentation counts differ because the suite evolved and prior runners used different discovery rules).

## Material finding fixed in v2.6 — opportunity qualification bypass
The public `qualify_opportunity_candidate()` function previously accepted narrative `evidence_basis` without requiring a persisted SUPPORTED `opportunity_mechanism_evidence` record. This meant code could bypass the intended mechanism-evidence gate even though an evidenced wrapper existed.

v2.6 makes supported mechanism evidence mandatory inside the core qualification function itself. The wrapper is no longer the only enforcement point. A new adversarial regression test proves direct qualification without mechanism evidence is refused. Duplicate `record_mechanism_evidence()` implementation was also removed.

This is financially important: Expected Opportunity £ must not be creatable merely because a caller supplies plausible prose.

## Database/resource lifecycle — still open
Single-process discovery still stalls in the Economic Engine area after accumulating many unclosed SQLite connections. ResourceWarnings confirm leaked connection objects. A forced-GC test runner did not make the full single-process estate deterministic within the audit window.

Root cause is primarily test/connection lifecycle discipline, amplified by repeated end-to-end fixture construction. Only a minority of test connection paths explicitly close their connection. The current `db.py` also builds schema through a long chain of redefined `connect()` wrappers, which is functional but unnecessarily difficult to reason about and migrate.

Required before production label:
1. One canonical connection/session lifecycle.
2. Context-managed DB usage in tests and application orchestration.
3. One schema initialisation path/migrations rather than chained `connect()` redefinitions.
4. Full suite must finish in one process with ResourceWarning treated as error.
5. PostgreSQL integration gate before production deployment.

## Regression observations
- Economic Engine after v2.6 hardening: 10/10 PASS independently.
- Management & Benefit Engine after v2.6 hardening: 7/7 PASS independently.
- Adversarial SME Gate: 10/10 PASS.
- Risk & Controls: 7/7 PASS.
- Single-process whole-suite: FAILS ENGINEERING GATE by timeout/resource lifecycle, not by observed assertion failure before the stall.

## Additional observations
- No `eval`, `exec`, `os.system` or shell execution was found in production engine code.
- Client/run matching is enforced in opportunity relationship creation.
- Opportunity funnel checks enforce non-negative economics, Expected <= Addressable, Addressable <= theoretical when theoretical exists, and both Expected/Addressable <= Recovery Envelope.
- Portfolio overlap/exclusivity arithmetic is conservative, but relationship uniqueness/canonicalisation should be hardened before large opportunity portfolios to prevent duplicate relationship rows from over-deducting value.
- SQLite is appropriate for prototype testing, not the intended production persistence layer.

## v1.0 release blockers
**P0:** close DB/resource lifecycle and achieve deterministic one-process regression.
**P0:** PostgreSQL migration/integration test and transactional rollback tests.
**P1:** opportunity-relationship uniqueness/canonicalisation and adversarial graph tests.
**P1:** full 56-test eligibility matrix by business model/data maturity, proving FULL/PARTIAL/UNAVAILABLE/N/A behaviour.
**P1:** numeric invariant/property tests for signs, zero denominators, credits/reversals, currency and period comparability.
**P1:** cross-client isolation tests expanded beyond accounting integrity to every economic/management object family.
**P1:** restatement/version propagation test proving dependent calculations/findings are invalidated and regenerated correctly.

## Release recommendation
Do not call the current build production-ready or final v1.0. Call it a strong pre-v1 diagnostic engine with a materially improved economic control gate. Complete the P0 items, then run the P1 matrix before productisation.

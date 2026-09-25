# Engineering Gate 4 — Full End-to-End Review

Date: 2026-09-24
Engine: v2.4 candidate, derived from v2.3 (56/56 diagnostic registry)

## Scope
1. Re-ran every test module in process isolation.
2. Re-ran the three synthetic SMEs (micro professional-services, mid-market product/distribution, large subscription/mixed-revenue) through the current v2.3/v2.4 chain: ingestion → trust → cross-source reconciliation → primitives → 56-test diagnostic registry → reasoning → economic stories.
3. Audited portability and test discoverability.

## Important defects found and remediated
- **Non-portable test fixtures:** many tests referenced `/mnt/data/profit_doctor_v1_2`; Gate-3 tests referenced `/mnt/data/pd_gate3/...`. The packaged engine could therefore appear healthy only in the original build environment. v2.4 vendors the required fixtures under `tests/fixtures/` and all test paths are package-relative.
- **Four Gate-3 tests were invisible to unittest discovery:** they were module-level pytest-style functions. v2.4 exposes them through `load_tests`, so the standard unittest gate sees them.
- **Single-process shutdown/resource debt remains:** the legacy suite can stall after many modules because older code/tests leave SQLite/file handles open. v2.4 adds a portable isolated regression gate (`scripts/run_regression_gate.py`) so all modules can be run deterministically while the underlying handle hygiene is remediated. This is containment, not a claim that the resource debt is solved.

## Regression evidence
Across isolated module runs, **134/134 test cases passed**. This includes the four previously undiscovered Gate-3 remediation tests. The monolithic one-process runner still stalls; therefore the engineering verdict is not an unconditional production-readiness pass.

## Three-business current-engine replay
All 56 diagnostics were registered for every business. Eligibility/graceful degradation correctly prevented unsupported tests from running.

- Micro (~£0.5m professional services): 41/56 completed, 200 signals, 40 findings/stories. All four cross-source reconciliations reconciled.
- Mid (~£5m product/distribution): 41/56 completed, 214 signals, 28 findings/stories. All four cross-source reconciliations reconciled.
- Large (~£50m subscription/mixed revenue): 40/56 completed, 205 signals, 27 findings/stories. All four cross-source reconciliations reconciled.

The principal non-runs are expected because the historical synthetic packs do not contain D11 workforce, supplier/purchase-detail or D13 plan/forecast evidence. The engine did not fabricate those analyses. The large scenario also did not force PRI-05 where no supported pricing candidate was available.

## Verdict
**CONDITIONAL PASS.** The economic/diagnostic architecture survived end-to-end replay and the complete isolated regression estate passes. However, before calling the engine productisation-ready, fix the underlying SQLite/file-handle lifecycle and then require the same 134-test estate to complete cleanly in one process. A subsequent adversarial-data gate should also inject malformed/missing/contradictory SME data into the now-portable fixtures.

# v2.42 — Full Estate CI & Cross-Platform Qualification

## Scope and authoritative command

The complete applicable automated estate is discovered from `tests/`; no passing
subset is used as a substitute. Run from the repository root:

```text
python -m pip install -r requirements-dev.txt
python scripts/run_full_estate.py --report qualification_outputs/v242/full-estate.json
```

`scripts_run_full_regression.py` delegates to the same runner. The runner refuses
to start if `PROFIT_DOCTOR_POSTGRES_TEST_URL` is set. Live PostgreSQL remains the
separate, explicitly invoked **v2.41 PostgreSQL Qualification** workflow, whose
workflow, test assertions and migrations are unchanged by v2.42. Its successful
Neon run is the reported v2.41 baseline, not evidence produced by this local run.

Full Estate CI runs on push, pull request and manual dispatch, on both Ubuntu and
Windows with Python 3.12 and 3.13. Each job discovers the same estate, treats
`DeprecationWarning` and `ResourceWarning` as errors, and uploads a JSON report
with individual outcomes and exact totals even when tests fail. Python 3.13 adds
SQLite's native unclosed-connection resource warning. Destructor-time exceptions
are explicitly recorded as test errors; warning filters alone can otherwise
print these errors without failing unittest. Garbage collection is used to
observe delayed warnings, not as connection/file lifecycle management.

Only the nine existing live PostgreSQL tests may skip: two v2.17 attacks and seven
v2.18 attacks. The five PostgreSQL static/contract tests execute locally. Any
other skip, expected failure, missing/duplicate outcome, or mismatch between
discovery and the classified module/test-count inventory fails the gate. A skip
is always reported as a skip, never a pass.

## Baseline investigation

Started from `origin/main` at `f0affc6c25334c12f3e0dd5e2b238347ee88ecc3`, after a
successful `git pull --ff-only origin main`. No source changes preceded the
baseline discovery. A preliminary `unittest discover -s tests -t .` failed before
running tests because `tests` lacked `__init__.py`; v2.42 makes it an explicit
package for stable imports/discovery.

The unchanged baseline command was:

```text
python -W error::DeprecationWarning -W error::ResourceWarning -m unittest discover -s tests -v
```

With live PostgreSQL and external workbook overrides unset, Windows/Python 3.12.14
ran **297 tests: 115 passed, 0 assertion failures, 173 errors, 9 skipped** in
508.520 seconds. The 173 errors comprise:

* **125 WinError 32 cleanup errors:** open SQLite handles prevented deletion of
  temporary databases. Test helpers returned connections without transferring
  explicit cleanup ownership. Some tests closed only on success; some setUp
  methods never closed connections or deleted named temporary files. The old
  connection destructor and post-test GC could not close a still-referenced
  connection before its temporary-directory context exited.
* **48 missing-workbook errors:** tests expected external Scenario-1/Scenario-2
  paths under `/mnt/data`, absent on a clean checkout and on Windows.

All original test assertion ASTs were compared against the baseline and remain
unchanged. The Gate-3 function tests are included via their existing `load_tests`
hook; they are not silently lost by choosing unittest.

## Corrections

Test resources are now registered at acquisition with their explicit owner:
`ExitStack.callback` inside temporary-directory scopes, or `TestCase.addCleanup`
for whole-test resources. Connections close and engines dispose before files
are removed, including setup/assertion failure paths. Fixture helpers accept
the caller's resource scope rather than relying on finalization. Existing
transaction/session assertions are retained.

Production ownership corrections cover the SQLite bootstrap, CLI, workbook
readers, unknown-workbook orchestration, upload/report orchestration and Level-3
builder. Internal resources close on exceptions as well as success. The
Level-3 builder still transfers its successful connection to the caller, but
closes it if construction fails. Workbook readers explicitly own both the
source stream and workbook. The SQLite destructor that masked missing owners
was removed; the shared in-memory schema template retains its explicit atexit
owner. No sleeps, retries or warning suppressions were added.

The original Scenario-2 demo file is used byte-for-byte. Scenario 1 is a clearly
labelled, generated synthetic regression contract, not a claimed reconstruction
of the missing workbook. Its existing assertions and fail-closed expectations
are unchanged. See `tests/fixtures/workbooks/README.md` for provenance, fixed
inputs, generation and override rules. `requirements-dev.txt` includes the
workbook dependency missing from the old test installation recipe.

Eleven new regressions cover inventory completeness, refusal of live credentials
by the non-live runner, deterministic fixture provenance, ownership during
bootstrap/CLI/intake/Level-3/report/parser failures, and enforcement of unraisable
resource warnings. No new diagnostic or economic rule was introduced.

## Inventory and local results

`qualification/test_estate_v242.json` classifies every module and records its
expected discovery count plus baseline pass/fail/error/skip totals. There are
**54 modules, 308 tests** after adding the eleven CI/lifecycle regressions.
The fixture flag identifies modules that required external workbooks at baseline;
other tests may use repository CSV/JSON fixtures or local synthetic rows.

| Module | Classification | Tests | Baseline errors | External workbook at baseline |
| --- | --- | ---: | ---: | --- |
| `test_accounting_trust` | intake/data-quality | 5 | 5 | No |
| `test_adversarial_sme_gate` | governance/security | 10 | 1 | No |
| `test_alembic_schema_v241` | persistence/migration | 5 | 0 | No |
| `test_crm_d15_v240` | CRM/Level-3 | 5 | 0 | No |
| `test_customer_expansion` | diagnostic | 7 | 7 | No |
| `test_diagnostic_engine` | diagnostic | 7 | 7 | No |
| `test_economic_engine` | reasoning/economic | 11 | 9 | No |
| `test_forecasting_expansion` | diagnostic | 6 | 0 | No |
| `test_foundation` | deterministic core | 9 | 8 | No |
| `test_full_estate_v242` | CI/resource lifecycle/fixture provenance | 11 | 0 | No |
| `test_gate3_remediation` | deterministic core | 4 | 0 | No |
| `test_granularity_handoff_v226` | intake/data-quality | 3 | 3 | Yes |
| `test_intelligent_intake_v224` | intake/data-quality | 5 | 5 | Yes |
| `test_interactive_drilldown_v236` | management/output | 5 | 5 | Yes |
| `test_level3_qualification_v239` | CRM/Level-3 | 3 | 0 | No |
| `test_longitudinal_advisory_v230` | longitudinal/benefit | 6 | 6 | No |
| `test_management_action_opportunity_v228` | management/output | 5 | 5 | Yes |
| `test_management_attention_v227` | management/output | 4 | 4 | Yes |
| `test_management_benefit_engine` | longitudinal/benefit | 7 | 7 | No |
| `test_management_output_spec_v233` | management/output | 6 | 6 | Yes |
| `test_margin_expansion` | diagnostic | 5 | 5 | No |
| `test_multi_client_governance_v232` | governance/security | 8 | 8 | No |
| `test_opportunity_portfolio_v229` | reasoning/economic | 5 | 5 | No |
| `test_people_expansion` | diagnostic | 6 | 0 | No |
| `test_period_basis_v222` | deterministic core | 1 | 0 | No |
| `test_persistence_cus_prod_pri_v211` | persistence/migration | 4 | 0 | No |
| `test_persistence_fcst_risk_v214` | persistence/migration | 4 | 0 | No |
| `test_persistence_peo_sup_v212` | persistence/migration | 4 | 0 | No |
| `test_persistence_rev_gm_v210` | persistence/migration | 4 | 0 | No |
| `test_persistence_v28` | persistence/migration | 5 | 0 | No |
| `test_persistence_v29` | persistence/migration | 3 | 0 | No |
| `test_persistence_wc_v213` | persistence/migration | 4 | 0 | No |
| `test_postgresql_live_qualification_v218` | PostgreSQL-static/live | 9 | 0 | No |
| `test_postgresql_readiness_v217` | PostgreSQL-static/live | 5 | 0 | No |
| `test_pricing_expansion` | diagnostic | 6 | 6 | No |
| `test_primitive_engine` | deterministic core | 16 | 16 | No |
| `test_product_expansion` | diagnostic | 6 | 6 | No |
| `test_product_view_model_v234` | management/output | 6 | 6 | Yes |
| `test_real_sme_qualification_programme_v219` | qualification-contract (not real-SME evidence) | 4 | 0 | No |
| `test_reasoning_engine` | reasoning/economic | 11 | 11 | No |
| `test_restatement_revision_v231` | longitudinal/benefit | 7 | 5 | No |
| `test_revenue_expansion` | diagnostic | 5 | 5 | No |
| `test_risk_controls_expansion` | governance/security | 7 | 0 | No |
| `test_supplier_overhead_expansion` | diagnostic | 7 | 0 | No |
| `test_trust` | intake/data-quality | 5 | 5 | No |
| `test_unknown_workbook_bridge_v225` | intake/data-quality | 3 | 3 | Yes |
| `test_unknown_workbook_intake_v223` | intake/data-quality | 4 | 4 | Yes |
| `test_upload_readiness_v238` | intake/data-quality | 5 | 0 | No |
| `test_upload_to_report_v237` | management/output | 5 | 5 | Yes |
| `test_v10_qualification` | longitudinal/benefit | 3 | 3 | No |
| `test_visual_prototype_v235` | management/output | 4 | 0 | No |
| `test_visual_prototype_v236` | management/output | 5 | 0 | No |
| `test_visual_readiness_v235` | management/output | 2 | 2 | Yes |
| `test_working_capital_expansion` | diagnostic | 6 | 0 | No |

The first full v2.42 run completed 308 tests: **299 passed, 0 failures, 0 errors,
9 live PostgreSQL skips**, with no policy errors. The final compatibility-entry-point
run (`python scripts_run_full_regression.py --report .venv/v242-final-full.json`)
also collected and ran exactly **308 tests: 299 passed, 0 failures, 0 errors,
9 live PostgreSQL skips**, with no expected failures, unexpected successes or
policy errors. It completed in 553.016 seconds on Windows 10 / Python 3.12.14,
with deprecation and resource warnings treated as errors. Both entry points
therefore exercised the same complete estate successfully. Linux and Python 3.13
remain pending execution by the configured CI matrix.

## Qualification boundary

A successful non-live gate establishes that all discovered applicable automated
tests passed together on that reported platform/dependency set. It checks the
existing deterministic arithmetic, economic guardrails, tenant boundaries,
confidence distinctions, FULL/PARTIAL/UNAVAILABLE/N/A behaviour, migration
contracts and output projections covered by those tests. The diagnostic registry
remains 56; this work introduces no diagnostic 57 or product functionality.

It does **not** establish live PostgreSQL semantics, production capacity,
concurrency or disaster recovery outside the separate v2.41 attacks. It does not
replace real-SME evidence, independent financial validation, security/penetration
review, user/product acceptance, Excel formula evaluation, or qualification of
the missing original Scenario-1 workbook. The Linux/Windows Python matrix is a
configured gate; only actually executed jobs are evidence. No remote CI run is
claimed before the changes are committed/pushed and Actions executes them.

## Final working-tree review

Against `origin/main`: 54 modified tracked files and 11 new files. All remain
unstaged and uncommitted. Existing assertion ASTs, test definitions and test
decorators are unchanged. Normalizing only the explicit resource-owner and
workbook-selection edits leaves every existing modified test AST identical
to the baseline. The v2.41 workflow, both PostgreSQL qualification modules,
the v2.41 Alembic schema regression, Alembic configuration and migrations are
unchanged. No credential patterns or accidental environment/cache/log/database
files were found in the change set. The new generated workbook is intentional;
it contains no macros or external workbook links. `git diff --check` passes.

| File | Status | Change |
| --- | --- | --- |
| `.github/workflows/full-estate-ci.yml` | New | Run the full non-live estate in the four-job Linux/Windows Python matrix. |
| `README.md` | Modified | Document the full-estate command and qualification guide. |
| `docs/V2_42_FULL_ESTATE_CI.md` | New | Record baseline, inventory, fixes, exact results, review manifest and qualification limits. |
| `profit_doctor/cli.py` | Modified | Close the internally owned SQLite connection on success and ingestion failure. |
| `profit_doctor/core/db.py` | Modified | Close failed bootstrap/template connections; remove the destructor that concealed missing ownership. |
| `profit_doctor/intake/bridge.py` | Modified | Scope workbook readers and the orchestration connection through exceptions. |
| `profit_doctor/intake/workbook.py` | Modified | Own source streams and workbooks explicitly, including parser failures. |
| `profit_doctor/product_demo.py` | Modified | Close the report connection when projection/export fails. |
| `profit_doctor/qualification_level3.py` | Modified | Close failed construction connections; retain caller ownership on successful return. |
| `qualification/test_estate_v242.json` | New | Classify every discovered module and record baseline/expected counts. |
| `requirements-dev.txt` | New | Include runtime requirements and pin openpyxl for workbook tests and fixture generation. |
| `scripts/run_full_estate.py` | New | Discover the full estate; enforce inventory, strict warnings and explicit skip policy; emit JSON results. |
| `scripts_run_full_regression.py` | Modified | Delegate the compatibility entry point to authoritative discovery. |
| `tests/__init__.py` | New | Make tests a package for stable complete discovery and cross-test imports. |
| `tests/fixtures/workbooks/README.md` | New | Document synthetic Scenario-1 provenance and unchanged original Scenario-2 identity. |
| `tests/fixtures/workbooks/scenario1_synthetic.xlsx` | New | Add the intentional reproducible synthetic Scenario-1 contract fixture. |
| `tests/resources.py` | New | Register connection closure, engine disposal and temporary-file removal with explicit owners. |
| `tests/test_accounting_trust.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_adversarial_sme_gate.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_crm_d15_v240.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_customer_expansion.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_diagnostic_engine.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_economic_engine.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_forecasting_expansion.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_foundation.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_full_estate_v242.py` | New | Add eleven discovery, exception-path ownership, warning-enforcement and provenance regressions. |
| `tests/test_gate3_remediation.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_granularity_handoff_v226.py` | Modified | use documented repository workbook fixtures, retaining external overrides. Existing assertions unchanged. |
| `tests/test_intelligent_intake_v224.py` | Modified | use documented repository workbook fixtures, retaining external overrides. Existing assertions unchanged. |
| `tests/test_interactive_drilldown_v236.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal; use documented repository workbook fixtures, retaining external overrides. Existing assertions unchanged. |
| `tests/test_level3_qualification_v239.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_longitudinal_advisory_v230.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_management_action_opportunity_v228.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal; use documented repository workbook fixtures, retaining external overrides. Existing assertions unchanged. |
| `tests/test_management_attention_v227.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal; use documented repository workbook fixtures, retaining external overrides. Existing assertions unchanged. |
| `tests/test_management_benefit_engine.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_management_output_spec_v233.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal; use documented repository workbook fixtures, retaining external overrides. Existing assertions unchanged. |
| `tests/test_margin_expansion.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_multi_client_governance_v232.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_opportunity_portfolio_v229.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_people_expansion.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_period_basis_v222.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_persistence_cus_prod_pri_v211.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_persistence_fcst_risk_v214.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_persistence_peo_sup_v212.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_persistence_rev_gm_v210.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_persistence_v28.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_persistence_v29.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_persistence_wc_v213.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_pricing_expansion.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_primitive_engine.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_product_expansion.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_product_view_model_v234.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal; use documented repository workbook fixtures, retaining external overrides. Existing assertions unchanged. |
| `tests/test_reasoning_engine.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_restatement_revision_v231.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_revenue_expansion.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_risk_controls_expansion.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_supplier_overhead_expansion.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_trust.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_unknown_workbook_bridge_v225.py` | Modified | use documented repository workbook fixtures, retaining external overrides. Existing assertions unchanged. |
| `tests/test_unknown_workbook_intake_v223.py` | Modified | use documented repository workbook fixtures, retaining external overrides. Existing assertions unchanged. |
| `tests/test_upload_to_report_v237.py` | Modified | use documented repository workbook fixtures, retaining external overrides. Existing assertions unchanged. |
| `tests/test_v10_qualification.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/test_visual_readiness_v235.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal; use documented repository workbook fixtures, retaining external overrides. Existing assertions unchanged. |
| `tests/test_working_capital_expansion.py` | Modified | Register explicit resource cleanup before temporary-file/directory removal. Existing assertions unchanged. |
| `tests/workbook_fixtures.py` | New | Resolve explicit workbook evidence and reproducibly generate synthetic Scenario 1. |

`git diff --stat origin/main` (tracked files only; the 11 new files above are
not included until staged):

```text
 README.md                                        |   8 +
 profit_doctor/cli.py                             |  30 ++--
 profit_doctor/core/db.py                         |  43 ++---
 profit_doctor/intake/bridge.py                   | 141 ++++++++--------
 profit_doctor/intake/workbook.py                 | 195 ++++++++++++-----------
 profit_doctor/product_demo.py                    |  58 +++----
 profit_doctor/qualification_level3.py            | 122 +++++++-------
 scripts_run_full_regression.py                   |  17 +-
 tests/test_accounting_trust.py                   |  22 +--
 tests/test_adversarial_sme_gate.py               |  42 ++---
 tests/test_crm_d15_v240.py                       |  26 +--
 tests/test_customer_expansion.py                 |  34 ++--
 tests/test_diagnostic_engine.py                  |  34 ++--
 tests/test_economic_engine.py                    |  50 +++---
 tests/test_forecasting_expansion.py              |   3 +-
 tests/test_foundation.py                         |  34 ++--
 tests/test_gate3_remediation.py                  |  22 +--
 tests/test_granularity_handoff_v226.py           |   3 +-
 tests/test_intelligent_intake_v224.py            |   3 +-
 tests/test_interactive_drilldown_v236.py         |   4 +-
 tests/test_level3_qualification_v239.py          |  16 +-
 tests/test_longitudinal_advisory_v230.py         |  30 ++--
 tests/test_management_action_opportunity_v228.py |   6 +-
 tests/test_management_attention_v227.py          |   6 +-
 tests/test_management_benefit_engine.py          |  34 ++--
 tests/test_management_output_spec_v233.py        |   6 +-
 tests/test_margin_expansion.py                   |  26 +--
 tests/test_multi_client_governance_v232.py       |  38 ++---
 tests/test_opportunity_portfolio_v229.py         |  26 +--
 tests/test_people_expansion.py                   |   3 +-
 tests/test_period_basis_v222.py                  |   6 +-
 tests/test_persistence_cus_prod_pri_v211.py      |  26 +--
 tests/test_persistence_fcst_risk_v214.py         |  26 +--
 tests/test_persistence_peo_sup_v212.py           |  26 +--
 tests/test_persistence_rev_gm_v210.py            |  26 +--
 tests/test_persistence_v28.py                    |   9 +-
 tests/test_persistence_v29.py                    |   5 +-
 tests/test_persistence_wc_v213.py                |  26 +--
 tests/test_pricing_expansion.py                  |  30 ++--
 tests/test_primitive_engine.py                   |  66 ++++----
 tests/test_product_expansion.py                  |  30 ++--
 tests/test_product_view_model_v234.py            |   6 +-
 tests/test_reasoning_engine.py                   |  50 +++---
 tests/test_restatement_revision_v231.py          |  26 +--
 tests/test_revenue_expansion.py                  |  26 +--
 tests/test_risk_controls_expansion.py            |   3 +-
 tests/test_supplier_overhead_expansion.py        |   3 +-
 tests/test_trust.py                              |  22 +--
 tests/test_unknown_workbook_bridge_v225.py       |   3 +-
 tests/test_unknown_workbook_intake_v223.py       |   5 +-
 tests/test_upload_to_report_v237.py              |   3 +-
 tests/test_v10_qualification.py                  |  17 +-
 tests/test_visual_readiness_v235.py              |  12 +-
 tests/test_working_capital_expansion.py          |   3 +-
 54 files changed, 825 insertions(+), 712 deletions(-)
```

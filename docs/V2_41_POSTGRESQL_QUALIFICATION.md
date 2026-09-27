# v2.41 PostgreSQL Qualification

This repository package is based on the Profit Doctor v2.40 source baseline and adds the
GitHub Actions harness needed to qualify the engine against a disposable/live PostgreSQL database.

## Safety boundary

The live PostgreSQL test suite is destructive by design. It drops the Profit Doctor metadata
schema at setup and performs an Alembic downgrade to `base` before upgrading to `head`.

**Never point `PROFIT_DOCTOR_POSTGRES_TEST_URL` at the production branch/database.**
Use only the dedicated Neon `v2-41-qualification` branch.

## Required GitHub secret

Create this repository Actions secret:

`PROFIT_DOCTOR_POSTGRES_TEST_URL`

Its value must be the direct PostgreSQL connection string for the dedicated qualification
branch/database. Do not commit the URL to this repository and do not paste it into source files.

## Run

GitHub -> Actions -> `v2.41 PostgreSQL Qualification` -> Run workflow.

The workflow:
1. installs the pinned-range Python dependencies including psycopg;
2. refuses to run if the PostgreSQL secret is missing or not PostgreSQL;
3. compiles source/tests;
4. runs PostgreSQL static readiness;
5. runs the destructive live PostgreSQL attacks;
6. runs persistence/migration regressions;
7. runs v2.40 CRM D15 and Level-3 qualification tests.

A green workflow is evidence for these automated gates only. It does not by itself close
real-SME validation, security review, UI/product validation, or every whole-estate CI concern.

## Repeated-run setup and schema audit

The qualification fixture drops all application tables before running migrations.
SQLAlchemy's metadata does not include `alembic_version`, so dropping the application
tables leaves the previous Alembic revision intact. On a reused database already at
head, `upgrade head` then does nothing. The first per-test cleanup fails on
`benefit_leg_v2` because it is first in reverse dependency order; all 16 application
tables are absent, not just the benefit table.

After the destructive drop, the fixture now stamps `base` and upgrades through the
complete migration chain. This reset belongs only to the disposable qualification
fixture; it is not a production repair procedure. No application tables are ignored
and none are created using `Base.metadata.create_all()` by this fixture.

The local audit of a fresh database upgraded through `0003_rev_gm_diagnostics` found
no schema drift against current `Base.metadata`:

| Revision | Application tables created |
| --- | --- |
| `0001_persistence_foundation` | `client`, `engine_run`, `opportunity_relationship_v2` |
| `0002_economic_backbone` | `primitive_result_v2`, `signal_v2`, `finding_v2`, `economic_story_v2`, `economic_impact_v2`, `economic_exposure_v2`, `opportunity_candidate_v2`, `opportunity_v2`, `decision_v2`, `action_v2`, `benefit_leg_v2` |
| `0003_rev_gm_diagnostics` | `test_execution_v2`, `diagnostic_lineage_v2` |

The audit covers 16 tables, 174 columns, 16 primary keys, 41 foreign keys, two unique
constraints and 14 indexes; neither metadata nor the migrated schema defines check
constraints. Column types, nullability and server defaults also match. No forward
production migration is required for the reproduced failure.

`tests.test_alembic_schema_v241` verifies the complete reflected SQLite schema,
compares PostgreSQL DDL compiled from migration-created objects with metadata,
tests repeated fixture setup and recovery from an empty schema with a stale head,
and checks downgrade/re-upgrade and data retention on an ordinary repeated upgrade.
These local checks do not substitute for executing migrations and qualification
attacks against live PostgreSQL. Existing migrations 0002 and 0003 import current
application metadata, so this audit describes the current checkout's migration chain.

### Local validation (2026-09-27)

Windows, Python 3.12.14, SQLAlchemy 2.1.1, Alembic 1.20.0. Test invocations used
`python -W error::DeprecationWarning -m unittest ... -v` with
`PROFIT_DOCTOR_POSTGRES_TEST_URL` cleared. The table below gives the latest result
for each requested module (all module names have the `tests.` prefix).

| Module | Passed | Errors | Skipped |
| --- | ---: | ---: | ---: |
| `test_alembic_schema_v241` | 5 | 0 | 0 |
| `test_postgresql_readiness_v217` | 3 | 0 | 2 |
| `test_postgresql_live_qualification_v218` | 2 | 0 | 7 |
| `test_persistence_v28` | 5 | 0 | 0 |
| `test_persistence_v29` | 3 | 0 | 0 |
| `test_persistence_rev_gm_v210` | 4 | 0 | 0 |
| `test_persistence_cus_prod_pri_v211` | 4 | 0 | 0 |
| `test_persistence_peo_sup_v212` | 4 | 0 | 0 |
| `test_persistence_wc_v213` | 4 | 0 | 0 |
| `test_persistence_fcst_risk_v214` | 4 | 0 | 0 |
| `test_economic_engine` | 2 | 9 | 0 |
| `test_management_benefit_engine` | 0 | 7 | 0 |
| `test_management_attention_v227` | 3 | 1 | 0 |
| `test_management_action_opportunity_v228` | 4 | 1 | 0 |
| `test_management_output_spec_v233` | 5 | 1 | 0 |
| `test_opportunity_portfolio_v229` | 0 | 5 | 0 |
| `test_longitudinal_advisory_v230` | 0 | 6 | 0 |
| `test_restatement_revision_v231` | 2 | 5 | 0 |
| `test_multi_client_governance_v232` | 0 | 8 | 0 |
| `test_crm_d15_v240` | 5 | 0 | 0 |
| `test_level3_qualification_v239` | 3 | 0 | 0 |
| **Total** | **62** | **43** | **9** |

Forty errors are existing Windows `WinError 32` cleanup failures: legacy tests leave
their SQLite `x.db` connections open when removing temporary directories. The
economic `test_concentration_candidate_has_no_invented_money` test reproduces this
in isolation without importing the qualification fixture. The other three errors
are missing external `scenario1.xlsx` files, one in each management module.

Run history: the five new tests passed alone, then the broad invocation reported
102 tests: 50 passed, 43 errors, nine skipped. That invocation included three module
import errors for missing `openpyxl`. After installing it only in the ignored local
environment, the three management modules ran 15 tests, all blocked by absent
external workbook paths. Setting their supported `PD_UWB2` override to
`demo/v237_scenario2/uploaded_source.xlsx` (checksum verified against its manifest)
allowed 12 to pass; the remaining three require scenario 1, which is not included
in the repository or bundled source ZIP. No assertions were changed or skipped to
work around these errors. Source compilation and `git diff --check` also passed.

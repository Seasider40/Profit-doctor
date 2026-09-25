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

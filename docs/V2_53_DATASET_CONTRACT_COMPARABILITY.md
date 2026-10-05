# Profit Doctor v2.53 — Governed Dataset Contract & Comparability

## Purpose and release boundary

v2.53 adds an auditable description of what an imported dataset is known to represent and a dimensional comparison of two such descriptions. Similar rows, matching totals, filenames and row counts are not population evidence. This foundation does not enable longitudinal findings, recurrence, worsening, recommendations, or AI decisions. v2.52 attention and temporal refusal behaviour remain unchanged.

## Architecture

`profit_doctor.reasoning.dataset` contains three layers:

- `contracts.py` defines immutable `DatasetContract`, human/system/source `DatasetAssertion`, `DatasetCoverage`, and dimensional `DatasetComparability` documents.
- `source.py` resolves existing legacy SQLite dataset, dataset-version and immutable-file lineage. Its first qualified capture is limited to the existing `D07_SALES_TRANSACTIONS` / `northstar:transactions` route.
- `service.py` provides caller-transaction-owned capture, human declaration revisions, comparisons and audit reads. `comparability.py` is the deterministic pure evaluator.

The legacy `dataset` and `dataset_version` records remain the import/source identity owner. The v2.53 canonical records add semantic claims without replacing importer metadata, Measurement Context, or any diagnostic contract. Cross-store source references use the existing scoped `LineageReference` convention; canonical persistence enforces client/run ownership and source-version/revision uniqueness.

## What the production capture establishes

The qualified Northstar sales route can verify the source dataset family, provider key, data domain, immutable source file and hash, import/version identity, completion state, observed imported-row count and observed date bounds. A retained snapshot digest includes the captured source metadata and ordered imported transaction rows, so a changed row invalidates a current snapshot even when count and date bounds stay the same.

Capture does **not** establish the commercial population, filters, business completeness, accounting/commercial definition, organisational scope, currency, unit, time basis, coverage completeness, or whether a version is a restatement versus a new observation. Those claims remain unknown until governed evidence supports them. The observed rows and bounds are technical observations; they are not completeness claims.

Only this existing sales route is enabled. Other domain/provider combinations fail closed. Source identity is obtained from the registered ingestion records, never inferred from a filename.

## Declarations and verification

Each claim can retain a declared value and a separate verified value. A declaration requires an identified human/management actor, explicit human authority and a timestamp. The caller remains responsible for authenticating that actor; an `Actor` object alone is not proof of identity. A declaration is evidence of what was stated, not proof that the statement is true.

Source/system verification retains its authority and lineage evidence independently. If verified evidence contradicts a declaration, the contradiction is retained and that dimension is a mismatch. A new declaration creates an immutable revision; previous revisions and audit records remain available. Replaying the same declaration against its prior revision returns the current identical revision.

## Comparability and temporal classification

Every assessment explains all eleven dimensions: dataset family, population, inclusion/exclusion basis, coverage, definition, organisational scope, currency, unit, time basis, source lineage and revision relationship. Each dimension records state, reason, evidence references and limitations. The overall result is one of `COMPARABLE`, `COMPARABLE_WITH_LIMITATIONS`, `NOT_COMPARABLE`, or `INSUFFICIENT_EVIDENCE`; there is no score.

Unknown claims yield insufficient evidence. Contradicted or different claims yield a mismatch. Complete and partial coverage do not silently match. Period basis and overlap are checked explicitly. Matching declarations can only produce a limited match. A restatement/correction/supersession/partial replacement is classified as revision-only. Same-period inputs or unknown revision relationships do not become new time evidence. `NEW_OBSERVATION` is a source-verified relationship classification, not permission to run temporal analysis; comparability and v2.52 downstream gates remain separate.

The evaluator never reads economic values, totals, row counts or calculated diagnostic outputs. Thus equal totals, row counts or apparent trends cannot supply missing population or definition evidence.

## Persistence and migration

Forward-only Alembic migration `0015_dataset_comparability` follows `0014_priority_decision`. It adds `canonical_dataset_contract`, `canonical_dataset_comparability`, and `canonical_dataset_audit`, with client/run ownership, immutable source-version revisions, scoped revision references, pair/policy uniqueness, and scoped comparison/audit foreign keys. Downgrade removes only these three v2.53 tables; it does not alter v2.52 tables or legacy imports. A preserved `tests/fixtures/v252_schema.sql` supports frozen-schema upgrade and data-preservation qualification. SQLite and PostgreSQL use the same SQLAlchemy/Alembic schema. Revision identifiers are regression-checked against Alembic's default `VARCHAR(32)` version column limit, which PostgreSQL enforces.

## Qualification

`test_dataset_contract_v253.py` covers dimensional matches/mismatches, missing population, differing filters/scope/family/currency/units, incomplete coverage, declaration authority, contradiction, revision semantics, serialization and cross-client refusal.

`test_dataset_contract_service_v253.py` covers the production source boundary, technical-only capture, replay/idempotency, immutable declarations/audit, source edits, client scope, caller-owned rollback and transaction persistence.

`test_dataset_migrations_v253.py` covers clean creation, repeat upgrade, upgrade from frozen v2.52, preservation of pre-existing rows across downgrade/re-upgrade, and schema/FK parity. `scripts/qualify_dataset_postgresql_v253.py` runs one fail-fast live suite that reuses the established v2.43-v2.52 live test classes, adds v2.53 migration/domain/service checks, and runs the v2.41 PostgreSQL resource/isolation gate once at the end. Earlier v2.43-v2.47 checkpoint migration tests are retained because the v2.52 cumulative runner did not include them. The v2.48 Measurement Context checkpoint and BIQ source assertions are also explicitly included. Repeated assertions already inherited through later test classes are not separately re-added.

Before its first PostgreSQL connection or destructive reset, the runner performs read-only Neon API GETs for the exact project, branch, and project endpoint collection. It requires project `tiny-meadow-46991842`, branch `br-royal-math-za046ex1` / `v2-41-qualification`, explicit `primary=False`, `default=False`, `READY` state, and one unambiguous enabled `read_write` endpoint whose host matches the direct, non-pooler PostgreSQL URL. The process must provide `PROFIT_DOCTOR_POSTGRES_TEST_URL` and `NEON_API_KEY` or `NEON_API_TOKEN`; values are not printed or written to reports. Missing credentials, unsafe branch metadata, URL/host mismatch, pooled hosts, or endpoint mismatch stop before PostgreSQL access. `--list-checks` prints offline discovery without credentials or database access.

Static `--list-checks` discovery returns **472 test cases** without Neon credentials, API calls, or a PostgreSQL connection. The runner executes all inherited and v2.53 cases in one `unittest` suite with `failfast=True`, strict deprecation/resource warnings, and final pool/unraisable checks. Its test order preserves the existing reset model: frozen checkpoint upgrades precede their persistence suites; v2.53 runs after inherited schema checks; the existing v2.41 live gate runs last because it resets the qualification schema. BIQ policy cases run as deterministic contract tests in the same suite, while its source-boundary assertions use canonical persistence directed to PostgreSQL.

The authoritative non-live estate discovered and ran **851 tests: 842 passed, 0 failed, 0 errors, and 9 legitimate live-PostgreSQL skips**. Strict deprecation/resource warnings passed, source/test compilation passed, and the estate inventory matched all **85/85** test modules. The nine live-only skips are not counted as passes.

The complete cumulative live qualification discovered and ran **472 checks: 472 passed, 0 failed, 0 errors, and 0 skipped** against PostgreSQL **18.6** on the independently verified disposable Neon `v2-41-qualification` branch (`primary=False`, `default=False`). It covered inherited v2.43-v2.52 checks, v2.53 clean and frozen-v2.52 migration paths, persistence and integrity, and the v2.41 resource/isolation gate. Final cleanup reported zero open connections, zero checked-out connections, and no unraisable resource errors. The primary/default Neon branch was not used.

## Deferred work and limitations

- No production population or completeness declaration is fabricated.
- No general dataset-family ingestion framework is added.
- Dataset comparability is not wired into REV-01 or any other diagnostic.
- v2.52 temporal assessment remains not assessed where its existing evidence contract requires more.
- No recurrence/worsening engine, urgency, controllability, materiality uplift, longitudinal benchmarking, recommendations, or AI/LLM behaviour is implemented.

The intended follow-on work may use this evidence layer only after separate architectural and qualification approval. The governing rule remains: business performance must not be compared across time until the underlying evidence is sufficiently comparable.

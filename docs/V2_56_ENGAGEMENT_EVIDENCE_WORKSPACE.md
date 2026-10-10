# Profit Doctor v2.56 — Engagement & Controlled Evidence Workspace

## Status and baseline

Architecturally approved release candidate with local and cumulative live PostgreSQL qualification complete. Subsequent user approval authorises final staged review, commit and push. Formal freeze remains pending all four cross-platform CI jobs. The accepted audit remains separately preserved in `V2_56_ADVISER_WORKFLOW_PRODUCT_READINESS_AUDIT.md`.

Starting `main`/cached `origin/main`: `dae614057623e012db24e7828d29fc2deb186a5c` (frozen v2.55.1). The only pre-existing untracked file was the accepted architecture audit. No remote baseline refresh or external deployment qualification is claimed.

## Implemented boundary

This is a single trusted adviser, local loopback application. It creates clients only within explicit operator grants, persists administratively scoped engagements, retains original evidence bytes, associates exact existing registrations, displays explicitly selected existing governed readiness snapshots, and tracks missing-information requests. It does not ingest, authenticate, reconcile, calculate, qualify or promote evidence.

The workflow is:

1. Launch against an explicitly selected local SQLite database and protected evidence directory, with explicit client grants.
2. Enter the process-lifetime local operator access code. Select/create an authorised client.
3. Create an engagement with entity, ledger and period declarations. These declarations are administrative, not verified source semantics. Scope is fixed; a different scope requires a different engagement.
4. Receive original files. Each receipt retains filename, exact SHA-256, byte count, actor/time, declared role, and optional predecessor. Replacement retains both receipt identities/bytes. Unsupported formats remain opaque; receipt is not accounting-pack acceptance.
5. Optionally associate a completed immutable existing dataset registration. Client ownership, retained registered bytes and exact receipt hash must match. Different normalized/transformed bytes are refused unless a separately qualified transformation adapter exists; none is invented here.
6. Select existing run/readiness owner identifiers. Current selections invoke existing current validation. Historical selections preserve the owning snapshot and are visibly historical; they cannot masquerade as current. Existing source authority remains unknown by default in the launcher.
7. Inspect governed readiness separately from legacy diagnostic coverage. Missing selections display no assessment, not an invented persisted NOT_ASSESSED result or whole-company score.
8. Record a question, evidence requirement, optional prerequisite reference/due date; associate received files; record an attributable administrative fulfilment review or withdrawal rationale.
9. Save, reload, close/reopen and inspect immutable revision/audit history.

## Reused authority and contracts

Existing SQLAlchemy `Client`, `EngineRun`, `Base`, `DatabaseConfig`, engine/session ownership and caller-owned transaction patterns are reused. Typed documents reuse the existing immutable Pydantic `Contract`, identifier validation and deterministic JSON serialization. Receipt filenames never become storage paths.

Read adapters call the existing legacy source registry, product projection, `ProductionEvidenceService`, production assessment/AR admission services and `EvidenceReadinessService`. Readiness scope is resolved from typed owned monthly/AR/temporal evidence; no encoded scope-string heuristic establishes semantics. A display period envelope is not population completeness or comparability.

No existing diagnostic/product consumer is switched to these workflow records. Frozen diagnostic Facts, monthly owners, AR admission, temporal assessment and analytical services retain their authority. Same economic family still does not imply same measurement owner/time basis.

## Evidence distinctions

| State | Authority |
|---|---|
| Received/uploaded | Workspace owns retained bytes and attributable receipt only |
| Registered | Existing completed immutable registration with exact matching bytes/client; not source authentication |
| Authenticated | Existing governed owner only; workspace cannot grant it |
| Reconciled | Existing reconciliation owner only; arithmetic/receipt is insufficient |
| Qualified | Existing qualified contract/readiness owner only; administrative review is insufficient |

`FULFILMENT_REVIEWED` means the adviser reviewed a request's received files. It does not mean the source is authentic, the population is complete or a financial capability is qualified. Legacy coverage is labelled `LEGACY_DIAGNOSTIC_COVERAGE_NOT_GOVERNED_READINESS` and explicitly does not establish entity/period semantic equivalence.

## Persistence and migration

Forward migration `0020_engagement_workspace` follows `0019_production_history`, adding seven administrative tables:

- `workspace_engagement`: stable identity/client/creation.
- `workspace_engagement_revision`: sequential immutable engagement documents.
- `workspace_receipt`: retained original identity/document and scoped predecessor.
- `workspace_registration_reference`: exact existing registered-source association.
- `workspace_information_request`: stable scoped request identity.
- `workspace_information_request_revision`: sequential immutable request documents.
- `workspace_audit`: actor, event, previous/result, timestamp and replay identity.

Client/engagement composite foreign keys, scoped receipt/request relationships, revision uniqueness and replay uniqueness are database-enforced. Services additionally enforce authorised clients, selected runs, declared scope, immutable owner validation and stale-revision refusal. There are no workspace update/delete APIs. This is an application audit trail, not protection against an OS/database administrator editing data directly.

Downgrade to 0019 intentionally removes workspace records/history only; legacy tables and their rows remain. Original file bytes are not automatically deleted by downgrade. Files are durably written before database references; caller rollback can leave a detectable content-addressed orphan. The store reports unreferenced hashes rather than deleting evidence automatically.

`tests/fixtures/v2551_schema.sql` is a schema-only checkpoint constructed from migrations through 0019, not evolving application metadata: 73 tables including Alembic bookkeeping, 540 columns, 198 FK constraints, 48 unique constraints and 15 indexes. Existing portable fixture construction handles PostgreSQL forward/cyclic FKs. Historical migrations and existing frozen fixtures are unchanged.

## Local security and lifecycle

Example local launch (replace the explicit paths and authorised client ID; this is not a PostgreSQL command):

```powershell
.\.venv\Scripts\python.exe .\scripts\run_workspace_v256.py --database C:\ProtectedWorkspace\workspace.db --store C:\ProtectedWorkspace\originals --client CLIENT_ID --initialize
```

Add `--legacy-database` only for an explicitly selected existing legacy source registry. The launcher opens that registry read-only. Existing canonical analytical owners must be in the selected migrated SQLAlchemy database; creating a new empty workspace database does not import existing owners automatically. No credential environment variable is read by this launcher.

The launcher binds only `127.0.0.1`, disables trusted proxy headers and access logging, and requires explicit client grants and an OS-derived actor. The browser cannot supply an actor or expand grants. Host/origin validation, a random process-lifetime access code, HttpOnly SameSite=Strict session cookie and CSRF token protect the local HTTP boundary. No CORS/public docs/API discovery are enabled. CSP, no-store, no-referrer and nosniff headers are applied; uploaded content is downloaded as an attachment rather than rendered as application-origin HTML.

File uploads are bounded to 50 MiB; traversal filenames, invalid digests, symlink hash targets and altered retained bytes fail closed. Request-scoped sessions and optional read-only legacy connections close deterministically; the launcher disposes its engine. The services never commit/close caller-owned sessions.

This is not multi-user or public SaaS authentication. The trusted OS operator must protect the console, evidence directory, SQLite database and backups. No production ACL, encrypted-storage, disaster-recovery or external penetration-test certification is claimed. The local access code is not source-authority evidence.

## Qualification

Windows, repository Python 3.12.14, strict DeprecationWarning/ResourceWarning errors:

- Final focused estate: 53/53 PASS (25 workflow, 8 HTTP, 5 migration, 11 existing-owner reader, 4 offline live-runner tests).
- Source/tests/scripts/migrations compilation: PASS.
- Final authoritative full estate: 1,342 discovered/run; 1,333 PASS; 0 FAIL; 0 ERROR; 9 legitimate live-only SKIPs; 110/110 modules inventoried; strict-warning/resource policy PASS (`policy_errors=[]`). Windows Python 3.12.14, 2,133.578 seconds. Skips are not passes.
- Following external-whitespace normalization of the new SQL fixture, all 88 DDL statements plus its checkpoint insert were independently compared with the original migration-created SQLite schema; no semantic change. The five focused migration checks passed again. The final estate used the normalized fixture.
- Static cumulative live discovery: 743 inherited checks plus 41 workspace/migration/reader checks = 784 unique checks; no duplicates. Final inherited v2.41 resource/isolation gate retained last.
- Approved uninterrupted cumulative live PostgreSQL: 784 collected/run; 784 PASS; 0 FAIL; 0 ERROR; 0 SKIP. PostgreSQL 18.6, independently verified disposable `v2-41-qualification` branch, `primary=false`, `default=false`; zero open connections, checked-out connections and unraisable resource errors. All 743 inherited checks remain included. The retained local report records 24,044.688 seconds; the supplied completion result records 24,033.566 seconds. Both are approximately 6 hours 40 minutes; the small timing discrepancy is retained rather than silently reconciled.
- Cross-platform GitHub matrix: pending execution after release-candidate push; formal freeze requires Ubuntu/Windows with Python 3.12/3.13 all passing.

Coverage includes client/engagement isolation, grants/spoof refusal, replay/revision conflicts, durable originals/replacements, altered-byte refusal, request lifecycle/rationale, caller-owned rollback, DB FKs, clean metadata equivalence, frozen upgrade, downgrade/re-upgrade preservation, PostgreSQL DDL and portable fixtures, source registration identity, current/historical readiness, exact typed scope, and proof that workflow operations do not change analytical-owner rows.

The browser was exercised using synthetic local data only: client/engagement creation, two original receipts, missing-information receipt association and administrative review, closure/reopening and reloading persisted history. No private workbook/source authority was used. HTTP/adaptor tests qualify the added current/historical selection boundary; the browser exercise does not certify real-client usability or external deployment.

Dependency bounds keep the tested FastAPI/Starlette and AnyIO combination compatible with strict-warning HTTP tests; no warning suppression was added. HTTP test transport uses development-only httpx. Existing strict-warning estate commands/workflow remain unchanged.

## Non-goals and limitations

No automatic intake or analytical execution, general source authentication, new financial calculation, temporal activation, causality, AI recommendation, adviser Decision writer, client publication/report export, Action/Benefit behaviour or v2.57+ capability is implemented.

Owner selection currently requires explicit existing identifiers. Source-authority enrolment and qualified transformation lineage remain separately governed integration work. The structured evidence/readiness/history presentation prioritises exact meanings; a broader adviser usability/operational pilot remains to be qualified. Unavailable current trust fails closed; historical display cannot repair missing current prerequisites.

## Changed-file inventory

New implementation:
`profit_doctor/workspace/{__init__.py,contracts.py,storage.py,service.py,readers.py,app.py,index.html,ui.js,ui.css}`;
`profit_doctor/persistence/workspace_schema.py`;
`alembic/versions/0020_engagement_workspace.py`;
`scripts/run_workspace_v256.py`;
`scripts/qualify_workspace_postgresql_v256.py`.

New qualification/documentation:
`tests/fixtures/v2551_schema.sql`;
`tests/test_workspace_v256.py`;
`tests/test_workspace_http_v256.py`;
`tests/test_workspace_migrations_v256.py`;
`tests/test_workspace_readers_v256.py`;
`tests/test_workspace_runner_v256.py`;
this engineering document.

Additive registration/dependencies:
`profit_doctor/persistence/__init__.py`;
`qualification/test_estate_v242.json`;
`requirements.txt`;
`requirements-dev.txt`.

Current-head constants only:
`scripts/qualify_dataset_postgresql_v253.py`;
`scripts/qualify_production_postgresql_v255.py`.

Legitimate expected-head advancement only (0019 to 0020):
`tests/test_canonical_migrations_v244.py`;
`tests/test_component_margin_migrations_v255.py`;
`tests/test_dataset_migrations_v253.py`;
`tests/test_economic_bridge_migrations_v248b.py`;
`tests/test_economic_impact_migrations_v249.py`;
`tests/test_graph_migrations_v245.py`;
`tests/test_hypothesis_migrations_v246.py`;
`tests/test_measurement_context_migrations_v248.py`;
`tests/test_opportunity_migrations_v250.py`;
`tests/test_priority_migrations_v251.py`;
`tests/test_production_evidence_migrations_v255.py`;
`tests/test_production_history_migrations_v255.py`;
`tests/test_production_history_v255.py`;
`tests/test_production_runner_v255.py`;
`tests/test_receivables_migrations_v249.py`;
`tests/test_story_migrations_v247.py`;
`tests/test_temporal_migrations_v254.py`;
`tests/test_temporal_runner_v254.py`.

The pre-existing accepted audit is preserved unchanged. Ignored `.venv` logs, qualification JSON, disposable SQLite/browser data and temporary verification artifacts are local-only and must not be staged.

Final commit inventory: 44 intended implementation/qualification/documentation files (24 tracked modifications, 20 new files), plus the separately reviewed and preserved architecture audit: 45 files total. All 43 qualified source/test/configuration/fixture hashes and the original audit hash remain unchanged; only this engineering document was updated after qualification. Historical migrations 0001–0019, existing frozen fixtures, analytical source, the v2.41 live gate and v2.42 workflow/resource policy are unchanged. Existing test edits are exact current-head substitution only. No credential, private workbook, grading, cache, database or generated qualification-result file is included in the intended set; runtime/test artifacts remain ignored local-only.

## Live qualification duration review

The retained live report records aggregate elapsed time and per-check status, but no per-check duration, SQL timing, lock samples or network telemetry. All 784 checks passed without retries or recorded connection/resource errors. This does not establish whether latency, locks, contention or unrecorded network delays contributed to the long run.

Repository inspection identifies repeated expensive setup as a plausible contributor: the inherited live-class adapter restores the current schema before each adapted test, and migration qualification also performs checkpoint construction, upgrade, downgrade and re-upgrade. That repeated work is verified in the runner, but its share of elapsed time cannot be quantified from the retained report. No runner or test was changed for this release. Future separately approved performance investigation should measure setup/test/teardown durations, migration and fixture construction time, database round trips and lock waits before proposing any optimization; fail-fast, inherited assertions, checkpoint isolation and resource accounting must remain intact.

## Subsequent gates

Architectural and live qualification reviews are approved. Final staged review and the authorised release-candidate commit/push are followed by four-job cross-platform CI. This document does not declare v2.56 frozen or production SaaS ready. No v2.57 work is authorised here.

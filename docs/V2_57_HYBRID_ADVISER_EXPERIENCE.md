# Profit Doctor v2.57 — Hybrid Adviser Experience

## Candidate status and baseline

Implementation candidate for architectural review, not a frozen release. No staging, commit, push, CI trigger or live PostgreSQL execution is authorised by this document.

Frozen predecessor: `37a9e63617c4764383f36bd638c59ba1fd095ec3`. Before implementation, HEAD, local main, cached origin/main and independently queried remote main matched; the only untracked file was the approved architecture contract. That contract remains unchanged: `V2_57_HYBRID_ADVISER_EXPERIENCE_ARCHITECTURE.md`, SHA-256 `9ac820d591438b5f34e7523d1f202d2a59da4b1b5d9c296e957092fb0efe579a`.

This release implements an administrative adviser experience on the frozen evidence architecture. It does not integrate analytical execution or financial publication.

## User journeys and actual interface

The home screen lists only granted businesses, Business Reviews newest-created first, outstanding information counts and resumable setup. Name search filters the displayed businesses/review page; it is not a global search or a claim about recent user access. Reviews are paginated in bounded pages of 50. Business creation chooses an unused existing client grant; the browser cannot expand grants or fabricate an authorised client identity.

Guided setup has three stages: Business details; Financial documents; Review and continue. Save and exit retains incomplete fields without an invalid engagement. Continue from complete business details materialises one strict fixed-scope engagement. Uploads are optional and belong to that engagement. Back retains saved scope and original receipts. Final completion marks administrative setup only, never qualification. Reopening a frozen v2.56 review bypasses setup and retains its ownership/history.

Entity/ledger choices are explicit reuse of a prior review's declared pair or new administrative UUID identities. They are not source authentication, canonical entity registration or a mapping to qualified financial records. Exact source correspondence remains the responsibility of frozen governed services.

Review navigation separates Overview, Financial Documents, Information Check, Information Needed and Activity History. Fragment routes carry only opaque selection identities and section names; each changed selection is loaded through scoped APIs. Browser history, refresh and per-tab selection restoration are qualified independently. Technical identifiers, hashes and raw documents are hidden in expandable disclosures. Business Analysis, Adviser Decisions and Client Reports are explicitly unavailable.

Original-file cards show declared category, readable timestamp, byte count, extension labelled as unvalidated content type, receipt/registration limitations, retained predecessor information and original download. Upload results are per-file; batch failure does not erase successful receipts or claim all files saved. An additive encoded filename header preserves UTF-8 filenames while retaining the old header contract.

Information Check displays the frozen nine domains and owner-provided statuses. Empty selection means no assessed information selected for this review, not absence of verified information anywhere. Missing/incomplete/conflicted/unavailable/current/historical states remain distinct. Known prerequisite codes receive narrow plain-English explanations; unknown codes remain conservative and available in Technical Details. No readiness score is computed. Receiving a file or reviewing a request never unlocks an analytical capability.

Information requests retain the frozen OPEN, EVIDENCE_RECEIVED, FULFILMENT_REVIEWED and WITHDRAWN transitions. The interface says Information requested, Information received, Request reviewed and Request withdrawn. Receipt associations and rationale remain administrative. Request history and attributable setup history are available without editing prior events.

Save messages identify the actual acknowledged operation/revision. Busy state prevents conflicting UI operations. Network-uncertain writes are not labelled saved; operation identities are retained in memory for the same payload rather than silently regenerated. No automatic assertion or mutation retry is configured.

## Modules and API mapping

| Area | Implementation |
|---|---|
| Layout/navigation/presentation | Existing `workspace/index.html`, `ui.css`, `ui.js`, updated without a new frontend framework |
| Operator lifetime | New `workspace/session.py`; integrated into existing `workspace/app.py` |
| Administrative drafts | New `workspace/setup.py` with `SetupFields`, `SetupDraft`, `SetupService` |
| Home summaries | New `workspace/home.py`; bounded grant-scoped queries, no original hashing or analytical writes |
| Persistence | New `persistence/setup_schema.py`, additive registration in persistence package |
| Local launch | `scripts/run_workspace_v257.py` delegates to the supported existing local launcher; its head guard advances to 0021 |
| Existing evidence/readiness | Frozen `WorkspaceService`, `OwnedEvidenceReader`, receipt store and governed readiness services reused unchanged |

Additional local routes:

- `GET /workspace/session`: authenticated session metadata/CSRF recovery, no operator code or cookie value.
- `POST /workspace/session/renew` and `/end`: CSRF-protected explicit renewal/sign-out.
- `GET /workspace/home`: bounded administrative review/request summaries and granted clients.
- `GET /clients/{client}/setup-drafts`: scoped bounded draft list.
- `GET /clients/{client}/setup-drafts/{draft}` and `/history`: owned draft/current revision and attributable retained history.
- `POST /clients/{client}/setup-drafts`: typed fields, expected revision, explicit operation and idempotency key.

Existing client/review/receipt/registration/request/readiness/coverage APIs retain their authority and compatibility. The workspace response adds a separate `setup_history` projection; frozen engagement audit records are not rewritten. Administrative scope and typed owned readiness validation remain separate.

## Session and security decisions

Local-only deployment remains mandatory: IPv4 loopback bind, exact Host, mutation Origin, CSRF, HttpOnly SameSite=Strict browser-session cookie, no CORS/proxy trust, no-store/CSP and attachment downloads. The single OS-derived operator and explicit grants remain authoritative; HTTP JSON cannot supply actor, grant expansion or evidence verification flags.

The host uses a monotonic server clock, 60-minute inactivity and eight-hour absolute limits. Introspection does not extend inactivity. Protected user data access or explicit renewal can extend idle time within the absolute limit. Sign-out revokes the token and deletes the cookie; a fresh login rotates session/CSRF values and may invalidate other tabs. Restart requires the new console code. The UI gives a five-minute warning and a Keep working action; browser timers do not confer server authority.

Refresh recovers CSRF only after a valid authenticated cookie. Access code and CSRF stay out of localStorage/sessionStorage, URLs, persisted draft documents and logs. Per-tab sessionStorage holds only versioned selection pointers, revalidated against grants and owned APIs before rendering. Changing scope clears previously rendered data; late responses are guarded. Signing out clears pointers and rendered business data. Unsaved form work is not durably saved by a session/selection pointer; expiry or closing the tab may require re-entering unsaved edits, while server-saved work is retained.

The local HTTP cookie is not claimed to be suitable for public SaaS deployment. There is no remote authentication, grant administration, trusted issuer enrolment or source-authority expansion. Application append-only history is not protection against an OS/database administrator altering files directly.

## Migration and transaction ownership

Forward migration `0021_adviser_setup` follows frozen `0020_engagement_workspace`; revision length is 18, within Alembic's VARCHAR(32) limit. It adds exactly:

1. `workspace_setup_draft`: immutable draft/client identity and creation.
2. `workspace_setup_revision`: sequential typed snapshots, predecessor, actor/time/event, operation digest/key; each revision is its audit event.
3. `workspace_setup_review_link`: one-time same-client draft/review association, never retargeted.

Composite scoped FKs, positive/sequential revision CHECKs, non-null predecessors after revision 1, replay uniqueness and one-draft/one-review linkage are enforced. No placeholder entity/period or new evidence status is inserted into frozen engagement models. Materialisation, linkage, draft revision and existing review audit share the caller-owned transaction; the new service never commits/closes the caller session.

Clean creation, actual migration-defined 0020 checkpoint upgrade, legacy-row preservation, caller rollback, PostgreSQL DDL, FK/CHECK refusal, downgrade/re-upgrade and full metadata equality are covered. Downgrade intentionally removes new draft records/history/links only, retaining v2.56 records and original files; re-upgrade does not invent old draft histories.

Historical migrations 0001–0020 and all frozen SQL fixtures are unchanged. Existing migration assertions advance expected head to 0021. One preserved-v2.55.1 comparison also explicitly excludes the three named new setup tables in addition to the seven existing workspace tables; its exact frozen table equality and metadata comparisons remain asserted. New preservation tests independently snapshot all pre-setup tables. No schema assertion is skipped or weakened.

## Qualification record

- Repository Python 3.12.14; strict DeprecationWarning/ResourceWarning policy retained.
- New focused tests: 47 PASS (21 draft, 12 session/HTTP, five migration, six home, three offline runner checks).
- Frozen v2.56 compatibility: 53 PASS; combined focused/compatibility gate 100/100 PASS.
- Real-browser gate: 15/15 PASS, zero failures/errors, graceful test-server/browser cleanup; isolated headless Edge using bundled Playwright 1.62.1 and synthetic local SQLite only. Covers invalid-scope refusal, partial save/resume, Back/Continue, receipt bytes/non-promotion, request revisions, refresh, historical empty selection, client refusal/storage tampering, scoped browser Back/Forward, five viewport widths, keyboard focus, untrusted text escaping/visible-text contrast, setup pagination beyond 50 drafts, sign-out/expiry and process restart.
- Source/test/script/migration in-memory compilation and JavaScript syntax checks PASS.
- Authoritative discovery: 1,389 tests / 115 modules; inventory consistency PASS. Final full-estate execution: 1,389 discovered/run, 1,380 PASS, 0 FAIL, 0 ERROR, nine legitimate live-only SKIPs, 115/115 modules, strict/resource policy PASS (`policy_errors=[]`), 2,093.625 seconds. Skips are not passes.
- Cumulative live discovery: 816 unique checks, zero duplicates; all 784 inherited checks retained; 32 new service/home/migration checks. Final v2.41 resource/isolation tail retained. Missing-credential refusal and offline delegation/checkpoint registration checks PASS. Live PostgreSQL was not run at that initial checkpoint; the final approved live result is recorded below.
- `git diff --check` and final credential/artifact review: PASS. Nothing staged; 47 intended files (30 tracked modifications, 17 new including the preserved architecture contract). No credential, private financial workbook, qualification result/log, cache or database is included.

The first sandbox-only focused attempts could not open/clean temporary SQLite paths due execution-environment ACL restrictions (WinError 5); no product suppression, sleeps or resource retry was added. Focused/local qualification uses an authorised process outside that sandbox and isolated temporary directories. One inherited schema comparison failed because the new additive tables were not yet represented in its expected-set calculation; the explicit adjustment above preserves its assertion. Browser testing then exposed and corrected initial unsaved-draft/history routing. These were reported before correction; final focused/browser results are separate from failed development runs.

During the full Python estate, only the HTML/JavaScript presentation assets and the standalone browser qualification script received the final routing/form/pagination regressions; Python source, tests, migrations, configuration and fixture hashes remain unchanged from estate start. The final browser gate qualifies those final UI files separately. No financial/evidence engine file was changed during implementation. No live gate or expensive suite was retried unchanged to force a passing assertion.

## CI and local operation

Existing Full Estate CI remains unchanged: Ubuntu/Windows × Python 3.12/3.13, strict warnings, exact-result retention, fail-fast=false, Ubuntu 45-minute and Windows 60-minute limits. An additive `adviser-browser-ci.yml` defines a separate required real-browser gate on Ubuntu/Windows with Python 3.12 and Node 22, isolated pinned Playwright 1.62.1, Chromium installation and exact JSON retention. It requires no financial/live secrets. Neither workflow has been triggered by this task; cross-platform success is not claimed. The new workflow received a manual structure/command review; a YAML parser was not available in the local bundled runtimes, so parser-level validation is not claimed.

The browser gate uses `tests/adviser_browser_server.py` for a fresh synthetic loopback fixture, controlled clock and stdin-owned graceful shutdown. It is not a production route, source-authority adapter or qualification bypass. Its temporary-root checks and explicit resume mode prevent incidental reuse of ordinary customer databases. The CLI browser runner performs one fail-fast execution, without assertion retries. It does not record auth traces or private workbooks. Missing browser/runtime is a failed gate, not a skipped pass.

Do not use a previously running v2.56 server to test changed static assets against its old in-memory backend. Stop that console before candidate hands-on testing. The pre-existing hands-on database/original store has not been migrated or written by this implementation. Use separate disposable local candidate data for architectural review; any intentional upgrade of retained valuable data requires its own operator decision and backup discipline.

Candidate local launcher, with explicitly selected disposable paths and client grants:

```powershell
.\.venv\Scripts\python.exe -B .\scripts\run_workspace_v257.py --database "$env:TEMP\ProfitDoctor-v257-review\workspace.db" --store "$env:TEMP\ProfitDoctor-v257-review\originals" --client seaside-demo-client --client isolation-demo-client --initialize --port 8767
```

The command is illustrative and was not run against those paths. Choose a fresh directory before first use. Existing local data is not deleted/reset. Read the code privately from that console; Ctrl+C stops the host and disposes its engine. Browser URL is the configured loopback port. This launcher still reads no PostgreSQL URL or Neon token.

## Limitations and deferred work

No new analytical execution, financial calculations, canonical writers, source authentication, readiness scoring, temporal promotion, general adviser notebook, adviser Decision writer, AI recommendation, report generation/publication, action/benefit logic, multi-user SaaS or v2.58 functionality.

Source-authority enrolment, transformation lineage and friendly analytical-owner discovery remain deferred. Explicit existing owner selections stay advanced and scoped; default trust remains UNKNOWN and current revalidation may refuse. No fabricated positive assessment was seeded into the ordinary candidate workspace or browser route.

Automated viewport/focus/contrast checks and visual inspection are not full accessibility certification or a real-client pilot. Manual screen-reader/Firefox checks and product-owner hands-on acceptance remain review/freeze prerequisites. Historical positive readiness is qualified through frozen owner/reader compatibility tests; the empty browser fixture honestly cannot demonstrate a real historical positive result.

Search currently covers the loaded review page. Draft listings are bounded to 50 per client with explicit setup paging; those pages advance across the authorised businesses together. Search applies to the displayed pages rather than claiming a whole-estate query. Recent user-access ranking, whole-company readiness and evidence sufficiency promises are deliberately absent. Unsaved edits are not stored in browser persistent storage.

## Intended file inventory

**New:**
`.github/workflows/adviser-browser-ci.yml`;
`alembic/versions/0021_adviser_setup.py`;
`profit_doctor/persistence/setup_schema.py`;
`profit_doctor/workspace/{home.py,session.py,setup.py}`;
`scripts/{run_workspace_v257.py,qualify_adviser_postgresql_v257.py,qualify_adviser_browser_v257.cjs}`;
`tests/adviser_browser_server.py`;
`tests/test_adviser_{setup,session,migrations,home,runner}_v257.py`;
this engineering document;
the separately preserved pre-existing approved architecture document.

**Modified implementation/registration:**
`profit_doctor/persistence/__init__.py`;
`profit_doctor/workspace/{app.py,index.html,ui.css,ui.js}`;
`qualification/test_estate_v242.json`.

**Expected current-head advancement only:**
`scripts/{qualify_dataset_postgresql_v253.py,qualify_production_postgresql_v255.py,qualify_workspace_postgresql_v256.py,run_workspace_v256.py}`;
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
`tests/test_temporal_runner_v254.py`;
`tests/test_workspace_runner_v256.py`.

**Head plus explicit additive-schema expectation:**
`tests/test_workspace_migrations_v256.py`, as explained above.

Ignored `.venv` test logs, reports, screenshots, source-hash inventories, browser directories, temporary SQLite files and runtime tooling are local-only and must not be staged. Frozen v2.56 qualification reports, architecture audit, analytical contracts and Golden Manufacturing packages are not changed.


## Targeted architectural safety remediation

The final read-only review reproduced a session-binding race: middleware authenticated an old token, but metadata then read whichever session was current. A controlled rotation returned a successor CSRF value to the admitted old request. The review also proved that a matching direct host could select one of two enabled read-write endpoints on the qualification branch. Post-sign-out browser history/cache restoration had not been explicitly qualified.

The session host now authenticates token, CSRF and expiry together under its lock and attaches an immutable, opaque SessionBinding to the request. Metadata, renewal and revocation require that exact binding under the same lock; rotated, revoked, copied and expired bindings refuse with HTTP 401. Wrong CSRF refuses with HTTP 403. A stale sign-out cannot revoke its successor. Login responses remain bound to their newly created identity. Single local operator ownership, inactivity/absolute limits, HttpOnly/SameSite cookies, grant checks and process-only secrets remain unchanged. This is not a remote/multi-user identity system or cancellation of business requests already authorised before sign-out.

The Neon verifier now counts all explicitly enabled read-write endpoints belonging to the approved branch before host selection. It requires exactly one, rejects project mismatch and host collisions, and requires that same endpoint to match the direct URL host. Existing exact project/branch identity, primary/default=false, READY, direct-host and pre-engine verification remain intact. All verification qualification in this remediation is mocked/offline; no Neon request or live PostgreSQL connection occurred.

The browser clears protected DOM, forms, selections and session authority on sign-out/expiry. Pagehide clears protected DOM and in-memory authority before cache capture while retaining only the scoped selection pointer. A persisted pageshow hides protected content and revalidates through the server before restoration. Invalid sessions clear that pointer. Browser qualification adds signed-out Back/Forward/refresh, revoked-cookie API refusal and deterministic persisted-pageshow handling; actual document navigation/Back also exercises pagehide and authenticated restoration. The deterministic event exercise is not a claim that every browser necessarily uses bfcache for the tested navigation.

Added regression coverage: 16 session checks (including cross-client refusal after rotation), 17 endpoint checks, and two browser scenarios. Session tests use controlled authentication/handler interleavings and a two-party barrier, without sleeps. The original 16 negative endpoint cases called the runner without its mandatory --report argument. Their early parser refusals were green but did not verify endpoint safety; they must not be treated as endpoint-verification evidence. The test-only correction and new execution-boundary proof are recorded below.

Remediation qualification: 35 standalone session/offline runner checks PASS; expanded real-browser gate 17/17 PASS, zero failures/errors and cleanup closed. Authoritative discovery is now 1,422 tests / 115 modules with exact inventory agreement. Cumulative live discovery remains 816 unique checks, all 784 inherited retained and the v2.41 resource/isolation gate last; the new safety checks are offline and do not inflate live discovery. Python in-memory compilation, JavaScript syntax and whitespace checks PASS. Expanded focused/compatibility qualification: 133/133 PASS (80 v2.57 tests plus 53 frozen v2.56 compatibility tests), zero failures/errors under strict deprecation/resource warning filters, 196.069 seconds. This includes existing migration compatibility. Final authoritative non-live estate: 1,422 discovered/run, 1,413 PASS, 0 FAIL, 0 ERROR, 9 legitimate live-only SKIP, 115/115 modules with exact inventory agreement, strict deprecation/resource/unraisable policy PASS (policy_errors=[]), 2,179.219 seconds on Python 3.12.14. Qualified source/test/configuration/fixture hashes remained unchanged throughout this run; only this documentation was updated with results.

The original architecture contract remains unchanged. No migration or financial/temporal/AR/evidence-authority semantics changed in this remediation; head remains 0021_adviser_setup. The intended inventory remains the same 47 files. These nine existing candidate files received remediation edits: session.py, app.py, ui.js, qualify_dataset_postgresql_v253.py, test_adviser_session_v257.py, test_adviser_runner_v257.py, qualify_adviser_browser_v257.cjs, test_estate_v242.json and this engineering document. Reports, hashes, screenshots and temporary test data remain ignored/local only. No staging, commit, push, live run or v2.58 work occurred.


## Endpoint regression-test integrity correction

Final safety re-review found that EndpointSafetyV257.refuse omitted the runner's mandatory --report argument. All 16 negative cases exited with status 2 during argument parsing, before verification or any mocked Neon metadata call. The earlier recorded full-estate and focused counts are accurate execution counts, but their green negative endpoint results were insufficient safety evidence. Independent offline reproductions supported the production verifier; no production defect or change was indicated.

The helper now supplies a report filename inside a fresh TemporaryDirectory for each case. The directory is isolated and the filename is asserted absent both before and after refusal, so existing qualification reports cannot be overwritten. The real verify_neon_target function is wrapped, not replaced: each negative case asserts exactly one verifier invocation, the exact expected refusal reason, and the ordered mocked API calls with the synthetic token. Endpoint-level refusals require project, branch and endpoint calls; branch flags/READY refusals require project and branch calls; a pooled URL reaches the verifier's direct-host guard with zero API calls. Argument-parser failures cannot satisfy these assertions. Every case also asserts zero engine-factory and destructive schema-reset calls.

The positive control retains acceptance/identity assertions and additionally invokes the actual CLI entry point. Its injected engine factory verifies that all three ownership metadata calls have completed and the URL was safely normalised to psycopg, then raises a private test sentinel before constructing any engine or connecting. The verifier and factory must each be called exactly once; schema reset and report creation remain forbidden. This proves ordering without a database or external service.

Only test_adviser_runner_v257.py and this engineering document changed in this test-only remediation. The 17 endpoint cases, three existing runner/checkpoint cases, authoritative 1,422-test count, 115 modules and cumulative 816-check inventory remain unchanged. Production code, migration 0021, historical migrations, browser assets/workflow, fixtures, analytical/temporal/AR contracts and the preserved architecture contract were not modified. No staging, commit, push, Neon request, PostgreSQL qualification or v2.58 work occurred.

Corrected runner qualification: 20/20 PASS (17 endpoint cases plus three existing runner/checkpoint tests) under strict deprecation/resource warnings. Expanded v2.57 focused and frozen v2.56 compatibility qualification: 133/133 PASS, zero failures/errors/skips, 211.999 seconds; this executes all session safety regressions and relevant migration compatibility. In-memory Python compilation PASS; authoritative discovery/inventory remains 1,422 / 115 with exact agreement; static live discovery is 816 unique, all 784 inherited retained, final v2.41 gate last. Final authoritative non-live estate: 1,422 discovered/run, 1,413 PASS, 0 FAIL, 0 ERROR, 9 legitimate live-only SKIP; 115/115 modules, strict deprecation/resource/unraisable policy PASS (policy_errors=[]), 2,466.391 seconds on Python 3.12.14. All 17 corrected endpoint cases genuinely execute in the registered suite; no source/test/configuration/fixture hash changed during the run. The only subsequent update is this documentation. git diff --check and final credential/artifact review PASS; the 47-file intended inventory is preserved and nothing is staged. Reports/hashes remain ignored in .venv; live PostgreSQL was not executed at that offline checkpoint; see the final approved live result below.


## Final approved live PostgreSQL qualification

The uninterrupted cumulative v2.57 live gate completed: 816 collected/run, 816 PASS, 0 FAIL, 0 ERROR, 0 SKIP on PostgreSQL 18.6. Independent verification targeted project tiny-meadow-46991842, branch br-royal-math-za046ex1 / v2-41-qualification, endpoint ep-mute-forest-zanl59mf and its approved direct host, with primary=false and default=false. The existing endpoint was started to unarchive the same branch before qualification; no branch replacement/reset was used for reactivation. The unchanged runner then performed its explicitly authorised disposable qualification resets.

Final cleanup: open_connections=0, checked_out=0, unraisable=[]. All 816 per-check outcomes in the retained local report are passed. The approved test execution duration was 9,233.966 seconds; the retained runner JSON records 9,243.391 seconds. These are recorded separately rather than asserted to be identical timing scopes. The private local JSON report is excluded from Git.

All 47 candidate hashes matched the qualified checkpoint before this documentation-only update. Static discovery still contains 816 unique checks, including all 784 inherited checks, with the final v2.41 resource/isolation gate last. No expensive qualification was rerun for release preparation. Migration head remains 0021_adviser_setup, historical migrations and fixtures remain unchanged, and no analytical/temporal/AR/source-authority boundary was expanded. The 17 endpoint regressions genuinely reach verification; the earlier argument-parser-only green results remain explicitly disclaimed above.

Release candidate approval does not establish a formal freeze. Full Estate CI on Ubuntu/Windows and Python 3.12/3.13, plus the separate Ubuntu/Windows Adviser Browser CI, remain required after push. Existing local/browser accessibility and single-operator deployment limitations remain in force. No v2.58 functionality is included.

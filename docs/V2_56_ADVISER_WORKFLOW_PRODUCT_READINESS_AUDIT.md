# Profit Doctor v2.56 — Adviser Workflow & Product Readiness Architecture Audit

Date: 9 October 2026. Status: architecture decision requested; implementation is **not authorised by this document**.

## 1. Executive summary

Profit Doctor has a substantial, qualified analytical engine and governed service layer. It does not yet have an end-to-end adviser application. The shortest safe route is to integrate existing owners into a persistent engagement and evidence workspace, then expose canonical review and decisions, then produce a controlled client report. Rebuilding the reasoning engine, adding scores or accelerating unqualified financial conclusions would solve the wrong problem.

Three different things currently coexist:

1. A legacy SQLite diagnostic/runtime pipeline, with workbook intake, deterministic calculations, legacy Findings, management attention and JSON product projections.
2. A static, embedded-data HTML prototype illustrating navigation and drill-down.
3. Additive SQLAlchemy canonical reasoning/evidence services, qualified locally and against disposable PostgreSQL, but not orchestrated by the upload demo or exposed through an authenticated HTTP application.

The prototype is not a live adviser workspace. The module named `api/service.py` is a callable Python projection boundary, not an HTTP server. A PostgreSQL-compatible schema does not make the SQLite diagnostic execution path PostgreSQL-native. A registered file does not establish source authority. A source-derived monthly owner does not replace a rolling diagnostic Fact.

**Recommended v2.56:** a controlled, initially operator-only Engagement & Evidence Workspace: persistent review identity/scope, durable original-file inventory, explicit run/evidence ownership, read-only readiness presentation and tracked missing-information requests. Do not include new analytical methods, general source authentication, autonomous recommendations or the complete client-report release in this first slice.

No current evidence supports calling the repository a production-ready, multi-user SME SaaS product. A single qualified adviser can use the engine through engineering scripts, but that is not a repeatable adviser workflow. A supervised, restricted pilot can precede self-service SaaS, provided security, source retention, explicit interpretation boundaries and adviser-approved reporting are qualified first.

## 2. Baseline, method and confidence limits

Before the audit, `HEAD`, local `main` and cached `origin/main` were all `dae614057623e012db24e7828d29fc2deb186a5c`; `git status --short` was empty. This is the frozen v2.55.1 baseline.

Accepted qualification supplied by the architectural contract:

- Authoritative local estate: 1,289 discovered/run, 1,280 PASS, nine legitimate live-only SKIPs, zero FAIL/ERROR; strict warnings and compilation PASS; inventory 105/105.
- Cumulative live PostgreSQL: 743/743 PASS, PostgreSQL 18.6, verified disposable branch, zero connection/resource leaks.
- Cross-platform CI: four required jobs PASS, as supplied by the user; no GitHub request was made to reverify this.
- Historical-restatement independent qualification signed off following BLIND TEST 02 and BLIND TEST 03, as supplied by the user. The evidence was synthetic financial evidence with local SQLite persistence, not real-client production qualification.

This audit reads repository source, schemas, tests, workflows and engineering documentation. It does not execute an application, rerun qualification, inspect private answer keys, contact GitHub/Neon, connect to databases or verify external deployment controls. Remote `origin/main` was not fetched; synchronization here refers to the cached remote-tracking ref. Baseline test evidence is accepted, not recreated.

The only authorised new file is this audit. No existing documentation, product code, tests, migrations or configuration is changed. References below are repository-relative source locators, not claims that a module is an operational UI.

### Classification rules

- **IMPLEMENTED AND INTEGRATED:** a traced invocation exists within a named bounded runtime path. It does not mean the whole adviser journey is complete.
- **IMPLEMENTED BUT NOT EXPOSED:** a callable owner/service exists, but no adviser UI/HTTP route invokes it.
- **PARTIALLY IMPLEMENTED:** useful components exist; essential workflow or operational dependencies are absent.
- **DESIGNED BUT NOT IMPLEMENTED:** explicit plans/contracts exist but no functioning implementation was found.
- **ABSENT:** no relevant implementation found in the inspected repository.

Security uses READY / PARTIAL / MISSING / NOT VERIFIED separately. A passing synthetic scope test is not production authorization certification.

## 3. Actual application architecture and capability inventory

### Entry points and execution paths

`profit_doctor/cli.py:main` accepts a folder, database and storage path, creates a hard-coded Northstar client/run and invokes Northstar ingestion plus commercial financial calculations. This is a narrow engineering entry point, not a generic client/engagement application.

`scripts/run_upload_to_report_v237.py` calls `product_demo.run_upload_to_report`. That copies one workbook, calls `intake.bridge.execute_unknown_workbook`, opens a local SQLite database, and writes `review.json`, readiness, priority/diagnostic JSON and a manifest. The traced analytical path is:

`workbook -> legacy intake/CSV registration -> primitives -> 56-diagnostic runtime and aggregate handoff -> legacy reasoning/economic/management modules -> legacy ProductView/drill-down JSON`.

It does **not** invoke the canonical Fact/Finding, Evidence Graph, Hypothesis, Story, Bridge, Impact, Opportunity, canonical Priority or v2.55 production readiness orchestration. Its manifest label `CANONICAL_HANDOFF` describes legacy canonical data handoff, not proof of v2.44 canonical Fact creation or v2.55 production qualification.

`prototype/v235/index.html` and `prototype/v236/index.html` are static prototypes. The inspected v2.36 page embeds Scenario 2 data; its functions open priority/diagnostic drawers. It has no `fetch`, file reader, persistent decision storage or report-download route. It does not consume a newly uploaded workbook or a saved engagement automatically.

| Capability | Classification | Actual implementation and integration boundary | Persistence / evidence / qualification |
|---|---|---|---|
| Application launcher | PARTIALLY IMPLEMENTED | CLI and upload-demo script; no general adviser launcher | SQLite demo/run; script and upload tests |
| Frontend navigation | PARTIALLY IMPLEMENTED | Static v2.35/v2.36 HTML with embedded scenario data | No user-workspace persistence; visual/drill-down tests |
| HTTP backend/API | DESIGNED BUT NOT IMPLEMENTED | `api/service.py` returns Python/Pydantic views; README names FastAPI as target, but no running FastAPI application/routes found | Product-view tests prove Python contracts, not HTTP authentication or deployment |
| Client/run identities | PARTIALLY IMPLEMENTED | Existing `client`, `engine_run`; scripts create them | Legacy and SQLAlchemy models; scope tests; no client-management UI |
| Legal entity/ledger/period scope | IMPLEMENTED BUT NOT EXPOSED | Typed production `EvidenceScope`, Dataset Contracts and Measurement Context | Scoped owned evidence; no adviser setup/review flow |
| Engagement/review lifecycle | ABSENT | `engine_run` is an analytical run, not a client engagement owner | No engagement workspace or engagement-to-many-runs lifecycle found |
| Workbook profile/semantic suggestions | IMPLEMENTED AND INTEGRATED in legacy demo | `intake/workbook.py`, `intake_assessment`, semantic maps | Source sheet/row suggestions and control limitations; no durable confirmation workflow |
| Exact accounting CSV ingestion | IMPLEMENTED BUT NOT EXPOSED to advisers | `ingestion/accounting.py`, `northstar.py` | Registered files/datasets, Decimal-text rows and ingestion jobs; engineering callers only |
| Optional workbook evidence providers | IMPLEMENTED BUT NOT EXPOSED in adviser app | `intake/receivables.py`, `intake/collection.py`; narrow declared accounting reader | Explicit supported layouts/providers; not universal ERP parsing or source authentication |
| Reconciliation | IMPLEMENTED AND INTEGRATED in legacy demo; canonical owner unexposed | Legacy reconciliation projections plus exact production reconciliation | Distinct arithmetic, population, definition and authority guards; no exception resolution UI |
| Registered production source authority/semantics | IMPLEMENTED BUT NOT EXPOSED | `production_evidence/source.py`, `semantics.py`; default resolver yields unknown | Exact registered profile, immutable hashes, manifests/charts/mappings, per-dimension verification; no deployed issuer trust/enrolment workflow |
| Diagnostic execution / Signals | IMPLEMENTED AND INTEGRATED in legacy runtime | `diagnostic/engine.py`, registry/eligibility and primitives | 56 diagnostics; FULL/PARTIAL/UNAVAILABLE/N/A semantics remain distinct; not every pack supports every diagnostic |
| Canonical Facts / Findings | IMPLEMENTED BUT NOT EXPOSED | `canonical/service.py:canonicalise, assess`; governed mapping registry | Canonical schema/history; explicit unmapped/refused results; significance separate from Fact creation |
| Evidence Graph | IMPLEMENTED BUT NOT EXPOSED | `graph/service.py:EvidenceGraph` | Scoped versioned edges, ancestry/independence; incomplete lineage remains indeterminate |
| Hypotheses / disconfirmation | IMPLEMENTED BUT NOT EXPOSED | `hypothesis/service.py:generate, assess` | Evidence gaps/history; class-specific support and mandatory disconfirmation, not general causal inference |
| Economic Stories | IMPLEMENTED BUT NOT EXPOSED | `story/service.py:synthesise` | Two qualified condition contracts: margin compression and customer concentration; three candidates deferred; no positive mechanism-resolved Story route |
| Measurement Context / BIQ / Bridges | IMPLEMENTED BUT NOT EXPOSED | `measurement/`, `bridge/` owning services | Revenue, Contribution 0 and Working Capital; Profit-to-Cash and Cost-to-Output refused; residuals/partial coverage retained |
| Economic Impacts | IMPLEMENTED BUT NOT EXPOSED | `impact/service.py`, registered receivables route | Only qualified records aggregate; production-positive receivables CASH_TRAPPED has narrow evidence requirements; Bridge movement is not automatically loss or cash trapped |
| Canonical Opportunities | IMPLEMENTED BUT NOT EXPOSED | `opportunity/service.py` over owned qualified Impacts and collection evidence | Frozen matched-outcome capture, explicit horizon/range and initiative completeness; no arbitrary recoverability percentage |
| Legacy management attention / register | IMPLEMENTED AND INTEGRATED in old product demo | `management/attention.py`, `opportunity_register.py`, `output_spec.py` | Persisted legacy themes/actions/register; not equivalent to canonical Priority or qualified Opportunity |
| Canonical Priority / human decisions | IMPLEMENTED BUT NOT EXPOSED | `priority/service.py`; opt-in `attention/service.py` | Immutable assessment/decision revisions, human request and audit; unsupported dimensions unknown, no universal score |
| Temporal production assessment | IMPLEMENTED BUT NOT EXPOSED | `production_evidence/temporal.py`, `assessments.py`, AR admission owner | Separate monthly owners, explicit windows/comparability/history; frozen v2.54 canonical refusal retained |
| Governed Evidence Readiness | IMPLEMENTED BUT NOT EXPOSED | `production_evidence/readiness.py:EvidenceReadinessService` | Domain-specific state, missing/conflicting prerequisites, capability limits and immutable history; not a whole-company score |
| Product JSON / evidence drill-down | IMPLEMENTED AND INTEGRATED in legacy demo | `api/service.py` / `view_models.py` | Persisted legacy KPI/Signal/control projections; no canonical decision/readiness report integration |
| Client publication/export workflow | PARTIALLY IMPLEMENTED | JSON output and static visual demonstration; no verified PDF/DOCX/report approval/download service found | No publication snapshot, recipient authorization or report-release audit |
| Audit/history | IMPLEMENTED BUT NOT EXPOSED consistently | Legacy governance/restatement and canonical audit/history owners | Service-level tests; no consolidated adviser event timeline or operational audit policy |
| Authentication / adviser roles | ABSENT | No login, authenticated principal or role-based endpoint implementation found | Actor fields are domain attribution, not proof of authenticated identity |
| AI/LLM functionality | ABSENT in inspected runtime | Deterministic reasoning and textual explanations; no model-call/client integration found | Existing legacy recommended-action text is deterministic, not AI; no AI release recommended |

### Persistence integration is unfinished, not disposable

`core/db.py` owns the SQLite analytical harness. `persistence/database.py` owns SQLAlchemy engines/sessions, transaction scope and PostgreSQL compatibility. Canonical source readers and production evidence services deliberately receive both a caller-owned SQLAlchemy session and a legacy connection. Preserve those conventions; do not introduce a third source registry or flatten them into one untyped document.

Cross-store commits are not a demonstrated single distributed transaction. `ingest_accounting_file` commits source ingestion before optional `context_sink` capture; the sink owns its transaction and failure can be retried independently. A product coordinator must therefore distinguish receipt, registration, qualification and analysis, support resumable/idempotent work, and never claim an atomic all-stage success.

## 4. Current end-to-end adviser journey

“End to end today” below means through an actual adviser interface, with durable ownership and reopening, not a developer constructing services or SQL rows. None of the full journeys has been established by this read-only audit.

| Step | Existing implementation / actual entry | Persistence and test evidence | Missing dependency / current end-to-end result / risk |
|---|---|---|---|
| 1. Create client | Script/SQL insertion in CLI or unknown-workbook demo | `client`; multi-client governance and upload tests | No client UI, identity validation or principal assignment. **No adviser flow**; hard-coded/demo metadata cannot establish a real legal entity. |
| 2. Establish entity/accounting scope | Production typed entity/ledger/population/period contracts | Production semantics, Dataset Contract and Measurement Context tests | No confirmed scope form or evidence-backed review. **Not exposed**; client label alone is insufficient. |
| 3. Create engagement/review | Runs exist | `engine_run`; persistence tests | No engagement owner, status, adviser assignment or many-run review. **Absent**. |
| 4. Upload finance pack | Script takes one workbook; CSV ingestion functions accept exact contracts | Source registration / upload / workbook tests | No upload endpoint/multi-file workspace/normalization review. **Engineering path only**; no general production-source qualification. |
| 5. Inspect files | Original workbook copied by demo; profiles report sheets | Hash/source preservation test; source registry | No secure browser/source viewer, version inventory or persistent normalized-store assurance. **Partial**. |
| 6. Map periods/accounts | Heuristic suggestions; explicit typed mapping evidence exists separately | Intake tests and production semantic mapping tests | No confirm/reject/edit workflow tied to version/authority. **Partial**; defaults must not be treated as verified. |
| 7. Review provenance/extraction | Source file/dataset lineage, source manifests/charts and audit contracts | Registered-source, lineage and tamper tests | No user-facing row locator/export identity/trust review. **Not exposed**. |
| 8. Resolve reconciliation differences | Calculators/persisted exceptions exist | Accounting/intake/reconciliation tests | No issue owner, evidence request, rerun history or adviser resolution workflow. **Partial**; “resolved” must require new evidence, not dismissal of the difference. |
| 9. Challenge semantics | Dataset declarations and source-supported verification are distinct | Dataset and production semantics adversarial tests | No declaration/verification side-by-side UI or confirmed mapping chain. **Not exposed**. |
| 10. Review readiness | Legacy `build_upload_readiness`; canonical readiness owner | Upload readiness and governed readiness tests | Old readiness is not v2.55 readiness. **Partial**; unknown/missing/conflict explanations need explicit domain selection. |
| 11. Run diagnostics | Script invokes engine and saves executions | Diagnostic estate / upload pipeline tests | No engagement command/status/recovery/control-selection UI. **Engineering path works within supported fixtures**, not qualified general adviser operation. |
| 12. Inspect KPIs/movements | Product JSON and embedded UI KPIs; Bridges/temporal owners separate | Product view/drill-down/Bridge/temporal tests | No live binding from workspace to current owned results; no audited trend-chart route. **Partial**. |
| 13. Examine Findings/evidence | Legacy diagnostic/priority drill-down; canonical reads exist | Signal lineage / canonical / graph tests | No canonical Finding view, source-version distinction or integrated graph inspection. **Partial**; legacy Findings must not masquerade as canonical significance. |
| 14. Review alternatives | Hypothesis/Interpretation services | Hypothesis/disconfirmation tests | No adviser route for generation, gaps or counter-evidence. **Not exposed**; support is class-specific. |
| 15. Accept/investigate/reject | `PriorityService.decide` with human `AdviserRequest` | `canonical_adviser_decision`; priority tests | No authenticated actor/endpoint/forms. **Not exposed**; decision applies to the precise canonical subject/assessment revision. |
| 16. Inspect Impacts/Opportunities | Canonical owner APIs; old register projection | Impact/receivables/Opportunity/overlap tests | No qualified-status-aware UI/API projection. **Not exposed**; cannot reinterpret old register as qualified economic value. |
| 17. Adviser commentary | Decision rationale/provenance/questions/evidence; legacy decision notes | Canonical decision history / legacy management tests | No engagement-wide commentary/attachments/revision UI. **Partial**; comments cannot verify source facts. |
| 18. Save/reopen engagement | Local DB and owner histories can be reopened by code | Persistence/history tests | No engagement, safe resume coordinator or UI reload. **Partial**; legacy demo recreates client and overwrites fixed output filenames. |
| 19. Client report | Management output specification / JSON export / static prototype | Output spec/product/upload tests | No adviser-approved canonical publication snapshot, printable export or secure distribution. **Not ready**. |
| 20. Track decisions/evidence | Canonical holding/history; required-evidence strings and legacy review queue | Priority holding/history/governance tests | No request lifecycle, due/received/reviewed links or consolidated dashboard. **Partial**. |

## 5. Realistic finance-pack intake and evidence qualification gaps

### A. Basic diagnostic ingestion

Excel profiling, semantic suggestions, reconciliation and diagnostic execution exist. Exact CSV contracts support P&L, Balance Sheet, Trial Balance, AR, AP, bank and inventory. Northstar ingestion supports its declared commercial transaction/customer/product schema. CRM/Level-3 modules provide enhanced analytical capability where appropriate data exists; they are not prerequisites for a core review.

The unknown-workbook demo is narrower than a normal multi-file accounting pack. Specific code observations in `intake/bridge.py`:

- `_ma_rows` searches a management-accounts sheet, a limited month/header/line vocabulary, takes a year from a title with a 2026 fallback and multiplies recognised values by 1,000.
- `_tb_rows` uses column/name assumptions and assigns year-end; `_bs_from_tb` derives selected controls conservatively from names. These are legacy engineering mappings, not monthly GL semantic authority.
- `_insert_workforce` uses a fixed date and an explicitly limited staff-cost surrogate. Do not represent this as fully verified payroll evidence.
- It does not manufacture invoice-level AR/AP from aggregates, which is a safeguard worth preserving.
- Normalized source registration uses a `TemporaryDirectory` source store that disappears when the function returns. The copied original workbook is preserved, but persisted normalized dataset/source references can point to removed files. This is a concrete product-retention blocker, not permission to refactor the frozen engine during this audit.
- Client insertion and fixed demo output names do not implement repeatable uploads to an existing client/engagement.

The profile/readiness functions explain ambiguity and control failures, but a declaration of “human confirmation required” is not an implemented confirmation workflow. Tests demonstrate supported layouts and failures, not arbitrary accounting systems, zipped packs, scanned PDFs or every Excel variant.

### B. Frozen registered production qualification

`RegisteredAccountingSource` requires the exact ordered `ACCOUNTING_RECORDS_1` CSV profile, completed registration, scoped immutable files and matching hashes/counts. Transport labels do not verify population or economic definition. `RegisteredSemanticSource` defaults source authority to unknown; an application-supplied trusted resolver must authenticate a scoped issuer/export, not accept a flag inside uploaded JSON.

Production qualification consumes registered records plus manifests, controls, source charts, attributable mappings, revision authority and Dataset Contracts. Arithmetic agreement, population completeness, semantic definition, source authority and production qualification remain different gates. Completeness requires governed membership/boundaries; row counts or totals cannot establish population equivalence.

Monthly Revenue and monthly monetary C0 have separately owned identities and contexts. Monthly C0 margin requires qualified component bindings. They cannot revise/replace rolling-12-month REV-01/GM-01 Facts. The v2.55 production temporal boundary is opt-in and must not bypass the frozen v2.54 canonical refusal. Historical lookup in v2.55.1 remains explicit; stale evidence cannot enter as current.

### Connected and disconnected paths

There is reusable connection at the source registry and caller-owned legacy connection, plus an explicit optional accounting `context_sink`. Narrow declared-accounting, receivables and collection workbook providers also exist. There is **no general UI coordinator** converting an ordinary multi-file SME pack into all v2.55 semantic evidence, provisioning real issuer trust, qualifying owners and exposing those outcomes alongside diagnostics.

Uploaded workbook -> hashed possession -> registration is possible. Uploaded workbook -> authenticated source -> complete population -> verified definition -> comparable monthly observations is **not automatic**. The UI must expose every intermediate state and never fabricate an empty source manifest or default missing initiative/absence evidence.

### Intake support assessment

| Input/problem | Existing support | Pilot requirement |
|---|---|---|
| Excel | Profiling, legacy execution, narrow explicit providers | Bounded supported layouts, explicit amount/date/time-basis confirmation, original preservation; unsupported sheets fail closed |
| CSV | Exact accounting/commercial profiles and registered production transport | Preview/schema validation and explicit mapping into the existing profile, no guessed verified fields |
| Monthly P&L/BS/TB | Accounting contracts; demo MA/TB extraction; declared reader | Independent statement/ledger identity, period/unit/sign and source membership review; do not derive all monthly BS from year-end TB |
| Sales/purchase exports | Sales transaction runtime; accounting AR/AP contracts | Maintain transaction versus invoice snapshot versus aggregate distinctions; purchase invoice capture is not a universal purchase-journal adapter |
| Aged AR/AP | Exact contracts; registered receivables provider | Due date, outstanding/original amounts, status and control scope; production-positive CASH_TRAPPED is a qualified AR route, not an AP value method |
| Mapping tables | Attributable mapping and source-chart contracts | Review/version/effective period/source authority; no name-based C0 membership verification |
| Multiple periods/restatements | Dataset revision, comparability, production history and temporal services | Version browser, explicit supersession authority, old evidence retained; repeated periods are not new observations |
| Incomplete/inconsistent packs | Eligibility, limitations, refusals and readiness | Useful supported analysis continues; conflicts and unassessed capabilities visible; no “all green” score |
| Different accounting systems | Normalized interfaces, named test source and narrow providers | One explicitly qualified export profile at a time; no universal Sage/Xero/QuickBooks connector found or assumed |

## 6. Adviser review, judgement and reporting

### Existing decision contract should be reused

`PriorityService` assesses only canonical Findings or current qualified Opportunities. Its subject identity pins the source. `AdviserRequest` requires an identified HUMAN actor with HUMAN_FD_JUDGEMENT, nonblank rationale/provenance, and questions plus required evidence for INVESTIGATE. Decisions reference an assessment revision, require an explicit predecessor when changing, support idempotent request replay, and retain immutable audit/history. `holding(ACCEPT/INVESTIGATE/REJECT)` also indicates whether evidence is current and whether reassessment postdates the decision.

These are not login/authorization checks. A future endpoint must derive the human actor from an authenticated adviser/session, not accept a trusted actor ID/type from arbitrary request JSON. Acceptance means adviser judgement, not verified fact, source authentication, qualified economic mechanism or realised benefit.

Investigation evidence is presently structured request text, not an operational evidence-request owner with recipients, status, file links and fulfilment review. A workflow layer should track those tasks and link to immutable decision revisions; it should not replace `canonical_adviser_decision` or edit its rationale in place. General commentary likewise needs explicit scope/type and versioning without changing economic records.

Legacy `management/engine.py` has opportunity-linked decisions/actions/benefit functions and the legacy reasoning engine populates an FD review queue. These must not be silently treated as the canonical Accept/Investigate/Reject writer. Existing benefits/action methods are not absent engine capability, but enabling them is out of scope for the first Adviser Edition.

### What can currently be seen/exported

`build_management_output` projects stored legacy KPIs, attention themes, recommended actions, opportunity-register amounts, diagnostic availability and reconciliation limitations. Product drill-down returns Signals/core questions under run/client checks. JSON output is useful engineering evidence, but not a governed publication service.

| Adviser view | Current evidence route | Product gap |
|---|---|---|
| Business overview | Legacy ProductView KPI/control/coverage fields | No live engagement binding or confirmed period/entity basis |
| Revenue / margin | Legacy primitives and Signals; canonical Facts/monthly owners separately | No qualified trend chart/time-basis selector; Contribution 0 must not be relabelled gross profit |
| Cash / working capital | Legacy primitives; qualified Working Capital Bridge and AR Impact owner APIs | Stock versus flow, movement versus trapped cash, and prospective capture must stay visible |
| Customer concentration | Legacy Signals and canonical concentration Finding/condition Story | No renewal probability, expected loss or mechanism implication |
| Cost movements | Diagnostic evidence and narrow supported economic routes | Do not imply the refused Cost-to-Output Bridge exists |
| Findings / alternatives | Canonical Finding/Graph/Hypothesis owners | No consolidated challenge/gap/counter-evidence screen |
| Impacts / Opportunities | Qualified canonical services and ranges/horizon | No UI projection with production origin, qualification state, effect overlap and currentness |
| Evidence quality / readiness | Legacy upload explanation and distinct governed readiness | No side-by-side distinction between mapping readiness, source authority and capability eligibility |
| Adviser decisions | Canonical immutable history | Missing in legacy ProductView/output specification; no report integration |
| Client report | JSON/demo illustration | No publication snapshot, selection/approval, printable export, access policy or revocation/history |

The legacy output already distinguishes profit/cash and leaves unsupported opportunities and benefits unavailable. Preserve that. However, old `expected` fields, confidence labels and recommended actions do not automatically meet canonical v2.49/v2.50/v2.51 qualification. Do not publish them under a new canonical badge.

A future report must distinguish: source observations; verified semantics; significant canonical Findings; hypotheses/unresolved alternatives; condition Stories; qualified Impact categories; qualified prospective Opportunity ranges/horizon; human decision/commentary; missing evidence and NOT_ASSESSED capabilities. It must pin owner/revision IDs and refuse silent refresh after adviser approval. No combined profit/cash/risk total; no Bridge residual monetisation; no conversion of adviser acceptance into evidence verification.

## 7. Governed Evidence Readiness integration

`EvidenceReadinessService` already supports nine domains: core accounting evidence; monthly Revenue; monthly C0; C0 margin; receivables snapshot; receivables absence; Revenue temporal; C0 temporal; receivables lifecycle. States are VERIFIED, DECLARED, PARTIAL, INSUFFICIENT, NOT_PROVIDED and CONFLICTED. It retains explicit selected references, missing/satisfied prerequisites, conflicts, unlocked/refused capabilities, lineage, limits and revisions.

Its limitations matter: it assesses only the selected scoped evidence, not all company records. Core accounting evidence can remain PARTIAL even when a monthly owner is qualified. A verified monthly value does not by itself establish a complete pack or a comparable temporal series. Unknown AR can block lifecycle admission before lifecycle evaluation. Reassessment reads current owners, while history retains prior snapshots.

Minimum integration: a read-only domain panel linked to the engagement's explicit owned evidence selection; show owner revision/currentness, missing/conflicting prerequisites and links to exact source inventory; create a separate request task for needed records; associate received versions with that request; reassess through the existing owner when authorised prerequisites exist. If no owned evidence is available, display NOT_PROVIDED, not a synthetic VERIFIED/UNKNOWN calculation.

The legacy `build_upload_readiness` panel must be labelled separately as upload/diagnostic coverage. Do not merge its `READY_FOR_EVIDENCED_ANALYSIS` label with governed production readiness. Do not expose a universal score or let staff override readiness state directly.

## 8. Security and deployment assessment

| Area | State | Evidence and gap / required control |
|---|---|---|
| Authentication | MISSING | No application login/session principal found; actor contracts are not authentication |
| Authorization | PARTIAL | Scoped owner reads/write checks exist; no endpoint permission model or authenticated client assignment |
| Tenant/client isolation | PARTIAL | Composite relationships, service guards and synthetic/live qualification exist; no demonstrated deployed per-principal policy or full legacy-route access audit |
| Adviser/user roles | MISSING | No membership/role-management implementation found; caller-supplied actor attribution cannot authorize access |
| File retention/access | PARTIAL | Hash-addressed files and client path segregation exist; local chmod/hash checks are not secure cloud storage or access authorization; demo temporary-store loss is a blocker |
| Source authentication | PARTIAL | Trusted resolver boundary exists and defaults unknown; actual issuer enrolment, authentication and credential lifecycle not supplied by a generic pack upload |
| Database permissions/RLS | NOT VERIFIED | FK/service integrity is qualified; least-privilege roles, RLS policy, runtime network access and permission review were not verified |
| Secrets management | PARTIAL | Environment-based DB config and process-local qualification credentials; no deployed secret rotation/access policy verified; no secret values inspected |
| Audit logging | PARTIAL | Domain audit/history and blocked legacy access events; no consolidated authenticated operational audit, tamper protection/export retention policy |
| Retention/deletion | PARTIAL | Archive state exists; archive is not GDPR deletion, retention scheduling, object-store cleanup or legal-hold governance |
| Backups/recovery | NOT VERIFIED | No inspected operator restore/retention runbook or exercised real application/file-store restore gate |
| Deployment | MISSING in application repository | No deployed HTTP application, container/server configuration or environment promotion process found; CI is qualification, not deployment |
| Secure reports | MISSING | No authenticated download, recipient access, publication version/revocation or audited distribution route |
| Upload safety | PARTIAL | Narrow bounded OOXML reader and exact-schema validation exist; general upload size/type/path/archive limits and malicious input controls not qualified as a web intake boundary |
| Operational monitoring | NOT VERIFIED | Test resource accounting exists; no deployed job/incident/health/alert ownership demonstrated |

No area is labelled READY merely because a model or scope test exists. UK real-client handling requires an appropriately reviewed privacy/processing arrangement, least privilege, secure workstation/storage and tested retention/recovery; this audit is not legal or penetration-test certification.

A local single-adviser pilot can avoid premature multi-user SaaS, but must still use controlled storage, OS access, explicit client scope, audit and approved report handling. Loopback/operator-only software is not authorization for sharing an unauthenticated server. Any remote UI requires authenticated actor/client ownership before use with client data.

## 9. Architecture gap matrix and reuse plan

This matrix complements the capability inventory; “tests” are existing proof to reuse, not tests executed during this audit. Release labels after v2.56 are proposals, not implementation authority.

| Capability / current UI | Existing owner / evidence / persistence | Existing tests | Missing work / risk | Recommended release / dependencies |
|---|---|---|---|---|
| Client/scope / no management UI | `client`, typed EvidenceScope, run ownership | Multi-client, production ownership | Scope setup/confirmed entity and ledger; wrong-client risk | v2.56; existing identities, operator boundary |
| Engagement / absent | Existing runs and immutable analytical owners | Persistence/history | Add review lifecycle/reference association, not replacement run/client abstractions | v2.56; approved additive workflow contract |
| Original-file inventory / script only | `source_file`, dataset/version, immutable retention | Upload source/hash, registered-source | Durable workspace store, multi-file receipt/provenance viewer; temp-store and overwrite risk | v2.56; storage/session lifecycle |
| Mapping/period review / suggestions only | Intake plus governed mapping/declaration contracts | Intake, production semantics | Explicit mapping proposal/confirmation with no verification uplift | v2.56 view; qualified adapter writes v2.57 |
| Reconciliation review / JSON only | Legacy exceptions and production exact controls | Accounting, semantics, component tests | Scoped exception/evidence request presentation and corrected-source linkage | v2.56 view; qualification v2.57 |
| Source authority / resolver only | Registered source + trust resolver, default unknown | Foundation/semantics adversarial | One audited authentication approach/source profile; uncontrolled verifier risk | v2.57; separate reviewed issuer boundary |
| Readiness / old panel only | Existing governed Readiness/history | `test_evidence_readiness_v255` | Typed explicit selection and explanatory UI; misleading whole-company badge risk | v2.56; owned evidence retrieval |
| Missing information / strings only | Existing decision questions and readiness prerequisites | Priority/readiness tests | Workflow task status, receipts/review links and audit; no fabricated absence | v2.56; engagement/file links |
| Run coordination / synchronous script | Diagnostic executors, source jobs, canonical owners | Upload, engine, caller-rollback/replay tests | Persistent stage status, idempotent recovery, explicit run scope; cross-store atomicity risk | v2.57; durable intake and qualification |
| Facts/Findings / no canonical UI | Canonical source/registry/writer/assessment/history | Canonical service/migration/semantic tests | Safe explicit mapping orchestration and refused/unmapped view | v2.57; no generic fallback/cutover |
| Graph/alternatives / unexposed | EvidenceGraph, Hypothesis/Interpretation owners | Graph/ancestry/disconfirmation | Read-only evidence navigation/gaps/counter-evidence, no mechanism strengthening | v2.58; canonical review projection |
| Stories / unexposed | Two condition contracts/history | Story/no-Story tests | Expose only current qualified states, limits and unresolved why | v2.58 optional; no new contracts |
| Bridges/Impacts/Opportunities / old register only | Existing qualified owners/effects/overlap | Bridge/Impact/Opportunity/adversarial tests | Status-aware projection with residual, category, range, horizon/currentness | v2.58; reviewed source/run orchestration |
| Decisions / writer not UI | `canonical_priority_subject`, assessment, adviser decision/audit | Priority, attention, history tests | Authenticated human actor, revision concurrency, holding/reopen UI | v2.58; scoped app boundary |
| Financial charts / prototype KPIs | Existing persisted measurements/context and movements | Product, CMC, temporal tests | Chart data projection pins unit/time basis and evidence; no chart-side analytical invention | v2.58 desirable; confirmed observation owner |
| Client report / JSON only | Existing ProductView and canonical owners | Output guardrails, product view | Approved immutable report snapshot/export/access and explicit evidence classes | v2.59; canonical decision/report authority |
| Security/operations / undeployed | Session/connection ownership, governance guards | v2.41/live and cross-platform tests | Auth/access/storage/retention/restore/configuration review; client-data exposure risk | v2.56 operator restrictions; hardening before v2.59 pilot |
| Benefits/advisory / legacy methods | Legacy management/longitudinal benefit controls | Management/benefit/restatement tests | Separate future integration; not inferred from prospective opportunity | Deferred beyond first Review pilot |

## 10. Minimum genuinely usable Adviser Edition

### Essential for the first controlled pilot

One identified finance professional manages explicit clients and engagements; receives a supported multi-file core pack into durable isolated storage; confirms scope/period/unit and reviews mapping proposals; sees source versions, extraction evidence, reconciliation exceptions and governed capability readiness; requests specific missing evidence; runs only eligible analysis; inspects canonical Findings and their evidence/limits; records explicit human decisions; reopens the same review; produces an approved, traceable client report.

Supported Level 1 data must yield a useful review without Level 2/3 inputs. Enhanced evidence progressively unlocks existing capabilities. Lack of CRM, forecasts, SKU economics or operational data must be visible as coverage constraints, not interpreted as a bad business or a requirement to complete a commercial review.

For a core-only pack, a report may properly contain verified financial observations, significant Findings and unresolved investigation requests with **no quantified Opportunity**. That is an honest useful service. Do not make a guaranteed savings headline a product acceptance condition.

### Desirable but deferrable

Interactive temporal/Bridge charts, richer graph navigation, standard email-request templates, bulk export adapters, reusable adviser mapping suggestions with explicit confirmation, side-by-side review history and controlled client portal delivery. Preserve provenance even when these conveniences are absent.

### Advanced future functionality

Multi-adviser organizations/self-service onboarding, general ERP integrations, additional economic-mechanism/Story contracts, new valuation/capture methods, forecasts, ongoing action/benefit workflows, organizational memory and any AI Partner. Existing Level 3 analytical modules remain available to supported evidence; integrating them broadly is not required before a core pilot.

### Milestones

| Milestone | Explicit criterion |
|---|---|
| TECHNICALLY FUNCTIONAL | Existing analytical services execute correctly on qualified supported inputs with persistence/replay; substantially achieved at engine level, not as a full adviser application |
| ADVISER-USABLE | An adviser completes receipt, review, challenge, decision and saved/reopened report preparation without SQL edits or bespoke per-client scripts |
| PILOT-READY | Adviser-usability plus representative supported packs, fail-closed evidence/security checks, controlled deployment/storage, restore/retention, approved reporting and supervised operating procedure |
| PRODUCTION-READY | Demonstrated real-client source trust, operational ownership, security/access review, recovery/retention, release/deployment discipline and repeatable service delivery at intended scale; synthetic tests alone cannot establish this |

## 11. Proposed v2.56 boundary

**Engagement & Controlled Evidence Workspace**, not a new reasoning release.

Include only:

1. Existing-client/run-linked review identity and confirmed legal/entity/ledger/period metadata; avoid parallel client/dataset registries.
2. Durable original-file inventory with hashes, filenames, source role, registered version references and explicit registration/qualification states. No temporary store as lasting evidence ownership.
3. Operator UI to inspect inventory, available legacy controls/mapping proposals and separately labelled governed readiness. No unsupported synthetic readiness results.
4. Missing-information requests with client/engagement scope, prerequisite references and receipt/review status; no automatic evidence authentication.
5. Save/reopen, history/currentness visibility and fail-closed scope boundaries.

Exclude from v2.56: universal finance-pack normalization, new trusted issuer authentication, new canonical writers/temporal assessment activation, full canonical decision UI, printable publication and cloud multi-user deployment. These deserve separate reviewed integration slices. Existing owners may be read through scoped projections; external callers cannot choose arbitrary client/actor IDs.

An operator-only/local boundary is the smallest starting surface. If remote/multi-user use is required, authentication and per-client authorization become blocking dependencies and scope must be reapproved; do not quietly ship an unauthenticated API.

New workflow persistence may need an additive migration. Decide that after approving engagement/request ownership; no migration is drafted by this audit. All frozen analytical writers, enums, revision history and qualification gates remain unchanged.

## 12. Proposed roadmap and acceptance gates

| Release proposal | Objective / deliverables | Dependencies | Acceptance / required tests | Complexity / adviser benefit |
|---|---|---|---|---|
| v2.56 | Engagement, durable evidence inventory, readiness presentation, missing-information tasks | Approved identity/transaction/storage contracts; existing owners | Create two clients/reviews; receive multiple files; scope isolation; save/reopen; original hashes survive restart; no qualification uplift; exact readiness refusals/history; request receipt links; no temp-store leak; UI acceptance, resource/strict full estate and any new migration/live gates | Medium-high integration; removes file/run administration and reveals what is missing |
| v2.57 | Controlled supported-pack normalization and resumable analytical orchestration | v2.56; separately approved source authority/profile approach | One qualified core export family; units/periods/definitions confirmed; authority unknown by default; incomplete/conflicting inputs refuse; source membership and restatement authority retained; old diagnostic contracts unchanged; explicit mapping coverage; cross-store partial failure/replay; representative core/enhanced packs; migration/live gates when affected | High; converts received evidence into defensible supported analysis without bespoke scripting |
| v2.58 | Canonical review, human decisions and current-result navigation | Canonical owners and current scoped runs from v2.57; authenticated/local operator identity | Findings/evidence/gaps/counter-evidence; ACCEPT/INVESTIGATE/REJECT using existing writer; actor spoofing denied; stale assessment and lost-update refusal; immutable history; no causal/economic uplift; Impact/Opportunity distinctions; core-only review remains useful | Medium-high; enables professional challenge and repeatable review preparation |
| v2.59 | Adviser-approved report and controlled pilot hardening | v2.58 plus deployment/security/storage/restore review | Snapshot pins all owner/revisions; unsupported claims absent; human judgement distinct; profit/cash/risk non-additive; absence/unknown explicit; export reproducible; report permissions/revocation; full supervised journey on representative consented real-client packs; restore/retention rehearsal; no uncontrolled source trust | High; first defensible paid Review workflow and go/no-go pilot decision |
| Later, separately approved | Advisory monitoring/action/benefit integration and additional source profiles | Successful controlled Review pilot and approved contracts | Preserve prospective capture versus realised benefit and attribution; no automatic new methods/AI | Variable; ongoing advisory capability, not a prerequisite for the first Review |

These are dependency-ordered engineering slices, not dates or promises of a fixed number of releases. A discovered source-profile/security conflict must stop that slice for architectural resolution. Combine slices only if their complete acceptance remains reviewable.

### Common acceptance conditions

- Existing 56 diagnostics, source semantics, canonical writers and frozen refusal gates remain intact; no assertion weakening or skipped gate to obtain green.
- Reuse current transaction/resource ownership and immutable histories. Persist task/run state before claiming completion; no UI side effects in reads.
- Never silently switch consumers between legacy and canonical authority. Keep legacy projections explicitly labelled during transition. Canonical publication becomes the sole descriptive/significance authority for supported mappings only after explicit qualification; unmapped evidence remains visible without guessed Facts. No permanent second canonical writer.
- Monthly owners remain distinct from rolling diagnostic Facts; Contribution 0 remains Contribution 0; restatements remain same-period revisions; explicit historical/current lookup is preserved.
- No readiness score, source-authentication checkbox, inferred population completeness, arbitrary recoverability, unsupported mechanism promotion or profit/cash grand total.
- Unit/service qualification plus actual UI/HTTP/operator journey tests are required. PostgreSQL qualifies persistence, not real-client truth. Cross-platform CI, schema upgrade/preservation, caller rollback, leaks and negative scope tests remain required where affected.

## 13. Commercial practicality, risks and operating model

A paid adviser-led Review is plausible before self-service SaaS. The current software still requires too much engineering administration to claim repeatable delivery. Highest-friction tasks are normalizing pack layouts, establishing legal/ledger/period scope, retaining original and transformed evidence, authenticating exports/mappings, reconciling exceptions, assembling current IDs across services and translating outputs into a client report.

Safe automation: file hashing/version inventory; typed previews; supported profile validation; explicit mapping suggestions for adviser confirmation; prerequisite-specific request templates; idempotent owner-service orchestration; currentness/contradiction displays; approved-snapshot report formatting. Unsafe shortcuts: verified-source flags from uploaded JSON, synthetic issuer roots used for real clients, silence about unassessed domains, automatic acceptance, hidden history replacement or any value claim inferred from a discrepancy.

For the initial service, use one professional operator, a documented supported-pack checklist, bounded import profiles, an evidence/request log and adviser-approved distribution. Make manual source-authority review attributable without pretending it supplies verification beyond the frozen contract. A refusal with a precise information request is a valid deliverable, not a failure requiring invented evidence.

| Key risk | Consequence | Required response |
|---|---|---|
| UI connected only to legacy demo | Sophisticated canonical engine appears implemented but never reaches adviser | Explicit scoped projection and integration inventory; test actual route |
| Temporary normalized store / overwritten demo files | Reopened evidence or historical requalification fails | Durable retained source ownership and multi-file/version workspace before pilot |
| Heuristic unit/date/account assumptions | Incorrect finance interpretation despite arithmetic consistency | Explicit supported normalization and confirmation; production definition still separately qualified |
| Caller-controlled trust or actor labels | False verification or unauthorized adviser decision | Approved trusted resolver and authenticated/operator identity boundary; fail closed |
| Cross-store partial commit | Receipt shown as qualified after downstream failure | Persistent stages, retryable idempotent coordinator and honest failure state |
| Legacy/canonical authority ambiguity | Old register or recommendation presented as new qualified conclusion | Explicit authority labels and gated cutover; no dual writers |
| Scope/history hidden by UI | Cross-client leakage or stale evidence treated current | Server/service-derived scope, exact owner revision links and negative journey tests |
| Domain readiness shown as whole-company quality | False assurance and unsupported temporal unlock | Selected-evidence limitations and domain prerequisite presentation |
| Report without snapshot/approval | Changed numbers or unqualified claims reach client | Immutable publication snapshot and adviser approval/access audit |
| Synthetic qualifications called production readiness | Real source/operational weaknesses overlooked | Representative real-client pilot and security/restore/trust gates |

## 14. Explicit deferred functionality

No AI-generated recommendations, autonomous decisions, new Impact or Opportunity methods, forecasting, benefit-realisation integration, new Story mechanisms, scoring, arbitrary recoverability or general source authentication is recommended for v2.56. No existing advanced module is removed or weakened. Business Health Check/self-service acquisition and Advisory/Virtual FD can follow a working adviser-led Review; they are not substitute acceptance criteria for it.

## 15. Immediate architecture decision requested

Approve or revise the narrow **v2.56 Engagement & Controlled Evidence Workspace** boundary first. Resolve three implementation inputs explicitly: local operator versus remote deployment; engagement/request ownership over existing client/run/dataset identities; durable original/normalized source-store and cross-store failure semantics.

Then implement that approved workflow slice against existing services, with actual save/reopen and client-scope journey acceptance. Do not begin a broad UI, new analytical integration or issuer-authentication design merely because this audit lists it as a later dependency.

## 16. Source evidence map and audit verification

Principal inspected anchors:

- `profit_doctor/cli.py`; `scripts/run_upload_to_report_v237.py`; `profit_doctor/product_demo.py` — actual callable entry points and output ownership.
- `prototype/v235/index.html`, `prototype/v236/index.html`; `docs/INTERACTIVE_DRILLDOWN_V2_36.md` — visual prototype and actual navigation boundary.
- `profit_doctor/api/service.py`, `api/view_models.py`, `management/output_spec.py` — product projections, scope checks and publication gaps.
- `profit_doctor/intake/{workbook,bridge,readiness,declared_accounting,receivables,collection}.py`; `ingestion/{accounting,northstar}.py` — supported input contracts, heuristics and file lifecycle.
- `profit_doctor/core/db.py`; `persistence/{database,models,canonical_schema,priority_schema,production_evidence_schema,production_history_schema}.py` — persistence ownership and scope.
- `profit_doctor/reasoning/{canonical,graph,hypothesis,story,bridge,impact,opportunity,priority,attention,dataset,measurement,temporal}/` — canonical owner boundaries and consumer references.
- `profit_doctor/reasoning/production_evidence/{source,semantics,service,temporal,assessments,readiness,ar_semantics,ar_admission}.py` — registered production qualification and history.
- `profit_doctor/management/{governance,engine,longitudinal,restatement}.py`; `docs/MULTI_CLIENT_GOVERNANCE_V2_32.md` — legacy functions, ownership guards and limits.
- `tests/test_upload_to_report_v237.py`, `test_product_view_model_v234.py`, `test_upload_readiness_v238.py`, `test_multi_client_governance_v232.py`, `test_priority_v251.py`, production/readiness/history tests and `qualification/test_estate_v242.json` — existing bounded qualification, not executed in this audit.
- `README.md`, `requirements.txt`, `requirements-dev.txt`, `.github/workflows/full-estate-ci.yml` and v2.55/v2.55.1 engineering documentation — target versus implemented deployment and accepted qualification.

Final intended state: this file is the only new/untracked file; existing tracked diff remains empty. No product code, tests, migrations or configuration changed. No GitHub/Neon action, PostgreSQL access, qualification rerun, stage, commit or push occurred. No private qualification material was used in the audit.

Limitations: actual installed/deployed services, real issuer authentication, workstation/cloud permissions, backup restoration, real SME layout coverage and adviser usability were not exercised. The repository does not establish them. Accepted CI/blind sign-offs are user-provided frozen evidence; cached `origin/main` is not a fresh remote check. Proposed release complexities are qualitative integration assessments, not delivery estimates.

**READY FOR V2.56 ARCHITECTURE DECISION**

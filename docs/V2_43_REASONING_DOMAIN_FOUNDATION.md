# Profit Doctor v2.43 â€” Reasoning Domain Foundation

## Release boundary and authority

Baseline: `0d826b0158e199b8f59a9561c22e30ea86217580` (v2.42, frozen).
This is an additive foundation, not a new reasoning engine or a claim that the
legacy reasoning path already implements the target semantics.

**Destination: Option B, controlled versioned evolution of the existing domain.**
Option C is temporary compatibility machinery only. There is no second governance
lifecycle attached to legacy rows and no permanent Option D overlay.

Existing runtime services remain the only active production writers of existing
reasoning/economic objects in v2.43. No existing object is copied, regenerated,
promoted, dual-written or automatically linked into the new foundation. The new
explicit service can persist foundation contracts, but no diagnostic, intake,
report, management or legacy reasoning entry point calls it.

One future semantic slice must have one writer after its separately qualified
cutover. Canonical tables are the destination, not permanent competing authorities.
The `_v243` table suffix identifies this initial schema introduction; future
releases should evolve these tables through migrations, not clone them per release.

## Authoritative domain dictionary

| Object type | Intended semantic meaning; behaviour is not implemented here |
|---|---|
| SIGNAL | A diagnostic observation |
| FACT | A faithful description of evidence, preserving measurement meaning |
| FINDING | An assessment of significance |
| HYPOTHESIS | A proposed explanation requiring challenge |
| INTERPRETATION | An assessment of explanations and uncertainty |
| ECONOMIC_STORY | A traceable connection between observations and consequences |
| ECONOMIC_IMPACT | A typed economic consequence, distinct from an opportunity |
| OPPORTUNITY_CANDIDATE | A possibility whose addressability is not established |
| VALIDATED_OPPORTUNITY | An opportunity supported by a qualified addressability process |
| MANAGEMENT_DECISION | A management decision, not a system recommendation disguised as one |
| ACTION_PLAN | An identity for future planned execution |
| ACTION | Execution of a decision |
| BENEFIT_RECORD | Evidence about what actually happened |

Diagnostics observe; Facts describe; Findings establish significance; Hypotheses
propose explanations; Disconfirmation challenges them; Interpretations assess
them; Stories connect them; Impacts quantify consequences; Opportunities establish
addressability; Priorities allocate attention; Decisions remain management
decisions; Actions execute them; Benefits measure actual outcomes; Memory retains
learning. Every material statement must remain traceable to evidence.

`ReasoningObject` is a governed **identity contract** with an explicit `ObjectType`,
not an arbitrary analytical payload. It has no generic narrative or value field.
The foundation does not assert that declaring an identity establishes a fact or
validates an opportunity. Type-specific analytical contracts and the evidence
required to justify stronger states belong to future qualified semantic slices.

## Contracts and repository conventions

`profit_doctor/reasoning/domain/` holds Pydantic v2 contracts and string enums.
It extends the existing reasoning package rather than creating another runtime.
SQLAlchemy 2.x and Alembic continue to own production persistence.

Identity uses UUID4-based `rd_` identifiers, existing string ID conventions, existing
Client and EngineRun FKs, optional existing entity references, optional reporting
period dates, aware UTC creation timestamps and an explicit `RDF-2.43` schema
version. Object updates require an incremented integer revision and an update
timestamp; identity, scope, source authority and ancestry are immutable. A changed
scope/origin needs a new identity, not a silent rewrite of history.

Financial values use Decimal in Python and exact decimal strings in serialized
contracts, consistent with the existing persistence convention. No float-based
financial storage or new serialization dependency was introduced. Typed JSON
contract documents use SQL Text for SQLite/PostgreSQL parity; indexed identities,
FK endpoints and revision are separate relational columns. There is no JSONB
requirement. Read services check that the stored document agrees with its indexed
envelope and fail closed on disagreement.

Repository convention reconciliation:

- Existing timestamps are ISO strings in SQL. New contracts validate timezone-aware
  datetimes and normalize to UTC before storing ISO strings.
- Existing ORM fields use plain strings, not SQL enums/CHECKs. Canonical Pydantic
  enums and family-specific lifecycle validation govern new service writes.
- Existing `Base` metadata is reused and all old model definitions remain unchanged.
- Historical revisions importing current metadata remain untouched. Revision 0004
  contains explicit frozen DDL and imports no runtime models.
- Client/run ownership is validated in the service; existing EngineRun definitions
  are not altered to add a composite uniqueness constraint.
- The zero-CHECK invariant remains intact. It is not a claim that direct SQL can
  enforce all semantic validation.

## Vocabulary

Evidence relationships: `SUPPORTS`, `CONTRADICTS`, `QUANTIFIES`, `CONTEXTUALISES`,
`EXPLAINS`, `TEMPORALLY_PRECEDES`, `CO_MOVES_WITH`, `MITIGATES`,
`POTENTIALLY_DRIVES`, `SUPPORTED_DRIVER_OF`, `CONSEQUENCE_OF`, `AMPLIFIES`,
`SHARES_EFFECT_WITH`.

Evidence roles: `CONDITION`, `DRIVER_CANDIDATE`, `CONSEQUENCE_CANDIDATE`,
`SUPPORTING`, `CONTRADICTORY`, `QUANTIFICATION`, `SEGMENTATION`, `TEMPORAL`,
`CONTEXTUAL`, `MITIGATING`.

Source authority: `SOURCE_DATA`, `SYSTEM_DERIVED`, `MANAGEMENT_ASSERTION`,
`HUMAN_FD_JUDGEMENT`, `EXTERNAL`, `LEGACY_UNCLASSIFIED`.

An evidence link is a declared relationship, not proof of causality. Potential and
supported drivers are different values; no promotion logic exists. The writer
must retain the source object's authority on its links. A management assertion
retains management authority even when supporting another object; it cannot
relabel itself as system-derived evidence through the service. No verified flag,
automatic confidence increase or truth promotion is inferred from a link.

All self-links and self-overlaps are prohibited. Missing or foreign-tenant
endpoints are rejected. Cross-run references within one client are intentionally
allowed for temporal comparisons and ancestry; a link's run is the run recording
the relationship, not a demand that both endpoints originated in that run.

### Namespaced target lifecycles

| Family | Values |
|---|---|
| FindingStatus | DETECTED, VALIDATED, MATERIAL, PROMOTED_TO_REASONING, DISMISSED |
| ExplanationStatus (Hypothesis / Interpretation) | GENERATED, TESTING, SUPPORTED, PLAUSIBLE, UNRESOLVED, CONTRADICTED |
| StoryStatus | CANDIDATE, INVESTIGATING, SUPPORTED, QUANTIFIED, ACTIONABLE, MONITORING, IMPROVING, RESOLVED, PERSISTENT, WORSENING, REJECTED, UNRESOLVED |
| OpportunityStatus (candidate / validated opportunity) | CANDIDATE, INVESTIGATING, VALIDATED, PRIORITISED, DECISION_REQUIRED, APPROVED, DECLINED, NOT_VIABLE, EXPIRED, SUPERSEDED |
| ActionStatus | PROPOSED, APPROVED, NOT_STARTED, IN_PROGRESS, BLOCKED, COMPLETED, CANCELLED, DEFERRED, FAILED, SUPERSEDED |
| BenefitStatus | EXPECTED, OBSERVED, ATTRIBUTION_TESTING, ATTRIBUTED, PARTIALLY_ATTRIBUTED, UNRESOLVED, NOT_ATTRIBUTABLE, SUSTAINED, DECAYING |

Status validation uses the object's family. No status is required or supplied
automatically. Signal, Fact, Impact, Management Decision and Action Plan currently
have no specified lifecycle in this contract, so a non-null status is rejected.
There is no transition engine or automatic proof of eligibility for a state.

## Confidence and materiality

`ConfidenceProfile` independently stores data, attribution, interpretation,
quantification, opportunity and benefit-attribution confidence. Each accepts
`VERY_LOW`, `LOW`, `MEDIUM`, `HIGH`, `VERY_HIGH`, `NOT_ASSESSED`, or null.
Default is NOT_ASSESSED. No universal confidence score or percentage exists.

`MaterialityProfile` stores optional Decimal absolute economic magnitude,
percentage of revenue, percentage of gross profit, percentage of EBITDA and
cash impact. Percentages use percentage points (12.5 means 12.5%). Monetary values
require an explicit three-letter uppercase currency; no currency conversion or
ISO currency catalogue verification occurs here. Decimal scale is preserved.
Null means unknown, never zero. Floats, booleans and non-finite monetary values
are rejected.

Persistence, trend velocity, concentration, strategic relevance, risk severity,
urgency and controllability are independent qualitative `AssessmentLevel` values
(VERY_LOW / LOW / MEDIUM / HIGH / VERY_HIGH / NOT_ASSESSED, or null). These are
recorded assessments, not calculated metrics or universally calibrated thresholds.
Trend velocity does not imply direction; future measured trends require an
explicit typed measurement contract. Each profile can retain structured rationale.
No profile is inferred from the legacy scalar HIGH/MEDIUM/LOW strings.

## Economic effects and impacts

`EconomicEffect` owns an identity independent of a story, impact or opportunity.
`EffectReference` allows multiple Stories, Impacts or Opportunities to reference
one effect. Duplicate object/effect pairs are rejected by database uniqueness.

`EffectOverlap` declares `SAME_EFFECT`, `PARTIAL_OVERLAP`, `PARENT_CHILD`,
`INDEPENDENT` or `UNKNOWN_OVERLAP`. One declaration per unordered pair is allowed;
For PARENT_CHILD, source is the parent and target is the child. Conflicting or
reverse duplicate declarations are refused. Future reassessment/replacement needs
a separately designed lifecycle; this release does not overwrite declarations.

`ImpactType`: OBSERVED_LOSS, RUN_RATE_LEAKAGE, CASH_TRAPPED, AVOIDABLE_COST,
CAPITAL_AT_RISK, FUTURE_EXPOSURE, VALUE_CREATION_POTENTIAL, REALISED_BENEFIT.

`ImpactBasis`: RECURRING_PROFIT, ONE_OFF_PROFIT, CASH_RELEASE,
BALANCE_SHEET_EXPOSURE, FUTURE_RISK_EXPOSURE, REALISED_BENEFIT, NOT_ASSESSED.
These fields belong only to ECONOMIC_IMPACT identities. They distinguish dimensions
but do not calculate amounts, enforce a future taxonomy of valid combinations,
consolidate overlaps, calculate net opportunities or reinterpret legacy REV rows.

## Lineage and the cross-store boundary

`LineageReference` preserves kind, owning store, resource name, source ID, client
and optional originating run. Kinds cover source file, dataset, dataset version,
canonical record, entity, primitive result, diagnostic, analytical run, derived
ancestor, calculation lineage, diagnostic lineage and evidence bundle.

References reuse existing identities. No competing source-file, dataset, entity,
client or run tables are created. Multiple identities can retain precisely the
same ancestry; that does not establish independent corroboration.

The service resolves existing SQLAlchemy EngineRun, PrimitiveResult and
TestExecution identities directly and canonical ancestors through scoped reads.
Legacy SQLite references require a trusted owning-store resolver returning actual
client/run ownership. Missing resolvers and scope disagreement fail closed.
The resolver must validate resource/kind, existence and actual ownership rather
than echo claims from input. It is an injection boundary for later integration,
not a new ingestion or polymorphic query engine. Other legacy ancestry types can
be represented now but require their owning-store resolver before service writes.

Cross-store references cannot have database FKs or a distributed transaction.
Their historical identities are retained in typed documents; deletion/lifecycle
policy of their external store remains outside this foundation. There is no
evidence-independence score or automatic ancestry traversal.

## Audit and transaction ownership

`AuditEvent` targets exactly one reasoning object or economic effect and records
actor type/source authority, timestamp, optional run/lineage, before/after values
and structured rationale. Actor types are SYSTEM, HUMAN, MANAGEMENT, MIGRATION,
UNKNOWN. Actor IDs are optional; authentication/authorization remains the caller's
responsibility.

Event vocabulary: OBJECT_CREATED, OBJECT_UPDATED, STATUS_CHANGED, EVIDENCE_LINKED,
EVIDENCE_UNLINKED, CONFIDENCE_CHANGED, MATERIALITY_CHANGED,
MANAGEMENT_ASSERTION_RECORDED, HUMAN_OVERRIDE_RECORDED, OBJECT_SUPERSEDED.

The service automatically records creation, object updates, changed profile/status
fields, evidence links, effect references and overlap declarations. Explicit audit
append supports management assertions and human overrides without changing object
state. Management assertion events retain management source authority; human
override events require a human/management actor. Audit append is not a transition
engine. Events are append-only through this API; no unlink, delete, supersession
operation or tamper-proof event-sourcing mechanism is implemented. Event timestamps
and UUID tie-breaks provide deterministic retrieval, not a causal total ordering.
Financial values in structured audit/metadata must be decimal strings, as produced
by typed contract serialization, not untyped JSON numeric amounts.

`FoundationService` uses a caller-owned SQLAlchemy Session and never commits,
rolls back, closes it or disposes its engine. The caller owns one transaction for
an operation/batch and must roll back on exceptions, using the existing
`session_scope` convention. Existing Client/EngineRun rows must be flushed before
service calls. Revision-conditional SQL UPDATE prevents lost object updates;
conflicting revisions are rejected. There is no autonomous runtime execution.

## Persistence and migration

Six additive tables:

- `reasoning_object_v243`: typed/versioned identity, authority and revision.
- `economic_effect_v243`: independent effect identity.
- `evidence_link_v243`: relational endpoints and governed typed contract.
- `effect_reference_v243`: object/effect membership with unique pair.
- `effect_overlap_v243`: scoped pair identity and overlap declaration.
- `reasoning_audit_event_v243`: subject FKs and typed append-only audit contract.

All have existing Client and optional EngineRun FKs. Composite endpoint/client FKs
prevent cross-tenant relationships even when application services are bypassed.
Object/effect identity plus client has explicit uniqueness. No CHECK constraints,
new database extension, server-default calculation or legacy table alteration.
Direct SQL remains privileged: enum validation, self-link rejection, document
consistency at write time, run/client pairing and audit append-only policy are
application-boundary guarantees, not comprehensive database constraints.

Forward revision: `0004_reasoning_foundation`, after `0003_rev_gm_diagnostics`.
Upgrade only creates new tables and leaves all legacy rows untouched. Downgrade
removes the six new tables in dependency order and preserves legacy schema/data.
**Downgrade discards canonical foundation records and their audits**; export or
back up these records before an operational downgrade. It is not a lossless
rollback once the new foundation has been used.

`tests/fixtures/v242_schema.sql` is an intentional schema-only test fixture captured
from the frozen baseline before any metadata additions. It includes all 16 old
tables, their keys/indexes and the original Alembic revision. It is not regenerated
at test time and is independent of current Base metadata. Tests populate every
baseline table/field, upgrade, compare unchanged values, downgrade to 0003, compare
again, and re-upgrade. This avoids treating today's metadata as historical proof.
The existing v2.41 tests additionally compare fresh head with all current metadata,
compile migrated DDL for PostgreSQL, test destructive fixture reset, downgrade/base
and re-upgrade, and retain the zero-CHECK assertion unchanged.

## Compatibility policy and controlled technical debt

`LegacyObservation` is a temporary read-only envelope, not another persisted
reasoning model. It retains original fields, source identity and legacy type,
status, confidence and materiality, marks authority LEGACY_UNCLASSIFIED and conversion
UNRESOLVED. It cannot produce a canonical lifecycle or populate profile dimensions.
No automatic mappings exist for ACCEPTED, OPEN, QUALIFIED, SUPPORTED, REALISED or REV.

v2.44 Facts & Findings must specify measurement contracts, eligibility for conversion,
source ownership, evidence preservation, writer cutover, regression equivalence
where legitimate, and rollback before migrating data. Ambiguous rows remain legacy
observations until reviewed; missing meaning must not be invented. Remove adapters
per semantic slice after verified cutover. Do not maintain permanent dual writers.

Deferred defects from reconciliation are recorded, not silently fixed here:

1. Generic Fact rendering can misstate measurement units/meaning.
2. Management assertions can affect legacy escalation without verification.
3. Signal count can act as false corroboration.
4. Legacy scalar confidence conflates sufficiency and interpretation.
5. Production persistence covers only part of the legacy estate.
6. Existing polymorphic lineage is weak and some source paths are transient.
7. Legacy audit mechanisms are fragmented.
8. Benefit statuses conflate observation, attribution and retention.
9. Longitudinal aggregation includes float-based sums.
10. Historical migrations depend on current legacy metadata.

## Qualification evidence

New tests:

- `test_reasoning_domain_v243.py`: 17 tests covering vocabulary, identity, schema
  versions, deterministic strict round trips, precision, profiles, source authority,
  links, ancestry, lifecycle namespaces, effects, impact bases, audits and unresolved
  legacy compatibility.
- `test_reasoning_persistence_v243.py`: 21 tests covering migrated create/read/update,
  revision checks, caller rollback, audits, tenant/run scope, endpoint FKs, persisted
  shared ancestry, resolver refusal, effect sharing/uniqueness, document consistency,
  preserved-v2.42 upgrades, downgrade/re-upgrade and independent forward DDL.

Local compile: passed. Focused new plus unchanged v2.41 schema suite: 43 PASS,
0 FAIL, 0 ERROR, 0 SKIP, with DeprecationWarning and ResourceWarning as errors.
Authoritative command: `.venv/Scripts/python.exe scripts_run_full_regression.py
--report .venv/v243-full-estate.json`. Windows 10 / Python 3.12.14: **346 discovered
and run across 56 modules; 337 PASS, 0 FAIL, 0 ERROR, 9 legitimate live PostgreSQL
SKIP**, in 672.5 seconds. No expected failures, unexpected successes or policy
errors. The runner treats deprecation/resource warnings as errors and observes
unraisable resource failures. Within this result the original estate remains
308 tests: 299 PASS, 0 FAIL, 0 ERROR, 9 SKIP. All 38 new tests pass. All 28 existing
persistence tests pass within the full run. No skip is counted as a pass.
The v2.42 inventory receives only the two new classified modules; runner and CI
workflow remain unchanged (Ubuntu + Windows x Python 3.12 + 3.13). Existing inventory
entries and assertions are unchanged. Local reports remain ignored under `.venv/`.

## Explicit non-goals and remaining gates

No diagnostic 57. No changed diagnostic calculations/contracts, intake behaviour,
canonicalisation, report outputs, suppression, management priorities or legacy
resource ownership. No new Fact extraction/correction, Finding promotion,
hypothesis/disconfirmation engine, evidence-independence scoring, cross-diagnostic
reasoning, causality, Story detection/contracts/taxonomy, economic bridges,
addressability/recoverability, net opportunity calculations, Action Plan behaviour,
benefit-attribution redesign, organisational memory, LLM calls or AI narrative.

Live PostgreSQL is not qualified by SQLite or dialect compilation. The focused
real PostgreSQL qualification below has now passed, including the unchanged nine
explicitly live tests. No live URL or credential is placed in source. GitHub
Actions has not run this uncommitted v2.43 tree; the four-platform/version matrix
remains required before release freeze. Next intended semantic release: **v2.44 Facts &
Findings**, with no automatic migration authorized by this foundation alone.


## Focused live PostgreSQL qualification after architectural approval

Environment: Neon project `tiny-meadow-46991842`, existing dedicated branch
`v2-41-qualification` (`br-royal-math-za046ex1`), AWS eu-west-2. Provider metadata
confirmed ready, non-primary, non-default and unprotected. The direct compute
endpoint was verified against the provider's branch/endpoint mapping before use.
No database connection or mutation targeted the production/default branch.
Credentials were process-local and are absent from source and result reports.

Server: **PostgreSQL 18.6**, aarch64 Linux; **READ COMMITTED** isolation.
`scripts/qualify_reasoning_postgresql_v243.py` is an explicit destructive opt-in
entry point. Set the existing qualification environment variable securely, then
supply `--disposable-branch v2-41-qualification`, `--expected-host` with the verified
direct host, and `--report` with a local output path. Missing credentials, host
mismatch, pooled hosts and a different driver are refused. The operator must
verify branch ownership independently; the CLI does not query Neon metadata.

Result: **36 collected/run; 36 PASS, 0 FAIL, 0 ERROR, 0 SKIP**, 66.593 seconds.
This includes 31 tests using actual PostgreSQL and five static/contract checks:

- 2 migration tests: clean/repeated head upgrade and independent preserved-v2.42
  upgrade plus populated downgrade/re-upgrade. All 16 legacy tables were seeded
  and compared field-for-field. All six new tables held committed records before
  downgrade; downgrade removed them and their audits, preserved every legacy row,
  and re-upgrade created empty canonical tables.
- 18 approved v2.43 persistence tests reused without changing assertions; only
  the fixture is replaced by PostgreSQL setup and explicit resource cleanup.
- 2 additional tests: vocabulary persistence through the approved service and
  caller-owned commit visibility/rollback using independent sessions.
- 5 unchanged PostgreSQL readiness tests: 2 live plus 3 static.
- 9 unchanged v2.41 qualification-module tests: 7 live plus 2 contract checks,
  including FK rejection, concurrent uniqueness, isolation, pool recovery and
  downgrade/base/re-upgrade.

New migration tests use the preserved portable SQL DDL and Alembic, never
`create_all`. The unchanged v2.17 readiness tests retain their pre-existing
metadata-created fixture; v2.41 subsequently rebuilds through Alembic. The final
disposable schema is at `0004_reasoning_foundation`.

Persistence checks cover Decimal precision, profiles, vocabulary/authority,
evidence endpoints, shared run/source ancestry, canonical ancestors, economic
effects/overlap, audits, tenant/run scope, revisions, uniqueness and corrupt-document
refusal. Cross-store source-file resolution retains the SQLite owning-store
boundary; canonical records and lineage documents are persisted to PostgreSQL.

DeprecationWarning and ResourceWarning were errors during test execution, with
unraisable-warning observation. Final tracked SQLAlchemy connections: **0 open,
0 checked out, no unraisable errors**. No implementation correction or architectural
change was needed. Post-review additions are the qualification script and this
evidence update only. The complete local regression remains 346 tests / 337 PASS /
9 legitimate live skips; unrelated regression was not repeated for these
qualification-only additions. Cross-platform CI remains pending.

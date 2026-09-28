# Profit Doctor v2.44 - Canonical Facts & Findings

## Baseline and authority

Frozen baseline: `16576f6805f73287fac5bba1b8c050bd2ae432a4`, `main`.
The working tree was clean and origin/main matched before implementation. All
four v2.43 Full Estate CI jobs were verified successful. Part 1 of the approved
v2.44 contract, the subsequent acceptance instructions, and the repository's
v2.43 architecture document govern this implementation.

This is Option B controlled evolution. It adds typed semantic extensions to
existing v2.43 reasoning identities. It does not introduce independent Fact or
Finding identity authorities, or change legacy runtime writers. No historical
Fact prose, accepted Finding, materiality label or confidence label is promoted.

## Source inspection and coverage

The frozen 56 diagnostics emit Signals through `diagnostic.engine._execute`.
Workbook/intake handoff calls that engine. The SQLAlchemy diagnostic migration
copies existing Signals; it is not a new semantic producer. Legacy reasoning,
recurrence, evidence bundles, contradictory/context evidence, economic joins,
management attention and API projections were inspected and remain unchanged.

There are 86 distinct emitted Signal types, represented by 91 static emission
variants including the explicitly expanded working-capital, PVM and margin loops.
This is code-path coverage, not a claim that a workbook exercised every branch.

- 59 types have explicit SAFE_TO_CANONICALISE mappings.
- 11 have INSUFFICIENT_SEMANTICS.
- 9 REQUIRE_TYPE_SPECIFIC_MAPPING (registry value REQUIRES_TYPE_SPECIFIC_MAPPING).
- 7 are NOT_APPLICABLE_TO_FACT.
- 0 frozen emitted types need LEGACY_ONLY classification.

The governed registry is keyed by diagnostic AND Signal type: for example,
CUSTOMER_OVERDUE_AR and NEW_CUSTOMER_REVENUE have different producer meanings.
`qualification/signal_mapping_v244.json` retains emission locations, source slot
expressions and all mapped metric/unit/basis definitions. `V2_44_SIGNAL_MAPPING.md`
lists every type and refusal reason. `scripts/inventory_signals_v244.py` reproduces
these intentional qualification artifacts and refuses unclassified dynamic sites.
The regression compares the retained inventory with current source declarations.

Safe type coverage is not unconditional record coverage. Inactive/ineligible or
incomplete executions, wrong units/entities, absent ancestry and missing required
measurements are refused. Unknown producer/type pairs have no generic fallback.
Five mappings also refuse ambiguous zero sentinels: CUS-07 contribution Pareto,
PROD-02 mix comparison, SUP-01 spend share, SUP-03 dependency share and PROD-04
long-tail count. Their frozen producers can encode an unavailable denominator or
selection as zero. Without the missing denominator, a genuine zero cannot always
be distinguished from that sentinel. These are record-level refusals, not invented
zero measurements or claims that all records of a mapped type are eligible.
Malformed domain contracts and invalid scope raise explicit validation errors;
the caller must roll back on exceptions. Refused/unmapped results contain reasons.

Examples withheld: realised-price movement drops product identity; transaction
exceptions drop transaction identity; seasonal peak/trough retain month identity
only in prose; forecast Signals omit vintage/target-period ancestry. Scenario and
opportunity/governance candidates are not established descriptive Facts. These
limitations do not authorize changing frozen diagnostics to fill the gaps.

## Typed Facts and measurement safety

`CanonicalFact` is the typed payload of a v2.43 FACT identity. It preserves source
Signal, diagnostic, client/run, mapping/schema version, scope, eligibility,
limitations, authority, lineage, confidence and lifecycle. Supported families are
MEASUREMENT, MEASUREMENT_SET, COMPARATIVE and RECONCILIATION. They are constrained
by a retained mapping rather than an arbitrary free-form analytical dictionary.

Observed, comparison and derived slots independently carry metric, exact Decimal,
unit, currency where monetary, and calculation basis. A derived slot is NOT
necessarily a variance. Contribution/revenue/margin use GBP/GBP/percentage;
margin levels use percentage while movement uses percentage points. Retention
ratio is not contractual GRR. Product-count ratio does not become sales potential.
Per-FTE measures are descriptive ratios, not causal productivity conclusions.

Units are CURRENCY, PERCENTAGE, PERCENTAGE_POINTS, DAYS, COUNT, INDEX,
INDEX_POINTS, HOURS, FTE, CURRENCY_PER_FTE and CURRENCY_PER_UNIT. No unsupported
generic ratio or currency conversion was added. Monetary mappings retain the
frozen producer's explicit GBP convention; they do not certify source FX treatment.
Counts reject fractional and negative values; financial inputs reject binary
floats, booleans and non-finite values. Exact decimal strings persist in SQL Text,
reusing the v2.43 serializer and avoiding a second serialization framework.

Structured fields are truth; the renderer projects each populated slot with its
own unit/basis and displays state, eligibility, limitations and scope. Missing
dates are explicitly unknown. Comparison-window roles do not invent precise
calendar boundaries. No prose is parsed to manufacture missing semantics.
Source dimension labels such as department names retain their spaces; blank and
control-character labels are rejected. These scope labels are not reclassified
as canonical entity IDs, and v2.43 lineage-reference validation is unchanged.

## Identity, replay and correction

Fact identity hashes client/run/source Signal/mapping version, never rendered
prose. A digest of the owning-store Signal, execution and diagnostic-lineage rows
detects source mutation under a stable identity. Replay returns the existing
record without new Fact writes, links or creation audits. Database primary keys
enforce uniqueness. Concurrent insert conflicts require caller rollback and
transaction replay; the service does not conceal races with retries.

Namespaced Fact states are OBSERVED, SUPERSEDED and INVALIDATED. No automatic
VALIDATED state exists. This lifecycle belongs to the typed Fact extension;
the foundation FACT identity retains its existing null status convention. There
is no competing legacy governance overlay.

An explicit correction requires a different qualified mapping version, the same
source/run, an observed predecessor and rationale. It creates a new Fact identity,
records its predecessor, supersedes the old Fact, and retains old semantic
revisions and audit history. The mapping-version registry must retain historical
definitions when adding corrected versions. v2.44 ships one production mapping
version; the correction test injects a distinct test-only qualified version.
Invalidation similarly retains the original payload and records rationale.

## Lineage and authority

`LegacySignalSource` is a read-only owning-store adapter over a caller-owned SQLite
connection. It joins the existing Signal to its matching diagnostic execution,
retains existing diagnostic-lineage identities, and resolves dataset-version and
primitive-result ancestry where present. No parallel source/run/company tables
are created. Existing lineage records can retain the same underlying source
identity for multiple Signals without increasing confidence or corroboration.

The explicit canonical service creates a v2.43 SIGNAL identity envelope for the
existing observation and a SUPPORTS link to the FACT. This is not a new diagnostic
Signal calculation. Fact-to-Finding links use the same v2.43 evidence mechanism.
Cross-store lineage remains subject to the owning store's retention policy; it
is not a distributed transaction or a snapshot copy of source files.

Only reviewed diagnostic Signal mappings produce SYSTEM_DERIVED Facts. Management
context is not a source Signal or verified Fact. A separately supplied management
assertion can hold significance assessment, retaining its source authority and
explicit contradictory/mitigating relationship. Context never rewrites evidence.
All confidence dimensions remain NOT_ASSESSED in this mapping version. FULL
eligibility does not establish HIGH interpretation or opportunity confidence.

## Findings and significance

Fact creation never creates a Finding. The separate `assess` operation returns
FINDING_CREATED, NOT_SIGNIFICANT, INSUFFICIENT_EVIDENCE or HELD_LIMITED. It audits
the assessment, including declared counter-evidence. Invalidated/superseded Facts
are not eligible; partial eligibility, recorded limitations and challenges hold
assessment rather than increasing confidence or silently suppressing evidence.

Three versioned policies reuse explicit frozen diagnostic thresholds:

- REV-01: absolute revenue movement at least 5% of nonzero prior revenue.
- GM-01: absolute contribution-margin movement at least 1 percentage point.
- CUS-01 largest customer: revenue share at least 15%.

These establish observed significance only. They do not establish loss,
recoverability, attribution, probability, cause or a recommendation. Other valid
Facts return INSUFFICIENT_EVIDENCE until a type-specific policy is qualified.
MaterialityProfile remains unassessed where these measures do not establish its
financial/risk dimensions; revenue movement is not automatically profit impact.
No universal materiality or confidence score exists.

Finding identity uses client, semantic Finding type, diagnostic/metric family,
entity and reporting basis/version, not a title or analytical run. Observations
retain run, Fact and period scope. Later assessments append revision history.
Matching same-period observations are REPEATED_OBSERVATION, not persistence.
PREVIOUS_COMPARABLE_PERIOD requires ordered run timestamps, disjoint ordered
periods, equal duration and identical governed scope/basis. Missing dates produce
INSUFFICIENT_TEMPORAL_EVIDENCE. No automatic PERSISTENT conclusion is implemented.

Contradictory and mitigating IDs are scoped foundation endpoints. They are
recorded in Finding revisions and linked with retained source authority when a
Finding exists. A held initial assessment does not manufacture a Finding.
This is significance challenge, not Hypothesis disconfirmation. Callers must
explicitly reassess when evidence changes; there is no autonomous propagation
engine that invalidates every downstream assessment.

## Persistence, ownership and compatibility

Revision `0005_canonical_facts_findings` follows the unchanged 0004. It adds:

- canonical_fact_v244: typed semantic extension keyed by the foundation object ID.
- canonical_finding_v244: typed significance extension keyed by the same authority.
- canonical_semantic_revision_v244: immutable-through-service historical documents.

Composite object/client FKs reject missing or foreign-tenant endpoints. Revision
uniqueness and conditional updates protect history; indexed scope is compared
with typed documents and foundation identities on reads. Vocabulary, lifecycle,
source scope and document semantics remain application-boundary guarantees, as
in v2.43. Privileged raw SQL can bypass semantic validation; no CHECK invariant is
weakened. PostgreSQL and SQLite use the same schema and Decimal-string contracts.

Sessions, source connections, commit/rollback and engines remain caller-owned.
An operation and its audit are one caller transaction. No production path imports
the destructive qualification fixture. Legacy economic, opportunity, management,
benefit, API/product and diagnostic writers/consumers are unchanged. Canonical
semantics are opt-in and have one explicit writer; there is no automatic dual
write or silent consumer switch. Future cutover must separately qualify each
consumer slice, retire the corresponding legacy writer and preserve rollback.

The schema-only `tests/fixtures/v243_schema.sql` was captured from the frozen
baseline before metadata changes, then ordered by FK dependencies for PostgreSQL.
Tests seed every field of all 22 baseline tables, preserve them through upgrade
and downgrade, and independently compare fresh head with metadata.

Downgrade drops the three semantic tables, intentionally losing semantic payloads
and semantic revision history. It retains v2.43 identities, links and audits,
including pre-existing records. Re-upgrade creates empty extension tables.
Restoring payload backups is required before resuming writes for surviving IDs;
the service cannot silently reconstruct or overwrite them. This is not a lossless
operational downgrade after canonical use.

## Qualification and boundaries

Frozen tests and CI remain unchanged; new tests are added to the existing
authoritative inventory.
The live script has test-only URL/branch/direct-host opt-ins and uses only the
dedicated disposable Neon branch after independent provider verification.

Focused new qualification: 38 PASS, 0 FAIL, 0 ERROR, 0 SKIP (35 semantic/persistence
tests and 3 migration tests), with DeprecationWarning and ResourceWarning as errors.
An earlier combined run with the unchanged v2.43/v2.41 suites passed 72 tests;
the expanded focused run followed it. Compileall passed for source, migrations,
tests and scripts. The new live command refuses missing credentials before any
database access. Local SQLite operations required execution outside the filesystem
sandbox because sandbox-created temporary directories were not accessible to the
database driver; this was a sandbox permission issue, not a resource-leak workaround.

Final review exposed a defect in the new margin-significance implementation:
context-sensitive Decimal `abs` rounded a value immediately below 1 percentage
point up to the significance threshold. An added adversarial case reproduced one
failure, then the one-line `copy_abs` correction preserved all input digits and
the full 37-test focused suite passed again. The in-progress full run was stopped
and is not counted as qualification; final live and full-estate verification
include the correction. A subsequent semantic review added the five ambiguous-zero
refusals and their regression case. A source-dimension label test also confirms
spaces survive round-trip without relaxing endpoint identifiers. Superseded partial
full-estate runs are not counted as qualification. No frozen calculation or
assertion was changed.

Live qualification: PostgreSQL 18.6 on aarch64 Linux, Neon AWS eu-west-2, project
`tiny-meadow-46991842`, branch `v2-41-qualification` / `br-royal-math-za046ex1`.
Provider metadata verified non-primary, non-default and unprotected; only its
verified direct endpoint was used. No production/default connection was made.
Credentials were injected only into the qualification process, then cleared.

**69 collected/run, 69 PASS, 0 FAIL, 0 ERROR, 0 SKIP**, 236.375 seconds including
setup (231.011 seconds in the test runner), after all semantic safeguards. The suite contains 2 new live migration
tests, 35 new semantic/persistence assertions with PostgreSQL destination fixtures,
18 unchanged v2.43 persistence assertions and 14 unchanged PostgreSQL readiness/
v2.41 checks. The 69 include five pre-existing standalone static/contract checks;
the new suite also contains pure validation and inventory assertions, so 69 is
the suite count, not a claim of 69 independent database behaviours.
The owning-store Signal fixture remains SQLite by design; canonical persistence
and migration assertions use real PostgreSQL. Both upgrade paths, all 22 old-table
data preservation, populated downgrade/re-upgrade, Decimal precision, vocabulary,
scope/endpoints, correction history, caller transactions and audit passed.
Final resource counters: 0 open SQLAlchemy connections, 0 checked out, no
unraisable errors. The disposable database finished at migration 0005.

Final authoritative full estate: **384 discovered/run, 375 PASS, 0 FAIL, 0 ERROR,
9 SKIP**, 817.203 seconds, Windows 10 / Python 3.12.14, through the compatibility
entry point `scripts_run_full_regression.py`. DeprecationWarning and ResourceWarning
were errors; there were no policy errors, expected failures or unexpected successes.
The nine skips are exactly the existing live PostgreSQL tests, with the URL absent
from this non-live gate. They passed separately in the live suite above and are not
counted as passes in this result. All 38 new tests passed in this final run.

Final review: 17 intended files (2 existing files modified, 15 additions), no
historical migration, existing test, v2.43 foundation implementation or CI changes.
`git diff --check` passed; new-file whitespace, syntax and credential-pattern review
passed. Local reports/logs remain ignored under `.venv/`; nothing is staged,
committed or pushed. The unchanged CI matrix remains Ubuntu + Windows x Python
3.12 + 3.13. That matrix has not yet run for this uncommitted v2.44 tree.

Eligible mapped Facts are qualified as descriptive truth within their explicit
source/measurement contracts; this is not complete semantic coverage of the estate.
Findings are qualified as significance only within the three documented policies.
No downstream authority has switched. Source lineage depends on retaining the
owning-store rows, and counter-evidence changes require explicit reassessment.
The existing identity and typed extension interfaces support the intended next
release without an identified redesign, subject to architectural review and
subsequent cross-platform CI. This is not a formal release freeze.

No v2.45+ functionality: no general Evidence Graph, Hypotheses, disconfirmation
engine, causality, Stories, economic bridges, opportunity calculations, priority
redesign, Action Plans, memory, LLM/AI Partner, customer-facing redesign or
diagnostic 57. Future evidence graph work can reference foundation IDs and typed
extensions; it must not assume unmapped Signals or unassessed policies are solved.

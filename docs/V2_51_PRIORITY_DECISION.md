# Profit Doctor v2.51 — Priority & Decision Framework

## Authority and baseline

The frozen starting point is v2.50, `ae669d0c405587492710c4a2fc0654501ef06c3d`,
on `main`. The working tree was clean and fetching origin confirmed no divergence.
The approved conservative scope explicitly prohibits new production providers
for confidence, urgency, recurrence, controllability or causal attribution.

This release introduces an opt-in canonical assessment and adviser-decision
service. It does not replace the legacy management-attention agenda or switch
existing product/report consumers. No recommendation, client-publication,
action, benefit, AI investigation or v2.52 layer is implemented.

## Architectural reconciliation

Existing legacy management attention uses severity/count-based ranking. It is
not imported into canonical priority: its meaning and consumers remain unchanged.
Canonical Fact confidence is explicitly unassessed; Story validation prohibits
confidence/materiality uplift; Opportunity confidence is uncalibrated. Priority
does not reinterpret these controls as HIGH confidence.

The foundation has no PRIORITY object type. Rather than changing that frozen
vocabulary or pretending priority is a Finding, this release uses a typed
assessment extension with a foreign key to the existing source identity.
Adviser decisions are typed records linked to the exact assessment revision.
They do not reuse or promote legacy management decisions. Existing identifiers,
Actor/source authority, deterministic identity function, immutable text-JSON,
Decimal, ConfidenceProfile and MaterialityProfile conventions are reused.

## Structures

`PriorityBasis` retains five independent dimensions: materiality, evidence
strength, urgency, controllability and persistence. Each has governed vocabulary,
a reason and evidence references; an assessed state without evidence is invalid.
`EconomicBasis` is the sixth dimension, retaining economic meaning, amount OR
low/high/optional central, currency, dimension, horizon, evidence and limitations.
Raw Finding measurements stay in their exact typed source snapshot; they do not
become monetary losses. Missing amounts remain null, never zero.

Existing confidence and materiality profiles are retained independently.
Evidence strength is not a replacement universal confidence percentage.
`PriorityResult` exposes classification, versioned rule identifier, dimensional
reasons, gaps and the full basis. `Assessment` adds subject/client/run, immutable
revision and aware creation timestamp. All contracts reject extra fields,
invalid vocabulary, invalid ranges and floating-point financial inputs through
the existing strict contract conventions.

`AdviserRequest` records request identity, INVESTIGATE/ACCEPT/REJECT, identified
HUMAN actor with HUMAN_FD_JUDGEMENT authority, rationale and provenance.
INVESTIGATE additionally requires questions and required evidence. `Decision`
records its own immutable revision, timestamp and exact assessment revision.
The application calling this service must authenticate the adviser; recording
an Actor is not an authentication system or proof of real-world authority.

## Current production capability

`PriorityService` accepts a scoped CanonicalService and optionally the existing
OpportunityService sharing the same session/client/run. It exposes no API for
submitting arbitrary dimension values or a precomputed priority result.

Finding assessment resolves the current canonical Finding and its underlying
Facts. Superseded/invalidated Facts or changed source digests fail closed.
All source observations, scope, lineage, contradictions and mitigation remain
in the immutable source snapshot. Explicit contradiction is represented as
CONFLICTED evidence, not evidence of a causal explanation. Repeated observations
do not become recurrence. Finding significance does not become relative economic
materiality. Current profile values are copied without promotion.

Opportunity assessment accepts the stable candidate identity only to resolve
its current **qualified** Opportunity through the frozen owning service. An
unqualified candidate is refused. Current source Impact, immutable collection
evidence, origin, scope and economic validation remain that owner's authority.
The priority snapshot retains low/high, absent/exact central, CASH, currency,
horizon, partitioning, exclusions, uncertainty and EconomicEffect identity.
Addressability does not establish general management controllability; overdue
stock does not establish imminent liquidity pressure. No annualisation or new
valuation occurs. BLIND_QUALIFICATION source origin remains in the snapshot;
priority offers no monetary aggregation or route around origin/overlap controls.

Under the currently qualified production sources, overall classification is
INSUFFICIENT_EVIDENCE. That is correct governed behaviour. Adviser decisions
remain available on these assessments without changing machine evidence.

## Framework capability: isolated positive rules

The same pure `evaluate` function is exercised with explicitly labelled
SYNTHETIC_QUALIFICATION premises. These are domain qualification fixtures, not
registered production evidence providers. Production persistence rejects that
origin and rejects assessed urgency/materiality/control/recurrence states for
which no production provider exists. Even a forged CANONICAL label cannot
enable these future dimensions through the persistence reader.

Policy ATTENTION-2.51.1 uses explicit predicates, never a weighted score or
absolute currency thresholds. STRONG qualified evidence is a prerequisite for
positive framework classifications:

| Predicate | Classification | Reason code |
|---|---|---|
| HIGH materiality + CRITICAL urgency | CRITICAL | MATERIAL_IMMINENT_CONSEQUENCE |
| HIGH materiality + HIGH urgency | HIGH | MATERIAL_URGENT_CONSEQUENCE |
| HIGH materiality + RECURRING/STRUCTURAL/WORSENING | HIGH | MATERIAL_CONTINUING_CONDITION |
| Assessed materiality + HISTORICAL_ONLY + LOW urgency | LOW | HISTORICAL_NO_CONTINUING_CONSEQUENCE |
| MEDIUM materiality + MEDIUM urgency | MEDIUM | EVIDENCED_MODERATE_ATTENTION |
| No qualified predicate, weak/conflicted/unassessed evidence | INSUFFICIENT_EVIDENCE | NO_QUALIFIED_CLASSIFICATION |

Rules are evaluated in the listed order. Unknown non-decisive dimensions remain
explicit even when a qualified predicate determines attention. Controllability
does not suppress an important externally driven exposure, and never creates a
recommendation. Monetary magnitude is retained but not compared to invented
thresholds. Two HIGH results may therefore expose completely different reasons.
These predicates are framework policy, not a claim that production evidence can
currently satisfy them. Future providers need separately reviewed contracts.

## Decisions, history and holding areas

There is no automatic ACCEPT/REJECT/INVESTIGATE writer. A human command is
required for every decision. ACCEPT means adviser progression only, not client
approval, recommendation approval, guaranteed capture or realised benefit.
REJECT retains the Finding/Opportunity, assessment, rationale and complete
history. No source status, confidence or economic value is changed.

Assessment replay returns the original revision/timestamp. Changed evidence
requires an explicit predecessor revision and creates a new snapshot. Decision
request IDs provide idempotency; conflicting reuse is rejected. Decision changes
also require an explicit predecessor. Database revision uniqueness fails closed
on races; no blind retries are performed.

Automated reassessment never changes a prior adviser decision. New decisions
must reference the current assessment and current source; historical reads and
request replay remain available after source invalidation. `history` returns
all assessment and decision revisions. `holding` groups latest decisions by
choice at client scope, retaining the source identity and assessment. It exposes
whether assessment changed since decision and whether the source is current,
so stale evidence cannot be presented silently as a fresh assessment. Items
without a human decision remain available by subject/history but have no
invented holding choice. No UI or client-output publication gate is introduced.

## Persistence and migration

Forward migration `0014_priority_decision`, following `0013_opportunity`, adds:

- `canonical_priority_subject`: scoped stable source identity and source kind;
- `canonical_priority_assessment`: append-only assessment revisions and run;
- `canonical_adviser_decision`: human decision revisions, unique request ID and
  foreign key to the same subject/client's exact assessment revision;
- `canonical_priority_audit`: append-only previous/new state, actor and timestamp.

Composite client FKs protect source and assessment ownership. Run/client
consistency, source type and vocabulary are enforced by the application owner,
as in existing canonical extensions. The database enforces existence, composite
ownership and revision/request uniqueness, not arbitrary JSON semantics.
Financial precision is retained in Decimal-safe text-JSON. No native PostgreSQL
enum or SQLite-only shortcut is introduced.

The preserved `v250_opportunity_schema.sql` contains all 48 prior application
tables, independently captured before introducing priority metadata. It contains
schema and the Alembic revision marker only, not client data or credentials.
Migration qualification seeds every old table, upgrades, checks metadata/FKs,
verifies exact preservation, downgrades and re-upgrades. Clean creation and
repeat-head are separately checked. Historical migrations are untouched.

Downgrade intentionally removes all four v2.51 tables, their assessments,
decisions and extension audits. It preserves all legacy/v2.50 records and source
identities. Re-upgrade does not reconstruct deleted v2.51 history.

The caller owns the SQLAlchemy session/transaction. Nested savepoints use the
existing SQLite explicit-BEGIN safeguard; service methods never commit or close
the caller's session. No new connections or retained-file owners are introduced.

## Golden Manufacturing boundary

The approved repository v2.49 Golden Manufacturing workbook is reused unchanged.
It still establishes £340,000 CASH_TRAPPED, not an Opportunity. With no qualified
collection evidence in that fixture, Opportunity remains INSUFFICIENT_EVIDENCE
and priority correctly refuses the unqualified candidate. No amount becomes
HIGH urgency or new capture. No private v2.50 workbook or expected-result file
is copied into the repository.

This is an honest no-eligible-Opportunity end-to-end negative gate, not a claim
that this workbook exercises positive priority. Separate canonical-route tests
exercise qualified Opportunity ranges and Finding measurements, both yielding
INSUFFICIENT_EVIDENCE with retained dimensions. Synthetic framework tests alone
demonstrate positive HIGH/CRITICAL/MEDIUM/LOW classifications.

## Future governed evidence prerequisites

| Dimension | Required before any production-positive provider |
|---|---|
| Relative materiality | Explicit business denominator, matching scope/currency/period and reviewed threshold policy; values alone are insufficient |
| Confidence/evidence strength | Versioned evidence-quality policy, source authority, completeness, reconciliation, contradictions and shared-ancestry treatment; no signal-count uplift |
| Urgency | Dated consequence/deadline, current applicability and supported exposure; age or size alone is not a liquidity forecast |
| Controllability | Scoped authority, feasible management influence and constraints with evidence; negative movement or addressability alone is insufficient |
| Persistence/recurrence | Comparable periods, stable definitions, restatement/coverage checks and a governed temporal policy; run count is insufficient |
| Causal attribution | Separately qualified ECONOMIC_MECHANISM interpretation and mandatory disconfirmation; correlation or EVIDENCE_QUALITY support is insufficient |

These providers are deferred, not partially implemented. No v2.52 functionality,
economic consolidation, Opportunity recalculation, ranking score or legacy
semantic promotion is introduced.

## Qualification record

Focused strict DeprecationWarning/ResourceWarning qualification: 43 discovered/run,
43 PASS, 0 FAIL, 0 ERROR, 0 SKIP (50.080 seconds). This comprises 40 domain,
canonical-route, adviser, persistence and Golden checks plus three migration
checks. Source/tests/scripts/migrations compile successfully.

The first sandbox attempt could not open normal-host temporary SQLite files.
The initial normal-host run passed 34/35 tests; one new frozen-schema seed failed
an FK because its generic seed used a table-name identity instead of the actual
referenced row identity. The new fixture generator was corrected to resolve and
assert consistent referenced values. No migration or existing assertion was
weakened. Final focused results above cover that correction and added adversaries.

Authoritative full estate on Windows / Python 3.12.14: **780 discovered/run,
771 PASS, 0 FAIL, 0 ERROR, 9 SKIP** in 1187.734 seconds. No expected failures,
unexpected successes or warning/resource policy errors occurred. The nine skips
are the existing live PostgreSQL tests without a live URL in the local gate;
they are not passes. All 737 pre-existing tests remain registered, with 43 new
v2.51 checks added.

The uninterrupted fail-fast live gate passed **216 discovered/run, 216 PASS,
0 FAIL, 0 ERROR, 0 SKIP** (2291.313 seconds including setup/reporting;
2277.475 seconds in the test runner). PostgreSQL **18.6 (4e955f5), aarch64**,
on the independently verified `v2-41-qualification` branch
(`br-royal-math-za046ex1`, project `tiny-meadow-46991842`). The branch was ready,
non-primary, non-default and unprotected; its direct endpoint alone was used.
Primary/default was not targeted or modified, and no Neon configuration changed.

The 216 checks comprise 27 new live priority/decision/migration checks plus the
189 inherited Opportunity, receivables, Impact, Bridge, foundation and v2.41
checks. This includes clean creation, frozen upgrade, every-old-table preservation,
populated downgrade/re-upgrade, financial precision, source validation, scope/FKs,
revision/replay, human decisions, audits and caller-owned rollback. The existing
v2.41 gate passed unchanged. No retry, segmentation or infrastructure interruption
occurred. Final counts: **0 open connections, 0 checked-out connections,
0 unraisable resource errors**. Windows was held awake by the existing runner
pattern. Credentials were process-scoped and are absent from source/reports.

No production-code correction was required during final qualification. One
whitespace-only cleanup removed trailing spaces from the newly captured frozen
DDL fixture; its SQL tokens were verified unchanged. All implementation/test
source hashes stayed unchanged during the final full/live gates. Documentation
was updated afterwards with the measured results.

Final `git diff --check`, new-file whitespace checks and credential/artifact
review passed. The complete intended change set is 22 files: 11 modified and
11 new. Existing assertion changes are solely the nine expected-head updates.
No implementation, test, fixture, or qualification file has been staged.
The unchanged Ubuntu/Windows × Python 3.12/3.13 CI remains a post-approval gate:
uncommitted local code cannot claim a successful remote matrix. No commit or
push is authorised at this implementation stage.

## Changed-file inventory

| File | Purpose |
|---|---|
| profit_doctor/reasoning/priority/__init__.py | Opt-in package boundary |
| profit_doctor/reasoning/priority/contracts.py | Typed dimensions, economics, assessment and human decision contracts |
| profit_doctor/reasoning/priority/engine.py | Shared explicit predicate evaluator; no weighted score |
| profit_doctor/reasoning/priority/service.py | Canonical source resolution, immutable persistence, history and holding queries |
| profit_doctor/persistence/priority_schema.py | Four additive tables and ownership/revision constraints |
| profit_doctor/persistence/__init__.py | Register new metadata only |
| alembic/versions/0014_priority_decision.py | Forward migration and explicit downgrade |
| tests/fixtures/v250_opportunity_schema.sql | Independent preserved 48-table baseline |
| tests/test_priority_v251.py | 40 domain, production-boundary, human authority, persistence and Golden checks |
| tests/test_priority_migrations_v251.py | Three clean/frozen/schema-preservation checks |
| scripts/qualify_priority_postgresql_v251.py | Disposable fail-fast live gate, inherited tests and resource accounting |
| qualification/test_estate_v242.json | Additive registration of the two new modules |
| tests/test_canonical_migrations_v244.py | Expected-head advancement only |
| tests/test_graph_migrations_v245.py | Expected-head advancement only |
| tests/test_hypothesis_migrations_v246.py | Expected-head advancement only |
| tests/test_story_migrations_v247.py | Expected-head advancement only |
| tests/test_measurement_context_migrations_v248.py | Expected-head advancement only |
| tests/test_economic_bridge_migrations_v248b.py | Expected-head advancement only |
| tests/test_economic_impact_migrations_v249.py | Expected-head advancement only |
| tests/test_receivables_migrations_v249.py | Expected-head advancement only |
| tests/test_opportunity_migrations_v250.py | Expected-head advancement only |
| docs/V2_51_PRIORITY_DECISION.md | Architecture, governance, evidence prerequisites and qualification |

No historical migration, existing source assertion, diagnostic calculation,
Signal semantic, frozen reasoning writer, Opportunity capture rule, management
consumer, v2.41 live gate or v2.42 CI/resource owner is modified. Local logs,
JSON reports, review scripts and byte-hash snapshots remain ignored under `.venv`.

# Profit Doctor v2.45 — Evidence Graph

## Baseline and boundary

Implementation began from clean `main` / `origin/main` at
`368cd6a739bd7dd26211d30509750287dd51f50b`. All four v2.44 CI matrix jobs were
verified successful. The v2.43 architecture reconciliation and v2.44 typed
semantic extensions remain the design authority.

This release answers how evidence relates, not why an outcome happened.
The graph is opt-in. No existing diagnostic, intake, reasoning, economic,
Opportunity, management, benefit or product/API consumer switches to it.
No legacy object or status is automatically promoted. No v2.46 functionality,
Hypotheses, disconfirmation, causality, supported drivers, Stories, bridges,
new Opportunity logic, prioritisation, Action Plans, memory, LLM calls,
AI narrative, customer-facing graph or diagnostic 57 is implemented.

## Architecture and identity

`reasoning/graph/` uses the existing v2.43 Contract serializer, ReasoningObject,
EvidenceLink, source authority and audit contracts. Facts and Findings are read
through the unchanged v2.44 CanonicalService. No new node identity or edge store
is created. `Node` is a validated projection, not a competing persisted entity.

Supported endpoints are canonical Facts, canonical Findings and foundation
Signal/evidence identities. A Finding projection requires exactly one observation
for the requested run; it never guesses which historical period is intended.
Bare foundation FACT/FINDING identities without their canonical payloads fail
closed. Source mutation after Fact creation is rejected rather than silently
reinterpreting a frozen Fact. Existing source/client/run ownership is revalidated.

The only new table is `evidence_graph_record`, a governance extension keyed by
the existing EvidenceLink ID and append-only revision. It contains indexed client, recording run and
endpoints, plus a deterministic typed `EG-2.45.1` document with endpoint revisions,
ancestry/scope/authority snapshots, characteristics, explicit rationale and any
co-movement basis. Financial values remain in their existing Decimal-safe Facts.

`EvidenceGraph.link` reuses an existing matching EvidenceLink rather than copying
it. Existing duplicate links fail closed for explicit reconciliation. New IDs
derive deterministically from client, endpoint pair and relationship. Repeated
requests return the recorded snapshot without new edges or audits. Concurrent
insert races are rejected by primary-key uniqueness; the caller rolls back and
replays the transaction. There is no hidden retry or transaction ownership.

Records are immutable, versioned evidence snapshots. A changed endpoint revision
or basis raises RevisionConflict unless the caller explicitly supplies the current
expected_revision. A qualified revision appends a new snapshot and audit retaining
the previous value; it never changes the underlying relationship identity. The
composite primary key rejects concurrent writers of the same next revision.
`get` reads the latest or an explicit revision; `history` retains every revision.
`freshness` returns CURRENT, STALE or UNRESOLVED, so historical evidence remains
distinguishable from current proof. No correction UI or transition engine is added.

## Relationships and authority

The v2.45 writer allows SUPPORTS, CONTRADICTS, QUANTIFIES, CONTEXTUALISES,
TEMPORALLY_PRECEDES, CO_MOVES_WITH and MITIGATES. No new relationship enum was
needed. All except CO_MOVES_WITH are directional. Co-movement normalises endpoint
order and swaps the corresponding series basis, making reverse replay identical.
Self-links are prohibited. Client ownership is enforced; source and target entity
scope must match exactly. Cross-entity segmentation/localisation is deferred
rather than guessing that business evidence applies to a specific customer.

Ordinary relationships are explicit declarations with a rationale, not automatic
truth, confidence or causal promotion. Temporal/co-movement declarations undergo
additional checks below. POTENTIALLY_DRIVES, SUPPORTED_DRIVER_OF and other causal
vocabulary remain frozen in v2.43 but are rejected by this writer.

Links preserve the source object's authority. Management assertions, human/FD
judgement and unclassified legacy context may contextualise, contradict or
mitigate, but cannot be written as verified system corroboration. The graph does
not convert management statements into canonical Facts. Existing v2.44 support,
contradictory and mitigating links are queryable in place; an explicitly reviewed
link can acquire a governance record without copying its identity.

Legacy free-text context/contradiction rows are not bulk-converted. Their current
source-type and entity/period contracts do not justify silent canonical promotion.
Callers can supply already governed foundation evidence. Cross-entity management
context requires a future qualified scope contract and is currently refused.

## Ancestry and independence

AncestryReader traverses real owning-store rows: Signal, diagnostic execution,
diagnostic_lineage, primitive_result, calculation_lineage, dataset_version,
dataset and source_file. Explicit sales_transaction references retain their record
identity. Dataset ancestry is not expanded into invented record selections from
scope prose. A generic primitive name is not a primitive-result identity.

Reference strings retain existing store/resource/key identities. Source dataset,
file, record, primitive and diagnostic-family sets are exposed separately.
Dataset versions retain their logical dataset and source-file roots. Files must
exist with a hash and immutable flag; ownership is checked. Unknown resources,
missing paths, cycles and absent source roots are explicit unresolved items.
Canonical/SQLAlchemy ancestry not covered by this owning-store adapter remains
unresolved; it is not guessed. Invalid direct ownership anchors fail closed with
ScopeError; unresolved nested ancestry yields INDETERMINATE. Completeness means
all retained paths resolved, not proof that upstream recorded every dependency.
No new source/dataset identities are created.

Independence is categorical and applies to the retained provenance granularity:

- SAME_ANCESTRY: identical resolved root sets.
- SUBSTANTIALLY_SHARED: one root set wholly contains the other, or different
  datasets retain a shared source file/primitive/record. This is a structural
  category, not an undisclosed weighting or percentage.
- PARTIALLY_SHARED: intersecting root sets where each retains additional roots.
- INDEPENDENT: disjoint resolved dataset and source ancestry, eligible evidence,
  and system-derived authority on both sides.
- INDETERMINATE: incomplete ancestry, ineligible evidence or unverified authority.

INDEPENDENT means provenance-disjoint within the retained owning-store evidence;
it does not certify statistical independence, absence of undocumented copying,
business independence or causation. Different diagnostic names alone never
establish it. Shared dataset-level evidence stays shared even if diagnostics use
different undocumented row subsets. Such conservative granularity is intentional.

Management assertions never become independent verified corroboration. Source
retention and immutability remain owning-store responsibilities, not distributed
transactions or archival copies introduced by the graph.

## Temporal and co-movement rules

Temporal comparison exposes PRECEDES, FOLLOWS, OVERLAPS, SAME_COMPARABLE_PERIOD,
NOT_COMPARABLE and INSUFFICIENT_PERIOD_INFORMATION. Entity and reporting basis
must match. Dates must exist before chronology is established. Strictly disjoint
ordered intervals establish precedence; identical intervals establish the same
comparable period. Overlapping intervals do not become precedence. A recorded
TEMPORALLY_PRECEDES link additionally requires eligible endpoints.

CO_MOVES_WITH requires at least four distinct canonical Fact observations on each
side, exact aligned periods, ordered non-overlapping equal-duration intervals,
and unchanged metric, slot, unit, currency, entity, mapping and period basis within
each series. Endpoints must be the final aligned Facts with comparable bases.
All observations must be eligible and have complete ancestry. Every consecutive
direction of movement must be nonzero and match across the two series. Decimal
comparisons avoid rounded subtraction. This is the explicitly named
ALIGNED_NONZERO_DIRECTION-1 method, not Pearson correlation or causal inference.
Constant series, reverse chronology, unequal alignment and same-run coincidence
without series evidence are refused. Negative/inverse co-movement is not yet
qualified. The retained basis contains Fact IDs, never caller-supplied values.

## Queries and evidence characteristics

Deterministic service operations expose nodes by observation run, entity, exact
period, diagnostic family and authority; incoming/outgoing/both neighbours by
relationship and recording run; shared ancestry; independent candidate evidence;
and relationship freshness. Temporal and co-moving neighbours use the same
relationship query. Existing foundation links remain the relationship authority. Neighbour queries
return declarations, including pre-existing links without v2.45 governance; these
are not silently certified. Consumers use `get`/`freshness` to distinguish governed
current evidence from ungoverned or historical declarations.
An unfiltered neighbour query is explicitly across this client's runs; callers
can constrain the recording run. Finding observations use explicit run scope.

Characteristics expose categorical independence with rationale, shared references,
dataset/source diversity through Node ancestry, authorities, lineage completeness,
temporal comparability, contradiction presence and separate data-confidence
dimensions. There is no universal evidence score, independence percentage or
confidence uplift. Contradiction means evidence tension, not Hypothesis rejection.
Queries do not mutate Facts, Findings or their confidence/materiality profiles.

## Migration and compatibility

Forward migration `0006_evidence_graph` follows unchanged 0005 and creates only
the governance-extension table. Existing tables, historical migration files and
all existing source contracts are unchanged. The new table uses the existing
Text/Decimal-string contract convention, compatible with SQLite and PostgreSQL.
FKs protect link existence, endpoint/client ownership and run existence; matching
link/client semantics and run ownership are additionally enforced by the service.
As in v2.43, privileged raw SQL can bypass application semantic validation.

`tests/fixtures/v244_schema.sql` was captured by upgrading an isolated database
to frozen 0005 before adding graph metadata. Qualification seeds every column of
all 25 baseline application tables, proves preservation through upgrade/downgrade,
checks fresh metadata alignment, and tests populated governance removal followed
by empty re-upgrade. Downgrade intentionally drops governance snapshots but keeps
foundation links/audits and canonical Facts/Findings. Restore snapshots before
replaying previously governed links; missing governance is detected using retained
link metadata/audits and is not silently reconstructed.

The sole existing-test adaptation advances the explicit expected Alembic head in
the v2.44 migration test from 0005 to 0006. Its schema, FK, data preservation,
downgrade and repeat-upgrade assertions remain intact. v2.41 tests, v2.42 CI and
resource-lifecycle code, v2.43 foundation, v2.44 semantic writers and the 56
diagnostics are untouched. Inventory additions are additive.

## Qualification

Compilation passed. Final focused qualification ran 111 tests: 111 PASS, 0 FAIL,
0 ERROR, 0 SKIP, with DeprecationWarning and ResourceWarning treated as errors
(51.491 seconds). This includes all 35 new tests plus the v2.43/v2.44 contract,
persistence and migration suites. Existing Pydantic serializer UserWarnings from
v2.44 enum model_copy paths remain unchanged; the established strict policy treats
deprecation/resource warnings as errors and does not suppress these UserWarnings.

The initial 28-test focused run exposed two new test-fixture mistakes (26 PASS,
1 FAIL, 1 ERROR): a business scope paired with a customer-only mapping, and an
edge-count expectation omitting the existing Signal-to-Fact link. Both were fixed
without weakening frozen assertions. Intermediate 71/109/110-test runs passed.
An initial live run was deliberately stopped while explicit append-only relation
revisions were added; it is not counted as qualification.

Final live qualification: PostgreSQL 18.6 on aarch64 Linux, Neon AWS eu-west-2.
Provider metadata confirmed project `tiny-meadow-46991842`, branch
`v2-41-qualification` / `br-royal-math-za046ex1`, non-primary, non-default and
unprotected. Only its independently verified direct endpoint was used. The
production/default branch was neither connected to nor modified. Credentials
were process-only and cleared; no URL or password is persisted in the repository.

**103 collected/run, 103 PASS, 0 FAIL, 0 ERROR, 0 SKIP**, 424.437 seconds.
The suite includes 32 new graph tests, 2 new live migration tests, and the 69
v2.44 qualification checks (including existing v2.43 and v2.41 checks). Some are
pure contract/static assertions; this is not a claim of 103 independent SQL
behaviours. Canonical/graph persistence uses real PostgreSQL. The owning-store
Signal fixtures intentionally remain SQLite, matching the existing architecture.
Clean head, frozen-v2.44 upgrade, preservation of all 25 old tables, populated
downgrade/re-upgrade, graph persistence/revisions, lineage, authority, scope/FKs,
precision, audits and caller transactions passed. Final resource counters were
0 open connections, 0 checked-out connections and no unraisable errors. The
disposable branch finished at migration 0006.

Final authoritative non-live estate: **419 discovered/run, 410 PASS, 0 FAIL,
0 ERROR, 9 SKIP**, 600.781 seconds on Windows 10 / Python 3.12.14 through
`scripts_run_full_regression.py`. There were no policy errors, expected failures
or unexpected successes. The nine skips are exactly the existing explicitly live
PostgreSQL tests; they passed separately in the live suite and are not counted as
local passes. All 35 added graph/migration tests passed in the complete estate.
DeprecationWarning and ResourceWarning remained errors, including delayed
unraisable resource checks from the unchanged v2.42 runner.

Final diff review covers 14 intended files (3 modifications, 11 additions).
`git diff --check`, new-file whitespace/syntax checks and credential-pattern scans
passed. The preserved schema fixture and this document are intentional source
artifacts; logs/JSON results remain ignored under `.venv/`. Nothing was staged,
committed or pushed. No diagnostic, economic or product contract changed. The
existing-test change is only the explicit new Alembic head, not an assertion
removal or reduction. No v2.46 work was implemented.

The unchanged CI matrix remains Ubuntu + Windows x Python 3.12 + 3.13. It has not
run for this uncommitted v2.45 tree, so this is local/live qualification for
architectural review, not a formal cross-platform release freeze.
The new suites cover ancestry sharing/diversity/unknowns, authority, chronology,
co-movement, contradiction, entity/tenant/run scope, replay, primitive paths,
lineage cycles, freshness, persistence/FKs, audit, rollback, and migration paths.

## Next release and limitations

The intended next release is v2.46 Hypothesis & Disconfirmation. Its consumers can
use canonical identities, versioned relationship snapshots, explicit unknowns and
structured evidence characteristics without a new graph identity store. It must
respect stale/unresolved snapshots and incomplete ancestry. It must not assume
that every Signal has a canonical Fact, every source has record-level lineage,
or every declared relationship proves a conclusion. No v2.46 work begins here.

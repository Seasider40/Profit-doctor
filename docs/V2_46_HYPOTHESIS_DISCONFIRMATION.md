# Profit Doctor v2.46 — Hypothesis and Disconfirmation

Local and live qualification complete; pending architectural review and subsequent
cross-platform CI. This is not a release freeze. No commit or push was performed.

## Baseline and authority

Clean main/origin/main at 8bd6c130efe879991bebc7ad0347c69e8f3a5b13. All four
v2.45 CI jobs passed. The original engineering contract and two subsequent approved
reconciliations govern this release. The frozen v2.43 identity boundary, v2.44
canonical writers and v2.45 Evidence Graph remain authoritative and unchanged.

The new opt-in HypothesisService is not called by existing runtime/product writers.
There is no legacy promotion, dual write, downstream switch or new diagnostic.

## Class and proposition

Classes are EVIDENCE_QUALITY, ECONOMIC_MECHANISM and NULL_OR_ALTERNATIVE. Candidate
roles (PRIMARY, ALTERNATIVE, NULL) are separately governed; class describes what
kind of proposition is assessed, while role describes its place in an investigation.
No role is selected as a universal winner. Several primary candidates are possible
because they ask different questions. Peers share an existing Finding and explicit
analytical run; deterministic peer queries avoid another relationship store.

SUPPORTED means that this contract's support requirements survived its mandatory
disconfirmation search. It is never a universal causal/root-cause status. Each
Interpretation repeats the class, structured proposition key and contract version;
contract validation rejects cross-class substitutions. No LLM or narrative parser
participates in generation or assessment. Narrative is not the proposition authority.

## Six retained contracts (HC-2.46.1)

| Contract | Class / role | Finding coverage | Support | Other outcomes |
|---|---|---|---|---|
| INDEPENDENT_CORROBORATION | Evidence quality / primary | Revenue movement, margin movement, customer concentration | Eligible independent reproduction of exact typed values, entity and period; no unresolved challenge or contradictory comparable measurement | Shared reproduction: PLAUSIBLE. Independent comparable disagreement: CONTRADICTED. Missing/unsafe evidence: UNRESOLVED. |
| SHARED_CORROBORATION | Evidence quality / alternative | Same three | At least one exact comparable reproduction has SAME_ANCESTRY or SUBSTANTIALLY_SHARED ancestry | PARTIALLY_SHARED: PLAUSIBLE. All observed comparable reproductions independent: CONTRADICTED. Unknown or absent reproduction: UNRESOLVED. |
| TEMPORAL_NULL | Null or alternative / null | Same three | A declared related same-metric eligible Fact demonstrably has different/incomparable known periods | All relevant pairs exactly comparable: CONTRADICTED. Missing dates/relevant pairs: UNRESOLVED. No claim that timing caused the condition. |
| MARGIN_PRICING | Economic mechanism / primary | Margin movement | Not achievable under this version's frozen evidence prerequisites | UNRESOLVED with like-for-like identity, quantity, period, direct-cost and segmentation gaps. |
| MARGIN_COST | Economic mechanism / alternative | Margin movement | Not achievable under this version's frozen evidence prerequisites | UNRESOLVED with comparable direct-cost, supplier-cost, quantity, recovery and segmentation gaps. |
| MARGIN_MIX | Economic mechanism / alternative | Margin movement | Not achievable under this version's frozen evidence prerequisites | UNRESOLVED with comparable segment margin/share, coverage and residual decomposition gaps. |

This is three supported Finding types, not coverage of all diagnostics or all
economic explanations. Revenue price/volume attribution and customer-dependence
mechanisms were considered and deferred. Descriptive mechanical bridges and
concentration do not supply qualified economic disconfirmation. See the feasibility
document for the exact evidence boundaries.

The first three contracts can reach SUPPORTED today using qualified retained Facts.
The temporal-null contract establishes a mismatch, not an explanation of economic
movement. No economic-mechanism contract currently reaches SUPPORTED. This is an
explicit release limitation, not a hidden threshold or fabricated coverage claim.

Minimum diversity is proposition-specific: independent corroboration needs the
origin plus an INDEPENDENT reproduction; shared corroboration and temporal-null
need two eligible endpoints with resolved ancestry but do not require independent
roots to establish a structural sharing/mismatch proposition. Neither latter
contract contributes an independent confirmation of an economic mechanism.

## Search, independence and disconfirmation

Every assessment executes ORIGIN_CURRENT, AUTHORITY, LINEAGE, SHARED_ANCESTRY,
TEMPORAL, SEGMENTATION, COUNTER_EVIDENCE and ALTERNATIVES checks. The resulting
check vector and source snapshots are retained. No caller supplies an outcome,
support flag, independence percentage or confidence threshold.

The search scans all retained canonical Facts in the same client/run, not only
hand-selected support edges. Exact slot metric/unit/basis/currency definitions
select potential reproductions; exact entity scope and graph temporal comparison
control comparability. Values are compared losslessly without financial arithmetic.
Related graph declarations on the Finding and its observation are also searched
in both directions. Hypothesis/Interpretation declarations are not evidence for
other hypotheses. This prevents assessment recursion or cross-class promotion.

Graph characteristics supply categorical independence and ancestry completeness.
Shared evidence does not count as independent corroboration. Partial/ineligible or
unresolvable relevant evidence blocks support. Unknown dates do not become temporal
contradictions. All confidence dimensions remain NOT_ASSESSED, including when an
evidence-quality proposition is supported. Materiality remains the Finding's
existing assessment; no new materiality or universal evidence score is computed.

Declared management/context challenges retain authority. They trigger investigation
gaps rather than becoming verified contradictions or being silently ignored when
other sources agree. They cannot verify pricing/cost/mix mechanisms. Retained
provenance independence cannot rule out undocumented upstream copying.

Search is bounded to the explicit analytical run and retained graph declarations;
it does not claim an exhaustive external search or autonomous discovery of source
files. Cross-entity evidence is preserved in search snapshots but cannot establish
same-entity reproduction or repair missing segmentation. Changing source data or
Finding observation requires explicit reassessment; there is no automatic propagation.

A stored status is the last assessed state, not a live assertion that its sources
have remained unchanged. Future consumers must reassess before relying on current
support. Invalid or bare foundation identities without canonical payloads fail
closed, consistent with the frozen graph boundary; callers roll back on errors.
Sources without retained exact periods remain unresolved even when other values
match; the release does not populate missing dates in frozen diagnostic output.
Large-run query latency and snapshot storage growth have not been benchmarked.

## Gaps and competing interpretations

EvidenceGap retains missing evidence, reason, dimension/scope, investigation request,
related identities and whether support, contradiction or both are blocked. Mechanism
gaps do not invalidate the underlying observed condition. Requests are investigation
requirements, not Action Plans or recommendations. Canonical maps refuse unsafe
realised-price and purchase-recovery Signals exactly as before. Portfolio residual
does not become pure mix. No new segmentation or analytical primitive is introduced.

The adversarial example is intentional: a margin Finding independently reproduced
on distinct retained ancestry yields EVIDENCE_QUALITY/SUPPORTED, while pricing,
cost and mix hypotheses for that same Finding remain ECONOMIC_MECHANISM/UNRESOLVED.
Shared/partially shared alternatives can coexist; no loser is deleted or promoted.

## Persistence, revisions and audit

Hypothesis and Interpretation use existing foundation IDs, client/run ownership,
lineage, status validation, EvidenceLink and audit events. UUID/hash conventions,
Pydantic serialization and SQL Text JSON match earlier canonical extensions.
Hypothesis identity includes Finding, run, contract key/version; interpretation
identity is stable for that Hypothesis. Hypothesis-Finding links contextualise
the proposed explanation, never assert it. Assessment evidence links target the
Interpretation; no causal relationship is generated or promoted.

Migration 0007_hypothesis_interpretation follows unchanged 0006. It creates
canonical_hypothesis (current typed state) and canonical_interpretation_revision
(append-only assessment snapshots). Composite foundation/client FKs protect
ownership/existence; service checks enforce endpoint types and run agreement.
Privileged raw SQL can bypass semantic validation, as in earlier releases.

Unchanged evidence replays without new writes or audits. Changed evidence requires
explicit expected_revision; the writer appends assessment history, updates the
foundation status/revision and audits the full previous/new Interpretation.
Optimistic revision checks and primary keys reject concurrent stale writes.
Callers own commit/rollback and must roll back the complete transaction on errors.

Contract keys and HC-2.46.1 definitions are retained historical semantics. A future
corrected contract must retain this version's reader/evaluator and introduce a
qualified version/key; overwriting a historical registry definition is forbidden.

Downgrade drops the two new semantic tables, preserving all v2.45 data and foundation
identities/links/audits. This intentionally removes typed v2.46 payloads. Restore
payloads before replay: surviving identities cannot be silently reconstructed.
The frozen fixture captures actual 0006 DDL, independently of current metadata.

## Non-goals and future prerequisites

No causal conclusion, Economic Story, economic bridge, impact/opportunity redesign,
priority change, management recommendation, Action Plan, benefit/memory reasoning,
LLM/AI narrative, customer-facing change or diagnostic 57 is implemented.

v2.47 can consume class-scoped Interpretations, but must preserve unresolved
mechanisms. Pricing/cost/mix Stories that claim explained economic mechanisms need
separately qualified identity/segmentation/comparability evidence first. Story work
that preserves those unknowns need not invent those capabilities. This is a
coverage prerequisite for particular Stories, not authorization to fill gaps now.

## Qualification

Compilation passed. Final focused qualification: 152 tests, 152 PASS, 0 FAIL,
0 ERROR, 0 SKIP, 87.293 seconds, with deprecation/resource warnings as errors.
This covers 41 new tests and 111 v2.43-v2.45 compatibility tests.

Initial development qualification ran 64 tests (including an inadvertently imported
32-test fixture class), with 60 PASS and 4 FAIL. Corrections fixed tuple/list snapshot
round-trip equality, invalid-origin outcome handling and duplicate test collection.
Subsequent 35- and 149-test runs passed. Integrity review added snapshot digest and
incomplete-origin checks. A later review found lexical Decimal-string comparison;
the writer now compares typed Decimal measurements and retains exact snapshot strings.
A dedicated precision regression passed. Initial live/full runs were interrupted to
make this correction and are not reported as completed qualification.

Final authoritative full estate: 460 discovered/run, 451 PASS, 0 FAIL, 0 ERROR,
9 SKIP, 646.016 seconds on Windows 10 / Python 3.12.14. There were no policy errors,
expected failures or unexpected successes. The nine skips are the existing live
PostgreSQL tests, not local passes. The unchanged v2.42 runner enforced strict
DeprecationWarning/ResourceWarning and delayed unraisable-resource checks.
Existing Pydantic UserWarnings and deliberate invalid-enum mutation test warnings
were not suppressed; the established policy does not treat all UserWarnings as errors.

Final live PostgreSQL: 143 collected/run, 143 PASS, 0 FAIL, 0 ERROR, 0 SKIP.
Suite time 699.136 seconds; total qualification time 702.610 seconds. PostgreSQL
18.6 on aarch64 Linux (Ubuntu gcc 13.3), Neon AWS eu-west-2. Provider metadata
verified project tiny-meadow-46991842, branch v2-41-qualification /
br-royal-math-za046ex1 as ready, non-primary, non-default and unprotected. Only
its independently verified direct endpoint was used; production/default was not
connected to or modified. Credentials were process-only, then cleared.

The live suite adds 30 Hypothesis persistence/adversarial tests, 8 gap-contract
tests and 2 live migration tests to the 103 existing v2.45 qualification checks.
Some checks are pure/static contracts, not distinct SQL behaviours. Canonical
persistence runs on real PostgreSQL; owning-store Signal fixtures remain SQLite,
matching the existing architecture. The unchanged nine live v2.41 tests passed.
Resource counters: 0 open connections, 0 checked-out connections, no unraisable
errors. The disposable database finishes at 0007. Clean creation, frozen-v2.45
upgrade, every column of all 26 baseline application tables, populated semantic
downgrade and re-upgrade, FKs, precision, scope, audit and caller transactions passed.

All 18 intended changed/new files were reviewed. Existing source changes are only
the additive metadata registration; existing test changes are exactly two expected
head literals (0006 to 0007), with preservation/schema assertions intact. Inventory
entries are additive. Historical migrations, v2.41 qualification, v2.42 CI/resource
ownership, v2.43 foundation, v2.44 semantics/writers, v2.45 graph, diagnostics,
economic/Opportunity/management/benefit/longitudinal/product/API behavior remain
unchanged. Compilation, git diff --check, new-file whitespace/AST/JSON checks and
credential-pattern review passed. Reports/logs and environment files remain ignored
under .venv; the frozen schema fixture is an intentional qualification artifact.

The unchanged Ubuntu/Windows x Python 3.12/3.13 CI matrix has not run for this
uncommitted release. No formal cross-platform freeze is claimed.

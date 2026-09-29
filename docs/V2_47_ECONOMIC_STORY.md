# Profit Doctor v2.47 - Economic Story Engine

## Baseline and authority

Started from clean main/origin/main at
f2a7046e11bb4a9960cc2c578fc8dd6bb3c37b69. All four frozen v2.46 Full Estate CI jobs
(Ubuntu/Windows, Python 3.12/3.13) passed. The user approved the condition-only
catalogue and explicitly deferred positive mechanism-resolved qualification.

This follows v2.43 Option B: typed semantic extensions of the existing canonical
identities, with no copying or automatic promotion of legacy economic stories.
StoryService is opt-in. Existing economic/product consumers remain unchanged.
The canonical destination is not a second permanent authority: any future cutover
requires a separately qualified single writer and consumer migration.

## Feasibility and catalogue

| Candidate | Classification | v2.47 disposition / future prerequisite |
|---|---|---|
| MARGIN_COMPRESSION | CONDITION_ONLY | Implemented for significant negative Contribution 0 margin movement. This is not relabelled gross-profit deterioration. |
| CUSTOMER_CONCENTRATION_DEPENDENCY | CONDITION_ONLY | Implemented for significant largest-customer revenue share. No renewal risk, loss probability or causal dependency is inferred. |
| LOW_QUALITY_GROWTH | INSUFFICIENT_EVIDENCE | Deferred: qualified comparable revenue/margin reporting bases and a governed cross-metric condition contract are required. Equal dates alone do not override the frozen graph's basis check. |
| PROFIT_TO_CASH_DISCONNECT | INSUFFICIENT_EVIDENCE | Deferred: a governed profit-to-cash Finding/reconciliation, matched periods and coverage are required. Working-capital stock Facts do not establish a profit-to-cash bridge. |
| COST_GROWTH_OUTPACING_ECONOMIC_OUTPUT | INSUFFICIENT_EVIDENCE | Deferred: qualified cost/output Finding, matching window lengths, coverage and compatible measures are required. Captured overhead windows may differ. |

Exactly two of five candidate contracts are implemented. Registry SC-2.47.1 has
no generic fallback. The other three prerequisite capabilities are not implemented.

## Governed conditions

Each contract requires one eligible canonical Finding, its Fact-to-Finding support
link, a current supported INDEPENDENT_CORROBORATION Interpretation and an exact
independently reproduced observation. Source evidence must be current, FULL,
system-derived, without limitations, with complete retained ancestry and known
identical periods/reporting basis/entity. Multiple diagnostics or Findings alone
do not establish a Story. Shared/partial/indeterminate ancestry is exposed but
cannot substitute for independent corroboration in this initial catalogue.

Margin compression requires a derived Contribution 0 margin change <= -1
percentage point. Concentration requires observed largest-customer revenue share
>= 15%. These directional condition rules reuse the v2.44 significance boundaries.
Positive margin movement is not compression. No Story is created for an absent,
immaterial, unsupported, contradictory, unrelated or insufficiently evidenced
condition. Unknown/deferred contracts are explicitly rejected.

The engine searches all retained same-client/run, same-semantic, exact-entity
Facts, including unlinked counter-evidence. Comparable disagreements, regardless
of shared ancestry, prevent support. Declared contradiction and mitigation in
either orientation are retained. Unverified management context is an unresolved
challenge, never a verified Fact or mechanism. Existing Stories can be held at
INVESTIGATING as evidence weakens; they are not silently deleted or resolved.

The read-only v2.46 search revalidates Interpretation snapshots against current
Finding, Fact, ancestry and source relationships. Changed evidence raises a
revision conflict requiring explicit Hypothesis reassessment before synthesis.
Downstream Hypothesis/Interpretation/Story relationships are excluded from source
relationship freshness comparison so that synthesis cannot corroborate itself.
No frozen v2.46 method or validator is modified.

## Resolution and uncertainty

Resolution vocabulary distinguishes CONDITION_STORY and MECHANISM_RESOLVED_STORY.
The latter is reserved but rejected for every positive v2.47 Story. No current
qualified ECONOMIC_MECHANISM Interpretation can be SUPPORTED through the frozen
v2.46 boundary. This is an evidence qualification limitation, not a Story defect.

Qualification must prove the distinction, reject silent promotion, reject
fabricated mechanism support and keep EVIDENCE_QUALITY support separate. A
positive mechanism-resolved test is intentionally not required or simulated.
Future enabling work requires a separately qualified economic-mechanism contract,
its actual evidence prerequisites, mandatory disconfirmation and a qualified
Story-level relevance rule. A bare SUPPORTED label will never be sufficient.

Stories retain class-scoped Interpretations, explicit unresolved mechanism state,
v2.46 EvidenceGap structures, investigation requests and limitations. Margin
pricing/cost/mix gaps remain visible. Concentration alone does not explain WHY.
ConfidenceProfile and MaterialityProfile remain independently NOT_ASSESSED/unknown.
Exact Decimal measurements are retained with their original metric/unit/basis;
no amount, confidence score or universal materiality score is calculated.

## Identity, lifecycle and history

Stable identity derives from client, contract family, exact entity, governed
reporting basis and retained mapping version, not title or run count. Current
scope and first/latest seen runs are retained. Each changed synthesis requires
expected_revision, appends an immutable snapshot and audit, and uses optimistic
revision checking. Unchanged evidence replays without new versions/audits.

For ordered runs with disjoint equal-duration reporting intervals and the same
semantic identity, the contract's exact measure determines improving/worsening/
persistent. For margin compression this means the magnitude of negative movement,
not recovery of a historical margin level. For concentration it is revenue share.
No temporal transition is inferred merely from another run or unknown dates.

Resolution requires new eligible, independently corroborated comparable evidence
that the specified condition is absent and a non-held canonical assessment.
Where a non-significant observation cannot generate new v2.46 Hypotheses, previous
Interpretations remain explicitly historical (their original run IDs are retained).
They do not prove current resolution; the new canonical observations do. A later
qualified condition after resolution reopens the same identity and records
REOPENED as transition provenance, reusing existing SUPPORTED lifecycle vocabulary.
No new v2.43 status or automatic ACTIONABLE/Opportunity decision is introduced.
The qualified writer emits SUPPORTED, INVESTIGATING, IMPROVING, WORSENING,
PERSISTENT and RESOLVED. Other foundation Story vocabulary remains reserved for
separately qualified policies; in particular, this release cannot emit QUANTIFIED
or ACTIONABLE. Unresolved mechanisms are independent from the condition lifecycle.

## Effects and deterministic projection

Existing same-client, run-compatible EconomicEffects may be referenced through
v2.43 EffectReference. No effect identities are manufactured and no Story/effect
amounts are added. This preserves future double-count protection without financial
consolidation. Projection returns structured condition, presence/status, exact
scope/measurements, references, class-scoped outcomes, ancestry characteristics,
counter-evidence, gaps, investigation requirements and limitations. Text is a
fixed contract projection, never analytical authority or AI-generated narrative.

## Persistence and migration

Forward migration 0008_economic_story follows unchanged 0007. It adds only
canonical_story and canonical_story_revision. Both extend existing foundation
identity via client-scoped FKs; current state also references its Finding.
Application readers/writers validate typed semantics and indexed scope. As in
the prior releases, privileged raw SQL is not a replacement semantic writer.
Documents use the existing deterministic Pydantic/Decimal-string/Text convention
for SQLite/PostgreSQL parity. The caller owns Session, transaction and engine.

The frozen v246_schema.sql was captured from actual migration 0007 before new
metadata registration. Migration tests seed every column in all 28 baseline
application tables, preserve them through upgrade/downgrade, inspect new FKs and
metadata, and verify re-upgrade. Downgrade intentionally removes typed Story state
and revision history while preserving old rows and foundation identities/links/
audits. Restore typed history before replay; missing payload/history fails closed.

Only existing migration-test expected-head literals advance to 0008; historical
migrations, schema/preservation assertions, v2.41 gate, v2.42 CI/lifecycle, v2.43-
v2.46 semantics, 56 diagnostics, Signals and existing product behaviour are unchanged.

## Qualification

Initial focused run: 29 tests, 27 PASS, 0 FAIL, 2 ERROR, 0 SKIP. Two Windows cleanup
errors exposed lazily iterated SQL results in the new Story reader when semantic
validation raised. The implementation now materialises query results before
validation, releasing cursor ownership deterministically. No sleep, retry,
suppression or existing resource-lifecycle change was used.

An expanded 35-test run had 34 PASS and 1 ERROR: the new multiple-Finding fixture
added evidence after recording its first Interpretation. The expected stale-input
guard rejected that snapshot. The fixture now explicitly reassesses after all
evidence is assembled; the guard was not weakened.
An intermediate 173-test compatibility run also passed before the final added
adversarial cases and snapshot validation. It is not substituted for final results.

Final focused plus v2.43-v2.46 compatibility: 188 tests, 188 PASS, 0 FAIL,
0 ERROR, 0 SKIP, 160.635 seconds. This includes 33 Story tests and three new
migration tests. Source/tests/migrations/scripts compilation passed.

Final authoritative local estate: 496 discovered/run, 487 PASS, 0 FAIL, 0 ERROR,
9 SKIP, 743.984 seconds on Windows 10 / Python 3.12.14. No policy errors,
expected failures or unexpected successes. The unchanged v2.42 runner applies
strict DeprecationWarning/ResourceWarning and delayed unraisable checks. Existing
Pydantic UserWarnings are not suppressed or recategorised. The nine skips are
the original explicitly live PostgreSQL tests, not local passes.

Live PostgreSQL qualification: **178 collected/run, 178 PASS, 0 FAIL, 0 ERROR,
0 SKIP**, suite 2165.458 seconds, overall 2171.954 seconds. PostgreSQL 18.6 on
aarch64 Linux, Neon AWS eu-west-2. Provider metadata independently verified project
tiny-meadow-46991842 and branch v2-41-qualification / br-royal-math-za046ex1 as ready,
non-primary, non-default and unprotected. Only the verified direct endpoint was
used. The production/default database was not connected to or modified. Credentials
were process-only, cleared afterward and never written to source or an env file.

The live suite includes 33 new Story checks, two new migration checks and the 143
inherited qualification checks, including the unchanged v2.41 gate. Some checks
are pure/static assertions: this is not a claim of 178 independent SQL behaviours.
Canonical persistence used real PostgreSQL; the owning legacy Signal fixture
intentionally remains SQLite, matching the frozen repository architecture.
Clean creation, all-28-table frozen upgrade/preservation, populated downgrade and
re-upgrade, scope/FKs, precision, interpretation class boundaries, evidence gaps,
longitudinal history, replay, audits and caller transactions passed. Final counters:
0 open connections, 0 checked-out connections, no unraisable errors. The disposable
branch finished at migration 0008. No code correction was needed during the live run.

Final review: 16 intended files, credential-pattern and whitespace scans clean,
git diff --check passed. Historical migrations and frozen semantic implementations
are untouched. The three prior migration-test edits are only head advancement.
All old estate inventory entries are identical. No test assertion was weakened.
The captured SQL fixture is intentional qualification source; temporary logs,
reports, environment and caches remain ignored/local-only.

No cross-platform v2.47 freeze is claimed; the unchanged Ubuntu/Windows x Python
3.12/3.13 CI matrix has not run for this uncommitted tree. No commit or push has
been performed.

## Non-goals and limitations

No Economic Bridges, financial impacts/counterfactuals, Opportunity redesign,
recommendations, action planning, benefit redesign, memory, LLM calls, narrative,
Story UI, diagnostic 57 or other v2.48+ behaviour is implemented. There is no
cross-Story causal chain. Positive mechanism resolution remains unavailable.
Independence is only as strong as retained lineage; undocumented copying is not
excluded. Source retention is an owning-store responsibility. Historical snapshots
are evidence at assessment, not automatic reassessment of later source changes.
Large-run search/storage performance has not been benchmarked.

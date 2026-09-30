# v2.49 — Economic Impact qualification

## Baseline and release boundary

Started from clean main/origin/main at
`91dbfee35292c2e7658fd1741a571b2069ce2eef`, the user-frozen v2.48 release.
The retained feasibility assessment and subsequent user decision are authoritative:
**CASH_TRAPPED is not an observed stock increase.** A defensible required-position
counterfactual is necessary. No positive production Impact category is qualified
by the current evidence. Zero qualified Impacts is an intentional valid outcome.

No commit/push or cross-platform freeze is claimed here. Existing legacy
economic/Opportunity/product consumers remain unchanged. The explicit new service
is an opt-in semantic slice, not a dual writer or automatic product cutover.

## Architecture and authority

`reasoning/impact/contracts.py` defines a candidate's stable Source reference,
its versioned Qualification, governed outcomes, qualified Impact payload, Decimal
amount/counterfactual and dimension-specific Aggregation. A Qualification contains
candidate identity plus immutable assessment revision; a candidate is never a
foundation ECONOMIC_IMPACT identity. Only positive qualification creates that
identity and its typed extension. An unqualified candidate cannot carry an Impact.

`ImpactService` accepts source identities, not caller-labelled Impact amounts.
Bridge identities resolve through the unchanged BridgeService and its current
CMC/BIQ/source checks. Candidate snapshots retain the complete Bridge document,
including exact measure, inputs, residual, partial coverage and limitations.
Reasoning identities resolve through FoundationService; their type or status alone
cannot qualify an amount. Unverified source authority produces HELD. Stale Bridge
evidence produces HELD after explicit reassessment. Missing/foreign endpoints and
unknown vocabulary are errors, not silently substituted evidence.

The source-reference FKs point directly to existing Bridge/foundation identities.
No Bridge is falsely represented as a reasoning_object_v243 lineage endpoint.
No frozen lineage resolver is relaxed. Synthetic sources are explicitly resolved
by a qualification fixture owner and copied as deterministic typed evidence into
the assessment; no production synthetic provider or workbook shortcut is installed.

Outcomes are QUALIFIED_IMPACT, INSUFFICIENT_EVIDENCE, NOT_APPLICABLE and HELD.
Each assessment preserves available evidence, missing evidence, counterfactual
requirements, blockers, known effect references and UNKNOWN_OVERLAP by default.
An explicit category request cannot promote evidence or fill any missing input.

## Contracts and positive qualification limits

`registry.py` contains eight explicit versioned IC-2.49.1 requirement contracts.
All have `production_qualified=False`; no generic amount-plus-label fallback exists.
The feasibility matrix documents why each current production category is refused
or deferred. Unresolved Interpretation/condition Story support is not upgraded.

The one positive mechanical contract is `SYNTHETIC_EXCESS_WC_1`. It requires:

- an explicitly SYNTHETIC fixture resolved by the injected trusted fixture owner;
- observed net trade working-capital stock and an exact operational requirement;
- identical named scope and as-of date, GBP, and explicit population coverage;
- typed counterfactual basis, rationale, evidence and assumptions;
- strictly positive observed minus required amount.

The supplied fixture states observed GBP 1200.00000000000000000001 and required
GBP 1000.00000000000000000000. The qualified synthetic excess is therefore
GBP 200.00000000000000000001. This is a counterfactual excess-stock assessment,
not a measured cash flow. Zero or negative excess yields NOT_APPLICABLE and never
a realised benefit. Partial coverage stays partial and is never extrapolated.

This fixture axiom is not a production benchmark, Golden Manufacturing evidence,
or proof that arbitrary uploaded assumptions are valid. There is no production
provider for operational requirements in this release. A later production contract
needs separately qualified source authority, comparability and counterfactuals.

Qualified records and totals retain SYNTHETIC domain, and requests to include them
in PRODUCTION totals fail closed. Synthetic foundation identities are also refused
as generic production reasoning-source candidates; the domain cannot be laundered
through the identity-only foundation reader. The foundation confidence/materiality rationale
also marks the evidence domain. No legacy consumer is routed to these identities.

## Amounts, uncertainty and lifecycle

Decimal values use the existing financial validator, deterministic JSON strings
and SQL Text convention. Binary floats, invalid vocabulary and inconsistent
amount/counterfactual arithmetic are rejected. Addition/subtraction precision is
derived from the input exponents and term count rather than the default Decimal
context, so long exact fractional amounts survive persistence and aggregation.

The implemented amount basis is COUNTERFACTUAL_EXCESS_STOCK. Its observed stock
is separately retained, together with the required position, as-of, scope,
coverage, formula and assumptions. No annualisation, counterfactual benchmark,
range or scenario is invented. Range-based and run-rate positive contracts remain
deferred until their evidence and calculation policies are separately qualified.

Confidence uses the independent v2.43 profile. Only synthetic arithmetic receives
HIGH quantification confidence; attribution, interpretation, data, Opportunity and
benefit-attribution confidence remain NOT_ASSESSED. Materiality retains magnitude
and cash amount with currency; unsupported percentages, urgency and controllability
are not populated. There is no universal confidence/materiality/priority score.

The lifecycle vocabulary reserves candidate, quantified, supported, monitoring,
superseded, invalidated and realised. The current writer emits quantified synthetic
Impacts only. `lifecycle()` projects historical supersession or invalidation after
an explicit changed assessment; it does not silently rewrite a retained snapshot,
promote benefit status or alter the frozen foundation's status validation.

## Effects, overlap and aggregation

The existing v2.43 EconomicEffect, EffectReference, EffectOverlap and foundation
audit tables are reused. No parallel effect/lineage store is introduced. Synthetic
effect identity derives from domain, client, underlying consequence key, metric,
scope, as-of and currency, not the describing analytical path. Two descriptions
of the same consequence therefore reference one effect. Different current
valuations of that effect block totals rather than selecting a preferred amount.

Foundation overlap records are declarations, not proof of independent economics.
An explicit synthetic relationship resolver must substantiate the exact retained
declaration before aggregation can use it. No production relationship-certification
adapter is enabled. Missing proof is UNKNOWN_OVERLAP, even for a declared
INDEPENDENT relationship.

Aggregation requires an explicit domain, category and compatible dimension:
PROFIT_PNL, CASH, CAPITAL_RISK, FUTURE_EXPOSURE, POTENTIAL_UPSIDE or REALISED_BENEFIT.
It cannot provide a universal total. Exact currency, amount basis, date, scope and
coverage must agree. Current evidence is revalidated before values enter totals.

- Unqualified candidates are excluded; an empty qualified set returns EMPTY with
  no amount, not an assertion that total economic impact is zero.
- Identical valuations of one effect count once, including duplicate input IDs.
- Proven SAME_EFFECT aliases count once. Contradictory equivalence/independence
  declarations block the entire total.
- PARTIAL_OVERLAP, PARENT_CHILD and UNKNOWN_OVERLAP block naive addition.
- Only substantiated INDEPENDENT compatible effects can be added.
- Historical revisions, stale evidence and foreign scopes cannot enter totals.

No attempt is made to numerically allocate partial overlap. Aggregation is a
conservative query over a requested set, not a portfolio optimisation engine.
Existing foundation overlap declarations remain immutable per pair. Withdrawing
their qualification proof makes aggregation unknown/blocked; this release does
not introduce an overlap-amendment workflow. A future change of declared relation
requires a separately governed evolution of the existing store, never a silent
overwrite. Candidate/Impact assessment revision history is implemented separately.

## Golden Manufacturing

The principal qualification case creates exactly three production candidates:
Working Capital → CASH_TRAPPED, Revenue → VALUE_CREATION_POTENTIAL, and exact
Contribution 0 → OBSERVED_LOSS. All three are INSUFFICIENT_EVIDENCE. It creates
**zero qualified Impacts** and contributes no amount to any Impact total.

The GBP 700,000 net trade-WC increase remains the existing Bridge movement. It is
neither CASH_TRAPPED nor profit loss. The GBP 2,350,000 closing balance is not
an alternative automatic Impact. Required-position/excess evidence is absent.
Revenue growth remains revenue growth. Revenue residual -225,000 and C0 residual
-88,250 remain economically unclassified. Partial detail and exact Contribution 0
semantics survive candidate serialization. Profit-to-Cash and Cost-to-Output remain
refused and cannot supply persisted Bridge endpoints.

Reference-scenario counts (each test uses an isolated disposable database):

| Scenario | Candidates | Qualified Impacts | Insufficient/held |
|---|---:|---:|---:|
| Golden Manufacturing three-family assessment | 3 | 0 | 3 insufficient |
| Synthetic known operational-requirement positive fixture | 1 | 1 | 0 |

Other adversarial tests intentionally create independent variants, aliases and
revisions. They are not accumulated into a fictitious business-wide candidate or
Impact count. Only CASH_TRAPPED is positively demonstrated, and only synthetically.

## Persistence and migration

Forward migration `0011_economic_impact` follows unchanged 0010 and adds:

1. `canonical_impact_qualification`: append-only candidate revisions, source FKs,
   existing client/run references and typed assessment document.
2. `canonical_impact`: typed qualified Impact extension referencing existing
   reasoning identity, qualification revision and EconomicEffect with scoped FKs.
3. `canonical_impact_qualification_audit`: candidate assessment history with actor,
   timestamp, prior/new snapshot and rationale. Candidate audits are separate only
   because candidates are not canonical ECONOMIC_IMPACT objects. Actual Impact and
   effect audit uses the existing foundation mechanism.

Unchanged evidence replays without duplicating revisions, effects, Impacts or
audits. Changed evidence requires the explicit current revision. Database
uniqueness protects racing revisions; source/client FKs protect missing/foreign
endpoints. Run/client agreement remains an application-boundary check, consistent
with the existing schema. Raw SQL is not a semantic writer.

The caller owns transaction and resource lifetime. A nested transaction protects
one assessment write; SQLite explicitly opens the underlying transaction before
the first savepoint so releasing it cannot accidentally commit caller-owned work.
No sleep, retry, suppression or frozen resource-lifecycle code is changed.

The frozen 0010 fixture was captured before registering new metadata. Migration
qualification seeds every column in all 36 old application tables and verifies
preservation through upgrade, populated downgrade and re-upgrade. Downgrade removes
the three typed Impact/qualification tables and their candidate audits; existing
foundation identities/effects/references/audits remain, like previous semantic
slices. Re-upgrade does not reconstruct removed typed history. Restore that history
before replaying previously qualified identities; missing history fails closed.

## Qualification record

Initial focused run: 37 tests, 14 PASS, 0 FAIL, 23 ERROR, 0 SKIP. All errors shared
one new implementation defect: a date object was passed to the deterministic JSON
identity helper. ISO date serialization corrected it. The unchanged assertions
then passed: 37/37. Expanded adversarial coverage passed 42/42, no failures/errors/
skips, with DeprecationWarning and ResourceWarning treated as errors.

Initial authoritative local full estate: **625 discovered/run, 616 PASS, 0 FAIL, 0 ERROR,
9 SKIP**, 963.891 seconds on Windows 10 / Python 3.12.14. All 583 pre-existing tests
remain included. The nine skips are the explicitly live PostgreSQL tests, never
counted as passes. There are no policy errors, expected failures or unexpected
successes. The unchanged v2.42 runner checks deprecation/resource warnings and
unraisable resource errors. Compilation of source, tests, scripts and migrations
passed.

Final review identified an additional origin boundary: although a synthetic
foundation Impact could not qualify a production amount, it could be submitted
as an unqualified production candidate through the generic reasoning-source route.
The new service now rejects that route explicitly. One adversarial test was added;
no existing assertion changed. The resulting focused suite passed **43/43**, with
0 failures/errors/skips, in 46.405 seconds. Final authoritative full estate after that guard: **626 discovered/run, 617 PASS,
0 FAIL, 0 ERROR, 9 legitimate live SKIP**, 928.125 seconds, Windows 10 / Python
3.12.14. No policy errors, expected failures or unexpected successes. The 43 new
tests and all 583 frozen tests remain present; no existing assertion was weakened.
The affected live result is recorded below.

The live runner's default remains the complete new Impact plus inherited Bridge,
foundation and v2.41 scope. An explicit `--impact-only` mode supports the affected
Impact/migration/static/v2.41 rerun after this correction; reports name that scope.
Neither mode retries failed assertions or converts failures to skips.

The broader live run, loaded before the final origin guard, passed **108/108**:
0 FAIL, 0 ERROR, 0 SKIP, 1315.844 seconds, PostgreSQL 18.6 on aarch64 Linux.
It included new Impact checks, inherited Bridge/foundation checks and the unchanged
v2.41 live gate. Cleanup: 0 open, 0 checked-out connections, no unraisable errors.
The independently verified target was project tiny-meadow-46991842, branch
v2-41-qualification / br-royal-math-za046ex1, non-primary/non-default/unprotected.
Primary/default was never a connection target. No Neon configuration was changed.
Final affected live qualification passed **56/56**: 0 FAIL, 0 ERROR, 0 SKIP,
282.703 seconds, same PostgreSQL 18.6 disposable target. This explicitly covered
all 40 final Impact/Golden tests, two live Impact migration checks, five static
PostgreSQL checks and all nine unchanged v2.41 live checks. Final cleanup again
recorded 0 open connections, 0 checked-out connections and no unraisable errors.
The source-independence migration check is static and passed locally. Credentials
were process-only and removed after execution; no connection string is retained
in source or reports. No test assertion was retried until passing. The two live
results describe their different scopes; this is not a claim of a final 109-check
uninterrupted run after the small origin-boundary correction.

## File inventory

| File | Purpose |
|---|---|
| `profit_doctor/reasoning/impact/__init__.py` | Additive opt-in package. |
| `profit_doctor/reasoning/impact/contracts.py` | Typed qualification, amount, counterfactual, lifecycle and aggregation contracts. |
| `profit_doctor/reasoning/impact/registry.py` | Eight explicit category requirements; no positive production policy. |
| `profit_doctor/reasoning/impact/service.py` | Authoritative source resolution, qualification, revisions, effect reuse and safe totals. |
| `profit_doctor/persistence/impact_schema.py` | Three additive typed persistence tables and scoped FKs. |
| `profit_doctor/persistence/__init__.py` | Register those tables with existing Base. |
| `alembic/versions/0011_economic_impact.py` | Frozen forward DDL and typed-state-only downgrade. |
| `tests/fixtures/v248_schema.sql` | Preserved independent migration-0010 schema. |
| `tests/fixtures/impact_v249/excess_wc.json` | Explicit synthetic operational requirement; exact Decimal evidence. |
| `tests/fixtures/impact_v249/README.md` | Fixture provenance and synthetic-only authority. |
| `tests/test_economic_impact_v249.py` | 40 qualification, adversarial, scope, persistence and Golden tests. |
| `tests/test_economic_impact_migrations_v249.py` | Three migration/schema/preservation tests. |
| `tests/test_canonical_migrations_v244.py` | Expected head only: 0010 to 0011. |
| `tests/test_graph_migrations_v245.py` | Expected head only: 0010 to 0011. |
| `tests/test_hypothesis_migrations_v246.py` | Expected head only: 0010 to 0011. |
| `tests/test_story_migrations_v247.py` | Expected head only: 0010 to 0011. |
| `tests/test_measurement_context_migrations_v248.py` | Expected head only: 0010 to 0011. |
| `tests/test_economic_bridge_migrations_v248b.py` | Expected head only: 0010 to 0011. |
| `qualification/test_estate_v242.json` | Register the two new modules; prior entries unchanged. |
| `scripts/qualify_economic_impact_postgresql_v249.py` | Fail-fast direct disposable-branch qualification and cleanup accounting. |
| `docs/V2_49_IMPACT_FEASIBILITY.md` | Retained feasibility with the approved strict boundary. |
| `docs/V2_49_ECONOMIC_IMPACT.md` | Architecture, qualification, file inventory and limitations. |

Local reports/logs, capture scripts, virtual environment and caches are excluded.

## Compatibility, caveats and next release

Existing changes are limited to schema registration, estate registration and six
expected migration-head literals. Historical migrations, all 56 diagnostics,
Signals, v2.43–v2.48 semantic writers, legacy economic/Opportunity, management,
benefit, longitudinal, product/API, v2.41 gate and v2.42 CI/lifecycle remain intact.

No automatic Story expansion, Hypothesis reassessment, recoverability,
addressability, implementation probability, Opportunity value, recommendation,
AI narrative or v2.50+ functionality is introduced.

v2.50 can use the explicit qualification boundary to exclude every candidate and
unqualified assessment. It currently has **zero qualified production Impacts to
consume**. Synthetic positives must remain excluded. New positive categories,
production evidence providers, ranges and run-rate contracts require additional
qualified typed variants; this release does not claim those behaviours already
exist. No effect-store redesign is indicated, but production Opportunity valuation
cannot be demonstrated from synthetic-only positive qualification.

## Final review and assessment

All 22 intended files were reviewed. Existing diffs comprise schema registration,
two inventory entries and six expected-head replacements. Historical migration
files and frozen semantic/CI/resource-lifecycle paths have no diff. Implementation,
tests and fixtures match the hashes of the final qualified tree; only documentation
was updated afterward. Tracked diff and separate new-file whitespace checks pass.
Credential-pattern review is clean. Reports/logs and environment/cache files remain
ignored/local-only. Nothing is staged, committed or pushed.

The controlled candidate/qualification architecture is ready for architectural
review. Current production evidence yields zero positive qualified categories;
only synthetic CASH_TRAPPED mechanics have positive qualification. Future real
counterfactual sources, other positive category variants, range/run-rate contracts
and overlap amendments require separate qualification. No blocking effect-store
redesign is identified, but v2.50 must not treat synthetic evidence or candidates
as production Impacts. Cross-platform CI for this uncommitted tree has not run;
no release freeze is claimed.

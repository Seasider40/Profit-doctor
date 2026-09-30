# Profit Doctor v2.50 - Opportunity Engine

## Baseline and release boundary

Started from clean `main` / `origin/main` at
`132d3ea8be1bf3d79179a06884e104c4c6def246`, the user-confirmed frozen v2.49
production receivables baseline. The initial feasibility stop and subsequent
approved resolution are recorded in V2_50_OPPORTUNITY_FEASIBILITY.md.

This is an opt-in canonical service. Existing product, economic, Opportunity,
management and benefit consumers are unchanged. No automatic consumer cutover,
Impact promotion, priority, decision, recommendation, Action Plan, benefit
realisation, memory, AI narrative or diagnostic 57 has been implemented.
No Golden Manufacturing v2.50 blind workbook was requested, inspected or used.
No commit or push is part of this implementation task.

Economic Impact, prospective Opportunity, Action and realised Benefit remain
different concepts. Qualified Impact may legitimately have no Opportunity.

## Feasibility and the one implemented contract

| Impact category | Current feasibility | Boundary |
|---|---|---|
| OBSERVED_LOSS | INSUFFICIENT_EVIDENCE | No qualified production source and prospective capture contract. |
| RUN_RATE_LEAKAGE | INSUFFICIENT_EVIDENCE | No governed production source, persistence/counterfactual and capture contract. |
| CASH_TRAPPED | QUALIFIED_FOR_OPPORTUNITY_CONTRACT, narrowly | Only OVERDUE_RECEIVABLES_1 plus qualified collection evidence. Other cash sources remain unsupported. |
| AVOIDABLE_COST | INSUFFICIENT_EVIDENCE | No qualified production source and alternative cost/capture evidence. |
| CAPITAL_AT_RISK | INSUFFICIENT_EVIDENCE | Exposure is not prospective cash capture; no qualified mitigation contract. |
| FUTURE_EXPOSURE | INSUFFICIENT_EVIDENCE | No qualified scenario and incremental mitigation contract. |
| VALUE_CREATION_POTENTIAL | INSUFFICIENT_EVIDENCE | No qualified production upside/capture source. |
| REALISED_BENEFIT | NOT_APPLICABLE | Already-realised value cannot be reused as prospective capture. |

`MATCHED_COLLECTION_OUTCOMES_1` implements
`CASH_TRAPPED -> RECEIVABLES_COLLECTION_ACCELERATION`, GBP / CASH only.
There is no generic positive fallback. Impact Candidates, other reasoning layers,
the old synthetic Impact contract and stale Impacts cannot enter this writer.

## Domain and persistence boundaries

`OpportunityService` takes the existing owning `ImpactService` with a receivables
provider. It resolves a current qualified ReceivablesImpact and retains its full
qualification document, source candidate/revision, client/run, scope, origin,
amount and EconomicEffect. Candidate creation and assessment are separate calls.
The assessment date must equal the Impact snapshot date in this initial contract.

Candidates use deterministic identity including source Impact, date, horizon and
contract version. They reuse foundation `OPPORTUNITY_CANDIDATE` identities.
Positive assessment revisions create `VALIDATED_OPPORTUNITY` identities and
effect references; neither a candidate nor a valid source Impact implies value.
Foundation lineage points to the source Impact, whose retained ancestry remains
available. Typed assessment/evidence documents preserve invoice and historical
case source references, constraints, comparability assumptions and gaps/reasons.

`qualify` supports QUALIFIED, PARTIALLY_QUALIFIED, UNRESOLVED, NOT_ADDRESSABLE
and INSUFFICIENT_EVIDENCE. REJECTED is reserved vocabulary, not an automatically
generated rejection mechanism. Replay is idempotent. Changed evidence requires
an explicit predecessor revision and appends history. Historical reads preserve
old evidence; current reads and aggregation revalidate the current Impact and
retained evidence. Superseded/invalidated assessments cannot enter totals.

Canonical service writes use caller-owned SQLAlchemy transactions and nested
savepoints, including the established SQLite explicit-BEGIN safeguard. They do
not commit or close the caller session. Retained-file/legacy dataset ingestion
owns its separate existing ingestion transaction, as the v2.49 provider does;
this is not a distributed transaction. A canonical rollback may leave a retained
dataset registered, but leaves no canonical Opportunity rows from that operation.

## Collection evidence model and authority

The generic provider ingests one normalized CSV `collection` cell containing a
typed `CE-2.50.1` document. It registers and retains an immutable source file via
the existing ingestion/dataset-version machinery. Reads verify completion,
immutability, file hash, scope and exact document correspondence. This is a
normalized evidence boundary, not a new workbook-specific parser.

The document contains client/run/Impact identity, assessment date, horizon,
REAL_SOURCE or BLIND_QUALIFICATION origin, source version, dataset version,
COMPLETE/PARTIAL coverage and invoice reviews. Each review retains:

- invoice/customer identity and dated addressability authority;
- strategic/commercial constraints and optional management-approved flexibility;
- contact, acknowledgement and promise history with evidence dates/authority;
- explicit initiative state, review completeness, initiative identity/start date;
- complete cohort manifest, eligible pair count, exclusions and comparability basis;
- paired historical cases and optional central-estimate method.

Historical cases retain customer/invoice/case identity, GBP exposure, overdue
age, contractual terms, status, intervention, observation dates, received cash,
source authority and optional promise-kept / invoice / settlement / days-to-pay
history. Days-to-pay requires consistent invoice and settlement dates.
Contact, acknowledgement, promises and payment-history context never become
automatic recovery multipliers.

Authority is SOURCE_RECORD, MANAGEMENT_ASSERTION or HUMAN_FD_JUDGEMENT.
Management evidence may establish authority, a constraint or an existing
initiative. Empirical receipts, matching and cohort manifests must be source
records. An opinion such as "recover 90%" cannot set capture; extra percentage
fields are rejected. Authority labels are producer attestations, not independent
authentication of real-world truth. Trusted ingestion and source verification
remain operational prerequisites, as with existing evidence providers.

## Addressability and incrementality

Review states are ORDINARY_COLLECTION, COMMERCIAL_INTERVENTION,
STRATEGIC_CONSTRAINT and UNKNOWN. Result portions are ADDRESSABLE,
EXCLUDED_CONSTRAINT, EXCLUDED_PRIOR_INITIATIVE or UNRESOLVED.
The implementation qualifies whole invoices, not arbitrary fractional allocations.

Positive addressability requires current dated authority plus an explicit,
complete current review of NO_QUALIFYING_PRIOR_INITIATIVE_EVIDENCED. Missing
initiative review never means no initiative. ALREADY_UNDERWAY with evidenced
identity and commencement before assessment excludes newly claimed value.
UNKNOWN remains unresolved. A supported strategic constraint excludes the
portion without invalidating the underlying Impact.

Addressable + excluded + unresolved exactly equals the qualified source Impact
population. `capture_unresolved` is an explicit **subset of addressable**, not a
fourth additive partition: management influence may be established even when
capture cannot be estimated. Partial evidence never extrapolates to omitted
invoices. A COMPLETE review omitting eligible invoices is rejected.

## Empirical capture methodology

Current population: qualifying overdue invoices already admitted by the frozen
Impact contract. For each addressable invoice, historical evidence must supply
at least **three distinct matched pairs** from a complete inception cohort.
Three is a conservative contract eligibility floor, not a statistical confidence
claim or a proof of representativeness.

Each pair compares the relevant collection/commercial intervention with
BUSINESS_AS_USUAL. Both cases must match the current customer, GBP currency,
**exact outstanding exposure**, terms and ageing band (1-30, 31-60, 61-90,
over 90 days). The pair uses the same historical start/end dates, with a completed
window of exactly the candidate's horizon. The outcome is cash received within
that window, bounded by exposure. No scaling from a differently sized invoice,
unrelated customer or horizon is allowed.

The source-record manifest must identify the full inception denominator;
eligible pair count must equal supplied pairs. Selected successes, incomplete
cohorts, omitted/excluded cohort members, duplicated historical invoice identities,
the current invoice used as its own history, missing terms, future/unclosed
observations or incomparable cases fail closed. No outlier trimming is performed.

For each pair, incremental observed cash is treated receipts minus comparison
receipts. If any comparison outperforms its treatment, capture for that invoice
is unresolved; the negative outcome is not discarded to manufacture a positive
range. All-zero differences create no positive Opportunity.

Low/high are the minimum/maximum observed differences. They are an empirical
scenario envelope, **not a prediction interval, guarantee or causal estimate**.
Matching does not remove unobserved confounding. Within one qualified Impact,
supported disjoint invoice portions contribute their exact bounds; excluded and
unresolved portions contribute no claimed value.

Central is absent by default. If EMPIRICAL_PAIR_MEAN is explicitly selected,
the equal-weight mean of the paired differences is permitted only when exactly
representable as Decimal. A non-terminating mean remains absent; it is not rounded
or replaced by the midpoint. A combined central requires every contributing
portion to have one. The range always remains present independently of central.

Horizon is an explicit positive day count, not hard-coded to 90 days. Historical
windows must match it exactly; current evidence must name the same horizon.
No annualisation or substitution between 30-day, 90-day and 12-month evidence.
Financial serialization reuses strict Decimal strings and deterministic typed
JSON; calculations expand Decimal precision and do not use binary floats.

All ConfidenceProfile dimensions remain NOT_ASSESSED. Method/origin rationale
and limitations are retained; empirical receipts do not establish calibrated
opportunity or benefit-attribution confidence. There is no universal score,
priority or new materiality calculation.

## EconomicEffect and aggregation

Candidates and qualified revisions reference the source EconomicEffect. Current
positive portions only may enter aggregation. Same-effect identical valuations
deduplicate; conflicting valuations block. Scope, horizon, assessment date,
currency, coverage and evidence origin must be compatible. BLIND_QUALIFICATION
cannot enter the default REAL_SOURCE total. The synthetic v2.49 Impact contract
is rejected before candidate creation.

This first contract does not qualify independence between distinct effects.
Their aggregate therefore returns NOT_SAFELY_AGGREGATABLE, including declared
INDEPENDENT relationships that lack a qualified proof provider. Foundation
SAME_EFFECT/PARTIAL_OVERLAP/PARENT_CHILD/INDEPENDENT/UNKNOWN_OVERLAP vocabulary
is unchanged; none of these declarations is treated as permission to add unsafe
value. Only identity-based same-effect deduplication is positively supported now.
That conservative limitation is intentional and must remain visible to consumers.

Only CASH is supported; profit, capital/risk, future upside and realised benefit
cannot be summed into a universal total. Opportunity remains prospective cash
capture, not realised cash or Profit Doctor-attributed benefit.

## Migration and data preservation

`0013_opportunity` follows `0012_receivables_snapshot` and adds five tables:

1. canonical_collection_evidence;
2. canonical_opportunity_candidate;
3. canonical_opportunity_assessment;
4. canonical_opportunity;
5. canonical_opportunity_audit.

Composite client FKs protect source Impact/foundation/effect/assessment ownership;
run existence is a database FK, with run/client consistency and typed semantics
validated by the owning service. Revision/identity uniqueness is database-enforced.
Documents preserve exact typed values in the existing text-JSON convention.
The audit contains prior/new documents, actor and timestamp; foundation creation
also retains the existing audit/lineage semantics.

The forward migration contains frozen DDL, not imports of mutable application
models. Historical migrations remain unchanged. The preserved v2.49 schema
fixture contains all 43 prior application tables independently of current metadata.
Clean creation, frozen upgrade, every-table legacy data preservation, populated
downgrade and re-upgrade are qualified.

Downgrade removes the five v2.50 extension tables and their collection documents,
assessments and extension audits. It preserves legacy/v2.49 records, retained
source files and foundation identities/effect references/audits. Re-upgrade creates
empty v2.50 extension tables; it does not reconstruct removed Opportunity history.

## Qualification

Tests use synthetic architecture evidence through the production receivables boundary with explicit
BLIND_QUALIFICATION origin, not the hidden v2.50 workbook.

Final-source compilation passed. The focused strict-warning suite currently
contains 43 Opportunity tests and 3 migration tests: **46 PASS, 0 FAIL, 0 ERROR,
0 SKIP** (51.615 seconds).

The final authoritative estate completed on Windows / Python 3.12.14:
**708 discovered, 708 run, 699 PASS, 0 FAIL, 0 ERROR, 9 SKIP** in 1708.250
seconds. The nine skips are the established live PostgreSQL cases in the local
gate, not passes. No expected failures, unexpected successes or warning/resource
policy errors were recorded. Source/tests/scripts/migrations compile successfully.
Both final gates used strict DeprecationWarning and ResourceWarning handling;
the existing full-estate unraisable-resource policy remains unchanged.

The final uninterrupted live gate did **not** complete: **189 discovered,
121 run, 120 PASS, 0 FAIL, 1 ERROR, 0 SKIP; 68 not run**. All 43 new Opportunity
checks and both new live migration checks passed before the error. PostgreSQL
reported version **18.6**, aarch64, on the verified non-primary, non-default,
unprotected `v2-41-qualification` branch (`br-royal-math-za046ex1`, project
`tiny-meadow-46991842`). Primary/default was not targeted or modified.

The test runner stopped after 1274.830 seconds. Setup of inherited
`LiveGoldenImpact.test_residuals_partial_coverage_exact_c0_remain_source_evidence`
raised `psycopg.OperationalError: consuming input failed: server closed the
connection unexpectedly`. The statement was a SELECT of
`canonical_measurement_context.context_id` during existing measurement-context
capture. This is a connection-loss observation, not proof of its root cause.
Windows was held awake by the runner. No retry or code remediation was attempted.
The complete report took 1275.687 seconds and recorded **0 open connections,
0 checked-out connections and no unraisable resource errors**.

The remaining inherited Bridge/foundation/v2.41 live checks were not reached.
Their frozen implementations remain unchanged, but this run cannot claim that
the complete current-schema live gate passed. Live qualification is an explicit
remaining release blocker; neither focused positives nor local regression may
replace it. The independent local regression was allowed to finish.

During development, an initial 36-test run had 35 passes and one test-harness
error: the source-tamper test attempted to edit its deliberately read-only retained
fixture. The test now explicitly makes that disposable fixture writable before
tampering; source immutability checks remain intact. Subsequent focused runs
passed, including an intermediate 115-test Opportunity/receivables/Impact suite.

Final review also found that a terminating fraction's Decimal expansion could
exceed the optional central calculation's precision estimate. The estimate now
uses denominator bit length as a safe bound, with a 70-significant-digit
regression. No rounding policy or frozen code was changed. Preliminary broad
runs loaded the earlier source and were explicitly stopped, not counted as
completed qualifications. Final complete suites were restarted on the corrected
source, without retries or assertion changes.

The focused suite covers source gates, mixed populations, constraints, initiative
review, comparable/incomparable cohorts, insufficient samples, contradictory
outcomes, central estimates, precision, horizons, management authority, replay,
history, stale sources, retained-file tamper, client FKs, effect identity, audit,
caller rollback and populated downgrade. Migration tests cover clean/current/frozen
schema and exact prior-table preservation. The live runner adds these to the
established receivables/Impact/Bridge/foundation/v2.41 checks, using fail-fast,
no retries and the dedicated disposable branch while holding Windows awake.

## Known limits and next review

- Only the narrow GBP receivables contract is positive. Exact-exposure,
  same-customer, same-horizon complete historical cohorts may be unavailable in
  real data; UNRESOLVED is a correct result, not permission to relax comparability.
- The empirical envelope does not prove causation or future collection success.
- No partial-invoice allocations, cross-currency conversion, annualisation,
  calibrated confidence or independent-effect aggregate proof is implemented.
- Evidence authority/completeness depends on governed source attestations. The
  software checks their structure, retention and consistency, not external truth.
- New snapshot dates require new current qualified Impacts/candidates. Same-date
  changed collection evidence creates assessment revisions without overwriting.
- Blind Opportunity qualification and subsequent cross-platform CI remain future
  gates. Local synthetic/live qualification cannot substitute for either.

The canonical output is suitable as an opt-in, typed input to future priority
work without conflating capture with Impact or Benefit. Such work is not begun.
Architectural review must accept the narrow empirical/comparability and
aggregation limits before the hidden blind qualification phase.

## Changed-file inventory

| File | Purpose |
|---|---|
| profit_doctor/reasoning/opportunity/__init__.py | Opt-in package boundary. |
| profit_doctor/reasoning/opportunity/contracts.py | Typed collection evidence, candidates, portions and assessment validation. |
| profit_doctor/reasoning/opportunity/engine.py | Governed addressability, incrementality and empirical capture. |
| profit_doctor/reasoning/opportunity/service.py | Source ownership, retention, canonical persistence, replay/history and safe aggregation. |
| profit_doctor/persistence/opportunity_schema.py | Five additive canonical tables. |
| profit_doctor/persistence/__init__.py | Register new metadata for migration/schema qualification. |
| alembic/versions/0013_opportunity.py | Independent forward DDL and downgrade. |
| tests/fixtures/v249_receivables_schema.sql | Preserved pre-Opportunity schema for upgrade/preservation tests. |
| tests/test_opportunity_v250.py | Synthetic semantic, service and persistence adversarial coverage. |
| tests/test_opportunity_migrations_v250.py | Clean/frozen migration and preservation coverage. |
| scripts/qualify_opportunity_postgresql_v250.py | Explicit disposable, fail-fast live qualification. |
| qualification/test_estate_v242.json | Add the two new test modules to authoritative discovery. |
| tests/test_canonical_migrations_v244.py | Expected current head only: 0012 to 0013. |
| tests/test_graph_migrations_v245.py | Expected current head only: 0012 to 0013. |
| tests/test_hypothesis_migrations_v246.py | Expected current head only: 0012 to 0013. |
| tests/test_story_migrations_v247.py | Expected current head only: 0012 to 0013. |
| tests/test_measurement_context_migrations_v248.py | Expected current head only: 0012 to 0013. |
| tests/test_economic_bridge_migrations_v248b.py | Expected current head only: 0012 to 0013. |
| tests/test_economic_impact_migrations_v249.py | Expected current head only: 0012 to 0013. |
| tests/test_receivables_migrations_v249.py | Expected current head only: 0012 to 0013. |
| docs/V2_50_OPPORTUNITY_FEASIBILITY.md | Original feasibility stop plus approved resolution. |
| docs/V2_50_OPPORTUNITY_ENGINE.md | Architecture, methodology, limits and qualification evidence. |

No existing assertion is weakened. The eight expected-head edits retain every
schema/FK/data-preservation assertion. No historical migration, frozen diagnostic,
reasoning writer, v2.41 gate or v2.42 workflow/resource owner is changed. Local
logs, reports and hash snapshots remain ignored under `.venv`; they are not
source artifacts. No credentials or connection strings belong in this diff.

Final source/test/fixture hashes were unchanged throughout the final gates.
`git diff --check` passed; all 22 intended modified/new files were reviewed,
including a credential/connection-string and whitespace scan. Nothing is staged,
committed or pushed. Historical migrations and frozen production semantics remain
unchanged. The complete file inventory above is the intended review scope.

### Subsequent approved qualification and ingestion remediation

The user subsequently confirmed that the host slept during the interrupted live
run. The unchanged awake-host rerun completed 189 discovered/run, 189 PASS,
0 FAIL, 0 ERROR and 0 SKIP against PostgreSQL 18.6 on the dedicated disposable
qualification branch. Final open and checked-out connection counts were zero,
with no unraisable resource errors. No implementation change was required for
that live result. The earlier interrupted-run record above is historical.

The subsequent blind workbook exposed an ingestion-layout boundary, incomplete
initiative evidence and incompatible scaled-cohort methodology. The approved
remediation adds only a registered collection workbook adapter and qualification
data specification. `MATCHED_COLLECTION_OUTCOMES_1` remains unchanged.
See [Collection data qualification](V2_50_COLLECTION_DATA_QUALIFICATION.md) for
the source-preserving adapter, exact data requirements and honest unresolved
blind assessment. A positive blind Opportunity is not claimed. Four-job
cross-platform CI and formal v2.50 freeze are not claimed.

# v2.48 Bridge Input Qualification: implementation checkpoint

This is part of Economic Bridges, not a separate release. The user approved the
comparability boundary after the feasibility stop and explicitly required a second
stop if no family becomes safely calculable. That condition now applies. There is
no Bridge calculator, new persisted Bridge identity or claim of completed v2.48.

## Baseline and architecture

Baseline remains main at fec375f9701af9052748e58907431a1da3f83f8e, verified clean
before the original feasibility document. Origin was current and all four frozen
v2.47 CI jobs passed. No commit or push has occurred.

`reasoning/bridge/qualification.py` adds BIQ-2.48.1 contracts using the existing
Pydantic Contract, Decimal-safe Measurement, Identifier and LineageReference.
No second serialization library, source identity store or provenance graph exists.

- BridgeFamily names all five candidates; unknown family names are rejected.
- Outcome: QUALIFIED, PARTIALLY_QUALIFIED, INSUFFICIENT_EVIDENCE, INCOMPARABLE, INVALID.
- ReportingBasis: MONTHLY, QUARTERLY, ANNUAL, YTD, ROLLING, POINT_IN_TIME,
  OTHER_GOVERNED, UNKNOWN.
- Coverage: COMPLETE, PARTIAL, UNKNOWN.
- VersionRelationship: COMPATIBLE, RESTATED_COMPATIBLE, SUPERSEDED, INCOMPATIBLE,
  UNKNOWN. Compatible/restated labels need explicit basis and evidence references.
- Period retains inclusive bounds, reporting convention and FLOW/STOCK/RATE/UNKNOWN;
  duration is derived from bounds, not independently supplied.
- Endpoint retains Fact/client/run identity, exact typed measurement, entity and
  segment scope, economic basis, period, coverage/evidence, source versions,
  lineage/completeness, source snapshot digest, eligibility and limitations.
- RetainedSource exposes available dataset/primitive metadata as context, including
  dates, version number, row count, method and status. These are not silently
  assigned to a measurement's opening or closing interval.
- ComparisonInput binds endpoints and version/restatement evidence to a family.
- Qualification retains the full input description, gaps, outcome and deterministic
  content-based assessment identity. Deserialization recomputes outcome/gaps/ID;
  a changed label cannot convert a refusal to QUALIFIED.

The pure evaluator checks descriptors; it does not certify that caller assertions
are true. Positive policy tests use explicitly synthetic descriptors. Application
qualification goes through BridgeInputResolver with Fact IDs, not caller-provided
coverage, period or restatement overrides. No financial writer accepts a raw
Qualification object as permission to create a Bridge.

## Policy and read-only resolver

Only revenue/CURRENCY/FLOW and Contribution 0 CURRENCY/FLOW or margin
PERCENTAGE/RATE have endpoint allowlists. These allowlists are not qualified
Bridge calculation contracts. Cross-metric profit-to-cash, composite working
capital and cost/output contracts remain unavailable, with explicit gaps.

Client, entity, segment, metric, currency/unit, economic basis, reporting basis
and nature must agree. Chronology must be ordered/disjoint. The initial pure
policy accepts only complete calendar monthly/quarterly/annual intervals of equal
duration. It does not normalise unequal months or leap-year windows. Other basis
vocabulary is representable but remains unqualified pending a specific policy.
Unknown required semantics block; partial coverage/limitations remain visible.
No universal score, confidence uplift or financial reconciliation is calculated.

The resolver reuses canonical readers and EvidenceGraph's source freshness,
scope, eligibility and ancestry checks. It hashes the actual retained lineage
rows as well as the canonical Fact and ancestry. Dataset and primitive metadata
are recovered where referenced; retained canonical record references are read
when present. It does not discover or manufacture unretained row-level ancestry.
Source content paths and prose are not interpreted as evidence semantics.

Diagnostic FULL eligibility and completed ingestion do not prove full-period or
full-business coverage. Existing mapping_coverage/economic_coverage measure
coverage within captured data; their schema does not certify that all business
transactions or the complete reporting period were supplied. The resolver does
not turn those percentages into completeness certificates.

Identical dataset version IDs do not certify restatement comparability. Existing
version numbering records versions, not an explicit policy governing comparable
restated opening/closing measures. The resolver therefore returns UNKNOWN version
relationship, unknown complete coverage and unqualified separate slot periods.
It never splits a combined Signal interval, uses a dataset envelope as a slot
period, or treats source ancestry as accounting-policy equivalence.

The legacy management/restatement.py subsystem already has source_revision and
restatement_event records. They bind a logical_source_key and content hash to a
run/effective period, not canonical Fact slots or dataset_version identities.
Matching a source name or run would not establish that binding. This subsystem
remains unchanged and is a potential future reuse point; the gap is qualified
binding/compatibility evidence, not an assertion that the repository has no
restatement functionality.

Both SQL stores are caller-owned. Source queries are SELECT-only; canonical reads
run with autoflush disabled. There is no commit, rollback, close, audit append,
source update or canonical rewrite. Tests use source query_only and canonical SQL
instrumentation, not just an absence-of-dirty-objects assertion.

## Replay, persistence and remaining acceptance work

Unchanged input has identical serialization and assessment ID. Changed retained
metadata or evidence changes the digest/ID; previously serialized assessments
remain readable. This is deterministic immutable assessment output, not a durable
revision ledger or operational audit mechanism. Decimal scale is retained; amounts
are never calculated or converted to float.

No migration is needed for this read-only layer. Head remains 0008; historical
migrations, schema and canonical writers are untouched. No new ObjectType is
introduced while no Bridge family can be created. Persisted Bridge history,
component alignment, component/effect integration, calculation tolerance,
reconciliation and residual behaviour remain unimplemented.

In particular, the requested positive valid-endpoints/missing-components residual
Bridge test is NOT claimed as passed. There is no qualified application input
path or Bridge writer to test. The policy tests prove valid hypothetical endpoint
descriptors can qualify and invalid endpoints cannot be repaired with component
claims. They do not substitute for later positive Bridge qualification. No empty
or fictional Bridge was added to meet a test count.

## Reassessment after implementation

| Candidate | Before | After | Required evidence still missing |
|---|---|---|---|
| REVENUE_BRIDGE | PARTIALLY_QUALIFIED | PARTIALLY_QUALIFIED | Qualified separate producer windows, population/period coverage, segment binding and compatible accounting/restatement source basis |
| MARGIN_OR_PROFIT_BRIDGE | PARTIALLY_QUALIFIED | PARTIALLY_QUALIFIED | Exact Contribution 0 window/basis/coverage qualification; no substitution of gross profit; no qualified pricing/cost/mix attribution |
| PROFIT_TO_CASH_BRIDGE | INSUFFICIENT_EVIDENCE | INSUFFICIENT_EVIDENCE | Governed profit and operating-cash endpoints, matched basis and component coverage |
| WORKING_CAPITAL_BRIDGE | PARTIALLY_QUALIFIED | PARTIALLY_QUALIFIED | Paired comparable stock bundles, accounting/restatement and coverage evidence; ledger/control balances must stay distinct |
| COST_TO_OUTPUT_BRIDGE | INSUFFICIENT_EVIDENCE | INSUFFICIENT_EVIDENCE | Comparable cost windows, qualified output measure, population coverage and retained detailed ancestry |

None is QUALIFIED_NOW. No opening + components + residual = closing claim can yet
be made. Residual cannot compensate for these gaps. Shared ancestry is retained;
no independence claim or new EconomicEffect reference is manufactured.

LOW_QUALITY_GROWTH, PROFIT_TO_CASH_DISCONNECT and
COST_GROWTH_OUTPACING_ECONOMIC_OUTPUT remain blocked. No stronger pricing,
input-cost or mix mechanism evidence was created. No Story or Hypothesis was
implemented/reassessed. v2.49 cannot consume nonexistent Bridges; its bridge-input
dependency remains blocked by evidence qualification, not a demonstrated need
for a broad architectural refactor.

The safest next step is a governed source-evidence contract that actually records
coverage/completeness and source/restatement/accounting compatibility, plus a
qualified producer-specific binding of those records to exact opening/closing
windows and canonical measurements. A caller-supplied assertion or inferred
latest-version status is insufficient. This additional evidence acquisition/
qualification work has not been improvised or substituted into frozen contracts.

## Qualification results

Initial focused development run: 23 tests, 7 PASS, 0 FAIL, 16 ERROR, 0 SKIP.
The errors came from a new test helper argument named value colliding with the
measurement value override. The helper was corrected; no assertion was weakened.
Subsequent 23-test run passed. Final expanded focused run: 26 tests, 26 PASS,
0 FAIL, 0 ERROR, 0 SKIP in 3.985 seconds, with DeprecationWarning and ResourceWarning
treated as errors. Compilation of source and tests passed.

The 26 tests cover explicit positive synthetic comparability, mismatched reporting
bases/entities/stock-flow/metrics/segments, unknown/restated/superseded versions,
coverage, ancestry insufficiency, calendar duration/chronology, Decimal precision,
serialization tampering, replay/source changes, actual source refusals, caller
scope, stale Signals, no assertion override, retained dataset metadata, shared
ancestry and SELECT-only resource ownership.

Authoritative full estate: 522 discovered/run, 513 PASS, 0 FAIL, 0 ERROR,
9 legitimate live PostgreSQL SKIP, 750.672 seconds on Windows 10 / Python 3.12.14.
The unchanged runner enforced strict deprecation/resource warning policy, including
delayed unraisable checks. No policy errors, expected failures or unexpected
successes. All existing migration/persistence and v2.43-v2.47 compatibility tests
passed within that estate. The only subsequent source edit clarified a module
docstring about the existing legacy restatement boundary; behaviour was unchanged.

Live PostgreSQL not run: no new
schema or Bridge persistence exists, and the approved no-qualified-family stop
applies. This is not a PostgreSQL pass or completion of v2.48 qualification.

Only additive qualification source/tests, estate registration and these two
documents changed. No existing diagnostic, Signal, Fact/Finding, Evidence Graph,
Hypothesis, Story, economic/Opportunity, management/benefit, product/API, v2.41
gate or v2.42 CI/resource-lifecycle semantics changed. No v2.49+ functionality.

Final review: git diff --check passed, including a separate whitespace check of
untracked additions. Credential-pattern review found no connection strings, keys
or passwords. There are seven intended files; the only modified tracked file is
the additive six-line estate entry. Reports/logs remain ignored under .venv.
Nothing is staged. Cross-platform CI and full live v2.48 qualification are not
claimed. The tree is a tested qualification-layer checkpoint, not a completed
Economic Bridges release.

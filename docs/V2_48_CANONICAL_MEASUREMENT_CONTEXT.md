# v2.48 Canonical Measurement Context — qualification checkpoint

Baseline: `main`, frozen v2.47 `fec375f9701af9052748e58907431a1da3f83f8e`.
This extends the approved, uncommitted BIQ checkpoint. No commit, push or v2.49
implementation is part of this work. This document records the implemented
context boundary; the earlier feasibility, BIQ and trace documents remain the
historical investigation/qualification record.

## Authority and scope

`MeasurementContext` (CMC-2.48.1) is an immutable, reusable semantic description
of an existing measurement. It stores no financial amount. `MeasurementSlot`
identifies the owning store, resource, record and exact value slot. A
`ContextBinding` (MCB-2.48.1) pins that owner's content/lineage digest to a context
and, for propagation, its parent binding. SHA-256 identities use the existing
canonical identity helper and deterministic foundation serialization.

The context retains client/run, metric, unit/currency, optional entity, economic
basis, segment scope, coverage and its declared basis, period bounds/nature/basis/
convention, existing dataset version, source/canonical-record lineage, original
workbook locator where available, revision association, capture method and
limitations. Inclusive duration is derived from known bounds; missing bounds
never acquire an invented duration. The approved BIQ Period/Coverage vocabulary
is reused. No new source, dataset, financial-value or restatement store exists.

Authority is through `MeasurementContextService`, not a freely constructed
context document. Capture resolves retained owning-store evidence. Retrieval
can return a historical snapshot; current consumption reproduces the source and
checks every intermediate binding, including primitive/Signal lineage. Altered
dependencies refuse current qualification while historical context stays readable.

## Upstream capture and deliberately bounded propagation

* Existing accounting CSV ingestion has an optional post-success `context_sink`.
  Its default path is unchanged. Source row references and immutable file hashes
  resolve optional explicit semantic columns; canonical amounts are compared as
  Decimal before binding. Existing accounting aliases govern supported metrics.
* `capture_management_accounts` is an opt-in adapter around the unchanged
  management-account numerical extractor. It retains the original workbook in
  the caller's source store, sheet/cell locator and derived CSV ancestry. Explicit
  title year, month columns and the explicit £000 declaration survive capture.
  It does not treat the extractor's fallback year or assumed scale as evidence.
* A stock's verified statement date becomes its as-of context. A flow's end alone
  never supplies its start. Workbook capture does not invent accounting policy,
  population completeness or segment declarations.
* Governed propagation supports accounting row → primitive → Signal observed
  slot → canonical Fact slot, only where retained dependency edges, metric,
  exact value and unit agree. Multi-row aggregation is deliberately refused.
  The stock-AR regression exercises the whole path without rewriting the frozen
  Fact's missing period projection. Financial-revenue/GP/EBITDA accounting roots
  can be qualified directly; this does not add new Signal-to-Fact mappings.
* Every observed/comparison/derived Fact slot can have a different binding.
  Mixed currency/currency/percentage facts remain mixed; no object-wide unit or
  reporting period is applied to all slots.

This does not automatically replace existing intake or downstream consumers.
The standard unknown-workbook path and existing diagnostics keep their numerical
behaviour. The new adapter must be explicitly invoked. Trial-balance fallback
dates, dropped commercial comparison windows, ambiguous cash lineage and
multi-period primitive aggregates are not repaired by guessing.

## Backfill, revision and ownership

Backfill is an explicit service operation, not a migration that asserts missing
history. Retained accounting rows can preserve known metric, stock date and
source/version references. Verified original bytes add only explicit declarations.
Unavailable originals produce limited retained-accounting context with unknown
policy/coverage/start/currency. Unknown/ambiguous accounting aliases are refused.

Canonical Fact backfill is per slot and requires a current eligible Fact with one
unambiguous existing dataset version and resolvable ancestry. It preserves frozen
mapped unit/currency as such, with a limitation; these are not independent proof
of source accounting semantics. Periods and coverage remain unqualified.

Contexts may reference existing `source_revision` identity, content snapshot,
original/restatement state and prior revision when the source explicitly binds
that revision and hash to its logical dataset. Otherwise revision state remains
`UNKNOWN_UNBOUND`. Context supersession preserves old records and requires the
same logical measurement family and period. Neither a supersedes pointer nor a
declared revision association proves cross-vintage accounting comparability.

Capture/bind audit records retain actor, event, timestamp, context/binding IDs and
supersession. The caller owns the SQLAlchemy transaction; rollback removes new
contexts, bindings and audits together. Existing SQLite ingestion retains its
existing commit ownership. A context-sink failure does not mislabel an already
committed ingestion as failed. This is not a distributed atomic transaction:
callers retry context capture using the retained dataset version. Services never
close caller-owned connections or commit the canonical transaction.

## BIQ integration

The original BIQ-2.48.1 evaluator/resolver and its 26 tests are preserved.
BIQ-2.48.2 `qualify_contexts` accepts binding IDs and the Bridge family, resolves
authoritative contexts and returns deterministic qualification with explicit gaps.
It accepts no context/coverage override. Context supplies evidence; BIQ supplies
the comparison policy.

Qualified endpoint types are narrowly allowlisted: financial revenue; exact
financial GP or EBITDA; individual AR/inventory/AP stocks. Calendar monthly,
quarterly or annual totals need complete declared intervals. Unequal calendar
day counts do not trigger daily normalisation. Stock comparisons use explicit
as-of dates. Unknown currencies, policy, scope, coverage or periods fail closed;
different accounting/reporting/coverage bases are incomparable. Partial coverage
remains partial. Only the same immutable dataset/revision snapshot currently
establishes version compatibility. Unknown original/restatement classification
does not invalidate a demonstrably common snapshot; it does not prove compatibility
between different snapshots.

This is endpoint qualification, not an economic Bridge. In particular, an
individual AR stock pair is not a composite working-capital or operating-cash
reconciliation. Financial GP is not Contribution 0.

## Retained evidence reassessment

No real production dataset with newly qualified declarations was supplied.
Repository evidence was inspected without changing it:

* `gate3_micro/pnl.csv` and `bs.csv` contain only one date (2026-12-31), line code,
  name and amount. No pair, currency, accounting basis or coverage declaration.
* The existing Scenario-1 synthetic CI workbook and Scenario-2 demo workbook
  each captured 48 management-account contexts through the new adapter. For each
  workbook, the earliest two revenue, GP and EBITDA contexts all returned
  `INSUFFICIENT_EVIDENCE`: `COVERAGE_UNKNOWN` and
  `REQUIRED_MEASUREMENT_CONTEXT_UNKNOWN`. These files are not real-SME evidence.
* A separately labelled synthetic Level-1 CSV positive test supplies explicit
  January/February calendar, currency, accounting and coverage declarations in
  one immutable source snapshot. It qualifies without sales/customer/product/CRM
  data. This proves the application boundary can accept adequate Level-1 evidence;
  it does not prove production Bridge availability.

| Family | Before context | After context / remaining blocker |
|---|---|---|
| REVENUE_BRIDGE | Unqualified dates/basis/coverage/version | Capture now available; retained evidence still lacks policy/scope/coverage or a pair |
| MARGIN_OR_PROFIT_BRIDGE | Unqualified comparable profit endpoints | Exact GP/EBITDA context preserved; same retained policy/scope/coverage gaps; C0 never relabelled |
| WORKING_CAPITAL_BRIDGE | Missing paired scoped balances | Stock as-of can propagate; no qualified retained complete pair/composite coverage and sign contract |
| PROFIT_TO_CASH_BRIDGE | No qualified operating-cash reconciliation | Still blocked: cash stock is not operating cash flow; classification and matched profit basis absent |
| COST_TO_OUTPUT_BRIDGE | Cost/output definitions and windows unqualified | Still blocked: context cannot create a qualified output proxy or cost composition |

**Zero Bridges implemented.** There are no residual or reconciliation results.
As instructed, development stops at the qualified context checkpoint because no
actual retained production Bridge qualifies. Level-2/3 absence is not itself a
Level-1 blocker. The blockers above are missing evidence/contract qualification.

The three deferred Stories remain deferred: LOW_QUALITY_GROWTH needs qualified
comparable revenue/profit evidence; PROFIT_TO_CASH_DISCONNECT needs a governed
profit/operating-cash reconciliation; COST_GROWTH_OUTPACING_ECONOMIC_OUTPUT needs
qualified comparable cost/output evidence. Pricing/cost/mix mechanism support is
unchanged and unavailable; no causal hypothesis or Story is promoted.

## Persistence and qualification

Migration `0009_measurement_context` follows frozen `0008_economic_story`, adding
`canonical_measurement_context`, `canonical_measurement_binding` and
`canonical_measurement_audit`. SQLite and PostgreSQL use the existing Text
document/identifier conventions; amounts stay in their owning stores. Composite
client FKs protect context, binding, parent and audit references; run existence
is a database FK and run/client agreement is checked at the service boundary.
Legacy-store references cannot have cross-database SQL FKs and are resolved by
the scoped source adapter. Raw SQL access is not the semantic application boundary.

Clean/repeat-head schema and frozen-v2.47 fixture upgrade tests compare metadata
and FKs. All columns of all 30 legacy tables are seeded and preserved through
upgrade/downgrade/re-upgrade. Downgrade to 0008 intentionally removes context,
binding and audit records; it preserves every v2.47 table and seeded value.
No historical migration changed. Four older migration tests advance only their
expected head literal to 0009; all preservation/schema assertions remain intact.

Final focused tests: **51 PASS, 0 FAIL, 0 ERROR, 0 SKIP** (22 context, 3 migration,
26 unchanged BIQ). The earlier v2.43–v2.47 compatibility run passed all 238 tests;
the subsequent coverage safeguard is covered by the final focused and full runs.

Live qualification: PostgreSQL **18.6**, dedicated non-primary/non-default,
unprotected Neon branch `v2-41-qualification` (`br-royal-math-za046ex1`) in
`tiny-meadow-46991842`. **38 PASS, 0 FAIL, 0 ERROR, 0 SKIP**, including frozen
upgrade/data preservation/downgrade/re-upgrade, clean schema, all 22 context tests,
PostgreSQL readiness and the unchanged nine live v2.41 attacks. Zero open or
checked-out connections and no unraisable resource errors at completion.
Connection credentials were process-only. Destructive reset remains confined to
the opted-in disposable qualification script and existing test fixtures.

Final authoritative full estate, through `scripts_run_full_regression.py` on
Windows 10 / Python 3.12.14: **547 discovered and run, 538 PASS, 0 FAIL, 0 ERROR,
9 legitimate live PostgreSQL SKIPS**, 707.453 seconds. No expected failures,
unexpected successes or policy errors. Strict DeprecationWarning/ResourceWarning
handling uses the unchanged v2.42 gate; live skips are not counted as passes.
Source/tests/migrations/scripts compilation passed. `git diff --check` and a
separate untracked-file whitespace/credential/artifact review passed. Original
BIQ source, tests and checkpoint documentation were hash-verified unchanged.

## Completion boundary

1. Context is authoritative through the validated service and reusable beyond
   Bridges; it is not a new value store.
2. Implemented paths preserve source context. Unrecoverable historical and
   unsupported producer paths stay unknown rather than being reconstructed.
3. Unknown context leaves unrelated analysis unchanged; it limits qualification.
4. Sufficient Level-1 declarations can qualify endpoints. No genuine retained
   production Bridge has yet been established.
5. None of the five families currently qualifies from supplied production evidence.
6. The feasibility table identifies each remaining blocker.
7. v2.49 has no qualified Bridge outputs to consume. No v2.49 code was added.
8. No demonstrated architectural defect blocks review of this context foundation.
   Further Bridge development remains gated on qualified source evidence and,
   for composite/cross-metric Bridges, separately governed comparison contracts.

v2.48 Economic Bridges is **still blocked**, not a completed release. This is a
locally/live-qualified context checkpoint awaiting review and sufficient evidence.
Cross-platform CI has not run for this uncommitted tree. No commit or push.

## Complete working-tree file inventory

The tree contains seven tracked modifications and twenty intended new files.
Earlier approved BIQ/trace additions are included here, not attributed to this
context implementation. Local reports/review scripts remain ignored under
`.venv/`; no credentials or connection strings are written to them.

| File | Reason |
|---|---|
| `profit_doctor/ingestion/accounting.py` | Optional post-success capture hook; existing ingestion body unchanged |
| `profit_doctor/persistence/__init__.py` | Register additive context metadata |
| `qualification/test_estate_v242.json` | Register 26 BIQ, 22 context and 3 context-migration tests |
| `tests/test_canonical_migrations_v244.py` | Expected head only: 0009 |
| `tests/test_graph_migrations_v245.py` | Expected head only: 0009 |
| `tests/test_hypothesis_migrations_v246.py` | Expected head only: 0009 |
| `tests/test_story_migrations_v247.py` | Expected head only: 0009 |
| `alembic/versions/0009_measurement_context.py` | Forward-only three-table migration |
| `profit_doctor/persistence/measurement_schema.py` | Context/binding/audit metadata and integrity constraints |
| `profit_doctor/reasoning/measurement/__init__.py` | Additive package boundary |
| `profit_doctor/reasoning/measurement/contracts.py` | Immutable slot/context/binding contracts |
| `profit_doctor/reasoning/measurement/source.py` | Resolve scoped retained accounting declarations and ancestry |
| `profit_doctor/reasoning/measurement/service.py` | Capture, backfill, propagate, validate, replay, supersede and audit |
| `profit_doctor/intake/measurement_context.py` | Opt-in original-workbook and monthly context preservation |
| `profit_doctor/reasoning/bridge/context_qualification.py` | BIQ-2.48.2 authoritative-context policy |
| `tests/test_measurement_context_v248.py` | 22 context/persistence/adversarial cases |
| `tests/test_measurement_context_migrations_v248.py` | Three frozen upgrade/clean schema/migration cases |
| `tests/fixtures/v247_schema.sql` | Preserved schema at migration 0008, independent of mutable metadata |
| `scripts/qualify_measurement_context_postgresql_v248.py` | Explicit disposable live qualification, resource checks and redacted report |
| `docs/V2_48_CANONICAL_MEASUREMENT_CONTEXT.md` | Current implementation/qualification and remaining blockers |
| `docs/V2_48_MEASUREMENT_CONTEXT_TRACE.md` | Previously approved read-only trace |
| `docs/V2_48_BRIDGE_FEASIBILITY.md` | Preserved earlier feasibility checkpoint |
| `docs/V2_48_BRIDGE_INPUT_QUALIFICATION.md` | Preserved earlier BIQ checkpoint |
| `profit_doctor/reasoning/bridge/__init__.py` | Preserved earlier package boundary |
| `profit_doctor/reasoning/bridge/qualification.py` | Preserved BIQ-2.48.1 evaluator |
| `profit_doctor/reasoning/bridge/source.py` | Preserved original conservative Fact resolver |
| `tests/test_bridge_input_qualification_v248.py` | Preserved original 26 BIQ assertions |

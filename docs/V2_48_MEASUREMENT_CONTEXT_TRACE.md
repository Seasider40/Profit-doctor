# v2.48 Measurement Context Trace & Architecture Recommendation

Read-only investigation, 2026-09-29. No recommendation in this document has been
implemented. The accepted uncommitted Bridge Input Qualification checkpoint is
preserved. Baseline: main, fec375f9701af9052748e58907431a1da3f83f8e.

## 1. Main conclusion and investigation limits

The gap is not simply absent data, and it does not justify requiring Level-2/3
detail for basic Level-1 Bridges. Context is variously present upstream, dropped
at projection boundaries, implicit in executable methods, or never requested.
The current canonical Fact boundary also lacks a route for several existing
Level-1 financial measurements. A Bridge-only metadata patch would preserve
these structural problems.

Recommend a reusable, immutable, versioned Canonical Measurement Context, bound
to an existing source measurement or exact measurement slot. Capture context
where its meaning is established; propagate references rather than reconstruct
meaning from narrative downstream. Reuse source/dataset identities, primitive
definitions/methods, lineage and legacy revision records. Do not duplicate them.

This is static source/schema tracing plus inspection of repository CSV headers,
sample rows and the deterministic workbook fixture generator. No unseen customer
workbook is assumed to contain metadata. SOURCE in the matrices means the
representative supported contract/fixture described, not all possible SME files.
No database was opened, no ingestion executed, no tests or full regression run,
no live PostgreSQL accessed, and no production/test file changed in this task.

## 2. Actual architecture map (not a single universal chain)

```
Original CSV -> immutable file + dataset/version -> accounting or sales rows
Workbook -> profiling/semantic mapping -> temporary accounting CSV -> same rows
         -> aggregate handoff -> Signals (some branches bypass primitives)

Sales rows -> commercial primitives (all captured active rows)
          -> revenue/margin diagnostics (recalculate TWO sales windows directly)
          -> Signal + diagnostic_lineage -> LegacySignalSource -> CanonicalFact

Accounting rows -> Level-1 primitives -> WC diagnostics -> Signal -> CanonicalFact
                                  \-> FIN_REVENUE/GP/EBITDA: no general Fact route

Overhead rows -> supplier diagnostics (no overhead primitive stage) -> Signal
             -> CanonicalFact with limited ancestry
```

SQLAlchemy canonical Facts use a read-only owning-store adapter to legacy SQLite.
SQLAlchemy primitive_result_v2 is a separate incremental persistence surface,
not a complete copy of the SQLite primitive_result context. Existing diagnostic
migration adapters copy available Signal fields; they cannot restore absent ones.

## 3. Evidence index: exact boundaries inspected

Paths are relative to the repository; line numbers are starting anchors in the
preserved working tree, not proposed edits.

| Anchor | Model / function / fields and relevance |
|---|---|
| ingestion/northstar.py:24,39 | register_file / register_dataset_version: immutable hash/copy, logical dataset, version number; period_from/to are min/max of one input field, not certified reporting bounds |
| ingestion/northstar.py:75 | ingest_northstar: explicit selected sales fields; extra source segment/family/supplier columns are not retained in sales_transaction |
| ingestion/accounting.py:7,30 | CONTRACTS / ingest_accounting_file: D01/D02 require period_end only; D04/D05 invoice/due dates but no ledger as-of; no currency, scale, accounting/reporting-basis contract |
| intake/workbook.py:142,151,207 | _unit / semantic_map_workbook / canonical_extract: header unit/confidence/confirmation metadata exists, extraction copies semantic values and sheet/row but not those annotations |
| intake/bridge.py:23,27,52,68,103 | _year_from_title / _ma_rows / _tb_rows / _bs_from_tb / execute_unknown_workbook: month headings become period_end; fallback year 2026; MA scale 1000; TB date December 31; temporary CSV/store |
| core/db.py:21,27,32,44,62 | source_file, dataset, dataset_version, sales_transaction, primitive_result: retained identifiers, source row, periods, dimension, method, unit |
| core/db.py:101,115,150,156,162,169,175,529 | mapping/economic coverage; financial_statement_line; AR/AP; inventory; bank; overhead_transaction schemas |
| calc/primitive_engine.py:14,40,98,124,152 | REGISTRY/METHODS/_result/calculate_transaction_primitives/calculate_level1_primitives: meaning, stock/flow/rate, methods, dates and lineage |
| diagnostic/engine.py:85,93,116,151,215 | _execute / _windows / revenue_diagnostics / extended_revenue_diagnostics / margin_diagnostics: source window variables versus emitted fields |
| diagnostic/engine.py:606,629 | SUP-04 within supplier diagnostics; working_capital_diagnostics: omitted scope dates and primitive-result ancestry |
| reasoning/canonical/registry.py:57,67,84,156,186,204 | frozen slot semantics, generic captured scope, overhead caveat, WC mapping, PVM reconciliation |
| reasoning/canonical/service.py:83,107,118 | canonicalise: controlled unit/currency assignment; scope copied from Signal, no recovery of missing slot periods |
| reasoning/canonical/contracts.py:28,47,70 | Measurement / ReportingScope / CanonicalFact: per-slot metric/value/unit/basis, but one common scope interval |
| reasoning/canonical/source.py:17 | LegacySignalSource.read: source Signal/execution/diagnostic-lineage snapshot; no general measurement context |
| reasoning/graph/ancestry.py:17,74 | owning-store traversal and supported resource allowlist; PRIMITIVE by name, WORKBOOK_ROW and MULTIPLE are unresolved |
| management/restatement.py:17,51,64,91 | source_revision/prior_revision_id, register_revision, classify_period_change, detect_missing_periods |
| persistence/models.py:50,68 | PrimitiveResult lacks SQLite periods/dimensions; Signal retains only the fields supplied by legacy producers |
| persistence/diagnostic_migration.py:26,56 | Signal field-for-field copies preserve supplied periods, not missing context |

All paths above are under profit_doctor/. Representative source evidence also
includes tests/fixtures/gate3_micro/{pnl,bs,ar,ap,bank}.csv,
tests/fixtures/northstar/transactions.csv and tests/workbook_fixtures.py:54.

## 4. Measurement-by-layer matrices

Codes: A = AVAILABLE explicitly in the layer/contract; D = DERIVABLE safely from
retained definition/reference, subject to stated scope; B = AMBIGUOUS; L = LOST
from this layer after being known upstream (may remain recoverable upstream);
N = NOT_AVAILABLE in the representative contract/path. A does not mean independently
audited or complete. LOST is not proof of irreversible destruction of original bytes.

Each row has all 18 required dimensions, grouped in fixed order:

- Identity/basis [1-4]: client/entity; metric; economic/accounting basis; flow/stock.
- Time [5-8]: start; end; duration; reporting basis.
- Measure/scope [9-12]: currency; unit; completeness; segment scope.
- Provenance [13-18]: source file; dataset/version; original/restated status;
  version relationship; canonical measurement lineage; pair comparability.

For a source row before ingestion, client binding and canonical lineage do not yet
exist. D for source file/version at later layers means traversable retained IDs,
not an assertion that stored file bytes remain accessible forever.
Mapping rows are conceptual semantic checkpoints, not invented pipeline stages:
accounting aliases currently execute inside the primitive engine, after storage.

### 4.1 Commercial revenue (D07 -> REV-01; REV-02/03/04 differences below)

| Layer | 1-4 | 5-8 | 9-12 | 13-18 |
|---|---|---|---|---|
| Source transactions CSV | N A B D | B A B B | N B B A | A N N N N B |
| Intake register + select fields | A A B D | B A B B | N B B L | A A N B A B |
| Semantic mapping (explicit D07 fields) | A A A D | B A B B | B A B L | A A N B A B |
| Canonical sales_transaction | A A A D | B A B B | N B B L | D A N B A B |
| Commercial primitive | A A A A | A A D B | B A B L | D D N B D B |
| Diagnostic _windows calculation | A A A D | A A D D | B A B L | D A N B D B |
| REV-01 Signal | A A D D | L L L L | B A B L | D D N B D B |
| Canonical comparative Fact | A A A D | L L L B | B A B L | D D N B D B |

Source month is preserved verbatim as transaction_date; a month label/day is not
proof of complete daily coverage. Primitive extrema describe captured rows, not
whole reporting windows. Diagnostic _windows knows exclusive-start/inclusive-end
anniversary boundaries. REV-01 retains only the outer two-window span, hence L for
the individual opening/closing periods; REV-02/03/04 retain no period dates.
Source segment/family columns are dropped, while customer/product IDs survive.
GBP is a program contract, not per-file currency verification. The mapping's
current/prior comparable-window labels preserve calculation roles, not dates.

### 4.2 Contribution 0 / Contribution 0 margin (D07 -> GM-01/02)

| Layer | 1-4 | 5-8 | 9-12 | 13-18 |
| Source sales/direct-cost CSV | N A B D | B A B B | N B B A | A N N N N B |
| Intake | A A B D | B A B B | N B B L | A A N B A B |
| Semantic mapping | A A A D | B A B B | B A B L | A A N B A B |
| Canonical sales_transaction | A A A D | B A B B | N B B L | D A N B A B |
| C0 / margin primitive | A A A A | A A D B | B A B L | D D N B D B |
| GM calculation | A A A D | A A D D | B A B L | D A N B D B |
| GM-01/02 Signal | A A D D | L L L L | B A B L | D D N B D B |
| Canonical Fact | A A A D | L L L B | B A B L | D D N B D B |

C0 is explicitly net revenue minus direct product/service cost; margin is C0 /
revenue. This formula is known, while accounting recognition/cost coverage may not
be. Source gross_profit and contribution are separate retained values, not proof
of equivalence. GM calculates windows but omits dates. Canonical mapping correctly
separates GBP contribution, percentage margin and percentage-point movement.
All-row commercial primitive values are not the two-window diagnostic values.

### 4.3 Accounts receivable (D02 control balance -> WC-02)

| Layer | 1-4 | 5-8 | 9-12 | 13-18 |
| D02 CSV | N A B D | N A N D | N B B N | A N N N N B |
| Accounting intake | A A B D | N A N D | N B B N | A A N B A B |
| AR alias mapping | A A A A | N A N D | B A B N | D A N B A B |
| financial_statement_line | A A B D | N A N D | N B B N | D A N B A B |
| BS_ACCOUNTS_RECEIVABLE primitive | A A A A | N A N D | B A B N | D D N B D B |
| WC-02 reads primitive | A A A D | N A N D | B A B N | D D N B D B |
| Signal | A A D D | N L N L | B A B N | D D N B D B |
| Canonical Fact | A A A D | N L N B | B A B N | D D N B D B |

Start/duration N are not defects for a stock: one as-of date is sufficient.
WC-02 has the result row/date but emits no date. The primitive reference survives,
so this is recoverable loss. D04 ledger route differs: invoice/due dates are known,
but ledger snapshot date is absent from its CSV contract; the primitive uses
latest financial period or latest invoice date as assessment. That choice does not
prove the outstanding balance's as-of date. Do not substitute D04 for D02 silently.

### 4.4 Inventory (D02 stock -> WC-04; D12 alternative)

| Layer | 1-4 | 5-8 | 9-12 | 13-18 |
| D02 CSV | N A B D | N A N D | N B B N | A N N N N B |
| Accounting intake | A A B D | N A N D | N B B N | A A N B A B |
| Inventory alias mapping | A A A A | N A N D | B A B N | D A N B A B |
| financial_statement_line | A A B D | N A N D | N B B N | D A N B A B |
| BS_INVENTORY primitive | A A A A | N A N D | B A B N | D D N B D B |
| WC-04 reads primitive | A A A D | N A N D | B A B N | D D N B D B |
| Signal | A A D D | N L N L | B A B N | D D N B D B |
| Canonical Fact | A A A D | N L N B | B A B N | D D N B D B |

D12 explicitly retains snapshot_date/product_key/quantity/value and dataset/row
reference. Its latest snapshot date is preserved by INVENTORY_SNAPSHOT_VALUE then
omitted by the Signal. Product aggregation is known but valuation method, complete
portfolio coverage and write-down policy are not in that contract. D02 is already
a Level-1 stock basis; D12 is not mandatory for a simple D02 inventory movement.

### 4.5 Accounts payable (D02 control balance -> WC-03)

| Layer | 1-4 | 5-8 | 9-12 | 13-18 |
| D02 CSV | N A B D | N A N D | N B B N | A N N N N B |
| Accounting intake | A A B D | N A N D | N B B N | A A N B A B |
| AP alias mapping | A A A A | N A N D | B A B N | D A N B A B |
| financial_statement_line | A A B D | N A N D | N B B N | D A N B A B |
| BS_ACCOUNTS_PAYABLE primitive | A A A A | N A N D | B A B N | D D N B D B |
| WC-03 reads primitive | A A A D | N A N D | B A B N | D D N B D B |
| Signal | A A D D | N L N L | B A B N | D D N B D B |
| Canonical Fact | A A A D | N L N B | B A B N | D D N B D B |

Same stock-date loss as AR. D05 invoice/due dates do not establish ledger as-of.
The workbook TB adapter converts AP debit-minus-credit to absolute magnitude;
raw signed TB remains a separate record. Future stock/cash-effect conventions
must bind to the selected measure and sign policy, not infer signs from a label.

### 4.6 Available accounting profit AND financial revenue (D01)

The same context path applies separately to FIN_GROSS_PROFIT, FIN_EBITDA and
FIN_REVENUE. They are not interchangeable metrics or aliases of Contribution 0.

| Layer | 1-4 | 5-8 | 9-12 | 13-18 |
| D01 CSV | N A B D | N A N B | N B B N | A N N N N B |
| Accounting intake | A A B D | N A N B | N B B N | A A N B A B |
| Revenue/GP/EBITDA alias mapping | A A A A | N A N B | B A B N | D A N B A B |
| financial_statement_line | A A B D | N A N B | N B B N | D A N B A B |
| Level-1 financial primitive | A A A A | B A B B | B A B N | D D N B D B |
| General financial diagnostic | N N N N | N N N N | N N N N | N N N N N N |
| General financial Signal | N N N N | N N N N | N N N N | N N N N N N |
| Corresponding canonical Fact | N N N N | N N N N | N N N N | N N N N N N |

The primitive selects latest financial year, sums matching line codes across
captured period_end values, and sets period_from to the first end date. It does
not possess each row's start date or know whether rows are monthly, YTD snapshots
or annual totals. The YTD method is explicit; source suitability is not proven
by that label. Example gate3_micro P&L has one December 31 row per metric: the
CSV alone cannot establish annual versus monthly meaning. Workbook Jan-Dec
columns provide richer period intent, which the temporary CSV drops.

There is no general FIN_GP/EBITDA Signal-to-Fact mapping. FCST plan-versus-actual
revenue is a different comparison and is deliberately refused by the canonical
registry; it is not a substitute financial revenue Fact route. This is a missing
integration path, not merely loss in Fact serialization.

### 4.7 Available cash (D06 bank / D02 cash -> WC-05)

| Layer | 1-4 | 5-8 | 9-12 | 13-18 |
| Bank CSV | N A B D | N A N D | N B B B | A N N N N B |
| Accounting intake | A A B D | N A N D | N B B B | A A N B A B |
| Bank amount/balance mapping | A A B D | N A N D | B A B B | D A N B A B |
| bank_transaction | A A B D | N A N D | N B B B | D A N B A B |
| BANK_CLOSING_CASH primitive | A A A A | N A N D | B A B B | D D N B D B |
| AVAILABLE_CASH primitive | A A B A | N B N D | B A B B | B B N B B B |
| WC-05 selects result | A A B D | N B N D | B A B B | B B N B B B |
| WC-05 Signal | A A B D | N L N L | B A B B | B B N B B B |
| Canonical captured_cash Fact | A A A D | N L N B | B A B B | B B N B B B |

BANK_CLOSING_CASH uses the last dated running balance, not an aggregation of bank
accounts. Bank account identity, currency and restriction status are absent from
the input contract. AVAILABLE_CASH prefers bank over BS; its period_to is
latest_period from financial statements, potentially not the bank date. Its
lineage is PRIMITIVE plus a name rather than the exact result ID; current graph
traversal cannot resolve that dependency unambiguously. The Signal references
the selected result but omits dates. The canonical mapping conservatively calls
the value captured_cash, not verified unrestricted liquidity or operating flow.

### 4.8 Major overhead cost (SUP-04)

| Layer | 1-4 | 5-8 | 9-12 | 13-18 |
| Representative overhead evidence | B A B D | B A B B | B B B A | B N N N N B |
| Existing row insertion boundary | A A B D | B A B B | N B B A | N N N N A B |
| Category/amount mapping | A A B D | B A B B | B A B A | N N N N A B |
| overhead_transaction | A A B D | B A B B | N B B A | N N N N A B |
| Analytical primitive | N N N N | N N N N | N N N N | N N N N N N |
| SUP-04 calculation | A A A D | B B D B | B A B A | N N N N B B |
| Signal | A A D D | L L L L | B A B A | N N N N L B |
| Canonical Fact | A A A D | L L L B | B A B A | N N N N L B |

This route is represented by direct overhead rows and the synthetic Level-3
qualification fixture, not a demonstrated general source-file ingestion adapter.
overhead_transaction has date/category/amount/evidence_basis but no dataset,
source-file or source-row FK. SUP-04 splits the sorted observed month labels in
half; it knows membership and sums, not a declared reporting window. Gaps and
unequal halves prevent automatic normalisation. Signal ancestry uses
OVERHEAD_TRANSACTION/MULTIPLE; individual row identity is lost. A Level-1 mapped
P&L cost line would be a separate, simpler basis, not a reinterpretation of SUP-04.

## 5. Exact loss points and ambiguities

1. Workbook semantic mapping -> canonical_extract: column unit, mapping confidence
   and requires_confirmation are not carried with normalized values. Only
   source_sheet/source_row plus semantic keys survive this in-memory boundary.
2. _ma_rows -> temporary pnl.csv -> financial_statement_line: explicit month
   headers become period_end only. Original column/cell, scale annotation,
   month reporting convention and original workbook identity are not bound to
   each generated row. _year_from_title defaults 2026; multiplying by 1000 is
   hard-coded. These are assumptions to expose, not reliable recovery rules.
3. _tb_rows supplies year-end from a title/default; it cannot establish actual
   TB as-of solely from an arbitrary title. _bs_from_tb aggregates accounts,
   drops contributing account identities in the derived CSV, and normalises AP
   sign. Account/row evidence remains in the separately ingested TB, without an
   explicit derived-row binding.
4. execute_unknown_workbook registers generated CSVs under TemporaryDirectory,
   not the original workbook as their derivation parent. That store is removed
   on exit. A source_file row can survive while storage_location becomes stale.
   Metadata/hash retention is not permanent byte availability.
5. ingest_northstar's explicit tuple drops segment, family and other optional
   source columns. Customer/product keys survive; their existence is not full
   segmentation context. Source CSV bytes may allow controlled later recovery.
6. Accounting ingestion contracts never require period_start/reporting basis,
   currency/scale, accounting policy, ledger as-of, bank account ID or source
   revision relation. This is absence at contract entry, not Fact-layer loss.
7. register_dataset_version stores min/max field values; those values may be
   invoice dates, snapshot dates or period ends. No field explains which semantic
   interval they describe. Version numbers are not restatement classifications.
8. Level-1 P&L calculation knows its aggregation rule but cannot distinguish
   incremental monthly amounts from cumulative YTD rows. Earliest period_end
   stored as period_from is not the start of that first period. Do not backfill
   January 1 without a source/calendar contract.
9. _windows knows sales window boundaries, inclusivity and row selection.
   revenue_diagnostics retains only combined REV-01 dates; other revenue and
   GM producers omit them. _execute permits nullable dates and persists exactly
   that omission. This is a clear producer-projection loss.
10. WC diagnostics read dated primitive results, then omit period fields when
    constructing Signals. Exact PRIMITIVE_RESULT references often preserve a
    recovery route. AVAILABLE_CASH's own date/dependency ambiguity occurs earlier.
11. _result often records a DATASET_VERSION with prose scope rather than exact
    contributing statement-line IDs; dependent PRIMITIVE name references are
    not unique result IDs. Neither numerical equality nor the newest result
    safely resolves the historical dependency.
12. LegacySignalSource retains Signal/execution/diagnostic lineage; canonicalise
    copies one ReportingScope and constructs units/basis from frozen mapping.
    Measurement has no slot-specific context reference. from_json preserves
    the current contract; serialization does not itself drop an existing field.
13. SQLAlchemy PrimitiveResult lacks the legacy period_from/to and dimension
    fields. This is a representation gap; this investigation did not establish
    an active complete primitive migration that preserves them elsewhere.
14. Direct overhead storage lacks source versioning before diagnostic execution;
    the downstream MULTIPLE sentinel then loses even retained row membership.

## 6. Context available but unused; genuinely unavailable context

Reusable now: source_file hashes/IDs, dataset_version IDs and source row numbers;
statement_type and period_end; D12 snapshot dates; primitive registry stock/flow/
rate and method definitions; exact sales window variables; client/run identity;
customer/product keys; canonical slot metric/unit/basis; source revision chains;
existing lineage and audit services. Preserve these upstream rather than adding
human-supplied copies downstream. No new Company/Run/File/Dataset registry needed.

Not established by current contracts: company-wide population completeness,
unreported zero-activity periods, ledger as-of, full bank-account population,
currency/FX where not explicitly declared, accrual/cash accounting and consistent
classification policy, stock valuation/restatement basis, and linkage of a
management source revision to a specific dataset/measurement slot. Original
files may establish some, but inspection must verify each declaration. It is
incorrect to say those facts can never be known from ordinary SME data.

Captured-data quality differs from completeness: trust.engine counts populated
cells, unique IDs, observed months and mapped revenue. Its economic coverage
can default to 100 when no segment mapping is required. These controls do not
prove completeness of the business. Conversely a Bridge explicitly restricted
to a complete, defined captured portfolio need not claim whole-company coverage.

## 7. Level-1 / Level-2 / Level-3 implications

| Class | Context and appropriate source |
|---|---|
| A: ingestion should know | client/run, original file/hash, dataset/version, source cell/row, selected mapping/method version, metric, declared currency/scale, declared report basis/as-of, stock versus flow from mapped definition; store unknown if declaration missing |
| B: safely derivable | end/start from an explicit calendar month+year; duration from bounds; stock instant from explicit as-of; known fiscal/calendar intervals; selection scope and component membership; signed movement from matched stocks; same immutable snapshot relationship for evidence from that snapshot |
| C: richer L2/3 evidence | customer/product price-volume attribution, unit consistency, mix/segment-margin decomposition, invoice collection mechanisms, operational cost drivers, bank account/transaction classifications for richer cash explanations |
| D: genuinely unavailable without new evidence | omitted accounting policy/year/scale, missing opening statements, undocumented population omissions/restatements, restrictions on cash, missing bank accounts, causal WHY; no amount of downstream parsing supplies these |

Basic Level-1 Bridges should be possible with two well-defined accounting periods
or stock dates and a clearly bounded coverage policy. Customer/product transactions
are not prerequisites for accounting revenue/GP/EBITDA movement or AR/inventory/AP
stock movement. Level-1 does not mean dates or currency may be guessed.

The current BIQ equal-day policy is a conservative checkpoint, not the eventual
definition of comparability: calendar January and February differ in days yet
can be compared as unnormalised calendar-month totals under an explicit contract.
Annual leap years likewise need an explicit calendar policy, not automatic daily
normalisation. A stock has an instant, not a required artificial flow duration.

Unknown historical original-versus-restated status need not block every comparison:
a same-snapshot, consistently stated pair can be described as such without
claiming it is the originally reported series. Cross-vintage comparison requires
explicit compatibility/restatement binding. This is a proposed policy distinction,
not an override of the accepted checkpoint or its frozen tests.

## 8. Version and restatement analysis

dataset_version increments on changed file identity; unchanged latest hash replays.
It does not distinguish refreshed extracts, added periods, corrected records or
restatements. Original source bytes are retained in the ordinary immutable store,
subject to storage lifecycle; the temporary-workbook path is the exception above.

management.restatement.source_revision has logical_source_key, run, content_hash,
revision_number, prior_revision_id, revision_type, effective_period and reason.
register_revision labels any changed subsequent payload RESTATEMENT; that label
alone is not an accounting-period compatibility proof. classify_period_change
uses prior revision existence, so downstream consumers must not treat it as a
complete canonical definition of correction versus new reporting period.

Reuse its revision identities/history and preserve legacy behaviour, but add an
explicit scoped binding to dataset_version, source measurement, affected period
and interpretation of the revision. Do not match merely by run/name/date or
create a competing revision chain. Separate ORIGINAL_AS_REPORTED,
RESTATED_AS_OF and SAME_SNAPSHOT comparison policies conceptually; exact governed
vocabulary is for the next approved design, not implemented here.

## 9. Architecture options A-E

| Option | Strength | Weakness | Recommendation |
|---|---|---|---|
| A Extend measurement rows/slots directly | Simple access, context adjacent to value | Repeats context across sales/financial/primitive/Signal/Fact stores; shared restatements can diverge; invasive frozen-schema evolution | Use context references in these rows, not duplicated full context |
| B Reusable Canonical Measurement Context | Single versioned semantic definition; per-slot binding; shared provenance and consistent comparison across future features | Requires explicit authority, immutable revisions and cross-store ownership | Recommended core |
| C Dataset/lineage metadata + dynamic resolution | Reuses provenance; economical for dataset-wide declarations | A dataset can contain stock/flow, monthly/YTD and several currencies; latest resolution changes historical meaning | Supporting capture/resolver only; pin resolved context/version |
| D Bridge-specific metadata | Fast narrow integration | Repeats semantics for forecasting/impact; downstream reconstruction; risk of permanent parallel truth | Keep BIQ as consumer/policy, not context authority |
| E Producer-owned context capture + shared context bindings | Preserves exact window/aggregation semantics at calculation time while retaining old numerical writers | Needs small explicit projection/binding changes per route | Delivery pattern for B, not a second model |

Choose B with E capture and C provenance reuse. A is the minimal reference field/
extension at integration points. The canonical context describes meaning, not
financial value, confidence score, Story state or a new reasoning engine.

## 10. Recommended canonical contract and authority

Proposed immutable context: stable ID/schema/method version; client; exact metric
and economic basis; FLOW/STOCK/RATE; monetary currency and input scale/unit;
entity and explicitly bounded population/segment; period bounds with inclusivity,
calendar/fiscal/reporting convention or as-of; coverage extent plus evidence and
limitations; source vintage/revision relationship; existing LineageReferences.
Separate observed declaration, safely derived value and unknown, preserving the
evidence/derivation for each material context assertion.

Bind context to existing owner/store/resource/identity AND measurement slot
(observed/comparison/derived or source amount/balance), source digest and mapping/
calculation version. A whole-Signal context cannot stand for two windows or mixed
units. Derived context retains parent measurement/context references and exact
selection/aggregation method; no reconstruction from narrative.

Capture at intake/mapping and producer selection boundaries, publish/pin at the
canonical boundary. Use existing SQLAlchemy persistence conventions for canonical
authority and trusted owning-store references for legacy SQLite. Do not promise
cross-store ACID: validate/pin source snapshots and fail closed on mismatches.
No new duplicate financial values or alternate Fact authority. Pair comparability
is a versioned assessment over two immutable contexts, not a universal boolean
stored on one measurement or a permanent dataset guarantee.

Reuse the accepted BIQ Period/ReportingBasis ideas in the canonical context
contract rather than introducing another incompatible period vocabulary. Existing
ReportingScope remains a legacy projection with one interval; it must not be
mistaken for complete per-slot context. Any type relocation/evolution must preserve
the old BIQ serialized version and be separately qualified.

This serves later Impact, longitudinal comparisons, forecasting vintages and
traceable explanations. AI-facing projections may report only retained context;
they gain no authority to infer missing accounting meaning.

## 11. Migration, backfill and frozen semantics

Forward additive context/binding persistence only after design approval; existing
migrations remain untouched. Reuse Client/EngineRun, source references, audit and
Decimal serialization. Specify tenant-scoped FKs where the owner is in SQLAlchemy;
validate legacy references through the owning resolver. Context records should be
immutable with explicit revision/supersession; no rewriting historical readings.

Backfill only explicit source declarations or deterministic, version-qualified
derivations: verified stock as-of, known method type, IDs and source rows. Unknown
dates/policies/coverage stay unknown. Do not turn combined bounds into calendar
periods, assume Jan 1, label all latest versions original, or parse prose as truth.
Transient missing originals limit recoverability. Reproduced method selection
needs a verified source snapshot and version, not a silent rerun of today's code.

v2.43 identities/audits remain authoritative. v2.44 Fact values/mappings and
Finding significance remain frozen; use additive slot-context bindings first.
v2.45 graph, v2.46 hypotheses and v2.47 Stories must not auto-promote or relax their
existing comparability rules. Future consumers opt in after separate qualification.
No diagnostic numerical calculation change is authorised by this investigation.

The existing BIQ checkpoint remains unchanged and valid as a conservative refusal
boundary. It should eventually consume authoritative contexts, replacing its
UNKNOWN placeholders where proven. RetainedSource remains provenance inspection,
not a competing context authority. Existing BIQ version remains readable; improved
calendar/same-snapshot/stock policies need a new version and new positive tests,
not edits that retroactively qualify old assessments. Durable context/audit history
must not be confused with current content-hash-only assessment identity.

## 12. Bridge implications after the proposed change

These are conditional capabilities, not upgrades to current feasibility.

| Bridge | Expected legitimate scope after context preservation | Still missing |
|---|---|---|
| Revenue | Level-1 accounting revenue movement with residual, or qualified captured commercial revenue pair | Existing canonical route covers commercial Signals, not generic FIN_REVENUE; explicit scoped input binding needed; price/volume/mix needs richer evidence |
| Margin/profit | Exact accounting GP/EBITDA movement OR exact Contribution 0 movement, never conflated | Context cannot invent cost/price/mix causes; new Level-1 input path must preserve metric identity |
| Working capital | AR + inventory - AP movement from paired Level-1 balance sheets; cash-sign projection explicitly distinct | Like-for-like classification, coverage, N/A inventory and other-component policy; no claim of total operating cash from stock movement alone |
| Profit-to-cash | Potentially a bounded residual reconciliation only when an actual compatible profit and operating-cash measure exists | Current cash stock is not operating cash flow; tax/capex/financing/non-cash distinctions and matching coverage still needed |
| Cost-to-output | Possible cost-versus-qualified-output comparison with aligned definitions, not automatic from context alone | Choice/qualification of output proxy and cost composition; no assumed productivity or waste |

Revenue, exact margin/profit and bounded working-capital movement are reasonable
first targets using ordinary Level-1 evidence. Context preservation alone does
not implement those Bridges. Profit-to-cash and cost/output remain conditional.
The three deferred Stories and pricing/cost/mix Hypotheses remain unchanged; no
prerequisite is declared satisfied just because a context model is proposed.

## 13. Exact proposed next implementation scope (requires approval)

1. Approve B/E authority and define immutable per-measurement/per-slot context and
   bindings, including source declaration versus derivation versus unknown.
2. Define minimal Level-1 intake metadata for explicit period/as-of, calendar,
   currency/scale, metric/sign basis, bounded coverage and source vintage; retain
   original workbook/cell-to-derived-row provenance. Do not demand transaction
   detail for accounting totals or add invented defaults.
3. Preserve context for two representative statement periods: financial revenue,
   explicit GP/EBITDA, AR/inventory/AP and cash; retain producer-owned context for
   commercial C0 without changing its arithmetic. Qualify that context against
   source before attaching it to an existing value.
   If an existing aggregate cannot be reproduced under the asserted source basis,
   refuse the binding; do not silently repair the old amount or relabel its period.
4. Reuse source_revision through explicit dataset/measurement bindings; support
   same-snapshot comparisons without claiming unknown original status. Retain
   cross-vintage unknown/refusal where compatibility is unproven.
5. Add forward schema and controlled backfill, tenant/run/slot checks, immutable
   history/audits, precision and source-snapshot tests. Verify explicit monthly,
   annual, YTD and stock semantics; missing metadata must still refuse.
6. Add a new BIQ policy version consuming qualified context; test calendar periods
   of different day counts without automatic normalisation, correct stock handling,
   partial captured scope, source revisions and no downstream promotions.
7. Reassess all five families with real retained/declared evidence. Only then
   seek/execute the authorised Bridge calculation scope. No v2.49, causal mechanism,
   new diagnostic or silent canonical/legacy consumer cutover.

Do not implement generic Level-1 Fact conversion as an unnoticed side effect:
if a new source-to-canonical measurement path is needed, explicitly qualify its
typed binding while leaving frozen Signal-to-Fact mappings unchanged. The context
model must not become a new financial value store.

## 14. Investigation-only change record

Only this document was created. The seven accepted uncommitted checkpoint files
were hash-checked before and after investigation and remain byte-for-byte unchanged. No expensive
regression, schema migration, source repair, live query, commit or push was done.
Prior 522/513/0/0/9 results belong to the accepted checkpoint, not a new run.
git diff --check and a separate whitespace check of this untracked document passed.

# v2.48B — Blind Economic Bridge qualification

Baseline: `main` / `60399bfc006de945f74cfbb2e4ed8435b2856315`, pulled from
`origin/main` with a clean tree. The earlier Measurement Context/BIQ checkpoint
remains the foundation, not a retroactively completed Economic Bridges release.
No private answer key was requested, searched for or consulted. The source was
not repaired, recalculated or overwritten.

## Independent intake evidence

Source: `Golden_Manufacturing_v2.48_Blind.xlsx`, SHA-256
`5a3a627c465f15f6bef34eeb339cf0aabb3c037059e5d07e73b8af63adf89af2`.
Its README explicitly describes synthetic records. External/blind therefore
describes how qualification evidence was supplied; it does not mean real-SME data.

Seven sheets: README; Management PL; Balance Sheet; Customer Product; Versions;
Cash and Output; Context. Management PL and Balance Sheet each contain 24 monthly
records for 2025/2026. Customer Product contains 120 rows (five customer/product
keys over 24 months). Versions has 26 revenue releases, including two superseded
records and 24 canonical releases. The Context registry provides five measurement
contexts and a separate design record. Workbook text is source documentation,
not authority to issue agent instructions.

Context explicitly declares whole-pound GBP, monthly accrual accounting flows,
consistent accounting basis and complete legal-entity accounting coverage.
Contribution 0 is revenue less costs before C0; it is not gross profit. Balance
sheet measurements are month-end stocks. Selected customer/product detail is a
nonrandom partial population aligned to restated accounts. A/B units are only
comparable within SKU; other quantity fields are absent. Cash classification is
partial/unclassified; operating cash is absent. Production output is only Product
B good units completed in July–December 2026, without comparable 2025 coverage.

Initial inspection preceded Bridge calculations. The frozen workbook adapter did
not recognise this layout. A bounded, versioned source adapter was therefore
qualified before synthesis. Initial real-store context/BIQ checks qualified
revenue, exact Contribution 0 and stock endpoints. Full synthesis subsequently
checks every required monthly pair and all three working-capital stock pairs.

## Source binding and preserved semantics

`DECLARED_ACCOUNTING_PACK_1` is an opt-in, strict layout/declaration contract.
It does not infer arbitrary prose semantics, missing periods, currency scales or
population completeness. Unknown definitions, duplicate source/version keys,
unmatched source/release IDs, incomplete period sets, missing selected-panel rows,
broken supersession or unsupported authoritative formulas refuse capture.

OOXML numeric lexemes become Decimal directly. Authoritative revenue/C0 and
AR/inventory/AP source cells are used. Detail C0 multiplication formulas are
independently checked against their cached numeric values using Decimal; no
general Excel calculation engine or reliance on unverified cached profit/cash
reconciliations is introduced. Other workbook formulas are outside this reader's
qualified calculation scope.

The adapter reuses immutable source files, dataset versions, accounting ingestion,
financial statement records, existing source revisions and MeasurementContextService.
It retains original workbook hashes and cell references. The supplied workbook is
also an unchanged repository fixture so CI does not depend on a Downloads path.

Accounting records cannot contain repeated company line codes per period. The
selected customer/product values are therefore retained as explicitly partial
monthly subtotals, with every contributing source cell retained. Their dedicated
`SELECTED_REVENUE` and `SELECTED_CONTRIBUTION_0` codes/names are not legacy company
revenue/GP aliases. They do not enter frozen diagnostic totals as duplicate company
transactions. Plain `CONTRIBUTION_0` remains a distinct exact measure.

This produces 168 context-bound values: 48 company monthly flows, 48 partial
selected-population monthly flows and 72 AR/inventory/AP stocks. Per-slot entity,
period, scope, coverage and version semantics survive. No canonical Fact/Finding
writer is switched or required to manufacture a new Signal.

Existing CMC structures and authority remain intact. The source resolver gains
only explicit new measure labels and declared entity fields. BIQ-2.48.2 keeps its
original policy; new BIQ-2.48B.1 adds exact Contribution 0 amounts for this Bridge
contract using the same comparison checks. BIQ consumes contexts and cannot
override their declarations.

## Governed Bridge contracts (EB-2.48B.1)

All monetary results are GBP Decimal, using a fixed £0.01 reconciliation tolerance.
Residual is calculated exactly; it is not rounded away or allocated to a cause.
Every implemented Bridge satisfies opening + supported components + residual =
closing. The input service rechecks current context bindings and original source
pack membership, value, scope, coverage and active source vintage. No caller can
submit calculated amounts to the persistence writer.

| Family | Endpoint/comparability contract | Components and residual |
|---|---|---|
| REVENUE_BRIDGE | Two complete consecutive calendar years, twelve unique monthly financial-revenue flows each, complete entity coverage, common current source snapshot and accounting basis | Optional observed selected-population revenue change; partial detail never extrapolated. All unexplained movement remains residual. |
| MARGIN_OR_PROFIT_BRIDGE | Same annual contract, exact Contribution 0 GBP only | Optional selected-population Contribution 0 change. No GP substitution, margin-percentage subtraction, cost/price/mix inference or allocation of residual. |
| WORKING_CAPITAL_BRIDGE | December year-end AR/inventory/AP stock bundles, common source definitions, complete entity coverage and comparable current snapshot | Net trade WC = AR + inventory − AP. Components are signed stock changes. Cash-direction projection is the inverse of each stock contribution. It is not operating cash flow. |
| PROFIT_TO_CASH_BRIDGE | No qualified contract from this source | Refused: classified operating cash, timing and noncash reconciliation unavailable. |
| COST_TO_OUTPUT_BRIDGE | No qualified contract from this source | Refused: output period, population and measure are not comparable with company costs. |

Missing endpoint periods/components required by a stock bundle, wrong metrics,
duplicate bindings, partial company endpoints, changed source or incomparable
context refuse a Bridge. Missing optional attribution on otherwise qualified flow
endpoints instead yields an empty component set and the whole movement as residual.
There is no generic family fallback or universal financial-impact object.

This release qualifies selected-population movement as a component, not a detailed
price/volume/mix or customer-causality decomposition. Compatible A/B quantities in
the source remain evidence for later separately governed decomposition. They are
not silently promoted to supported economic mechanisms.

## Blind results and reconciliation

| Bridge | Opening | Supported components | Explicit residual | Closing |
|---|---:|---:|---:|---:|
| Revenue, FY2025 → FY2026 | £12,000,000 | Selected population +£1,725,000 | **−£225,000** | £13,500,000 |
| Contribution 0, FY2025 → FY2026 | £3,600,000 | Selected population +£200,750 | **−£88,250** | £3,712,500 |
| Net trade WC, Dec 2025 → Dec 2026 | £1,650,000 | AR +£550,000; inventory +£350,000; AP −£200,000 | £0 | £2,350,000 |

All three reconcile exactly (difference £0, within £0.01). The WC cash-direction
projections are AR −£550,000, inventory −£350,000 and AP +£200,000, net −£700,000.
That projection is not a measured cash flow or a full profit-to-cash reconciliation.

Selected revenue is £9,750,000 in 2025 and £11,475,000 in 2026: 81.25% and 85% of
the respective accounting revenue amounts. These are observed amount shares,
not sampling weights or a complete-population certificate. Selected Contribution
0 is £3,067,500 and £3,268,250. No amount is extrapolated. Residuals retain movement
outside the implemented component explanation; no unsupported WHY is assigned.

March 2026 revenue v1 £1,117,000 is superseded by v2 £1,067,000. April v1 £1,003,000
is superseded by v2 £1,053,000. The −£50,000/+£50,000 corrections net to zero over
the year. Management PL already matches both canonical v2 records. Version history
is never appended as extra transactions or Bridge movement.

The existing source_revision architecture records the imported canonical snapshot
and its retained superseded history; CMC revision state is snapshot-level. Exact
monthly release identities remain traceable through the original version table
and checked P&L source IDs. A later corrected source obtains new immutable
bindings/history. Older Bridge snapshots remain readable but superseded source
vintages refuse current qualification.

## Persistence, scope and transactions

Forward migration `0010_economic_bridge` follows checkpoint `0009_measurement_context`.
Historical migrations are unchanged. Three tables are additive:

* `canonical_bridge_snapshot`: deterministic snapshot ID, client/run, stable
  family/metric/period series ID, revision, predecessor and typed Decimal-safe document.
* `canonical_bridge_input`: client-scoped FKs to existing context bindings, with
  explicit opening/closing/component roles. WC components reuse their endpoint
  references rather than duplicating evidence.
* `canonical_bridge_audit`: actor, timestamp and creation/supersession state.

BridgeService recalculates through governed inputs before writing. Identical
replays do not add history/audits. Changed evidence requires the explicit current
predecessor; uniqueness prevents competing revisions. Cross-client and missing
references are database FK violations. Run/client agreement is enforced by the
existing context/foundation service. Legacy references are resolved in their
owning SQLite store, not represented as impossible cross-database FKs.

The caller owns the canonical transaction; rollback removes the Bridge, input
references and audit together. Source ingestion/revision registration retains its
existing SQLite commit ownership. This is not a distributed transaction. Historical
reads preserve their snapshot; current reads requalify pinned evidence. No existing
EconomicEffect is supplied by this source, so none is invented merely to populate
a link. Existing source/context lineage remains the evidence authority.

Clean creation and a frozen independent checkpoint fixture are tested. All values
in all 33 pre-Bridge tables survive upgrade/downgrade/re-upgrade. Downgrade to 0009
intentionally removes Bridge snapshots, input references and Bridge audits only.

## Qualification record

Initial 29-test run: 28 PASS, 1 FAIL, 0 ERROR. The failure was in the new temporary
workbook mutation helper (shared-string index versus text), not a changed financial
assertion. Correcting the helper preserved the refusal assertion. The expanded
82-test run passed before the final two source-identity tests were added.

Final local qualification on Windows 10 / Python 3.12.14:

| Run | Discovered/run | PASS | FAIL | ERROR | SKIP |
|---|---:|---:|---:|---:|---:|
| Final Bridge, migration, CMC and original BIQ focused suite | 84 | 84 | 0 | 0 | 0 |
| Migration rerun after whitespace-only preserved-fixture cleanup | 3 | 3 | 0 | 0 | 0 |
| Authoritative compatibility-entry-point full estate | 583 | 574 | 0 | 0 | 9 |
| Initial live PostgreSQL suite | 47 | 46 | 0 | 1 | 0 |
| Focused live source-identity/version/restatement rerun | 3 | 3 | 0 | 0 | 0 |

| Earlier complete live run (stopped on error) | 267 discovered / 219 run | 218 | 0 | 1 | 0 |
| Final uninterrupted complete live qualification | 267 | 267 | 0 | 0 | 0 |

The live environment was PostgreSQL 18.6 on aarch64 Linux. Two earlier runs
encountered `psycopg.OperationalError: server closed the connection unexpectedly`.
Read-only investigation found Windows host sleep followed by Neon compute suspension
in both incident windows. This supports an infrastructure/lifetime explanation;
no product correction or retry was introduced. After the host was configured to
remain awake, the unchanged complete suite passed once, uninterrupted and fail-fast:
**267 discovered, 267 run, 267 PASS, 0 FAIL, 0 ERROR, 0 SKIP** (3298.75 seconds).

Final cleanup recorded **zero open connections, zero checked-out connections**
and no unraisable resource errors. The complete run included the unchanged v2.41
live gate, inherited v2.43–v2.47 qualification, CMC, BIQ, migration 0010, frozen
checkpoint preservation/downgrade/re-upgrade, and all Bridge persistence/refusal,
precision, revision, scope and transaction checks. No implementation or test changes
were required for the final pass. Earlier interrupted results remain historical
failures, not converted passes. Local result JSON/logs remain excluded from source.

The full estate ran through `scripts_run_full_regression.py`; inventory/discovery
matched and policy_errors was empty. Its nine skips are exactly the existing live
tests, which passed separately on real PostgreSQL. No skip is counted as a pass.
Source/tests and the qualification script compile. DeprecationWarning and
ResourceWarning are errors; the authoritative runners also check unraisable
resource errors. Strict warning policy and the v2.42 runner/workflow are unchanged.
The live script requires explicit branch/host opt-in and only the verified
`v2-41-qualification` branch in Neon project `tiny-meadow-46991842`; primary/default
is never a database target. Credentials remain process-only. The unchanged v2.41
live gate remains included.

## Compatibility and remaining boundaries

The 56 diagnostics, Signal calculations, v2.43–v2.47 canonical reasoning,
economic/Opportunity, management, benefit and product/API writers remain unchanged.
Existing assertion edits advance only expected Alembic head to 0010. There is no
automatic downstream promotion, new diagnostic, general Evidence Graph change,
LLM call, recommendation, Action Plan or v2.49 implementation.

LOW_QUALITY_GROWTH now has comparable accounting revenue/C0 movement available as
potential future evidence, but its Story contract must separately qualify that
measure and meaning; no Story was created. PROFIT_TO_CASH_DISCONNECT remains
blocked. COST_GROWTH_OUTPACING_ECONOMIC_OUTPUT remains blocked. A/B sold-unit/price
evidence may support a future bounded mechanical decomposition, but no v2.46
pricing/cost/mix hypothesis has been reassessed or promoted here.

v2.49 could consume the three typed, qualified Bridge outputs after architectural
approval, preserving partial coverage, residuals and cash-stock limitations. It
cannot consume the two refused families or assume causal attribution. Cross-platform
CI remains a separate release-freeze gate, not a claimed pass in this record.

## File inventory

| File | Change / purpose |
|---|---|
| `profit_doctor/intake/declared_accounting.py` | New bounded source reader and existing-store/context capture adapter. |
| `profit_doctor/reasoning/measurement/source.py` | Explicit C0/selected-population labels and declared entity fields. |
| `profit_doctor/reasoning/bridge/context_qualification.py` | Additive versioned C0 BIQ entry point; original policy preserved. |
| `profit_doctor/reasoning/bridge/contracts.py` | Typed, Decimal-safe Bridge/component/refusal contracts. |
| `profit_doctor/reasoning/bridge/engine.py` | Governed inputs, source revalidation and three deterministic reconciliations. |
| `profit_doctor/reasoning/bridge/service.py` | Replay, history, audit and caller-owned persistence. |
| `profit_doctor/persistence/bridge_schema.py` | Three additive persistence tables and scope FKs. |
| `profit_doctor/persistence/__init__.py` | Register new schema with existing metadata. |
| `alembic/versions/0010_economic_bridge.py` | Forward upgrade and Bridge-only downgrade. |
| `tests/fixtures/v248_checkpoint_schema.sql` | Independent preserved 0009 schema; trailing whitespace normalised only. |
| `tests/fixtures/bridge_v248/Golden_Manufacturing_v2.48_Blind.xlsx` | Byte-identical supplied source, intentionally retained for repeatable CI. |
| `tests/fixtures/bridge_v248/README.md` | Fixture provenance, hash and blind/synthetic boundaries. |
| `tests/test_economic_bridge_v248b.py` | 33 source, arithmetic, refusal, history, scope and persistence tests. |
| `tests/test_economic_bridge_migrations_v248b.py` | Three clean-schema, preservation/rollback and migration-independence tests. |
| `tests/test_canonical_migrations_v244.py` | Expected head advancement only. |
| `tests/test_graph_migrations_v245.py` | Expected head advancement only. |
| `tests/test_hypothesis_migrations_v246.py` | Expected head advancement only. |
| `tests/test_story_migrations_v247.py` | Expected head advancement only. |
| `tests/test_measurement_context_migrations_v248.py` | Expected head advancement only. |
| `scripts/qualify_economic_bridge_postgresql_v248b.py` | Explicit disposable-branch live migration/persistence qualification. |
| `qualification/test_estate_v242.json` | Register both new modules and their discovered test counts. |
| `docs/V2_48B_BLIND_ECONOMIC_BRIDGES.md` | This architecture, evidence and qualification record. |

Reports, logs and temporary inspection scripts stay under ignored `.venv/` and
are not source deliverables. The workbook and preserved schema are intentional
qualification fixtures, not incidental generated output.

Final review: 22 intended files (9 modified, 13 new); no credentials, connection
strings, unrelated edits or incidental generated artefacts among them. Historical
migrations and existing live qualification/CI files are unchanged. Existing test
assertions change only the expected migration head. `git diff --check` and separate
untracked-file whitespace checks pass. The source workbook hash still matches the
retained fixture. Local reports remain excluded. Architectural, blind-dataset and
live PostgreSQL review is approved. Formal freeze still requires all four
Ubuntu/Windows × Python 3.12/3.13 CI jobs to pass.

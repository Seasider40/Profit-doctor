# Profit Doctor

## Current baseline: v2.40 / v2.41 qualification

Profit Doctor is an SME financial and commercial diagnostic/advisory engine. The locked
diagnostic estate contains 56 diagnostics. v2.41 is the live PostgreSQL qualification gate.

The GitHub Actions workflow at `.github/workflows/v241-postgresql-qualification.yml` is designed
to run only against a disposable/dedicated PostgreSQL qualification database. See
`docs/V2_41_POSTGRESQL_QUALIFICATION.md`.

**Never commit database credentials, connection strings, client data, or `.env` files.**

---

# Profit Doctor Engine v2.32

## v2.31 Opportunity Economics & Overlap Qualification
Adds economic-bucket portfolio reporting, overlap/exclusivity controls, shared recovery envelopes and explicit non-additive profit-to-cash manifestation. See `docs/OPPORTUNITY_ECONOMICS_OVERLAP_V2_29.md`.

# Profit Doctor Engine v0.2 — Foundation Hardened

Engineering Gate 1 remediation build. This remains an executable local harness, not the frozen v1.2 UI prototype and not yet the production deployment stack.

## What changed from v0.1
- Client-safe generated canonical IDs; source keys are no longer global primary keys.
- Financial values are preserved and calculated with Python `Decimal` rather than binary float.
- Correct semantic split: transaction-derived `COMMERCIAL_NET_REVENUE` and `ECON_CONTRIBUTION_0`; accounting `FIN_REVENUE` / `FIN_GROSS_PROFIT` are intentionally **not** fabricated from sales transactions.
- Source files are copied into hash-addressed, read-only controlled storage and verified by SHA-256.
- `SOURCE_FILE`, logical `DATASET`, `DATASET_VERSION`, and `INGESTION_JOB` are separated.
- Silent `INSERT OR REPLACE` on financial transactions is removed.
- Ingestion is atomic: validation failure rolls back canonical rows and records a failed ingestion job.
- Engine-run linkage is carried through ingestion and audit events.
- Primitive calculations are client + dataset-version scoped.
- Lineage points to the exact dataset version plus a reproducible scope definition.
- Structural CSV validation and duplicate-transaction detection are implemented.
- Regression tests cover known Northstar answers, client isolation, exact decimal arithmetic, lineage, immutable evidence, idempotent reprocessing, rollback, zero-revenue semantics, and restatement/version preservation.

## Run
```bash
python -m profit_doctor.cli \
  --input /mnt/data/profit_doctor_v1_2 \
  --db profit_doctor.db \
  --storage .profit_doctor_source_store

python -m unittest discover -s tests -v
```

## Important boundary
SQLite remains the local engineering harness. The production target remains PostgreSQL + Python/FastAPI/SQLAlchemy. SQLite stores decimal values as text in this harness so the engine never relies on SQLite binary floating-point arithmetic for financial amounts.

## Engineering Gate 1
Sprint 2 (Trust Layer) should begin only after this suite passes and the known Northstar financial assertions reconcile exactly.

## v0.3 — Sprint 2 Trust Layer
The engine now evaluates evidence before allowing diagnostics to run. It persists availability for all 18 canonical data domains, performs sales-transaction quality/mapping/integrity checks, and resolves test-specific eligibility. Deliberately damaged Northstar cases demonstrate graceful degradation to PARTIAL-A/B/C rather than false precision.

See `docs/SPRINT_2_TRUST_LAYER.md`.

## v0.4 — Sprint 2 Level 1 Accounting Trust
The Trust Layer now extends into D01–D06: P&L, Balance Sheet, Trial Balance, AR, AP and Bank. Canonical accounting import contracts are executable, domain-specific integrity checks are persisted, and test eligibility refuses/degrades analysis when required accounting evidence is missing or constrained.

Regression suite: **19/19 passing**. See `docs/SPRINT_2_LEVEL1_ACCOUNTING.md`.

## v0.7 — Sprint 3 Primitive Engine, first vertical slice
Sprint 3 is now executable. A versioned primitive/method/dependency registry has been added together with deterministic primitive execution and explicit refusal semantics.

Implemented in this slice:
- Commercial Net Revenue, Commercial Direct Cost, Contribution 0 and Contribution 0 Margin.
- Financial Revenue, Financial Gross Profit and EBITDA from explicitly mapped P&L lines when available.
- Balance Sheet AR, AP and Cash plus latest bank closing cash.
- DSO using closing AR / accounting revenue × period days when both facts exist.
- DPO deliberately remains UNAVAILABLE until an accounting direct-cost primitive is evidenced; the engine will not use revenue as a convenient proxy.
- Customer Revenue, Customer Contribution 0 and comparable-period Customer Revenue Growth.
- Primitive methods and dependencies persisted in the database.
- Primitive executions distinguish VALID, NOT_MEANINGFUL and UNAVAILABLE.
- Calculation lineage persists back to dataset versions or dependent primitives.

Northstar deterministic results remain £14,047,932.56 commercial revenue, £9,110,927.70 direct cost and £4,937,004.86 Contribution 0, with 75 customer roll-ups reconciling exactly to total revenue.

Regression suite: **26/26 passing**. The test run currently emits non-failing ResourceWarnings from some older test fixtures/connections; these are technical hygiene items to clean up and do not change financial results.

Sprint 3 is **IN PROGRESS**, not closed. Next slices should add robust accounting direct-cost derivation, AR/AP ledger primitives, cash/liquidity, DPO/CCC, customer growth/cadence primitives and then expand the dependency graph before diagnostics consume these facts.


## v0.7 milestone
Inventory/D12 support now unlocks DIO and genuine CCC where evidence is period-compatible. Engineering Gate 2 reviewed the Primitive Engine boundary and fixed a period-mismatch risk in DSO/DPO before diagnostics are allowed to depend on these facts. Regression suite: **35/35 passing**.

## v0.8 — Sprint 4 First Diagnostic Engine
Adds the first nine deterministic diagnostics (REV-01/02/03, GM-01/02, CUS-01/04, WC-01/02), persistent test execution and signal objects, diagnostic lineage, comparable-period revenue/margin/customer analysis, concentration evidence, and primitive-based working-capital diagnostics. Signals remain separate from interpretations/findings/opportunities.

## v0.9 — Sprint 5 FD Reasoning Engine

The engine now implements the first evidence-bound reasoning chain: Signal → Context/Suppression → Persistence → Evidence Bundle → Fact → Interpretation → Finding Candidate → Finding → FD Review Queue. Context suppresses escalation without deleting evidence; informational signals are retained without automatically becoming findings; interpretations avoid unsupported causal/opportunity claims; and every material finding requires FD review. Sprint 5 deliberately keeps opportunity economics out of the reasoning layer.

## v1.0 — Sprint 5 Reasoning Hardening

Sprint 5 has now passed its pre-economic hardening gate. The reasoning layer adds finding clustering, contradictory-evidence handling, longitudinal finding identity and a management-attention budget while preserving every underlying signal. Recurring issues now create new versions of the same finding instead of duplicate findings. Contradictory evidence holds the candidate for review and weakens confidence rather than being silently resolved. The default primary FD-review budget is seven findings per run; valid deferred findings remain stored and reviewable.

Regression suite: **53/53 passing**.

Next planned layer: Sprint 6 Economic Engine — Economic Story, Impact, Exposure, Opportunity Candidate, Recovery Envelope, overlap/compatibility and Opportunity. No opportunity economics have been introduced in v1.0.

## v1.1 — Sprint 6 Economic Resolution & Opportunity Engine
Adds Economic Story, Impact, Exposure, Baseline, Recovery Envelope, Opportunity Candidate, supported Opportunity qualification and relationship-aware portfolio economics. The engine now enforces Theoretical → Addressable → Expected and refuses to convert a finding directly into a financial opportunity. Overlapping and mutually-exclusive opportunities are adjusted rather than blindly added. Full regression suite: 62 tests passing.

## v1.2 — Sprint 7 Management, Action & Benefit Engine
Adds the first longitudinal management/value chain: supported Opportunity → Decision → Action → Progress → Benefit Event → Benefit Leg → Observation → Verification → Retention. Benefit economics are net of implementation/ongoing/adverse costs; action completion does not itself prove benefit; uncertain attribution cannot be promoted to verified benefit; realised value does not overwrite the original expected opportunity; and cash manifestation of the same profit is explicitly non-additive. Regression suite expanded with management/value adversarial tests.

## v1.3 — Engineering Gate 3 Remediation

Adds cross-source financial reconciliations, business-model inventory applicability, revenue cadence/type semantics, and a formal mechanism-evidence route for opportunity qualification. See `docs/ENGINEERING_GATE_3_REMEDIATION.md`.

The three-business review deliberately exposed a remaining boundary: workforce/payroll/commission (D11) is not yet analytically implemented and is not claimed by this version.

## v1.4 — Revenue & Growth module expansion
- Completes the executable Revenue & Growth diagnostic registry: REV-01 through REV-06.
- Adds REV-04 Price / Volume / Mix with an explicit residual so the bridge reconciles exactly and non-comparable/new/lost product economics are never silently labelled as price or volume.
- Adds REV-05 month-of-year seasonality indices and peak/trough spread. Seasonality is descriptive and never asserted as causality.
- Adds REV-06 monthly revenue volatility (coefficient of variation) and optional recurring-revenue mix enrichment when revenue semantics mapping is sufficiently complete.
- Recurring mix is withheld when >5% of revenue semantics are unmapped; recurring revenue is never treated as a forecast guarantee.
- Trust eligibility now covers REV-04/05/06 with product mapping required for full PVM.
- Adds five adversarial/regression tests for module completeness, PVM reconciliation, causal restraint, forecast restraint and semantic-mapping refusal.
- 78 tests are collected. All test files pass independently. The known combined-suite SQLite/file-handle shutdown stall remains engineering hygiene debt and is not represented as a clean single-process 78/78 run.

## v1.5 — Gross Margin & Leakage Expansion
Completed the executable Gross Margin module GM-01 through GM-07: trend, variance bridge, customer margin variance, product/service margin variance, margin leakage signals, purchase-cost inflation recovery, and negative/abnormal transaction margins. The module preserves the distinction between historical impact and supported opportunity, caps evidenced price recovery at comparable cost pressure, and treats transaction anomalies as investigation signals rather than automatic errors or savings.

Added five margin-expansion regression tests. Total collected suite is now 83 tests. All test files pass independently; the known legacy combined-process SQLite/file-handle shutdown stall remains engineering hygiene debt and is not represented as a clean single-process 83/83 run.

## v1.6 — Customer Economics Expansion
Completes the executable Customer Economics diagnostic module CUS-01 through CUS-07.

New executable capabilities:
- CUS-02 Customer Profitability: revenue, Contribution 0 and margin retained separately by customer.
- CUS-03 Contribution after Cost-to-Serve: uses evidenced transaction CTS only; refuses invented allocations when CTS is absent.
- CUS-05 Retention / Churn / Reactivation: separates retained, lost, reactivated and genuinely-new observed customer revenue; explicitly distinguishes observed revenue retention from contractual GRR.
- CUS-06 Payment Behaviour & Cash Quality: links AR ageing snapshot evidence to customer entities where mappings exist; refuses to infer historical payment speed, collectability or cause from a snapshot.
- CUS-07 Pareto & Economic Distribution: contribution-based customer distribution and 80% economic head, retained as descriptive evidence rather than an automatic customer-exit recommendation.

Existing CUS-01 concentration now explicitly states concentration exposure is not loss probability. CUS-04 movement now explicitly avoids causal overclaiming.

Seven new customer-expansion adversarial tests pass. The known legacy combined-run SQLite/file-handle shutdown issue remains unresolved; no clean all-suite single-process pass is claimed for v1.6.

## v1.7 — Product Economics Expansion

Adds the complete executable Product Economics module:
- PROD-01 Product / Service Profitability
- PROD-02 Product / Service Mix
- PROD-03 Product / Service Growth & Decline
- PROD-04 Long-Tail & Complexity Economics
- PROD-05 Cross-Sell & Penetration

Key controls:
- Revenue scale is kept separate from Contribution 0 and margin economics.
- Mix movement is descriptive and does not claim cause or desirability.
- Product growth/decline does not automatically become an opportunity.
- Long-tail position is not an automatic product-exit recommendation.
- Cross-sell whitespace is based on observed customer-product relationships and meaningful peer adoption, but remains theoretical until need, addressability, commercial fit, capacity and economics are evidenced.
- No forecast revenue, probability or opportunity value is invented from whitespace.

Regression note: product expansion tests pass 6/6. Expansion exposed a legacy reasoning assertion that assumed every finding would enter the FD Review Queue; with the previously implemented management-attention budget and the broader diagnostic estate, findings can legitimately exceed the seven-item queue. The regression assertion was corrected to the architectural contract: queue <= 7, queue <= findings, and every queued object must resolve to a real finding. Reasoning tests then pass 11/11. Existing SQLite resource warnings remain visible engineering hygiene debt.

## v1.8 — Pricing Expansion

Executable Pricing module now covers PRI-01 through PRI-05: realised price movement, comparable price dispersion, transaction price-leakage signals, realised price-increase coverage, and pricing opportunity candidate synthesis.

Guardrails are deliberate: different price is not automatically leakage; below-reference price is not automatically an unauthorised discount or recoverable saving; campaign effectiveness is withheld without D14 pricing-history/discount/rebate evidence; pricing candidates are not promoted to addressable or expected opportunity without commercial mechanism evidence.

Six dedicated pricing adversarial tests pass. Existing module test files exercised during this build continue to pass independently. The known legacy combined-process SQLite/file-handle shutdown/resource-warning debt remains visible and is not represented as a clean whole-suite single-process pass.

## v1.9 — People & Productivity Expansion
Adds executable PEO-01..PEO-05, D11 workforce snapshots, commission-plan structure, fully loaded people cost, output-per-FTE, department workforce economics, practical capacity/utilisation and workforce optimisation candidates. Critical rule: time/capacity released is not a financial saving until an evidenced economic use occurs. Dedicated People suite: 5/5 passing. Existing combined-run resource/shutdown warnings remain known debt.

## v2.0 — Suppliers & Overheads Expansion
Adds executable SUP-01..SUP-06 plus supplier master, purchase transaction and overhead transaction evidence structures. Covers supplier spend intelligence, like-for-like purchase-price variance, concentration/dependency, overhead drift, duplicate-looking forensic cases and supplier/overhead opportunity candidates.

Guardrails: high spend is not overspend; purchase-price movement does not prove supplier causality or recoverability; dependency does not create invented disruption probability/expected loss; overhead growth is not automatically waste; duplicate-looking transactions are not automatically duplicate payments; opportunity candidates remain unquantified until mechanism, constraints, addressability and recovery basis are evidenced.

Dedicated supplier/overhead adversarial suite: 7/7 passing. Broader module regression was exercised and continued passing until the previously documented legacy SQLite resource/shutdown issue caused the combined process to stall; this debt remains visible and is not represented as a clean whole-suite pass.

## v2.1 — Working Capital & Cash Expansion

Completes the executable Working Capital & Cash module: WC-01 through WC-07.

New executable diagnostics cover payables/payment performance, inventory economics, available cash/liquidity boundaries, working-capital release candidates, and cash optimisation synthesis. Guardrails are explicit: cash release is not profit; collection of recognised revenue is not new profit; inventory balance is not automatically releasable cash; supplier stretch is not free financing; available cash is not available liquidity without documented facility headroom; and expected release/timing remain unquantified until mechanism and operational guardrails are evidenced.

Dedicated adversarial Working Capital suite: 6/6 passing. Relevant existing diagnostic + primitive tests also pass; the legacy resource warnings remain visible. Two names supplied to a targeted unittest command (`test_primitive_engine_v06` and `test_primitive_engine_v07`) do not exist as modules in this package; this is a command-selection error, not an engine test failure.

## v2.3 — Forecasting & Performance Management Expansion

Adds the complete FCST-01..FCST-04 diagnostic registry and executable forecasting layer.

- FCST-01 preserves explicit plan versions and compares plan vs actual while refusing to treat variance as explanation.
- FCST-02 stores forecast vintages and measures signed error / MAE while refusing to convert historical accuracy into future certainty.
- FCST-03 introduces structured KPI observations and driver classes; association does not prove causality.
- FCST-04 produces transparent scenario sensitivities from explicit assumptions and labels them decision tools, not predictions/probabilities.
- Adds plan_version, plan_line, actual_metric, forecast_vintage and kpi_observation persistence.
- Dedicated forecasting adversarial suite: 6/6 passing.

The locked diagnostic estate is now 52/56 executable by specification (Revenue 6, Margin 7, Customer 7, Product 5, Pricing 5, People 5, Supplier/Overheads 6, Working Capital 7, Forecasting 4). Financial Risk & Controls (4) remains.

## v2.3 — Financial Risk & Controls / 56-of-56 milestone

The final locked diagnostic module is executable:
- RISK-01 Financial Integrity, Reconciliation & Accounting Control
- RISK-02 Transaction, Process & Control Exception Intelligence
- RISK-03 Financial Exposure, Resilience & Risk Intelligence
- RISK-04 Financial Risk, Control & Governance Optimisation

This brings the locked Master Test Registry to 56/56 executable diagnostic definitions. The new risk/control suite passes 7/7 adversarial tests. Profit Doctor does not claim audit assurance, infer fraud from anomalies, convert exposure into expected loss, or invent probabilities. Governance candidates use a minimum-effective-control principle.

Known engineering debt remains: the legacy combined/full regression process can stall with SQLite/file-handle ResourceWarnings. This milestone is therefore 56/56 diagnostic implementation, not a claim that the entire codebase has a clean one-process regression run.

## v2.4 — Engineering Gate 4 / portability hardening
- Full 56-test registry replayed across three synthetic SMEs through reasoning and economic-story creation.
- 134/134 regression tests pass when test modules are isolated.
- Test fixtures are now self-contained/package-relative; historical hard-coded `/mnt/data` dependencies removed.
- Four Gate-3 remediation tests are now visible to unittest discovery.
- Added `scripts/run_regression_gate.py` as a portable single-command isolated gate.
- **Known debt remains:** monolithic one-process execution can still stall due legacy SQLite/file-handle lifecycle issues. This is explicitly not marked resolved.
- See `docs/ENGINEERING_GATE_4_FULL_E2E.md` and scenario JSON.

## v2.5 — Adversarial SME Data Gate
Added a dedicated adversarial trust/refusal suite covering malformed schema/date evidence, duplicate source identifiers, abnormal receivables, unbalanced TBs, cross-source AR/cash mismatches, missing-bank refusal and client isolation. Dedicated suite: 10/10 passing. The legacy SQLite/resource-lifecycle stall remains explicitly open; v2.5 does not claim a clean monolithic full-suite run. See `docs/ADVERSARIAL_SME_GATE_V2_5.md`.

## v2.6 — Pre-v1.0 Engineering Audit
A deep audit identified and fixed a material opportunity-qualification bypass: core qualification now requires persisted supported mechanism evidence, rather than trusting narrative evidence passed by the caller. Duplicate mechanism-evidence implementation was removed and regression coverage added.

The audit also confirms the SQLite connection/resource lifecycle issue remains a release blocker: isolated suites pass, but the complete suite is not yet deterministic in one process. See `docs/PRE_V1_ENGINEERING_AUDIT_V2_6.md`.

## v2.7 — Engineering Attack Pass
- Canonicalised the runtime SQLite connection path across all 14 schema groups.
- Added defensive cleanup for legacy SQLite test connections and fast schema bootstrap for ephemeral databases.
- Hardened symmetric opportunity relationships against reverse-duplicate insertion and double-counting.
- Added adversarial relationship-dedup regression coverage.
- Selected high-risk gate observed: 28/28 PASS (Economic + Adversarial SME + Risk/Controls).
- Full historical one-process regression is **not** claimed clean; persistence/session lifecycle remains a pre-v1.0 release blocker.
See `docs/ENGINEERING_ATTACK_V2_7.md`.

## v2.8 — Production Persistence Foundation
Production persistence foundation added using SQLAlchemy 2.x and Alembic, with PostgreSQL as the production target. Explicit session ownership, atomic rollback, FK enforcement, migration upgrade/downgrade tests, and database-level opportunity relationship uniqueness are now covered. The 56-diagnostic calculation engine remains behaviourally frozen behind the legacy SQLite adapter during staged migration. Live PostgreSQL verification remains an explicit release gate because this build environment does not provide a PostgreSQL server.

## v2.9 — Economic Backbone Persistence Migration
Migrates the central value chain to SQLAlchemy/Alembic in a strangler slice: primitive results, signals, findings, economic stories, impacts, exposures, opportunity candidates, opportunities, decisions, actions and benefit legs. Monetary values intentionally remain canonical decimal strings during equivalence migration so the persistence rewrite cannot introduce binary-float or rounding changes. Tenant-safe service commands validate run/client/story ownership before writes. Legacy sqlite diagnostic execution remains intact until each vertical has an equivalence gate. PostgreSQL remains the production target; live PostgreSQL integration remains an external release gate where no server is available.

## v2.10 — Revenue + Gross Margin diagnostic persistence migration
REV-01..06 and GM-01..07 are the first 13 diagnostics with an explicit SQLAlchemy/Alembic persisted diagnostic contract and lossless old-vs-new equivalence gate. See `docs/PERSISTENCE_MIGRATION_V2_10_REV_GM.md`.

## v2.11 — Customer, Product & Pricing persistence migration

Migrates the next 17 diagnostic contracts onto the SQLAlchemy persistence path while freezing legacy calculation behaviour:
- CUS-01..CUS-07
- PROD-01..PROD-05
- PRI-01..PRI-05

Acceptance controls:
- all 17 test-execution contracts migrate losslessly;
- signal economics and lineage are preserved exactly;
- selected customer contribution, retention/Pareto, product economics/whitespace and pricing outputs match legacy persistence exactly;
- pricing migration does not create supported addressable/expected opportunity value from pricing signals alone;
- cross-client migration attempts are rejected.

Dedicated v2.11 migration suite: 4/4 PASS.
Commercial diagnostic suites: Customer 7/7, Product 6/6, Pricing 6/6 PASS.
High-risk isolated regression: Economic Engine 11/11, Adversarial SME Gate 10/10, Risk & Controls 7/7 PASS.
A combined long-lived process again timed out after 28 completed tests when entering the legacy Economic Engine; isolated suites pass. This is retained as known legacy SQLite/resource-lifecycle debt and is not represented as a clean single-process regression pass.

Migration status: Economic backbone + REV 6 + GM 7 + CUS 7 + PROD 5 + PRI 5. Diagnostic modules migrated: 30/56.

## v2.12 — People + Suppliers Production-Persistence Migration

Migrated the next 11 diagnostic contracts through the SQLAlchemy persistence equivalence gate:
- PEO-01..PEO-05 People & Productivity
- SUP-01..SUP-06 Suppliers & Overheads

This takes diagnostic migration coverage to 41/56. Calculation logic remains frozen in the legacy reference engine during strangler migration; v2 persistence stores the same execution contract, signals and diagnostic lineage.

### v2.12 controls verified
- 11/11 execution contracts persisted losslessly.
- People and supplier/overhead signal economics match the legacy representation exactly.
- PEO-05 capacity remains HOURS and explicitly £0 financial benefit until an evidenced economic use exists.
- Commission-plan structure does not become ROI/effectiveness evidence.
- High supplier spend does not become overspend.
- PPV/cost inflation does not become recoverable opportunity automatically.
- Supplier dependency does not manufacture disruption probability or expected loss.
- Duplicate-looking spend remains an investigation candidate, not proof of duplicate payment.
- SUP-06 optimisation candidates remain unquantified without mechanism/addressability evidence.
- Cross-client migration attempts are rejected.

### Test evidence
- Dedicated v2.12 persistence migration: 4/4 PASS.
- People + Supplier modules + persistence batches 1–3: 25/25 PASS.
- Economic Engine + Adversarial SME Gate + Risk & Controls: 28/28 PASS.
- Live PostgreSQL integration remains a release gate; these migration equivalence tests use the SQLAlchemy SQLite test adapter.

## v2.13 — Working Capital & Cash persistence migration
WC-01 through WC-07 now pass the controlled legacy-to-SQLAlchemy persistence equivalence gate. This takes diagnostic migration to 48/56. Cash-release/profit/liquidity/inventory anti-overstatement guardrails are explicitly regression-tested. See `docs/WORKING_CAPITAL_PERSISTENCE_MIGRATION_V2_13.md`.

## v2.14 — Final Diagnostic Persistence Migration
- Migrates FCST-01..04 and RISK-01..04 through the controlled SQLAlchemy diagnostic persistence boundary.
- Completes the staged diagnostic migration: 56/56 canonical diagnostics now have an equivalence-tested production-persistence path.
- Preserves forecast/scenario guardrails and risk/control distinctions: variance is not explanation; scenario is not prediction/probability; integrity findings are not audit opinions; exceptions do not prove fraud/loss; exposure is not expected loss.
- Adds exact old-vs-new signal/economic equivalence, lineage/execution-contract equivalence and cross-client refusal tests for the final batch.
- Live PostgreSQL integration/concurrency remains a v1.0 qualification release gate; SQLite remains the local SQLAlchemy test adapter.

## v2.15 — v1.0 Qualification Programme hardening

The formal qualification programme found and fixed cross-run management/benefit integrity weaknesses and reverse symmetric benefit-relationship duplication. Targeted high-risk requalification passes 58/58. Production v1.0 remains conditional because the historical single-process regression still exposes legacy resource-lifecycle debt, live PostgreSQL integration is not yet tested in this environment, and real-SME validation remains outstanding. See `docs/V1_0_QUALIFICATION_REPORT.md`.

## v2.16 — Qualification Remediation
Development remains frozen. This build fixes the reproduced legacy SQLite/test resource-lifecycle warnings and passes a strict 37-test high-risk run with ResourceWarning treated as an error. Live PostgreSQL qualification and real-SME validation remain explicit release gates. See `docs/QUALIFICATION_REMEDIATION_V2_16.md`.

## v2.17 — PostgreSQL Qualification Harness
The v1.0 qualification programme now includes an executable PostgreSQL readiness gate. Static PostgreSQL dialect/DDL compatibility is tested locally; live tests activate only when `PROFIT_DOCTOR_POSTGRES_TEST_URL` is provided. Absence of a live PostgreSQL service is reported as an open release gate, never inferred from SQLite.

## v2.18 — Live PostgreSQL Qualification Gate
Adds a fail-closed live PostgreSQL qualification runner and seven database-specific attacks: Alembic head/schema equivalence, atomic commit/rollback, FK enforcement, a real concurrent uniqueness race, READ COMMITTED visibility, pool reconnect/reuse, and downgrade/re-upgrade. The runner refuses to report success without a real PostgreSQL URL. In this build environment no PostgreSQL service is available, so the live gate remains explicitly OPEN rather than being inferred from SQLite. See `docs/POSTGRESQL_LIVE_QUALIFICATION_V2_18.md`.

## v2.19 — Real SME Qualification Programme foundation
Introduces the controlled real-SME qualification protocol, 12-case business-model/data-maturity matrix, fail-closed release rules, blind FD comparison methodology and executable programme-contract tests. Synthetic qualification is explicitly not represented as real-company evidence.

## v2.20 Controlled 12-SME qualification execution
Executed all 12 controlled qualification cases end-to-end. Current verdict: CONDITIONAL PASS for harness readiness. See `docs/CONTROLLED_12_SME_EXECUTION_V2_20.md`. The execution deliberately records that Level-2/3 archetype source fidelity still needs bespoke domain packs before these cases can be described as fully realistic business-model simulations.

## v2.21 — Bespoke 12-Archetype Qualification
Twelve distinct SME archetypes were generated and executed end-to-end with business-model-specific transaction economics and planted ground truths. Technical execution: 12/12. Qualification verdict: CONDITIONAL PASS. See `qualification/BESPOKE_12_QUALIFICATION_V2_21.md`. A material L1 working-capital period-basis issue was identified during FD sense-checking and remains a v1.0 release blocker; new-customer detection and genuine Level-3 source-domain simulation remain remediation items.

## v2.22 — Qualification remediation
Fixed the controlled-archetype working-capital period-basis defect by aggregating monthly P&L flows to the same YTD basis used by day calculations. Added explicit new-customer revenue detection, corrected unit=1 deterioration qualification cases, added genuine L3 forecast/KPI evidence to advanced archetypes, and reran all 12. Result: 12/12 controlled archetypes PASS; 58/58 targeted high-risk regression tests PASS with ResourceWarning treated as error. See `qualification/QUALIFICATION_REMEDIATION_V2_22.md`. Live PostgreSQL, D15 CRM/pipeline qualification, and real-company blind-FD validation remain open gates.

## v2.23 — Intelligent Data Intake Foundation
Adds unknown Excel workbook profiling, semantic sheet classification and independently recalculated AR/AP control reconciliations. Qualified against UWB-001 and UWB-002. See `docs/INTELLIGENT_DATA_INTAKE_V2_23.md`.

## v2.24 — Intelligent Intake II
Column-level semantics, units, mapping confidence, generic controls, canonical evidence hand-off and fail-closed intake assessment. Unknown workbook fixtures remain qualification evidence; unsupported detail is not invented.

## v2.26 — Unknown Workbook Canonical Hand-off & Eligibility Bridge
- Added `profit_doctor.intake.bridge.execute_unknown_workbook` to take original SME Excel workbooks through profiling/mapping, canonical accounting/workforce hand-off, independent reconciliation evidence, primitives, all-56 diagnostic execution, reasoning and economic engines.
- Aggregate customer/supplier schedules are deliberately NOT fabricated into invoice-level ledgers; invoice-dependent diagnostics remain unavailable unless evidence supports them.
- Both UWB qualification workbooks execute directly from `.xlsx` with 56 test contracts evaluated; 12 diagnostics complete on currently supportable canonical evidence and 44 fail closed/not-run.
- Scenario 1 retains £1.071639m AR control failure; Scenario 2 retains AR £982.806k, AP £279k, inventory £120k and debt £125k control failures.
- Qualification regression: 33/33 PASS with ResourceWarning promoted to error.


## v2.26
Evidence-granularity-aware commercial canonicalisation adds PARTIAL-A aggregate customer, supplier and capacity methods while preserving transaction-level refusals. See `docs/EVIDENCE_GRANULARITY_HANDOFF_V2_26.md`.

## v2.27 Management Attention / FD Output Qualification
Adds theme-level management-attention compression after deterministic reasoning. Related signals are compressed into a 3–7 item FD agenda where evidence supports it, with explicit management questions, next actions, confidence, evidence counts and limitations. Selection does not create opportunity economics or causal claims. See `docs/MANAGEMENT_ATTENTION_V2_27.md`.

## v2.28
Management Action & Opportunity Qualification adds evidence requirements, recommended action paths and a Profit & Cash Opportunity Register to the FD attention agenda. It deliberately refuses unsupported monetisation of control residuals, exposure and capacity.


## v2.30 Longitudinal Advisory & Benefit Realisation
Adds cross-run issue continuity, resolve/reopen history, longitudinal opportunity identity, stale-opportunity handling, cumulative benefit-claim registry, and anti-double-counting across repeated advisory runs.


## v2.31 Dirty Data, Restatement & Revision Qualification
Adds immutable source revision history, dirty-data exceptions, deterministic duplicate handling, missing-period detection, baseline revision locks and restatement events. Historical realised-benefit claims remain historical facts; revised baselines do not rewrite prior claims.

## v2.33 — Management Output Specification
Adds the first stable product-facing information hierarchy and `build_management_output()` view contract. It exposes Executive Health Check, 3–7 Management Attention priorities, Profit & Cash Opportunity Register, diagnostic coverage, actions, data/integrity evidence, benefit-progress guardrails and evidence/limitations without creating new economic facts. See `docs/MANAGEMENT_OUTPUT_SPEC_V2_33.md`.


## v2.34 Product View Model / API Layer
A strict Pydantic product boundary now exposes the v2.33 Management Output contract through `profit_doctor.api`. See `docs/PRODUCT_VIEW_MODEL_API_V2_34.md`. The next milestone is the v2.35 visual prototype.

## v2.35 — First Visual Prototype
- Adds `prototype/v235/index.html`, a self-contained owner-facing Business Health Check prototype driven by the PVM-2.34 payload.
- Adds Scenario 2 product-view fixture and visual qualification tests.
- Fixes conservative TB control-balance classification so debt/tax/other-debtor accounts cannot contaminate cash/AR/AP through broad name matching.
- Fixes owner KPI projection to use current FIN_* and WC_* primitive identifiers.
- See `docs/VISUAL_PROTOTYPE_V2_35.md`.

## v2.36 Interactive Drill-Down Prototype
Adds client-scoped product drill-down services and a richer Scenario 2 interactive prototype under `prototype/v236/`. See `docs/INTERACTIVE_DRILLDOWN_V2_36.md`.

## v2.37 Upload-to-Report Demo
See `docs/UPLOAD_TO_REPORT_DEMO_V2_37.md` and `scripts/run_upload_to_report_v237.py`.

## v2.38 — Upload Readiness & Coverage Explanation
Adds `UIR-2.38`, an owner-facing upload preflight that reports detected data, mapping confirmation needs, reconciliation/control failures, diagnostic coverage and evidence requests for deeper analysis. No universal data-quality score is created; missing data gracefully reduces coverage and failed controls remain control exceptions rather than losses/opportunities.

## v2.39 — Level-3 Synthetic Qualification
Adds a rich synthetic manufacturing qualification case spanning transaction sales/margin, customer/product/pricing evidence, workforce/capacity, suppliers/overheads, AR ageing, working capital, forecast/KPI and risk/control evidence. The current 56-test estate completes 56/56 on the case. D15 CRM/pipeline evidence is included as a qualification input artifact but is not falsely claimed as consumed: the current canonical model has no CRM/pipeline object or standalone diagnostic, so D15 remains an explicit open product gate.

## v2.40 — D15 CRM / Pipeline / Win-Loss
D15 is now a first-class canonical domain with opportunity, stage-history, activity and deterministic CRM-analysis objects. Level-3 qualification includes genuine CRM evidence while preserving the 56-diagnostic freeze. Pipeline/weighted pipeline are explicitly not recognised revenue or Profit Doctor forecasts. See `docs/CRM_D15_V2_40.md`.

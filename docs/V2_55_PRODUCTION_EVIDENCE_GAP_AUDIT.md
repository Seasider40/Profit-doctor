# v2.55 — Production Evidence Gap Audit & Unlock Matrix

## 1. Executive summary

**Status: audit/design only; no implementation authority.** Inspection baseline is clean `main`, with `HEAD` and the local `origin/main` reference both at `43aa15e246f70781569f5859da3a6d083092ee85`. No remote fetch was performed. This includes the frozen v2.54 implementation and CI-only timeout change. The supplied release baseline is 53/53 focused PASS, 904 executed estate checks (895 PASS, nine legitimate live skips), 520/520 live PASS, four CI jobs PASS and blind temporal qualification PASS. Those results are user-supplied completed qualification, not tests rerun for this audit. Some frozen engineering documents still describe their original release-candidate status; this audit does not edit them.

The audit identifies **34 important gaps**, grouped by responsibility rather than by every individual refusal branch. These are not 34 product defects. Most are appropriate boundaries between observed data and stronger claims. Production receivables CASH_TRAPPED and the narrow collection Opportunity route already exist; broad economic classification, temporal assessment and machine Priority do not become positive merely because a workbook contains plausible amounts.

**Critical architectural decision:** the proposed three production temporal proof paths cannot be unlocked by evidence providers alone while v2.54 remains completely unchanged. `temporal.engine.evaluate` unconditionally returns an unassessed result for `origin == 'CANONICAL'`. `AbsenceEvidence` accepts only `SYNTHETIC_QUALIFICATION`; `TemporalInput` rejects canonical absence. The production service obtains current owned evidence and recomputes results on readback, so bypassing those gates through direct persistence is also unsafe. This is an intentional frozen qualification boundary, not a threshold defect.

Stop at that boundary: do not relabel real data synthetic, mutate the frozen validator, inject verified documents or use raw inserts. An architectural decision is required for an **additive, versioned, trusted production qualification boundary**, preserving the frozen route, thresholds, scope checks and synthetic segregation. If no such extension is approved, v2.55 can improve verified evidence/readiness only; all three production temporal outputs must remain refused. This document describes the prerequisites and decision, not a workaround or implementation of that extension.

The highest-value foundation is a bounded **scoped ledger/control reconciliation provider**, supported by explicit period, population, coverage, definition and revision evidence. Matching totals alone cannot verify membership or semantics. Proposed providers should write evidence-backed claims through existing Dataset Contract, Measurement Context, lineage and audit ownership, not create a competing evidence store.

The smallest useful scope is a bounded accounting/sales/receivables qualification pack, first proving semantic readiness, then—only after the boundary decision—qualifying Revenue monthly trajectory, C0 margin trajectory and receivables absence/lifecycle. Urgency, controllability, relative materiality, new Impact categories, new Opportunity methods, economic mechanisms, recommendations and AI remain out of scope.

## 2. Current production evidence architecture

### Inspection basis

The findings below trace source code, contract validators, test assertions, runner construction and engineering documents. The principal inspected references are:

| Layer | Source of authority inspected | Tests/documentation cross-check |
|---|---|---|
| Intake and immutable imports | `intake/workbook.py`, `declared_accounting.py`, `receivables.py`, `collection.py`, `readiness.py`; `ingestion/northstar.py`, `accounting.py` | v2.38 readiness, v2.49 receivables and v2.50 collection qualification documents |
| Diagnostic/legacy reasoning | `diagnostic/engine.py`, `reasoning/engine.py` | frozen Signal mapping inventory; diagnostic emission and window construction |
| Domain/canonical | `reasoning/domain`, `canonical/registry.py`, `canonical/service.py` | v2.43 foundation; v2.44 typed mapping and Fact/Finding tests/documents |
| Graph and hypotheses | `graph/ancestry.py`, `graph/service.py`, `hypothesis/registry.py`, `hypothesis/service.py` | v2.45 graph and v2.46 disconfirmation/feasibility documents |
| Stories | `story/registry.py` and governed Story contracts | v2.47 engineering catalogue and deferrals |
| Measurement/BIQ/Bridges | `measurement/source.py`, `measurement/service.py`, `bridge/context_qualification.py`, `bridge/engine.py` | v2.48 context trace, BIQ and blind Bridge documents |
| Dataset semantics | `dataset/contracts.py`, `source.py`, `service.py`, `comparability.py` | `test_dataset_contract_v253.py`, `test_dataset_contract_service_v253.py`, v2.53 engineering document |
| Impact/receivables | `impact/registry.py`, `impact/receivables.py`, `impact/service.py`, `receivables/contracts.py`, `receivables/service.py` | v2.49 generic versus provider-specific qualification; Impact and receivables tests |
| Opportunity | `opportunity/engine.py`, `opportunity/service.py`, collection adapter/contracts | v2.50 capture/data specification and focused qualification assertions |
| Priority/Attention | `priority/engine.py`, `priority/service.py`, `attention/contracts.py`, `attention/service.py` | `test_attention_v252.py`; v2.51/v2.52 documents |
| Temporal | `temporal/contracts.py`, `policies.py`, `engine.py`, `service.py` | `test_temporal_contracts_v254.py`, `test_temporal_service_v254.py`, v2.54 document and cumulative runner |
| Legacy management/product | `management/engine.py`, `opportunity_register.py`, `longitudinal.py`; `api/service.py`, `api/view_models.py`; legacy economic engine/portfolio | actual legacy SQL consumers, source separation and benefit-claim eligibility |
| Persistence/qualification | existing Dataset/temporal ownership and revision patterns; `qualify_temporal_postgresql_v254.py` and inherited runner tests | preserved checkpoints, source scopes, caller-owned rollback and no automatic downstream switch |

Paths above are relative to `profit_doctor/` except tests, scripts and docs. This audit does not certify arbitrary external exports, inspect private grading material or rerun release qualification.

### Ownership and authority flow

1. Registered imports retain client-owned immutable files, file hashes, dataset/version IDs, row identity and ingestion status. Technical capture proves what was imported, not that the business population is complete.
2. Diagnostics retain execution eligibility, units, values, windows and lineage. Existing 56 calculations remain authoritative within their original contracts. A Signal can be mechanically valid without carrying enough semantics for a canonical Fact or financial consequence.
3. Canonicalisation uses producer-specific mappings. Unknown/ambiguous types refuse or remain unmapped; there is no generic fallback. Mixed GBP, percent and percentage-point slots remain separate. Finding assessment is a separate operation, with only the three qualified significance families and explicit held/insufficient outcomes.
4. Graph ancestry resolves known source resources. Missing/unsupported ancestry remains indeterminate. Corroboration is governed by current, eligible, comparable, exact evidence and mandatory disconfirmation. Two exports from one system are not independent merely because their filenames differ.
5. CMC owns each measurement's period, scope, units, basis and revision. Propagation requires an exact supported owner/slot/value binding. Dataset Contract owns eleven semantic comparison dimensions; BIQ owns Bridge comparability. These are complementary authorities, not interchangeable labels.
6. EconomicEffect identifies an effect independently from Story/Impact/Opportunity. Bridges reconcile movement without assigning an Impact category. Only qualified production Impacts and qualified Opportunity routes can support their respective aggregations.
7. Canonical services retain immutable history, explicit predecessors, replay identity, audit, client/run scope and caller-owned transactions. Legacy intake/import transactions have separate ownership; a new provider must not claim cross-store atomicity without an explicit design.
8. Existing product API builds legacy management output and queries legacy attention/Signal/action/Opportunity tables. It is not automatically a consumer of canonical Priority, temporal assessment or v2.55 readiness. No silent cutover should be proposed.

## 3. Evidence authority ladder

This is a set of distinct authorities, **not a universal ordinal confidence score**. A contract selects the authority needed for a particular claim.

| Evidence class | What it establishes | What it cannot establish by itself |
|---|---|---|
| Raw source record | A retained export/entry contains a value, date or assertion | Authenticity, completeness, applicability or truth of every label |
| Technical source identity | File hash, registered source, imported row, version and provenance | Economic definition, population equivalence, reporting basis |
| Machine-derived calculation | A reproducible calculation from identified inputs | Correct semantics of those inputs; causality |
| Management declaration | Identified management stated a claim at a time | Verified completeness, loss, absence, mechanism or recoverability |
| Adviser declaration | Identified adviser supplied context/judgement | Independent verification merely because adviser is trusted |
| Reconciled accounting evidence | Specified scoped amounts agree under a retained mapping and rule | Membership equivalence, valuation accuracy or economic causation |
| Contractual evidence | Applicable invoice terms, contract, due date or permission within scope | Current payment/dispute state, future payment or renewal probability |
| Verified source evidence | A versioned check proves a specific dimension with retained witnesses | Other dimensions or downstream classifications not checked |
| Qualified canonical evidence | Owned, typed, current evidence passes its exact contract | Blanket truth/confidence uplift across other object families |
| Synthetic qualification evidence | Engine behaves correctly under explicit test premises | Any production claim, production aggregation or real-business verification |

Matching declarations may produce a limited comparison; they do not produce verified matches. A source contradiction is retained and fails the relevant dimension closed. An actor object is not authentication: Adviser Edition must authenticate the actor and scope access externally to the domain record.

## 4. Full gap matrix

Taxonomy: **A** engine capability missing; **B** production provider missing; **C** ingestion/transport missing; **D** semantic verification missing; **E** reconciliation missing; **F** verified absence missing; **G** comparator/counterfactual missing; **H** authority missing; **I** history missing; **J** appropriately deferred.

The two joined tables form the full matrix, keyed by Gap ID. Together they contain all nineteen requested fields; splitting avoids an unreadable nineteen-column layout. Consumer counts are **potential named families**, not positive claims already unlocked. Prerequisite and boundary approval remain necessary. Complexity/value are qualitative engineering judgments, not measured SME adoption or a score.

### Evidence and verification half

| ID | Domain/release | Existing capability | Current production state | Missing prerequisite | Type | Required evidence | Likely SME source | Level | Verification method | Reconciliation required? | Human declaration allowed? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| G01 | Intake | Registered typed imports | Bounded adapters; arbitrary finance pack unsupported | Controlled export profiles | C | Schema, mapping, source manifest | Accounts/ledger exports | 1/2 | Explicit versioned parser; reject conflicts | Downstream | Mapping context only |
| G02 | Foundation | Scope/lineage/audit | Technical identity available | Authenticated authority and source scope | H/D | Actor, company, ledger, source authority | Source system/export metadata | All | Owner checks and authenticated attribution | No | Yes, attributed context |
| G03 | CMC | Measurement scope/basis | Some declared accounting contexts; commercial unknown | Verified month/entity/currency/unit | B/D | Period and report configuration | Monthly accounts/ledger | 1/2 | Retained export configuration and exact row binding | Where totals used | Declaration only until checked |
| G04 | Accounting controls | Intake control checks | Limited heuristic controls are not universal verification | Complete scoped account/control mapping | E/B | TB, statement accounts, adjustments | TB/P&L/BS/ledgers | 1 | Decimal control equations; residual witnesses | Yes | Account mapping with source check |
| G05 | Dataset v2.53 | Dimensional population comparison | Commercial population unknown | Defined population and membership/filter evidence | D/B | Stable population rule and membership witnesses | Ledger/query configuration | 1/2 | Validate included/excluded identities and source population | Yes, supplementary | Declared population only |
| G06 | Dataset | Complete/partial comparison | Imported count is not completeness | Verified coverage and omitted-record handling | E/D | Extract manifest, boundaries, coverage basis | Source-system export/control | 1/2 | Exhaustive coverage test plus controls | Yes | Declared complete only |
| G07 | C0 | Typed rate and qualified direction | Label is not verified cost definition | Governed numerator/denominator/account policy | D/G | Revenue/direct-cost components and allocation policy | Sales/direct costs/management accounts | 1/2 | Trace components, consistent definition, exact ratio | Yes | Policy declaration, independently checked |
| G08 | Dataset/CMC | Revision history | Import version is not restatement relation | Source-supported relationship to predecessor | D/H | Period/revision IDs, supersession, change record | Revised accounts/ledger exports | 1/2 | Explicit predecessor and same-period scope | Revised controls | Restatement declaration retained separately |
| G09 | Dataset service | Verified claim representation | Only sales technical capture writer | Trusted semantic verification and other owners | B/H | Checks/witnesses for each claim | Governed provider output | All | Current owned source revalidation; audited revisions | Per claim | Never caller verified JSON |
| G10 | Revenue temporal | Monthly trajectory policy | Production NOT_ASSESSED | Commercial observed-slot month context | B/D | Exact REV-01 observed metric period/lineage | Monthly sales source | 1/2 | Typed metric binding, not broad Signal interval | Yes | Period context only |
| G11 | C0 temporal | Rate trajectory policy | Production NOT_ASSESSED | Ratio context and qualified monthly definition | B/D | GM-01 rate numerator/denominator lineage | Detailed Revenue/direct cost | 2; 1 if complete | Typed ratio binding, not GP relabelling | Yes | Definition context only |
| G12 | Canonical | Facts and three significance policies | Not every monthly statement is an eligible Fact | Owned eligible monthly Fact/Finding route | B/D | Exact producer/type/run/slot/current evidence | Governed monthly diagnostic inputs | 1/2 | Exercise frozen mapping and eligibility | Supporting | No fabricated Signal/Finding |
| G13 | Temporal boundary | Qualified synthetic engine | Canonical hard refusal; absence synthetic only | Separate approved production contract | A/B/J | Trusted qualification witnesses, approved authority | Not a workbook field | All | Architecture decision; preserve old route | All prerequisites | No |
| G14 | Temporal | Windows/revisions/history | Runs and versions are not recurrence | Comparable complete monthly history | I/D | Explicit full window, stable scope, revisions | Monthly historical exports | 1/2 | Adjacent eleven-dimensional matches | Per month | Requested window can be declared |
| G15 | AR absence | Synthetic absence/lifecycle | Positive presence only; missing Impact unknown | Exhaustive absence proof | F/E/H | Complete reconciled classified AR universe | Aged AR, terms, status register, TB | 1/2 | Every invoice accounted for; no unresolved class | Yes | Review context; not absence assertion |
| G16 | AR owner/family | Snapshot/source owners | Empty snapshot unsupported; family route mismatch | Empty-population witness and honest Dataset owner | B/D/F | Empty-extract control and source-system identity | AR system/GL control | 1 | Reviewed owner/family semantics; zero must be evidenced | Yes | No dummy invoice or AR-as-GL label |
| G17 | Graph/Attention | Independent corroboration | Shared/incomplete ancestry often unresolved | Complete ancestry and qualified independent peer | B/D/H | Underlying record/primitive/system ancestry | Independent retained evidence | 1/2/3 | Resolve ancestry; mandatory disconfirmation | Where comparable | Human challenge only |
| G18 | Hypothesis | Mechanism vocabulary/requirements | Economic mechanism UNRESOLVED | Qualified mechanism contract, alternatives | A/G/J | Price/cost/mix comparable segments | Detailed commercial records | 2/3 | New contract required, not correlation | Yes | Hypothesis only |
| G19 | Story | Two condition Stories | Three deferred; no mechanism-resolved positive | New governed condition/WHY contracts | A/G/J | Comparable growth/cash/cost evidence | Accounts plus detail | 1/2/3 | Separate condition contracts and disconfirmation | Yes | Context only |
| G20 | Bridge | Revenue/C0/WC | Two other families refused; cross-version limits | Classified cash/cost/output and cross-source contract | A/D/E/J | Flow reconciliation and comparable populations | Cash/ledger/operations | 1/2/3 | New contract needed beyond current BIQ | Yes | Cannot override BIQ |
| G21 | Impact | OBSERVED_LOSS structure | No qualified production writer | Actual lost value and defensible comparator | B/G | Loss event/write-off evidence | Ledger, credit/write-off records | 1/2 | New source-specific qualified contract | Yes | Assertion not actual loss proof |
| G22 | Impact | RUN_RATE_LEAKAGE structure | Unqualified production | Persistent leakage, seasonality, expected state | G/I/J | Comparable history and expected-performance basis | Monthly accounts/detail | 1/2 | Separately qualified run-rate contract | Yes | Budget not verified loss |
| G23 | Impact | CASH_TRAPPED AR positive | Other balances unqualified | Required-position benchmark | G/B | Operational/contractual excess evidence | Inventory/AP/working-capital detail | 1/2 | Source-specific benchmark contract | Yes | Stock increase not trapped proof |
| G24 | Impact | AVOIDABLE_COST structure | Unqualified production | Supported alternative and avoidability | G/H/J | Contract/cancellation/alternative cost | Supplier/expense contracts | 1/2 | Qualified alternative-state contract | Yes | Intent not avoidability proof |
| G25 | Impact | Capital/risk/future/upside types | No positive production contracts | Exposure/risk/scenario/alternative qualification | G/A/J | Specific capital/risk/horizon evidence | Assets/contracts/forecast | 1/2/3 | Separate category contracts; no universal probability | Yes | Scenario context only |
| G26 | Benefit/Impact | REALISED_BENEFIT type; legacy claims | No canonical attribution provider | Baseline, intervention, observation/attribution | G/I/H/J | Dated action/outcome/counterfactual | Accounts, actions, collection records | 1/2 | Future attribution contract | Yes | Claimed result distinct from verified benefit |
| G27 | Opportunity | AR addressability/partition | Narrow qualified portions only | Complete current permissions/prior-initiative review | H/D | Dated constraints, contacts, initiatives, authority | Collection records/contracts | 1/2 | Exact invoice review at assessment date | Impact inherited | Declaration alone insufficient |
| G28 | Opportunity | Exact empirical capture | Many realistic cohorts insufficient | Complete exact-exposure matched cohort/horizon | G/I | Eligible matched history incl negative outcomes | Collection history | 1/2 | At least 3 pairs/current invoice, frozen matching | Impact inherited | No percentage/scaling assertion |
| G29 | Effect overlap | Effect IDs and safe aggregation | Unknown/partial overlap blocks | Governed effect membership/relations | D/G | Same effect, subsets, known independent basis | Shared ledger lineage | All | Existing overlap rules; unknown stays blocked | Where classified | Relation proposal needs evidence |
| G30 | Priority | Independent dimension evaluator | Relative materiality NOT_ASSESSED | Qualified denominator/relative policy provider | B/G/J | Scoped Revenue/GP/EBITDA/amount basis | Accounts/qualified Impact | 1/2 | New approved provider/policy, not generic score | Yes | Importance judgement remains human |
| G31 | Priority/Attention | Persistence vocabulary | Temporal always NOT_ASSESSED | Approved temporal consumer boundary | A/B/J | Owned current production temporal assessment | Qualified provider chain | 1/2 | Explicit consumer extension; no silent promotion | Inherited | No run-count persistence |
| G32 | Priority | Urgency/controllability dimensions | Both NOT_ASSESSED | Separate deadline/control evidence contracts | H/G/J | Dated legal/operational rights and constraints | Contracts/operations | 1/2/3 | Future qualified dimension policies | Case-specific | Adviser decision allowed, machine fact not inferred |
| G33 | Product/API | Legacy management projections | Canonical layers opt-in | Explicit reviewed consumer/cutover design | A/J | Readiness/provenance/scoped API contracts | Application integration | All | Compatibility tests and authority-labelled projection | Inherited | Human review, no auto recommendation |
| G34 | Management/benefit | Legacy review/action/claim safeguards | Separate legacy authority | Canonical integration and audit/auth boundary | A/H/J | Decisions/actions/benefit provenance | Adviser workflow records | All | Explicit release contract; preserve legacy history | Benefit-specific | Human decisions, not canonical promotion |

### Unlock and prioritisation half

Abbreviations: **DS** Dataset semantics; **MC** Measurement Context; **CF** canonical Facts/Findings; **TG** temporal; **GR** graph/quality; **BR** Bridge; **IM** Impact; **OP** Opportunity; **PA** Priority/Attention; **PV** product/adviser projection. Counts describe the listed families; they are dependency reach, not a promise that one provider enables all positive outcomes.

| ID | Capabilities potentially unlocked | Consumer families/count | Double-counting/semantic risk | Complexity | Commercial value | Recommended v2.55 scope? | Reason/rank |
|---|---|---|---|---|---|---|---|
| G01 | Bounded repeatable pack intake | DS, MC, CF, IM / 4 | Header guessing/embedded conclusions | Medium | High | Bounded profiles only | TOP PRIORITY; not universal ingestion |
| G02 | Attributable scoped evidence | DS, MC, GR, IM, OP, PA / 6 | Cross-tenant/false authority | Medium | High | Required foundation | TOP PRIORITY; reusable ownership |
| G03 | Exact monthly measurement basis | MC, DS, TG, BR / 4 | Stock/flow, percent/pp confusion | Medium | High | Yes | TOP PRIORITY; temporal prerequisite |
| G04 | Scoped ledger/control witnesses | DS, MC, CF, BR, IM, OP, TG / 7 | Equal totals mistaken for equivalence | Medium-high | High | Yes, bounded AR/Revenue/C0 | TOP PRIORITY; broadest reusable provider |
| G05 | Verified population comparison | DS, TG, GR, BR / 4 | Matching labels/totals not membership | High | High | Yes, explicit rules | TOP PRIORITY; false confidence blocker |
| G06 | Complete/partial readiness | DS, CF, TG, IM, OP / 5 | Extrapolation or hidden omissions | High | High | Yes | TOP PRIORITY; refuse uncertain coverage |
| G07 | Honest C0 rate definition | MC, DS, TG, BR / 4 | C0 relabelled gross profit | High | High where data available | Conditional core | TOP PRIORITY; refuse missing direct costs |
| G08 | Restatement/new-time distinction | MC, DS, TG, BR / 4 | Artificial movement/repeated periods | Medium | High | Yes | TOP PRIORITY; preserve history |
| G09 | Persisted verified semantics | DS, TG, MC, GR / 4 | Self-certified verified payload | High | High | Architecture decision prerequisite | TOP PRIORITY; trusted writer absent |
| G10 | Revenue monthly evidence | CF, TG, DS / 3 | Broad diagnostic windows as month | Medium-high | High | Conditional core | TOP PRIORITY; typed route required |
| G11 | C0 monthly evidence | CF, TG, MC / 3 | Inexact ratio/context transplant | High | High with direct costs | Conditional core | TOP PRIORITY; no generic binding |
| G12 | Owned production observations | CF, TG, GR / 3 | Manufactured diagnostics/canonical authority | Medium-high | High | Qualification prerequisite | TOP PRIORITY; establish lawful owner route |
| G13 | Production temporal authority | TG / 1 | Bypassing synthetic-only boundary | Architecture-gated | High | Decision first | TOP PRIORITY; cannot unlock unchanged v2.54 |
| G14 | Comparable window histories | DS, TG / 2 | Cherry-picked window/run count | Medium | High | Yes | TOP PRIORITY; at least complete requested window |
| G15 | AR verified absence/lifecycle | IM, TG, DS / 3 | No Impact mistaken for absence | High | High | Conditional core | TOP PRIORITY; separate absence proof |
| G16 | Honest AR universe ownership | DS, TG, IM / 3 | Mislabelled family/dummy invoice | Architecture-gated | High | Decision first | TOP PRIORITY; current source restrictions |
| G17 | Governed evidence quality | GR, PA, Story / 3 | Shared sources counted independent | High | High | Secondary | SECONDARY; avoid fake corroboration |
| G18 | Mechanism interpretation | Hypothesis, Story, IM / 3 | Correlation promoted to cause | High | Potentially high | No | DEFER; engine/contract scope |
| G19 | Deferred Stories | Story / 1 | Narrative outruns condition/WHY | High | Potentially high | No | DEFER; not evidence-provider-only work |
| G20 | Additional/cross-source Bridges | BR / 1 | Cash stocks as cash flow; false residual attribution | High | Potentially high | No new families | DEFER; retain refusal |
| G21 | Actual loss qualification | IM / 1 | Accounting movement as lost value | Medium-high | High for specific cases | Future narrow contract | SECONDARY; evidence attainable, writer missing |
| G22 | Run-rate qualification | IM / 1 | Annualising one month/ignoring seasonality | High | Potentially high | No | DEFER; comparator/history qualification |
| G23 | Additional trapped-balance cases | IM / 1 | All stock treated recoverable | High | Potentially high | AR only | DEFER extensions; preserve current positive |
| G24 | Avoidable-cost cases | IM / 1 | Spend reduction assumed feasible | High | Potentially high | No | DEFER; new economic contract |
| G25 | Capital/future/upside cases | IM / 1 | Risk/potential/observed amounts added | High | Potentially high | No | DEFER; separate categories/contracts |
| G26 | Attributed realised benefits | IM, management / 2 | Prospective capture counted realised | High | High later | No | DEFER; later attribution boundary |
| G27 | More usable existing AR Opportunities | OP / 1 | Missing initiatives default NONE | Medium-high | High | Readiness/specification only | SECONDARY; ordinary records often incomplete |
| G28 | Qualified capture cohorts | OP / 1 | Scaling/cherry-picked success | High; source availability uncertain | High if evidence exists | No methodology change | SECONDARY; exact exposure often restrictive |
| G29 | Safe classified aggregations | IM, OP, BR / 3 | Bridge + Impact + Opportunity double count | Medium-high | High | Reuse existing safeguards | TOP PRIORITY safeguard, not new totals |
| G30 | Relative materiality | PA / 1 | Universal score or invented thresholds | Architecture-gated | High later | No | DEFER; reconcile denominators but do not uplift |
| G31 | Priority temporal dimension | PA / 1 | Automatic priority/state promotion | Architecture-gated | High later | No consumer switch | DEFER; qualified temporal != Priority |
| G32 | Urgency/controllability | PA / 1 | Overdue implies urgent/controllable | High | High later | No | DEFER; human decision remains separate |
| G33 | Adviser readiness view | PV / 1 | Dual authority/automatic recommendations | Medium-high | High | Design only | SECONDARY; explicit integration later |
| G34 | Canonical management/benefit integration | PV, management / 2 | Legacy statuses silently promoted | High | High later | No | DEFER; preserve frozen authorities |

## 5. Dataset Contract dimension audit

The current sales capture verifies **family and provider/source-domain identity**, plus technical file/version/hash, imported rows and date bounds. The remaining business claims are not machine verified by this production writer. They may carry an identified declaration, otherwise remain unknown. `get_contract(current=True)` revalidates via `capture_sales`; constructing a valid model with verified fields does not establish a trusted production route.

| Dimension | Frozen production position | Evidence/verification proposed | Reconciliation and declaration boundary |
|---|---|---|---|
| DATASET_FAMILY | Northstar sales family verified; other owners refused | Registered export profile + source domain + qualified owner | File title or adviser label insufficient; AR cannot simply be called GENERAL_LEDGER |
| SOURCE_LINEAGE | Provider/domain verified; immutable provenance separate | Registered source/version/record/ancestor chain and source-system relationship | Matching hashes/rows are technical evidence; adviser may explain source but not assert independence |
| POPULATION | Declared or unknown | Stable rule identifying company, accounts, parties/segments, document classes and reporting population; membership/filter witnesses | Controls support completeness, not population equality. Changing invoice IDs across months is expected; verify the stable universe rule, not identical observations |
| INCLUSION_EXCLUSION | Declared or unknown | Export/query filters, included/excluded record classes, adjustment register | Match reconciled coverage under same filters; adviser can disclose exclusions, cannot verify an unobservable omitted universe |
| COVERAGE | Declared or unknown | Complete extraction manifest, report boundaries, omitted-record checks, scoped coverage basis | Full control tie plus membership evidence; equal counts/totals alone never enough. Partial stays partial |
| DEFINITION | Declared or unknown | Accounting policy, account mapping, recognition/cost basis and source computation specification | Recompute mapped components; C0 definition must be explicit. Adviser supplies policy context; implementation needs source checks |
| ORGANISATIONAL_SCOPE | Declared or unknown | Legal entity/ledger/business unit export settings and scoped account ownership | Consolidations/eliminations separately evidenced; no company name guessing |
| CURRENCY | Declared or unknown | Explicit currency field/report setting and conversion policy if relevant | Frozen proof paths GBP; no implicit FX conversion. Symbols alone insufficient |
| UNIT | Declared or unknown | Source measure type, money/rate distinction and denominator/numerator binding | C0 percent versus pp changes remain distinct; unit label alone does not qualify ratio |
| TIME_BASIS | Declared or unknown | Period start/end, calendar-month basis, stock as-of versus flow, accrual/cash and posting/invoice-date policy | Accounts/calendar controls; Signal union bounds do not establish observed metric month |
| REVISION_RELATIONSHIP | Declared or unknown | Stable report/source series, predecessor reference, source revision/change record | Restatement controls and explicit replacement lineage; version number/time stamp alone not NEW_OBSERVATION |

Verified claim publication must retain check version, source digest, client/run ownership, date, witnesses, limitations, contradictions and immutable predecessor/audit. One provider may establish some dimensions and refuse others. Comparability remains eleven-dimensional: mismatch is non-comparable; unknown is insufficient; matching declarations are limited. No composite percentage or value-based shortcut.

**Accounting versus commercial basis:** posted Revenue, invoice sales, VAT-inclusive invoices, net credit notes and management sales may differ legitimately. A reconciliation bridge explaining adjustments is necessary; accounting agreement cannot silently make unlike definitions equivalent. The frozen temporal contract needs SALES_TRANSACTIONS for Revenue/C0 and GENERAL_LEDGER for cash, while actual AR ownership uses `D04_AR_SNAPSHOT`. The honest composite/owner interpretation needs explicit architectural review; do not change the source's identity to fit the enum.

## 6. Impact category audit

All eight categories are governed. Generic registry entries remain production-unqualified; a separate provider contract enables the existing receivables exception. Having a model or synthetic positive case is not a production writer.

| Category | Current positive production contract | Missing evidence/contract | Ordinary Level 1/2 feasibility | v2.55 recommendation |
|---|---|---|---|---|
| OBSERVED_LOSS | None | Actual lost value/event, relevant defensible comparison, classification and overlap | Specific write-offs/credit events may provide evidence; expense posting alone not sufficient | Secondary later source-specific contract; not this scope |
| RUN_RATE_LEAKAGE | None | Qualified expected state, persistence, seasonality and distinct observed/run-rate windows | History may be available; comparable expectation frequently unsupported | Defer; never multiply one month by twelve |
| CASH_TRAPPED | `OVERDUE_RECEIVABLES_1` | For other cases, required operational/contractual position; for absence, complete reviewed universe | Existing AR positive can use ordinary aged AR + terms + current source reviews + control evidence | Retain existing positive semantics; design AR absence only |
| AVOIDABLE_COST | None | Evidence-backed avoidability/alternative cost state and constraints | Contracts/cancellation alternatives may support narrow future cases | Defer new contract; cost increase is not avoidable cost |
| CAPITAL_AT_RISK | None | Identified capital and supported risk/exposure/horizon | Asset/debtor records establish capital, not loss probability | Defer; concentration alone not risk qualification |
| FUTURE_EXPOSURE | None | Governed prospective downside/alternative and horizon | Forecast/scenario provides assumptions, not established exposure | Defer production contract; retain hypothetical authority |
| VALUE_CREATION_POTENTIAL | None | Supported economic alternative/upside rather than Revenue growth | Budgets/pricing detail may inform a future comparator | Defer; not Opportunity/recoverability by renaming |
| REALISED_BENEFIT | None in canonical Impact | Qualified baseline, action, realised observation and attribution | Subsequent accounting/collection history useful but attribution missing | Defer; legacy benefit claims remain separate |

Ordinary finance records could support **future narrow** OBSERVED_LOSS and AVOIDABLE_COST contracts; those categories cannot become positive through the current generic writer just by importing more data. CASH_TRAPPED is the only current positive production route. Inventory balances, customer concentration, Revenue/C0 movements and Bridge residuals remain unclassified economic evidence. Golden Manufacturing's £700,000 WC movement stays a Bridge movement; the separately qualified £340,000 AR Impact is neither a recoverability value nor an additive claim on top of that movement.

Aggregation retains separate profit/cash/capital-risk/future/potential/realised dimensions. Only qualified Impacts aggregate; SAME_EFFECT cannot count twice; PARTIAL_OVERLAP/UNKNOWN_OVERLAP block unsafe totals. A resolved AR condition does not itself establish collected cash or realised benefit: credits, write-offs and changed constraints may also remove a qualifying condition.

## 7. Opportunity audit

The existing production route is qualified receivables Impact → collection evidence → governed addressability/incrementality → `MATCHED_COLLECTION_OUTCOMES_1`. There is no general Opportunity generator for all Impact categories.

| Boundary | Existing capability | Missing ordinary evidence versus future contract |
|---|---|---|
| Impact | Accepts qualified current production receivables Impact | Other category/method routes need new contracts, not a generic source adapter |
| Addressability | Invoice-level addressable, excluded and unresolved portions coexist | Current dated permission, strategic constraints, collection history and applicable terms may be ingested through registered collection provider |
| Incrementality | Existing qualifying initiative excluded | Complete scoped prior-initiative review required. Missing initiative record remains unknown, not NONE |
| Capture | Exact matched-pair empirical envelope | At least three complete eligible pairs per current invoice; same customer, exact exposure, currency, age band, terms, intervention and horizon/window requirements |
| Counterfactual | Matched baseline/intervention cash outcomes | Historical eligible negatives retained; a negative paired difference refuses the applicable cohort. A success-only subset cannot qualify |
| Horizon | Explicit dates and capture horizon | Promise/payment-plan dates alone do not create qualified empirical capture |
| Overlap | Same EconomicEffect and governed relations | Unknown relation between claims must block unsafe aggregation |

Frozen low/high are min/max eligible paired differences; optional central is the equal-weight empirical mean only when exactly representable as Decimal. It is not a midpoint or probability. Different exposure sizes cannot be proportionally scaled. An ordinary collection system may have contacts/promises yet lack sufficient matched outcomes; ingestion success is not qualification success. v2.55 should report missing cohort/initiative evidence, not alter the methodology. Opportunity remains prospective capture, distinct from cash stock, Priority, adviser Decision and realised Benefit.

## 8. Priority / Attention audit

The machine evaluator already separates materiality, evidence strength, persistence, urgency and controllability. Production ownership is narrower than the model vocabulary. The default Priority service requires non-assessed materiality, urgency, controllability and persistence; Attention extends only evidence strength through its governed evidence-quality route.

| Dimension | Current production capability | Does better source evidence alone unlock it? |
|---|---|---|
| Evidence quality | STRONG from current scoped immutable `EVIDENCE_QUALITY` / `INDEPENDENT_CORROBORATION`, SUPPORTED with mandatory disconfirmation; conflicts retained | Potentially yes within the existing exact route, if independent eligible peer/ancestry/comparability genuinely exist |
| Absolute amount | Fact/Impact/capture amounts may be retained | Yes for their existing contracts; amount is not a HIGH relative-materiality label |
| Relative materiality | NOT_ASSESSED | No: verified denominators help, but a separately qualified provider/policy is required |
| Temporal persistence | NOT_ASSESSED in Attention/Priority | No: even future qualified temporal output needs an explicit approved consumer boundary |
| Worsening/improving | No production temporal interpretation consumer | No: C0 directionality is governed; Revenue is descriptive; Priority cannot silently translate either |
| Urgency / controllability | NOT_ASSESSED | No: deadline/control authority and distinct policies absent; overdue is not automatic urgency |
| Attention/Priority state | Insufficient evidence is a valid outcome | STRONG evidence alone cannot satisfy combinations requiring materiality/urgency/persistence |

Independence never implies completeness, reconciliation, economic mechanism, causality or confidence uplift. The Attention service rechecks current evidence/disconfirmation and refuses stale support; it does not automatically reassess a hypothesis. Adviser ACCEPT/INVESTIGATE/REJECT remains separately human-authoritative, immutable and audited. Readiness is a view of evidence availability, not a machine Priority result.

## 9. Temporal production audit

### Exact frozen refusal paths

Direct source references: [canonical-origin refusal](../profit_doctor/reasoning/temporal/engine.py#L190), [synthetic-only absence contract](../profit_doctor/reasoning/temporal/contracts.py#L87), [canonical absence rejection](../profit_doctor/reasoning/temporal/contracts.py#L168), [owned Impact/history route](../profit_doctor/reasoning/temporal/service.py#L76), [narrow Dataset capture](../profit_doctor/reasoning/dataset/service.py#L80), and [frozen Priority provider boundary](../profit_doctor/reasoning/priority/service.py#L139).

* `temporal/engine.py`, `evaluate`: canonical origin returns `PRODUCTION_TEMPORAL_PREREQUISITES_NOT_VERIFIED` irrespective of whether a caller supplied complete claims.
* `temporal/contracts.py`: absence proof is synthetic-only; canonical absence is rejected.
* `temporal/service.py`: Revenue/C0 require exact current canonical Fact owners and Finding membership; metric period is taken from CMC, not the broad Signal interval. Dataset owner revalidation is currently the narrow sales capture route.
* The AR route accepts an owned REAL_SOURCE production receivables qualification. A positive qualified Impact establishes PRESENT; otherwise presence is UNKNOWN. Blind qualification sources cannot enter that production route. No production absence is constructed.
* Readback recomputes the frozen result from owned basis; synthetic positive results cannot be read as canonical production.

These are confirmed by production service tests and `test_production_cannot_relabel_synthetic_positive_claim`. The cumulative live runner also exercises the synthetic engine tests and production refusal/persistence tests; its live PASS does not mean positive production temporal authority exists.

### Revenue proof prerequisites

Retained actual sales observations must map to exact REV-01/COMPARABLE_REVENUE_CHANGE Facts with active/current owned source, typed money observed slot, complete eligible monthly evidence and a lawful Finding membership/subject route. Obtain the observed month through a qualified CMC binding. Do not treat the diagnostic's current-plus-prior interval as that month, substitute an annual accounting total or manually manufacture a Signal. Revenue CMC accounting metric `financial_revenue` is not automatically the commercial Fact metric `revenue`; present propagation does not establish that cross-basis conversion.

For every month, verify all eleven Dataset dimensions and full calendar-month coverage; retain unchanged population definition, recognition policy, scope, GBP money unit and supported revision relationship. Reconcile sales to mapped Revenue controls with explicit credit/VAT/accrual adjustments. Choose and retain the full explicit observation window before assessment. Missing months and competing restatements must remain visible. At least three qualified observations support trajectory; two can describe adjacent movement, not a trajectory. A zero/negative prior base has no qualified relative movement.

After—and only after—the approved production-boundary extension, preserve the frozen adjacent **5% of strictly positive prior monthly Revenue** threshold, equality material, Decimal delta/threshold and descriptive direction only. Revenue decrease is not economic worsening/loss.

### Contribution 0 proof prerequisites

Exact GM-01/CONTRIBUTION_MARGIN_CHANGE Facts and observed **C0 percentage** require verified monthly numerator/denominator and a stable direct-cost definition, eligible coverage, source owner and reporting basis. CMC's exact amount propagation does not supply a new compound ratio binding. A label saying gross profit cannot replace C0; account mappings/allocation policy and detailed direct costs must support the measure. An ordinary P&L without those components is insufficient.

Verify monthly source populations, coverage and eleven dimensions, including PERCENTAGE unit and N/A currency for the rate, while retaining GBP for the underlying monetary components. Reconcile numerator/denominator to the qualified scoped accounts without silently moving accounting-rate evidence into a commercial-sales contract. At least three comparable observations are required for trajectory. Preserve **one percentage point**, equality material, and `HIGHER_IS_FAVOURABLE`. This is C0 economic direction, not a causal mechanism or quantified loss.

### CASH_TRAPPED verified absence proof

An acceptable future production proof must retain:

1. Complete scoped AR universe for an exact reporting date, company/entity, ledger, GBP and stable population rule; all invoice/credit/adjustment identities and extraction boundaries.
2. Authoritative matched AR control total, source identity, exhaustive account mapping and exact retained Decimal reconciliation. Unexplained differences or partial coverage refuse absence.
3. Invoice/customer identity, outstanding amounts, dates, contractual due dates or effective terms and governing source. Original invoice amount remains optional and is never filled from outstanding balance.
4. Complete, current, source-authoritative review of status, payment plans, disputes, pending credits and constraints; explicitly classified membership and dated review coverage. Unknown/conflicting due-date/status evidence blocks absence, including records outside the positive qualifying subset.
5. Exhaustive partition: no unresolved invoice/classification and no positive overdue unconstrained qualifying balance. Due on reporting date remains within terms. Excluded constrained balances are not labelled unrecoverable.
6. Versioned verifier output bound to exact immutable source/CMC/Dataset ownership, scope, reporting date, authority, policy and audit. All eleven comparison dimensions and complete per-period coverage remain required for lifecycle history.
7. Explicit revision/supersession and requested window; same-period replays are not new observations. Stable condition population/subject history is distinct from changing invoice IDs or per-run snapshot identity.

This evidence is **necessary but not presently representable as production absence**. Frozen Snapshot requires at least one invoice; a genuinely empty complete AR population needs a separately reviewed empty-population witness, not a dummy row. The AR source family/GENERAL_LEDGER temporal owner mismatch needs a truthful owner/composite accounting proof decision. Absence-only history also needs lawful subject identity: current service anchors the cash subject to an existing owned Impact, not an invented zero Impact. A first-ever all-absence series cannot be smuggled through that subject requirement.

Under qualified premises the existing synthetic lifecycle distinguishes first PRESENT in window (NEW), consecutive PRESENT (PERSISTENT), PRESENT→verified absence (RESOLVED), and PRESENT→absence→PRESENT (RECURRENT). Missing months/unknowns are not absence or recurrence; three present runs are not recurrence. Magnitude does not establish cash worsening. These policies can be preserved in a separately approved production contract; no positive production claim can be made under unchanged v2.54.

## 10. SME source catalogue

Profiles below are proposed minimum **semantic** export requirements, not already supported arbitrary workbook formats. L1/L2/L3 enrich sophistication progressively; absent detail limits eligibility rather than reducing analytical standards. Every source needs client/ledger scope, immutable file/version identity, currency/unit/date basis, filter/coverage metadata and source authority. Optional fields never silently default to economically significant values.

| Source / likely export | Minimum fields | Useful optional fields | Authoritative control and reconciliation | Dimensions potentially verified | Capabilities supported |
|---|---|---|---|---|---|
| Trial Balance — accounting CSV/XLSX (L1) | Entity/ledger, account code, debit/credit or signed balance, as-of/period, currency, account mapping | Opening/movement/closing, cost centre, revision ID | Debits/credits; scoped statement mapping; openings + movement = closing | Family, scope, currency, units, time, lineage; definition/coverage with configuration | Statement/control readiness, scoped ledger reconciliation |
| Monthly P&L — accounts XLSX (L1) | Entity, month start/end, account/line code, amount, currency, accrual/cash basis | Comparatives, adjustments, C0 components | Mapped TB movements; Revenue/direct-cost controls | Definition/time/scope/unit; coverage with full account map | Revenue/C0 basis where qualified; existing Bridge inputs |
| Monthly Balance Sheet — XLSX (L1) | Entity, as-of, account/line code, signed amount, currency | Opening balances, reconciliation schedules | TB closing balances; component controls | Stock/time/scope/definition; full coverage needs account universe | AR/AP/inventory controls; WC stock evidence |
| Aged Receivables — invoice export (L1) | Reporting date, ledger/entity, customer/invoice IDs, invoice/due dates or terms, outstanding, currency | Original amount, dispute/plan/credit review, audit IDs | AR control, credits/unallocated cash/adjustments explicitly reconciled | Population/coverage with manifest; contractual definition/time/scope | Existing AR Impact; proposed complete absence proof |
| Sales Invoice Ledger / Transactions — CSV (L1/2) | Unique document/line IDs, customer, dates/basis, net amount/currency, credits, scope/filter metadata | Product, units, prices, direct costs, posting account | Net ledger to Revenue controls with posting/VAT/accrual adjustments | Sales family, inclusion, population, coverage, time/unit/definition | Canonical commercial observations; proposed Revenue temporal |
| Aged Payables — supplier export (L1) | Supplier/invoice IDs, reporting date, outstanding, due terms, currency/scope | Disputes/credits/payment plan | AP control with explicit adjustments | AP population/coverage/time/scope | Existing diagnostics/WC; no automatic avoidable cost |
| Purchase Ledger — CSV (L1) | Supplier/document/line IDs, posting/invoice dates, account, net amount/currency | Product, cost centre, contract references | AP control/expenses/inventory under posting policy | Definition/inclusion/population/coverage | Spend/cost evidence; not avoidability by itself |
| Bank/Cash — CSV/statements (L1) | Account, transaction IDs/dates, amounts, opening/closing, currency | Clearing dates, categories, reconciled references | Statement balance to cash GL, outstanding items | Stock/flow/time/coverage/scope | Cash diagnostics; future cash reconciliation prerequisite |
| Customer Sales — accounting/ERP XLSX (L2) | Customer identity, period, net sales, company/currency, included population | Product, costs, CTS, contract/segment | Total to same-basis sales ledger/Revenue | Segmentation/coverage/definition with identity mapping | Customer concentration; profitability only with qualified costs |
| Product Sales — ERP CSV/XLSX (L2) | Product IDs, period, amounts/units, currency/scope | Prices, direct costs, returns | Total to same-basis ledger/Revenue; dimension join coverage | Product population/units/definition | Product/mix descriptive evidence; no causal mechanism alone |
| Inventory — stock valuation XLSX (L2) | As-of, item/location, quantity, carrying value, valuation basis, entity/currency | Age, demand, impairment, cost layers | Inventory control with valuation/adjustment map | Population/coverage/stock basis/units | Inventory diagnostics; excess/trapped capital needs benchmark |
| Payroll — payroll export (L2) | Employee/record ID, period, gross/employer components, scope/currency | FTE/hours, department, role, allocations | Payroll P&L/control with accrual/pension/tax mapping | Population/coverage/definition/time | Workforce cost evidence; no inferred capacity/avoidable cost |
| Budget/Forecast — finance XLSX (L2) | Version/vintage, target periods, scope, measure/unit, assumptions | Approval, scenarios, forecast changes | Same-basis actual mapping; assumption lineage | Definition/time/revision; observed truth not verified | Comparator readiness; no predicted Fact or loss |
| Departments/Cost Centres — ledger allocation XLSX (L2) | Stable codes, parent scope, accounts, periods, amounts, allocation basis | Manager, effective dates, reorganisations | Reconcile complete disjoint allocations to ledger | Scope/inclusion/coverage/definition | Segment evidence; prevent overlapping totals |

L3 CRM, pipeline, conversion, salesperson, detailed pricing history, WIP and operational output remain optional advanced sources with their own event/denominator/history contracts. They cannot repair missing Level-1 accounting verification by inference. An export's likely availability is an engineering expectation to test in a pilot, not a measured frequency for £1m–£10m SMEs.

## 11. Reconciliation graph design

Reuse existing lineage references, Dataset assertions, CMC owner bindings and audits. A proposed reconciliation edge retains exact source/target owners, client/entity/period/basis, account/population mappings, Decimal components, adjustments, residual, method/version, evidence and limitations. It is a **verification relation**, not a causal Evidence Graph edge or another financial source of truth. No schema or new vocabulary is implemented by this document.

| Proposed edge | Proof possible | Proof not supplied |
|---|---|---|
| TB ↔ P&L / BS | Complete mapped account amounts for same scope/basis | Correct recognition/valuation merely because sums agree |
| Sales ledger ↔ Revenue controls | Posted net amounts plus explained credits/accruals/adjustments | Identical commercial populations from equal totals |
| Aged AR ↔ AR control | Listed outstanding plus all reconciling items equals scoped control | Contractual due/status completeness, collectability or absence alone |
| Purchase/AP ledger ↔ AP control | Defined liability population/control agreement | Cost avoidability or payment opportunity |
| Inventory ↔ carrying balance | Same-date valuation/control agreement | Excess stock, usable demand, recoverability |
| Payroll ↔ payroll P&L | Scoped payroll components/accrual adjustments | Productivity or removable cost |
| Customer/product sales ↔ Revenue | Complete disjoint same-basis segmentation if joins/coverage also verified | Independence of two views of the same ledger |

Use two distinct witnesses: **arithmetic/control reconciliation** and **semantic population/coverage verification**. Only their conjunction can support a bounded completeness claim. A balanced incomplete extract, omitted zero-net items, duplicated compensating entries, matching totals with different customers and unexplained adjustments must not qualify. Exact Decimal equations and explicit policy-approved residual handling are required; do not reuse the heuristic intake's float-based default tolerance as financial verification authority.

Contradictory edges mark the affected dimension conflicted; they do not average away disagreement. Revision supersession invalidates current dependent witnesses and requires explicit reassessment while preserving history. Cross-source cycles must not create circular authority: derive witnesses from independently retained source/control records, never from mutually asserted VERIFIED labels.

## 12. Evidence Readiness design

Propose a projection of existing owned claims and refusals, not a new evaluator that promotes evidence. Each row includes capability/requirement, scope/window, source IDs, dimension outcomes, authority, verified/declared values, check version, limitations, exact missing evidence and freshness/revision state.

Proposed display statuses (design labels, not new repository enums):

* **VERIFIED** — required scoped evidence checks passed for this requirement, not universal verification.
* **DECLARED** — identified human claim exists; source verification unavailable.
* **PARTIAL** — known included/excluded coverage; no extrapolation.
* **INSUFFICIENT** — required evidence present incompletely or unknown.
* **NOT PROVIDED** — source not supplied; never interpreted as zero/absence.
* **CONFLICTED** — contradictory source/declaration/check evidence retained.

Separate capability state from evidence state. Example: “Monthly population — VERIFIED; production temporal assessment — unavailable under frozen v2.54 boundary.” Another: “Receivables — PARTIAL; identified overdue portion qualified; absence/lifecycle unavailable.” “Financial statements verified” must mean the listed controls and basis checks, not an audit opinion. No readiness percentage, confidence score or mechanical Priority uplift.

## 13. Adviser declaration policy

| Declaration | Legitimate use | Can satisfy positive verification contract alone? | Independent check / contradiction |
|---|---|---|---|
| Accounting period/calendar | Declared reporting context | No for production temporal verification | Export configuration, period rows and posting basis |
| Business-unit/entity scope | Declared organisational scope | No | Source ledger ownership, filters/consolidation map |
| Extract complete | Declared coverage | No | Population manifest, control and omitted-record checks |
| Known exclusions | Explicit declared limitation | Can limit scope; cannot create complete whole-business proof | Source/query filters and excluded membership |
| Restatement/correction | Declared revision relationship | No for verified new-time/replacement classification | Source series, predecessor/change record and revised controls |
| C0/account policy | Declared definition/mapping | No | Applicable account/cost/recognition evidence and recomputation |
| Collection initiative/constraint | Human context/challenge | Not a substitute for current source-authoritative complete review | Dated initiative/contact/contract records with population coverage |
| Materiality/urgency/controllability judgement | Adviser judgement and human decision rationale | No machine dimension promotion | Future dimension-specific contract, if approved |

Every declaration is identified, scoped, timestamped, attributed and audited; correction is a revision. It establishes the fact **that the actor made the statement**, not the truth of the underlying commercial claim. Source contradictions fail the affected comparison closed. Management and adviser can supply source documents; verification attaches to the independently checked document and method, not to the person's declaration.

## 14. Provider leverage ranking

No arbitrary score is used. Ranking weighs breadth, commercial usefulness, likely source availability, complexity, reliability, reuse and false-confidence risk. Availability in £1m–£10m SMEs is a working engineering judgment requiring pilot validation; no frequency percentages are claimed.

| Rank | Proposed reusable provider responsibility | Breadth and practical usefulness | Availability / complexity / reliability | Limits |
|---|---|---|---|---|
| TOP PRIORITY 1 | Scoped ledger/control reconciliation | Potential support for 7 families: DS, MC, CF, BR, IM, OP, TG; widest reusable accounting witness | Core accounting exports reasonably plausible; medium-high mapping complexity; reliable scoped arithmetic with retained sources | Alone does not verify population or activate consumers |
| TOP PRIORITY 2 | Period/scope/definition plus population/coverage verification | Makes controls meaningful and eleven-dimensional comparisons possible | Configuration/filter evidence less consistently exported; high semantic complexity | Unknown settings must remain unknown; no header guessing |
| TOP PRIORITY 3 | Revision/restatement verification | Prevents artificial movement and preserves corrected evidence across MC/DS/TG/BR | Report revision records may be available; medium complexity | Changed filename/hash/import date is insufficient |
| TOP PRIORITY 4 | Typed monthly commercial/ratio observation qualification | Connects qualified evidence to lawful Revenue/C0 Fact owners and measurement slots | Revenue often accessible; C0 direct-cost detail less certain; medium-high/high complexity | Cannot transplant P&L amounts into a sales contract or guess GP=C0 |
| TOP PRIORITY 5 | Complete receivables absence verification | High practical value for lifecycle; reuses existing positive AR qualification | Aged AR plausible; complete current terms/status review harder; high complexity | Empty universe, family/subject and production-origin decisions required |
| SECONDARY | Complete ancestry / independent corroboration | Quality/Attention and condition Story prerequisites | Truly independent exact same-basis peers less common than copied exports; high ownership complexity | Independence is not completeness or economic mechanism |
| SECONDARY | Collection evidence readiness | Extends practical use of existing Opportunity contract without changing it | Contacts often plausible, complete exact matched histories uncertain | Many SMEs may remain unqualified; no scaling/new capture method |
| SECONDARY | Narrow actual-loss evidence | Specific observed-loss cases may have accounting support | Write-off evidence plausible but comparator/authority needs qualification | New source-specific Impact contract, outside recommended core |
| DEFER | Mechanisms, additional Stories/Bridges/Impact methods | Potential future breadth | New reasoning/comparator contracts, high risk | Not merely reusable provider work |
| DEFER | Relative materiality, urgency/control, Priority integration, AI/action/benefit | Future adviser value | Separate policy/authority/consumer qualification needed | No implicit recommendation or source-of-truth switch |

The provider catalogue should be **responsibilities within existing authorities**, not seven independent databases. A bounded pack adapter routes into registered immutable sources; verifiers publish evidence-backed Dataset/CMC claims; absence verifier builds on exhaustive AR qualification. Use one audited verification boundary with per-dimension methods, rather than separate competing population/coverage truth layers.

## 15. Recommended v2.55 scope

### Required architectural decision before implementation

Approve or decline a new additive production qualification contract/owner route for trusted verified evidence, typed monthly observations and absence. Preserve the existing v2.54 route and all synthetic/refusal tests; preserve policies and thresholds. Review lawful Dataset owners/families, compound C0 binding, empty AR proof and cash-series subject identity explicitly. This is a real application-boundary extension, **not evidence-only configuration**. No implementation should start under the false premise that existing production validators already allow it.

If declined, implement only bounded evidence/readiness qualification in a later approved contract, with production temporal outcomes still NOT_ASSESSED. If approved, the smallest coherent proof comprises:

1. Bounded finance-pack ingestion into existing registered owners, with explicit schema/mapping and fail-closed unsupported/conflicting sources; no universal spreadsheet inference.
2. Scoped TB/statement and Revenue/AR controls plus period/definition/population/coverage verification. Persist only independently supported dimensions; audit declarations separately.
3. Source-supported revision/restatement relationships and current-source revalidation.
4. Lawful exact monthly Revenue/C0 observed-slot bindings, eligible Fact/Finding ownership and explicit window history. No changes to diagnostic calculations, canonical thresholds or consumers.
5. Complete AR classification and absence witness, including an honest empty-universe case, plus reviewed owner/subject identity.
6. Only through the approved new boundary: production descriptive Revenue trajectory, C0 trajectory/direction and AR lifecycle, reusing frozen arithmetic/meaning and retaining all negative cases.
7. Readiness projection/specification showing verified, declared, partial, conflicted and unavailable requirements; no Priority or API cutover in this release unless separately approved.

These three paths remain a good target **conditional on that architectural decision**. Reconciliation offers broader reuse than temporal alone, so implement its verifiable foundation first. If C0 data is insufficient, refuse it honestly; do not reduce standards to secure three positives. Qualification must prove failure states as well as lawful production positives and synthetic segregation.

## 16. Deferred gaps

Keep explicitly unavailable: pricing/cost/mix mechanism support; positive mechanism-resolved Story; LOW_QUALITY_GROWTH without same-basis Revenue/margin condition; PROFIT_TO_CASH_DISCONNECT without governed reconciliation/Finding; COST_GROWTH_OUTPACING_ECONOMIC_OUTPUT without comparable cost/output Finding. Existing mechanism assessment unconditionally supplies unresolved requirements; data alone cannot promote it under frozen v2.46.

Keep Profit-to-Cash and Cost-to-Output Bridges refused. Existing annual Revenue/C0/WC contracts require their governed period/source proof; verified Dataset comparisons do not silently replace BIQ's same-source/cross-version restrictions. Do not extrapolate partial detail or classify unexplained residuals.

Defer non-AR CASH_TRAPPED, all seven other new production Impact writers, new Opportunity methods/exposure scaling, relative materiality, urgency/control, automatic Priority persistence, recommendations, AI, publication, Action Plans, realised-benefit attribution and memory. Preserve legacy management calculations and outputs; their run-count persistence, legacy statuses and float-based summaries are not canonical production verification evidence.

## 17. Proposed realistic blind finance-pack qualification

**Design only; no workbook or expected-result dataset created.** Inputs should be ordinary source exports and supporting accounting/contract documents, not prebuilt Profit Doctor evidence objects. No internal labels such as ABSENT_VERIFIED, MATCH, INCREASING or WORSENING.

Minimum pack for the proposed three-path proof:

1. Trial Balance with monthly movement/closing controls and account mapping for one legal entity/ledger/currency.
2. Monthly P&L with explicit periods, Revenue and supported direct-cost/C0 components and recognition policy.
3. Monthly Balance Sheet with exact month-end AR/AP/inventory/cash controls.
4. Sales invoice/transaction ledger with all relevant months, identities, credits, scope/export filters and qualified direct-cost detail where C0 relies on commercial data.
5. Complete month-end aged AR snapshots, including within-terms, overdue, excluded and unresolved test records; a genuinely empty snapshot case if that new witness is approved.
6. Applicable customer terms/contracts and dated invoice status/review records (payment plans, disputes, pending credits and complete review coverage), plus extraction/settings manifests and reconciliation adjustments.
7. Source revision/change record with a same-period corrected export and explicit predecessor.

Use at least three full adjacent months for Revenue/C0 trajectory and an explicit history window. Include additional snapshots to test PRESENT→absence→PRESENT lifecycle, unknown/missing month and unresolved classification separately. Financial files alone cannot support absence without complete terms/status review.

Minimum **useful limited Review**, not all proof paths, can begin with TB + monthly P&L + BS and scope/period policy, with readiness clearly showing missing detail. Add sales ledger and aged AR/terms/reviews for meaningful commercial/receivables evidence. Customer/product reports, inventory/payroll detail, budgets and CRM are optional enrichments; C0 cannot qualify without its necessary costs regardless of pack size.

Blind design controls:

* Freeze architecture, mapping and policies before private expectations are exposed; separate the private grading authority from the source pack. Independently derive controls and classification; do not fit implementation to totals.
* Include matching totals with different populations, omitted zero-net/offsetting records, partial extracts, incompatible currencies/definitions, wrong scope, contradictory declarations, missing/cached-invalid formulas and duplicate periods.
* Include restatement versus new observation, competing revisions, month gaps, nonpositive prior Revenue, exact below/equal/above thresholds, and C0 percent versus pp.
* Include due-on-reporting-date, optional original amount, stale/unverified status, plan/dispute/credit exclusions, partial control coverage, complete no-qualifying balance and an empty universe. Absence must fail if any required review is missing.
* Include shared ancestry versus genuinely independent evidence; evidence-quality support must not become economic mechanism support or materiality uplift.
* Exercise real registered source providers and approved production boundaries, never test-only trusted payload injection. Separately retain synthetic tests.
* Qualify Decimal/replay/revisions/audit, tenant/run/scope integrity, caller rollback, frozen-schema preservation and live PostgreSQL only through the established disposable safeguards. Do not assume a migration is needed before persistence design is approved.

Expected results may include several refusals. A useful pilot does not require every capability positive; it requires truthful, explainable readiness and governed evidence.

## 18. Adviser Edition implications

The evidence layer supports: bounded upload → scoped evidence readiness → governed analysis → attributable adviser review. It does **not** complete recommendations → AI Adviser → client report. Those later stages need explicitly approved consumer and human-authority contracts.

Before a controlled real-business pilot, establish authenticated adviser/client ownership, secure upload/storage/retention, bounded export onboarding and mapping review, source permissions, readiness/provenance display, privacy controls, contradiction/correction workflow and explicit canonical-versus-legacy output authority. A run-level client check is useful but does not by itself establish complete product authentication/authorisation. No universal readiness score or diagnostic count can substitute for evidence review.

A read-only adviser Review pilot may precede recommendation/AI capability if it labels limitations and prohibits unsupported monetary/causal claims. Positive Priority, automatic recommendations, publication and realised Benefit remain unavailable until their own policies, integration, human sign-off and qualification are approved. v2.55 should not turn into a product/dashboard rewrite or a parallel canonical/legacy authority.

## 19. Risks / stop conditions

Stop for architectural review if:

* A provider must guess currency, period, definition, population, exclusions, scope or revision relationship.
* Totals/row counts/reconciliations are being used to prove dimensions beyond their witnesses.
* An adviser/management assertion, actor label or internal VERIFIED field substitutes for authenticated source verification.
* Production data must be relabelled synthetic or frozen v2.54 refusal weakened to obtain a positive.
* Aged AR must be mislabelled GL, an empty population needs a dummy invoice, or a C0 ratio is relabelled GP/transplanted from an incompatible accounting basis.
* Impact/Opportunity capture semantics, exact exposure, initiative completeness or overlap safeguards would need relaxing.
* Historical migrations/fixtures need rewriting, diagnostic calculations must change or a broad generic ingestion/refactor project appears necessary.
* An unsupported causal, financial, urgency, controllability or AI conclusion is introduced.

The unconditional temporal refusal is a confirmed stop condition for **provider-only positive production design**. This audit resolves the premise and presents the smallest decision required; it does not authorise that extension. Current production refusals remain correct until approved trusted routes and all prerequisites exist.

Audit validation is limited to read-only repository inspection and document consistency/whitespace review. No qualification suites, PostgreSQL, Neon API or private workbook/grading material were accessed for this audit. No source/test/migration change is required to deliver the document.

## 20. Explicit acceptance answers

1. **Five highest-leverage gaps:** (a) scoped accounting/ledger control reconciliation; (b) semantic population/coverage/period/definition verification; (c) source-supported revision/restatement identity; (d) lawful monthly Revenue/C0 canonical observation and CMC bindings; (e) complete AR absence proof including honest owner/empty-universe handling. The trusted publication/production-boundary decision is a prerequisite across these, not optional plumbing.
2. **Single highest-reuse provider:** scoped ledger/control reconciliation, with potential dependencies across seven named families. It supplies bounded witnesses, not seven automatic positive outcomes. Population verification must accompany it.
3. **Revenue temporal without changing v2.54?** No. Better providers alone cannot overcome unconditional canonical refusal. An additive separately versioned production boundary requires approval; frozen policies and old routes can remain intact.
4. **C0 temporal without changing v2.54?** No, for the same boundary reason plus absent lawful ratio/month binding and semantic verification. No GP substitution.
5. **Production CASH_TRAPPED ABSENT_VERIFIED evidence?** Complete scoped/reporting-date AR universe, exact authoritative control reconciliation, invoice identities/outstanding amounts, applicable contractual due/terms, complete current source-status/constraint review, no unresolved classifications, no qualifying overdue unconstrained positive balances, immutable lineage/authority/revision and all temporal Dataset dimensions. See section 9 for empty-universe, owner and subject restrictions. This proof cannot currently enter frozen canonical absence.
6. **Impact categories realistic from ordinary L1/L2?** CASH_TRAPPED already positive narrowly for AR. Narrow OBSERVED_LOSS or AVOIDABLE_COST cases may be feasible with actual loss/contractual alternative evidence and newly qualified contracts; balances alone cannot activate them. No claim that all seven generic categories become positive via a provider.
7. **What stays deferred?** Run-rate, capital/risk, future/upside, realised attribution, non-AR trapped benchmarks and broader Opportunity/mechanism/Story/Bridge contracts; relative materiality, urgency/control and automatic Priority integration.
8. **Permissible declarations?** Period, scope, completeness, exclusions, definition and restatement context may be attributable declarations. Positive dimensional verification/absence/independence/economic capture needs independent source/machine checks; source contradictions are retained and fail closed. Human adviser decisions remain human authority.
9. **Minimum valuable SME Review pack?** TB + monthly P&L + BS + explicit scope/period policy for a limited Review; sales ledger and aged AR/terms/status reviews for valuable commercial/cash evidence. The full three-path proof additionally needs qualified C0 detail, monthly history, extraction/control witnesses and revision records. Optional enrichment remains optional, required proof does not.
10. **What should v2.55 implement?** After the production-boundary decision: bounded registered pack transport, scoped reconciliation, per-dimension verification, revision evidence, lawful monthly observation bindings, complete AR absence evidence and transparent readiness. Positive production temporal proof only through the separately approved trusted contract; otherwise readiness-only scope.
11. **What must it not implement?** General spreadsheet inference, frozen validator bypass, synthetic relabelling, changed diagnostic/Impact/Opportunity semantics, new causal mechanisms/Stories/Bridges, urgency/control/materiality scores, recommendations, AI, Action Plans or Benefit attribution; no automatic consumer cutover.
12. **What remains before first controlled pilot?** Trusted boundary qualification, secure/authenticated tenant-scoped source onboarding, explicit output authority/readiness, correction/review workflow, realistic blind source qualification and applicable local/live/CI gates. Recommendations/AI/client publication need separate release authority; a bounded human-reviewed evidence Review can be piloted earlier with honest refusals.

**Decision requested:** approve a bounded additive trusted production evidence/temporal boundary while preserving frozen semantics, or approve evidence/readiness-only v2.55 with continued production temporal refusal. No code was implemented, and no v2.56+ work was begun.

READY FOR V2.55 ARCHITECTURE DECISION

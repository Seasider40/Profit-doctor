# v2.50 Opportunity feasibility and approved evidence-boundary resolution

## Approved resolution

The initial stop below was reviewed and approved. The user subsequently
authorised a generic collection-evidence provider and an empirical comparable-
outcomes methodology, independently of the hidden v2.50 workbook. That narrow
implementation is described in [V2_50_OPPORTUNITY_ENGINE.md](V2_50_OPPORTUNITY_ENGINE.md).

The historical assessment below remains the record of why the v2.49 snapshot
alone could not establish Opportunity value. Its statements about implementation
and qualification status describe the initial stop, not the current tree.

Current feasibility differs in one category: CASH_TRAPPED is
QUALIFIED_FOR_OPPORTUNITY_CONTRACT **only** for current OVERDUE_RECEIVABLES_1
Impacts accompanied by the new qualified collection evidence. Other CASH_TRAPPED
sources remain unsupported. The other seven classifications below are unchanged.
The implemented contract requires complete matched historical cohorts, explicit
addressability and prior-initiative review; missing evidence still produces no
positive Opportunity. No generic recovery-percentage fallback was authorised.

The v2.50 blind workbook has not been requested, opened or used. No commit or
push has been performed. See the engineering document for current qualification
results and the intentionally narrow comparability/aggregation limitations.

## Historical initial assessment

## Baseline and status

`main` and current `origin/main` are at
`132d3ea8be1bf3d79179a06884e104c4c6def246`. The starting working tree was clean;
`git pull --ff-only origin main` reported already up to date. The user identifies
this as the frozen, cross-platform-qualified v2.49 receivables baseline.

This is an initial feasibility assessment, not an implemented Opportunity Engine.
No v2.50 blind workbook was requested, opened or used. No production code, test,
migration, existing architecture document or runtime consumer has been changed.
No commit or push has been performed.

## Authority inspected

The v2.43 domain-foundation document establishes typed identity, independent
confidence/materiality, Decimal serialization, lineage, EconomicEffect/overlap,
caller-owned transactions and the controlled canonical evolution boundary.
The v2.49 Impact feasibility/engineering documents describe the initial Impact
slice; their earlier statements that no production positive contract exists are
superseded specifically by V2_49_RECEIVABLES_QUALIFICATION.md and its approved
implementation. They must not be read as overriding the receivables extension.

Concrete implementation evidence:

- `reasoning/impact/registry.py`: only OVERDUE_RECEIVABLES_1 is a qualified
  production-positive provider contract; the generic eight-category registry is
  not a positive writer.
- `reasoning/impact/contracts.py`: ReceivablesImpact is a CASH_TRAPPED/CASH
  contract; the other positive contract is explicitly synthetic. Qualification
  preserves the full source document and typed positive result.
- `reasoning/receivables/contracts.py`: invoice dates, terms, outstanding balance,
  dated blocking status and source references are governed. There are no fields
  establishing collection authority, strategic addressability, prior initiative
  coverage or horizon-specific prospective capture.
- `reasoning/impact/receivables.py`: qualification explicitly disclaims recovery
  guarantees and Opportunity value. NONE_RECORDED concerns its governed blocking
  statuses; it does not establish absence of existing collection activity.
- `intake/receivables.py`: Payment History and Customer Contracts are explicitly
  unconsumed as positive providers. Recognising a sheet is not qualified recovery
  evidence. No workbook data was inspected for this assessment.
- `economic/engine.py`: legacy qualification accepts caller-provided amounts and
  mechanism evidence under a separate legacy Story/Finding route. Its supported
  evidence label cannot certify a canonical population or capture methodology.
- `core/db.py` and `management/engine.py`: legacy actions/progress exist and must
  remain intact, but their current schema does not establish canonical
  invoice-population membership, a complete review of prior recovery activity,
  or expected recovery attributable to initiatives already underway. Created-at
  timestamps/free-text status are not a substitute for that evidence.

## Eight-category matrix

Classification concerns a defensible positive canonical Opportunity contract
with the currently governed sources, not merely serialization of a category.

| Impact category | Classification | Current boundary and prerequisite |
|---|---|---|
| OBSERVED_LOSS | INSUFFICIENT_EVIDENCE | No qualified production loss writer. A qualified loss alone would still need evidence of a prospective addressable mechanism, incrementality and capture horizon. |
| RUN_RATE_LEAKAGE | INSUFFICIENT_EVIDENCE | No qualified production leakage writer or governed persistence/counterfactual basis. Neither annualisation nor capture can be inferred. |
| CASH_TRAPPED | PARTIALLY_QUALIFIED | OVERDUE_RECEIVABLES_1 supplies an eligible, scoped, exact Impact population. Collection addressability, prior-initiative review and capture evidence remain unqualified. Candidate eligibility is feasible; a positive capture amount is not established. |
| AVOIDABLE_COST | INSUFFICIENT_EVIDENCE | No production-qualified avoidable-cost source; addressability, alternative cost state and incremental capture would need separate evidence. |
| CAPITAL_AT_RISK | INSUFFICIENT_EVIDENCE | No production-qualified exposure/risk source. Concentration cannot substitute for one; risk reduction is not cash collection. |
| FUTURE_EXPOSURE | INSUFFICIENT_EVIDENCE | No qualified scenario Impact or evidence of addressable incremental mitigation over its horizon. |
| VALUE_CREATION_POTENTIAL | INSUFFICIENT_EVIDENCE | No qualified production upside Impact. Revenue growth and Bridge residuals cannot bypass the Impact gate. |
| REALISED_BENEFIT | NOT_APPLICABLE | An already realised benefit is not prospective capture potential. Further improvement would require a distinct qualified prospective Impact and contract, not re-use of realised value. |

No currently governed evidence is qualified for a positive production Opportunity
amount. This does not invalidate CASH_TRAPPED or imply that its capture potential
is zero. An unresolved or unquantifiable candidate remains a valid future result.

## Stop condition

Section 32 of the supplied engineering contract requires stopping if existing
action cannot be distinguished from incremental opportunity, or addressability
and recoverability would require invented control or arbitrary percentages.
The current application boundary cannot make that distinction for the canonical
receivables population. Assuming no initiative exists because no reference is
present would fabricate incrementality. Treating ordinary overdue status as
management control, or applying a recovery fraction to it, would fabricate
addressability/capture evidence.

The absence of a capture provider is not a v2.49 defect; that release expressly
excluded recoverability. Legacy supported statuses must not be silently promoted
to the stronger canonical semantics. No historical migration or frozen validator
needs alteration to resolve this boundary.

## Smallest proposed resolution (not implemented)

Add a generic, retained and versioned collection-evidence provider alongside the
existing snapshot provider, without changing the snapshot's original meaning:

1. Resolve the exact current qualified ReceivablesImpact through its owning
   service; preserve client/run, source snapshot/revision, invoice identities,
   EconomicEffect, scope, currency and REAL_SOURCE/BLIND_QUALIFICATION origin.
   Candidates, synthetic positives, stale sources and other layers fail closed.
2. Record dated management authority and strategic/contractual constraints at an
   explicit invoice/amount scope. A management-authorised constraint can restrict
   addressability without verifying a recovery prediction. Absence remains
   unknown. Addressable, excluded and unresolved partitions must reconcile to
   the eligible Impact population, not the full ledger.
3. Record a complete-or-partial review of existing initiatives at assessment time,
   their source identity, evidenced commencement, covered population and expected
   baseline recovery where established. Read existing activity as evidence; do
   not create tasks, owners, instructions, Action Plans or Decision workflows.
   Missing review or unquantified overlapping activity blocks newly claimed value
   for the affected portion. Do not invalidate the source Impact.
4. Define a separate versioned capture-evidence contract and methodology before
   enabling a positive writer. It must explain evidence authority, the baseline
   without the new opportunity, incremental capture, a defined horizon, and why
   any low/high/central values apply to this population. Historical outcomes need
   a qualified denominator, comparison population, observation window and
   applicability policy; selected successful payments alone are insufficient.
   Caller-supplied percentages or a generic evidence-string label are insufficient.
5. Preserve exact Decimal ranges and an optional independently justified central
   estimate. Do not manufacture a midpoint, annualise, extrapolate coverage or
   add a central estimate to the range. Unknown capture is null/unquantifiable,
   not zero. A forecast is not an already realised benefit.

The outstanding design decision is the first defensible capture-evidence
methodology and its trusted source boundary. It must be settled independently
of the hidden v2.50 workbook. A generic field accepting claimed recoverability
would not resolve this decision.

## Opportunity architecture once the boundary is qualified

Reuse OPPORTUNITY_CANDIDATE and VALIDATED_OPPORTUNITY foundation identities with
typed canonical extensions and explicit source-Impact FKs. Keep the legacy
economic/management writers and product consumers unchanged; no automatic cutover.
Candidate creation and qualification remain separate operations. Candidate
eligibility alone does not create a positive amount.

Proposed outcomes are QUALIFIED, PARTIALLY_QUALIFIED, UNRESOLVED,
NOT_ADDRESSABLE, REJECTED and INSUFFICIENT_EVIDENCE. A partially qualified result
must distinguish the positive supported subset from unresolved/excluded value;
only its qualified portion could enter a compatible total. Missing evidence does
not require a negative conclusion about the Impact.

Reuse ConfidenceProfile, materiality without ranking, source lineage, immutable
revisions, replay identity and audit. Retain explicit assessment and horizon dates;
different horizons are not equivalent. Reassessment creates history and validates
the current source and evidence before totals. Use an additive forward migration
only after the source/contract boundary is resolved.

Reuse the source EconomicEffect and overlap infrastructure. Different labels,
mechanisms or horizons never prove independence. Identical same-effect valuations
may deduplicate; conflicting alternatives cannot be summed or resolved by picking
the larger value. PARTIAL_OVERLAP, PARENT_CHILD and UNKNOWN_OVERLAP block unsafe
aggregation. INDEPENDENT requires qualified proof. Aggregate only compatible
dimension, currency, scope, coverage, horizon, evidence origin and methodology;
no universal profit/cash/risk total.

## Qualification and continuation

No implementation qualification has been run: there is no v2.50 implementation
to compile, migrate or test. The baseline's 662-test / 144-live-check results are
historical accepted evidence, not newly rerun v2.50 results. No live database was
accessed or changed. Only this feasibility document has been added.

After resolving the evidence contract, implement the narrow canonical slice and
the required adversarial tests, then migration/persistence, inherited regression,
strict warnings and the established disposable live qualification with the host
awake. No Golden Manufacturing v2.50 blind workbook is needed for that design.

No v2.51+ functionality, code change, assertion relaxation, commit or push.
Status: NOT READY — REMEDIATION REQUIRED.

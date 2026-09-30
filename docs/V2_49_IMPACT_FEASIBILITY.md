# v2.49 Economic Impact feasibility — approved strict boundary

## Baseline and scope

Inspected clean `main` at `91dbfee35292c2e7658fd1741a571b2069ce2eef`.
`git pull --ff-only origin main` reported already up to date. The user has frozen
v2.48 after all four CI matrix jobs passed. This document records the initial assessment and its approved resolution.
Implementation and qualification are recorded in V2_49_ECONOMIC_IMPACT.md. No commit or push is authorized.

The design sources are the supplied v2.49 engineering contract and the repository
v2.43 foundation, v2.44 canonical registry, v2.46 feasibility/Interpretation,
v2.47 Story, and v2.48 CMC/BIQ/Bridge architecture and implementations.

## Eight-category feasibility

These classifications concern positive generation through the current governed
application boundary, not the ability to serialize the existing eight enum values.

| Category | Classification | Candidate governed sources | Required evidence and calculation basis | Period, uncertainty and overlap | Missing qualification |
|---|---|---|---|---|---|
| OBSERVED_LOSS | INSUFFICIENT_EVIDENCE | Canonical revenue/C0 Facts, Findings and Bridges; condition Stories | Evidence of an actual loss; a justified comparison or counterfactual where needed. Movement or residual alone is insufficient. | Exact loss interval, population and original measure; transaction/aggregate paths may share one effect. | No qualified loss contract. Frozen transaction-loss Signal mappings lack required identity; a declining comparison is not proof of value lost. |
| RUN_RATE_LEAKAGE | INSUFFICIENT_EVIDENCE | C0 margin condition and comparable annual C0 Bridge | Qualified underperformance basis, observation window, persistence and periodisation assumptions; no automatic multiplication by twelve. | Observation and projected windows must be separate; seasonal uncertainty and overlap with observed loss/upside remain explicit. | No governed leakage counterfactual or persistence/seasonality contract. Economic-mechanism Interpretations remain unresolved. |
| CASH_TRAPPED | INSUFFICIENT_EVIDENCE | Current qualified Working Capital Bridge, its CMC bindings and BIQ assessments | AR + inventory - AP measurements are qualified inputs only. Positive classification additionally requires a defensible comparable required position and evidence of excess/trapping. | Two December year-end snapshots, complete legal-entity trade-WC scope. Net total and component views must share economic identity; stock and stock-change views cannot be added. | Governed excess/trapped-position counterfactual is missing; stock growth alone is insufficient. |
| AVOIDABLE_COST | INSUFFICIENT_EVIDENCE | Potential future typed cost Facts/Findings; existing supplier observations do not suffice | Evidence of avoidability and a defensible alternative cost state; cost increase alone is not avoidable cost. | Matched scope/window and implementation-independent assumptions; may overlap loss/leakage. | Governed avoidability evidence and counterfactual absent. Cost-to-Output Bridge remains refused. |
| CAPITAL_AT_RISK | INSUFFICIENT_EVIDENCE | Concentration condition Story; future typed exposure evidence | Identified capital amount and a supported risk connecting that capital to exposure. No probability of failure inferred from concentration. | As-of exposure and risk horizon, valuation uncertainty, overlap with future exposure. | Concentration establishes neither exposed capital nor loss probability. Heterogeneous FINANCIAL_EXPOSURE mapping remains unqualified. |
| FUTURE_EXPOSURE | INSUFFICIENT_EVIDENCE | Future governed scenarios and risk evidence | Explicit supported scenario, baseline, horizon and downside calculation; illustrative scenario Signals are not observed Facts. | Future horizon and range; exposure is not realised loss; capital-at-risk overlap must be declared. | No canonical scenario/counterfactual qualification contract. |
| VALUE_CREATION_POTENTIAL | INSUFFICIENT_EVIDENCE | Comparable Revenue/C0 Bridges as descriptive inputs only | Defensible alternative economic state and explicit counterfactual calculation. Revenue growth is not value creation. | Counterfactual horizon, scope and uncertainty; possible overlap with leakage/avoidable cost. | No governed upside counterfactual. No addressability or Opportunity assumptions may fill this gap. |
| REALISED_BENEFIT | DEFERRED | Legacy benefit controls exist but are not automatically canonical authority | Observed improvement plus qualified attribution and baseline, with contradictory evidence considered. | Realisation interval and persistence; improvement must not be counted again as potential or loss avoided. | No qualified canonical benefit-attribution integration. Later Benefit Realisation work must not be pre-empted. |

No positive production category is qualified today. The approved implementation
provides candidate qualification and separately labelled synthetic positive checks.

## Exact Working Capital boundary

The frozen Bridge establishes, for Golden Manufacturing:

- net trade WC at December 2025: GBP 1,650,000;
- net trade WC at December 2026: GBP 2,350,000;
- net carrying-amount increase: GBP 700,000;
- components: AR +550,000, inventory +350,000, AP contribution -200,000;
- inverse stock-change cash-direction projection: GBP -700,000.

`bridge/engine.py` constructs the projection as the negative of each component.
It does not read operating cash flows or reconcile noncash movements. The source
basis declares consistent balance definitions; it does not establish an efficient
working-capital target, excess balances, recoverability or a cash-flow statement.
The authoritative v2.48B document explicitly preserves this distinction.

Therefore neither an actual GBP 700,000 cash outflow nor GBP 700,000 of excess or
recoverable cash may be asserted from this Bridge. No missing noncash movement is
being alleged; the evidence simply does not resolve that question.

## Approved decision

The user rejected classifying NET_TRADE_WORKING_CAPITAL_STOCK_INCREASE as CASH_TRAPPED.
It remains solely a Bridge movement. CASH_TRAPPED requires a defensible excess or
trapped position relative to an explicit comparable required position. Golden
Manufacturing may create a candidate but no qualified Impact or Impact total.

Future evidence could include separately qualified operational inventory needs,
contractual terms, normalised working-capital requirements or comparable history.
Scope, as-of, currency, population, authority, assumptions and revision must match.
No unsupported benchmark or recoverability/addressability logic is permitted.

All eight current production categories remain unqualified. The approved release
implements the candidate/qualification boundary and a small synthetic positive
contract. Fixture evidence must remain distinct from production evidence and can
never enter production totals. The initial classification stop is resolved.

## Reuse and aggregation design boundaries

The existing v2.43 EconomicEffect, EffectReference, EffectOverlap and audit service
can be reused. No effect-store redesign is indicated. Typed Impact state can extend
the existing ECONOMIC_IMPACT identity, as earlier semantic slices do. Its separate
typed lifecycle must not relax frozen foundation status validation.

Bridge snapshot/source FKs would retain the existing Bridge and CMC authorities;
FoundationService's closed canonical-lineage resolver must not be bypassed by
pretending a Bridge is a reasoning_object_v243. A typed source reference is needed
at the Impact boundary. This is an additive design requirement, not permission to
weaken the frozen resolver or duplicate source records.

Proposed aggregation policy is fail-closed: exact dimension, category, amount basis,
currency, scope and compatible period are required. One effect is counted once;
conflicting valuations of that effect require reconciliation, not arbitrary choice.
Distinct IDs do not establish independence. PARTIAL_OVERLAP, PARENT_CHILD and
UNKNOWN_OVERLAP block naive totals; SAME_EFFECT must not double count. An
INDEPENDENT declaration requires governed evidence and cannot be inferred from
different diagnostics, runs or sources. No universal total is allowed. These are
design requirements; implemented behaviour and qualification are recorded in V2_49_ECONOMIC_IMPACT.md.

No Revenue/C0 residual is classified. Exact Contribution 0 remains distinct from
gross profit and EBITDA. Partial selected detail is never extrapolated. Neither
refused Bridge becomes available. No Story or Hypothesis is promoted or reassessed.

## Continuation

See V2_49_ECONOMIC_IMPACT.md for implementation, qualification and limitations.
The earlier stock-only CASH_TRAPPED proposal is not implemented. No frozen
semantic change, effect-store redesign or v2.50 work is authorized.

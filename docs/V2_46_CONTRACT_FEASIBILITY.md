# v2.46 contract feasibility and evidence boundaries

Work in progress. This is an implementation investigation, not release qualification.
Baseline: main at 8bd6c130efe879991bebc7ad0347c69e8f3a5b13, clean at commencement;
all four frozen v2.45 CI jobs passed. The approved reconciliation preserves the
v2.44 refusal registry and v2.45 entity/period/ancestry boundaries.

## Economic mechanisms considered

| Candidate | Origin | Available evidence | Missing disconfirmation evidence | Current safe result |
|---|---|---|---|---|
| Price erosion | Margin movement | Aggregate margin and mechanical aggregate price effects | Qualified like-for-like customer/product price history, product identity, units, matched periods and direct costs | UNRESOLVED; matching directions cannot distinguish cost or mix |
| Input-cost pressure | Margin movement | Supplier-item purchase price variance | Qualified quantity/comparability basis, matching product/direct costs and selling-price recovery | UNRESOLVED; supplier-item evidence cannot silently become aggregate attribution |
| Product/customer mix | Margin movement | Product revenue-share changes and portfolio residual | Qualified segment-to-aggregate relationship, comparable segment margins and coverage | UNRESOLVED; residual includes new/lost and incomparable products |
| Price/volume composition | Revenue movement | Mechanical price and volume effects and bridge reconciliation | Independently corroborated comparable basis, qualified disconfirmation of portfolio/coverage differences | Descriptive bridge is available; explanatory support is not yet established |
| Customer dependence mechanism | Customer concentration | Largest customer share, customer revenue and contribution | Qualified causal mechanism and matching temporal/segmentation evidence | Concentration remains a condition; its cause is not established |

These are candidates for evidence-gap outputs, not implemented resolvable economic
contracts. No retained measurement is changed, no missing identity is reconstructed,
and no generic Fact or graph fallback is allowed.

## Evidence-quality propositions considered

The existing graph can compare exact same-scope, same-period, same-metric canonical
measurements with complete, disjoint retained ancestry. Such comparisons can test
whether a condition is independently corroborated, or whether comparable retained
measurements disagree. They cannot explain the economic mechanism behind it.

Any eventual contract for these propositions must explicitly identify its
evidence-quality scope. SUPPORTED for reproducibility must never render as supported
pricing, cost, mix or root cause. Provenance independence is only as strong as the
retained ancestry; it does not certify absence of undocumented source copying.
Data confidence remains separately NOT_ASSESSED unless a qualified rule establishes
it. The user approved class-scoped evidence-quality support: it must never promote
an economic-mechanism proposition. The implementation follows that decision.

## Evidence-gap value contract implemented

`reasoning/hypothesis/gaps.py` defines a deterministic versioned assessment component:
kind, missing evidence, reason required, dimension, reporting scope, investigation
request, blocking direction (support, contradiction or both), and related object IDs.
It rejects unknown vocabulary, blank/control-character descriptions, duplicate IDs
and extra fields. Related IDs are sorted for deterministic serialization.

This component is not persisted independently. Its containing Interpretation and
service own endpoint existence, client/run scope, audit and persistence. It does
not authorize actions, promote confidence or fill missing evidence.

At the initial checkpoint, eight value-contract tests passed with DeprecationWarning
and ResourceWarning treated as errors. Migration, live and complete-estate results
are tracked in the authoritative engineering document; this checkpoint is not a
claim of completed release qualification.

## Resolved continuation boundary

The approved class distinction is implemented in the contract registry and typed
Hypothesis/Interpretation extensions. See V2_46_HYPOTHESIS_DISCONFIRMATION.md for
the implemented catalogue, persistence and final qualification results.
Missing pricing/cost/mix semantics remain controlled prerequisites for the relevant
future Stories, not permission to repair frozen evidence in this release.

No commit/push, segmentation layer, diagnostic changes or v2.47 work.

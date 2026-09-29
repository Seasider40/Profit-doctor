# v2.48 Economic Bridges: feasibility checkpoint

Initial checkpoint: STOPPED before implementation under contract section 27.
The subsequent user approval authorised Bridge Input Qualification; see
V2_48_BRIDGE_INPUT_QUALIFICATION.md for the implemented layer and reassessment.
The sections below preserve the original feasibility findings and proposal.

## Verified baseline

Clean main at fec375f9701af9052748e58907431a1da3f83f8e. Pulling origin/main
with fast-forward-only reported already up to date. GitHub Actions run
36551728632 completed successfully for Ubuntu/Windows x Python 3.12/3.13.
The recorded frozen qualification is 496 discovered, 487 PASS, 0 FAIL, 0 ERROR,
9 live skips; 178/178 live PostgreSQL and 188/188 focused compatibility PASS.
Those counts are historical v2.47 evidence, not new v2.48 test results.

## Feasibility matrix

PARTIALLY_QUALIFIED means useful measurements exist; it does not authorize a
reconciled v2.48 Bridge. No family is currently QUALIFIED_NOW at the existing
canonical evidence boundary under the new comparability requirements.

| Family | Classification | Opening / closing and available components | Missing qualification / disposition |
|---|---|---|---|
| REVENUE_BRIDGE | PARTIALLY_QUALIFIED | Prior/current comparable sales revenue in GBP; customer movements, new/lost/existing customer aggregates; mechanical price/volume and explicit portfolio residual | Separate qualified window boundaries, coverage and restatement policy are not retained in canonical Facts. Customer legs are truncated to ten and have different entity scope. Component dates are absent. Defer calculation until a governed source-binding/comparability contract exists. |
| MARGIN_OR_PROFIT_BRIDGE | PARTIALLY_QUALIFIED | Prior/current Contribution 0 GBP or Contribution 0 margin percentages, with movement in percentage points; mechanical margin-rate effect in GBP | Signals omit dates; no qualified cross-metric period/basis binding. Price/cost/mix attribution remains unqualified. Contribution 0 must never become gross profit. Defer calculation. |
| PROFIT_TO_CASH_BRIDGE | INSUFFICIENT_EVIDENCE | Contribution 0 observations and separately captured cash/working-capital stocks | No canonical matched profit-to-operating-cash reconciliation, qualified cash movement, non-cash/other working-capital/tax/capex/financing coverage. Cash position is not operating cash flow. Defer. |
| WORKING_CAPITAL_BRIDGE | PARTIALLY_QUALIFIED | Individual AR, inventory and AP stocks; some owning primitive results retain closing dates | No qualified paired opening/closing stock bundle, common accounting/restatement basis and coverage policy at the canonical boundary. Ledger and balance-sheet measures cannot be substituted or added together. Defer. |
| COST_TO_OUTPUT_BRIDGE | INSUFFICIENT_EVIDENCE | Earlier/later overhead spend by category; separate revenue/contribution measures | Overhead windows can differ in length, dates are omitted, lineage uses OVERHEAD_TRANSACTION/MULTIPLE, and no governed matching output proxy or normalisation exists. Defer. |

## Concrete repository evidence

- `profit_doctor/reasoning/canonical/contracts.py`: ReportingScope has one optional
  period_from/period_to pair and a mapping-governed period_basis. CanonicalFact
  validates that basis against its retained mapping. There are no per-slot periods
  or structured restatement/comparability assertions.
- `profit_doctor/reasoning/canonical/registry.py`: revenue mappings explicitly say
  Signal dates span both windows. Contribution 0 retains the captured diagnostic
  scope basis. Overhead mapping explicitly acknowledges unequal window lengths.
  Price/volume are mechanical; portfolio residual is not pure mix.
- `profit_doctor/diagnostic/engine.py`: _windows selects two preceding anniversary
  windows from the latest transaction date (exclusive start, inclusive end).
  REV-01 emits only the combined outer bounds; REV-02/03/04 and GM-01/02 do not
  emit the individual windows. REV-02 retains at most ten customer legs. SUP-04
  splits observed month labels at floor(count/2), so durations need not match.
- The same producer emits working-capital Signals with primitive-result ancestry
  but without copying primitive dates. `profit_doctor/calc/primitive_engine.py`
  retains some stock dates and source dataset references. This is useful retained
  evidence, not proof of a complete comparable pair or common accounting policy.
- `profit_doctor/reasoning/canonical/source.py` resolves ownership and hashes the
  Signal/execution/diagnostic-lineage snapshot. It does not qualify paired periods
  or snapshot every underlying source record. Graph AncestryReader resolves shared
  roots and missing ancestry, not reporting-basis equivalence or restatements.

The arithmetic can be reproduced in the legacy diagnostics. That does not itself
meet the stricter v2.48 canonical Bridge evidence contract. Reconstructing windows
from source rows could be valid under a new qualified resolver; silently splitting
an interval, parsing narrative, or declaring unknown accounting bases equivalent
would not be valid. Neither identical dates nor shared dataset ancestry proves all
the required semantics. A residual addresses unexplained movement, not invalid
opening/closing comparability.

## Original proposed continuation boundary

Approve an additive, versioned Bridge input qualification contract and read-only
owning-store resolver, without changing frozen diagnostic or canonical writers.
It should bind existing Fact IDs/digests and lineage to retained source versions,
verify the precise producer/window semantics and values, and preserve the source
snapshot used for qualification. It must establish separate window bounds,
boundary inclusivity, duration/calendar basis, entity, currency, exact measure,
coverage and explicit accounting/restatement policy. Unknown prerequisites must
produce a refusal, not caller-supplied assurances treated as system evidence.

First target revenue and Contribution 0 only if the available source records can
actually establish that contract. Do not infer missing coverage from absent rows.
Where accounting/restatement evidence is unavailable, additional governed input
is required and the bridge remains blocked. Calendar-year windows may differ in
days; an explicit comparability policy is required, not automatic normalisation.

Keep any derived Bridge input separate from a rewrite of historical Facts. Reuse
existing lineage, audit, Decimal serialization and effect references. A Bridge
needs an explicitly governed identity type; do not disguise it as a Story or an
Economic Impact. This requires an additive vocabulary decision before persistence.
No second permanent source of truth or legacy consumer cutover is proposed.

After this boundary is resolved, implement only qualified contracts, retaining
unexplained movement as residual. Qualify scope, precision, components, replay,
history and migrations before live PostgreSQL/full-estate execution.

## Downstream prerequisites and explicit limits

All three deferred v2.47 Stories remain blocked: LOW_QUALITY_GROWTH needs qualified
cross-metric revenue/margin comparability; PROFIT_TO_CASH_DISCONNECT needs actual
governed reconciliation; COST_GROWTH_OUTPACING_ECONOMIC_OUTPUT needs comparable
cost/output evidence. No new pricing/cost/mix mechanism evidence was created.

Future working-capital contracts must distinguish stock contribution signs
(AR + inventory - AP) from the cash effect of movement (-delta AR - delta
inventory + delta AP); this formula alone does not qualify missing balances,
other components or an operating-cash reconciliation.

At this initial checkpoint no Bridge, component calculation, tolerance policy,
schema, migration or tests were implemented. Existing ancestry and EconomicEffect structures can support
future component references, but that integration is not yet qualified. No
statement that v2.49 can consume these Bridges is possible: none exists. The
evidence-boundary gap blocks that dependency; no broad refactor has been shown
necessary. No v2.49+ functionality, database access, commit or push occurred.

At the initial checkpoint only this feasibility document was added. No production code, test assertions,
historical migrations, frozen reasoning semantics or qualification gates changed.
No new regression or live suite was run for this documentation-only stop.

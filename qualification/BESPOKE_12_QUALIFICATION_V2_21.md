# Profit Doctor v2.21 — Bespoke 12-Archetype Qualification

## Execution result
All 12 distinct archetypes executed end-to-end. Technical harness verdict: 12/12 PASS. The enhanced archetypes use bespoke transaction corpora rather than the shared Northstar corpus. High-risk safeguards (no unsupported inventory cash for non-inventory models, causal restraint, capacity-not-money, deliberate reconciliation mismatch detection) passed.

## Ground-truth sense check
Four planted truths were used in enhanced archetypes: customer concentration, H2 customer deterioration, supplier/product cost inflation with partial price recovery, and a genuinely new 2025 customer. A fifth applicability truth requires inventory refusal for services/subscription/project models.

The engine reliably exposed concentration and purchase-cost inflation/recovery. It detected the planted customer decline in several models but not all, because materiality/comparison mechanics can suppress the deterioration when the business model's transaction economics offset it. The new-customer truth was not surfaced as a dedicated growth/new-logo signal in the enhanced cases. This is a qualification weakness, not a reason to manufacture a finding.

## FD sense-check defects / limitations
1. **Working-capital period-basis issue (material):** L1 cases with monthly P&L rows and point-in-time balance-sheet AR/AP produced commercially implausible DSO/DPO values (hundreds of days). The likely cause is denominator-period mismatch: a monthly revenue/cost primitive is being combined with balance-sheet balances as though the denominator were annual/comparable. This must be remediated before v1.0.
2. **New-customer detection gap:** the planted 2025 new customer is economically present but is not surfaced by CUS-04/CUS-05 as a dedicated new-customer signal in these cases. Review test contract/comparison-window logic.
3. **Customer deterioration sensitivity:** subscription/project archetypes can fail to surface the deliberately weakened customer when aggregate/comparable revenue mechanics offset the planted decline. Review whether customer-level comparable windows and materiality are sufficiently sensitive without increasing false positives.
4. **Qualification data breadth:** bespoke transaction economics are now distinct by business model, but Level-3 CRM/forecast/operational source domains are still not genuinely populated end-to-end. Advanced-case qualification remains incomplete until those source domains are constructed and ingested.
5. **Finding volume:** enhanced cases generate 43–49 findings internally. This is acceptable only if the management-attention layer reliably collapses these to a small decision-relevant set for client presentation.

## Verdict
**CONDITIONAL PASS.** The engine successfully executed all 12 archetypes and preserved key economic safeguards, but the L1 working-capital period-basis defect is a v1.0 release blocker. New-customer/customer-deterioration detection and true Level-3 source-domain simulation are qualification remediation items.

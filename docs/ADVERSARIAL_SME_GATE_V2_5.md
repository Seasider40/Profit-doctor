# Profit Doctor v2.5 — Adversarial SME Data Gate

Date: 2026-09-24

## Objective
Attempt to make Profit Doctor accept or confidently interpret deliberately bad SME accounting evidence. The gate focuses on refusal, degradation, integrity propagation and client isolation rather than feature breadth.

## New adversarial cases
1. Missing required accounting column — refused at ingestion.
2. Malformed accounting date — refused at ingestion.
3. Duplicate AR invoice ID — refused and transaction rolled back.
4. Duplicate bank transaction ID — refused.
5. AR outstanding greater than original invoice — retained as evidence but integrity downgraded to USABLE_WITH_LIMITATION and dependent test becomes PARTIAL-B.
6. Unbalanced trial balance — integrity becomes MATERIALLY_CONSTRAINED.
7. AR subledger versus balance-sheet mismatch — cross-source reconciliation fails and both affected domains are constrained.
8. Bank closing balance versus balance-sheet cash mismatch — cross-source reconciliation fails.
9. Missing bank evidence — liquidity test is UNAVAILABLE rather than inferred.
10. Multi-client contamination attempt — integrity results remain client isolated.

## Result
10/10 dedicated adversarial tests passed.

## Important limitation
The pre-existing SQLite/resource-lifecycle defect remains. The isolated dedicated adversarial suite completes cleanly, but attempts to execute the entire historical regression estate in one long orchestration still stall around legacy economic-engine lifecycle behaviour. This is not treated as fixed and remains an engineering blocker before a production-ready v1.0 declaration.

## Gate conclusion
PASS for the tested adversarial trust/refusal behaviours. CONDITIONAL overall engineering status until the legacy single-process/resource-lifecycle problem is removed and a wider malformed-data corpus is added for D07-D18, forecast vintages, workforce, supplier and management-explanation contradictions.

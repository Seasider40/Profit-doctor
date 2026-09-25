# Controlled 12-SME Qualification Execution — v2.20

## Executive result
All 12 controlled cases executed through ingestion/trust, primitives, 56-test diagnostic registry, reasoning and economic engines. The technical harness checks passed 12/12 after correcting a fixture-period reconciliation error discovered on the first run. This is **not** equivalent to 12 real-SME validations.

## Sense-check verdict
**CONDITIONAL PASS for controlled-harness readiness. NOT YET PASS for business-model realism.**

The run exposed an important qualification-design limitation: Level-2/3 cases currently reuse the Northstar commercial transaction corpus. Therefore they prove graceful degradation, reconciliation, economic guardrails and business-model applicability rules, but they do not yet constitute genuinely bespoke payroll/utilisation/CRM/project/hospitality operational datasets. That gap must be closed before claiming the 12 archetypes are fully realistic.

## Case results
|Case|Model|State|Completed|Refused/N/A|Signals|Findings|Verdict|
|---|---|---:|---:|---:|---:|---:|---|
|SME-001|PRODUCT_DISTRIBUTION|L1_CORE|10|46|28|14|PASS|
|SME-002|PRODUCT_DISTRIBUTION|L2_ENHANCED|40|16|333|30|PASS|
|SME-003|PROFESSIONAL_SERVICES|L1_CORE|9|47|22|12|PASS|
|SME-004|PROFESSIONAL_SERVICES|L2_ENHANCED|37|19|330|28|PASS|
|SME-005|SUBSCRIPTION|L2_ENHANCED|37|19|330|28|PASS|
|SME-006|SUBSCRIPTION|L3_ADVANCED|37|19|330|28|PASS|
|SME-007|PROJECT_CONTRACT|L1_MESSY|9|47|22|12|PASS|
|SME-008|PROJECT_CONTRACT|L2_ENHANCED|37|19|330|28|PASS|
|SME-009|HOSPITALITY_TRANSACTIONAL|L1_CORE|10|46|28|14|PASS|
|SME-010|HOSPITALITY_TRANSACTIONAL|L2_ENHANCED|40|16|333|30|PASS|
|SME-011|HYBRID|L1_MESSY|10|46|30|16|PASS|
|SME-012|HYBRID|L3_ADVANCED|40|16|337|34|PASS|

## Deliberate adverse cases
SME-011 correctly surfaced the AR-to-balance-sheet mismatch and absence of bank evidence rather than silently repairing it. SME-012 correctly surfaced the bank-to-balance-sheet cash contradiction while preserving the source evidence. Professional-services, subscription and project cases did not manufacture inventory cash-release economics. Level-1 cases executed only 9–10 diagnostics and refused/degraded the rest rather than inventing Level-2/3 evidence.

## FD-level sense check
The economic guardrails behaved coherently: no causal “caused by” claims were found in signals; capacity was not converted into unsupported GBP savings; project billing volatility was not presented as proven underlying growth; and the controlled reconciliation checks behaved as designed. The reasoning layer can generate many stored findings (12–34 per case), but the management-attention budget remains capped at seven primary items. This distinction should be preserved in client UI.

## Defect found during execution
The first constructed run produced SALES_TO_PNL failures for every enhanced case. Investigation showed this was a qualification-fixture error: monthly 2026 P&L rows were being compared with a 2023–2025 transaction corpus. The fixture was corrected to use a comparable 2025 annual accounting control total. Rerun then reconciled all enhanced cases except the deliberately contradictory SME-012 cash test. This was a test-design defect, not an engine defect.

## Regression evidence
After the 12-case rerun, the Real-SME programme, adversarial SME, economic engine and management/benefit suites were run together: **32/32 PASS**.

## Release implication
Controlled qualification is useful and has passed its current harness gate, but the next controlled build should create genuinely distinct source packs for the archetypes rather than relabelling one commercial corpus. In particular, Professional Services needs workforce/utilisation evidence; Subscription needs recurring-contract/churn/CRM evidence; Project needs project/WIP/cost-to-complete evidence; Hospitality needs covers/transactions/labour evidence; and Advanced cases need actual forecast/CRM/pricing/operational contradictions. Only then should the 12-case programme be called fully constructed. Real anonymised SME evidence and live PostgreSQL remain separate release gates.
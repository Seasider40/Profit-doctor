# Profit Doctor v2.22 — Qualification Remediation

## Verdict
PASS for the controlled 12-archetype remediation gate. Live PostgreSQL and real-company validation remain open release gates.

## Remediations completed
1. Working-capital period basis: monthly P&L flows are aggregated on a YTD basis before DSO/DPO/DIO day calculations. This removes the prior month-denominator/year-day mismatch.
2. Period-basis audit: working-capital stock/flow ratios now use coherent P&L flow basis; incompatible P&L/BS periods still refuse. Existing margin/concentration/forecast ratios were reviewed; they use same-window flows/rates rather than the stock/flow pattern that caused the WC defect.
3. Customer acquisition: CUS-05 now emits a dedicated NEW_CUSTOMER_REVENUE signal, while explicitly describing it as an evidence-window classification rather than proof of legal relationship inception.
4. Customer deterioration qualification: subscription/project archetype fixture logic was corrected so unit=1 models actually express the planted deterioration. CUS-04 then detects it without lowering materiality thresholds.
5. Advanced evidence: L3 archetypes now contain independent budget, actual, forecast-vintage and KPI evidence. FCST-01..04 execute on those cases. This is genuine forecast/KPI L3 qualification evidence; full CRM/pipeline ingestion remains a future data-domain implementation gap and is not claimed as qualified.
6. Qualification fixture coherence: enhanced-case BS/bank periods and inventory balances were aligned to their accounting/commercial control period. This prevents fixture-generated false WC anomalies.

## Controlled execution evidence
All 12 archetypes executed end-to-end: 12 PASS / 0 FAIL.
Level-1 cases degrade to 9–10 completed diagnostics as expected. Enhanced cases execute 37–40. Advanced cases execute 42 and 44, including FCST diagnostics.

Working-capital sense check after remediation:
- ordinary cases: DSO ~42 days, DPO ~38 days;
- inventory businesses: DIO ~58 days;
- planted slower-collection case SME-002: DSO ~62 days;
- deliberately mismatched AR case SME-011: DSO ~83.5 days and remains an adverse case.
The prior 300–470 day artefacts no longer occur.

Customer truth checks:
- NEW_CUSTOMER_REVENUE is explicitly surfaced in every enhanced/advanced archetype;
- planted customer deterioration is surfaced by CUS-04 in all enhanced/advanced archetypes after correcting the unit=1 simulation defect.

Advanced truth checks:
- L3 SME-006 and SME-012 emit five forecasting signals across FCST-01..04 (FCST-02 emits two separate historical-error signals).
- Scenario outputs remain sensitivity ranges, not predictions/probabilities.

## Regression
58/58 targeted high-risk tests PASS with ResourceWarning promoted to error, covering the new period-basis regression, primitive engine, economic engine, management/benefit, adversarial SME gate, forecasting and risk/control diagnostics.

## Remaining gates
- Live PostgreSQL execution remains OPEN.
- Genuine CRM/pipeline/win-loss ingestion and qualification remain OPEN; v2.22 does not pretend forecast/KPI evidence qualifies D15.
- First 5 anonymised real SMEs + blind FD review remain OPEN.

# Profit Doctor v2.23 — Intelligent Data Intake Foundation

This build begins the unknown-workbook intake layer using UWB-001 and UWB-002 as qualification fixtures.

## Implemented
- Workbook profiling without trusting workbook narrative sheets.
- Header-row discovery for irregular SME sheets.
- Semantic sheet classification into canonical domains/context/control evidence.
- Formula/cached-value quality signals.
- Independent AR↔TB and AP↔TB recalculation from underlying rows.
- Total/subtotal exclusion to prevent double counting.
- Fail-closed reconciliation status using configurable tolerance.

## Qualification evidence
UWB-001: 7 sheets classified; independently recalculated AR↔TB gap £1,071,639 FAIL.
UWB-002: 9 sheets classified; independently recalculated AR↔TB gap £982,806 FAIL and AP↔TB gap -£279,000 FAIL.

The engine does not trust the workbook's embedded reconciliation formula as authoritative evidence.

## Test result
33/33 targeted tests PASS with ResourceWarning promoted to error, including 4 new unknown-workbook intake tests plus period-basis, economic, management/benefit and adversarial gates.

## Still to build
Column-level semantic mapping, units/period inference, generic reconciliation registry (inventory/debt/cash etc.), mapping confidence/human confirmation, canonical conversion for D04/D05/D11/D16, and direct handoff to diagnostic eligibility.

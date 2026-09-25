# Profit Doctor v2.35 — First Visual Prototype

## Purpose
First owner-facing rendering of the Profit Doctor product boundary using the v2.34 typed product view and Scenario 2 synthetic manufacturing data.

## Product principles represented
- Default view is a Business Health Check, not raw accounting software.
- Management Attention is compressed to 3–7 issues and is the primary decision surface.
- Profit & Cash Opportunity Register keeps profit and cash non-additive and leaves unsupported economics unquantified.
- Diagnostics and evidence are drill-down surfaces, not landing-page clutter.
- Control residuals are shown as exceptions, not losses or savings.
- Unavailable diagnostics remain visible.

## v2.35 qualification defect fixes
Visual qualification exposed two pre-existing intake/output defects and both were fixed before the prototype was accepted:
1. Broad TB matching classified Bank Loan as cash, Other Debtors as AR and tax payable as AP. TB balance extraction is now conservative and trade/control-account specific. Scenario 2 now correctly produces AR £3.45m, AP £1.71m and available cash £95k.
2. The management output KPI projection used legacy primitive aliases, so core financial KPIs were omitted. It now recognises FIN_REVENUE, FIN_GROSS_PROFIT, FIN_EBITDA and WC_* primitives.

## Prototype surfaces
- Overview: KPI strip, five management priorities, clickable priority detail.
- Opportunity Register: purpose, benefit type, economic state, expected value and recommended actions.
- Diagnostics: completed, partial and unavailable tests.
- Evidence & Controls: reconciliation failures and permanent decision guardrails.

## Scope boundary
This is a visual/product prototype, not production frontend architecture. Authentication, routing, API transport, persistence service deployment, accessibility certification, responsive device qualification and live PostgreSQL remain future gates.

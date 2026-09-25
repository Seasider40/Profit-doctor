# Sprint 2 — Level 1 Accounting Trust Extension

v0.4 extends the executable Trust Layer from transaction data into the Level 1 accounting evidence required by the core SME Health Check.

Implemented canonical contracts and ingestion for:
- D01 P&L / Management Accounts
- D02 Balance Sheet
- D03 Trial Balance
- D04 Accounts Receivable
- D05 Accounts Payable
- D06 Cash / Bank

Trust behaviour now includes domain-specific checks rather than applying sales-transaction rules universally. Trial balances must reconcile debits to credits; AR/AP abnormal outstanding balances are limitations; bank balance movement inconsistencies are retained as integrity limitations; malformed financial values fail atomically.

Eligibility consumes the persisted trust state. Missing required evidence produces UNAVAILABLE rather than invented analysis. Material integrity failure produces PARTIAL-C. Usable integrity limitations produce PARTIAL-B.

## Regression gate
19 automated tests pass: 9 foundation tests, 5 sales Trust Layer tests, and 5 Level 1 accounting/adversarial tests.

## Deliberate boundary
This does not yet claim cross-source accounting reconciliation (for example P&L revenue to TB revenue, balance sheet cash to bank, AR control account to aged receivables). Those reconciliations require account mapping/control-account configuration and are the next Trust Layer increment before Sprint 3 is treated as fully unlocked.

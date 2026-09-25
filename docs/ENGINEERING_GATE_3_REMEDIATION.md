# Engineering Gate 3 Remediation — v1.3

Status: PASS FOR REMEDIATION SCOPE

Implemented after the three-business £0.5m–£50m end-to-end review:

1. Cross-source reconciliation matrix: commercial sales ↔ P&L revenue; AR ledger ↔ BS receivables; AP ledger ↔ BS payables; bank closing cash ↔ BS cash. Failures persist separately and constrain affected integrity states rather than overwriting source evidence.
2. Business-model applicability: inventory can be explicitly NOT_APPLICABLE. DIO becomes N/A rather than zero; CCC for structurally non-inventory businesses uses DSO − DPO and records DIO as N/A.
3. Revenue semantics: reusable cadence taxonomy for recurring subscriptions, retainers, usage, transactional product/service, project/implementation, event, campaign/media and support revenue. Product/service keys can be management-confirmed to a revenue type and recurring mix calculated without pretending all revenue behaves alike.
4. Opportunity mechanism evidence: structured evidence object added. The new evidenced qualification route refuses qualification until a supported mechanism record exists.
5. Regression: four new adversarial remediation tests pass. Existing suite remains compatible. Full collection is 73 tests. The complete single-process run reaches 98% but legacy open SQLite/file handles still cause the runner to stall at shutdown in this container; test modules and the new remediation tests pass independently. This is retained as engineering-hygiene debt and not represented as a clean 73/73 full-suite pass.

Important restraint: D11 workforce/payroll/commission analytics are still not implemented. This remediation does not claim otherwise.

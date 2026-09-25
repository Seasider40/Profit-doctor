# Profit Doctor v2.3 — Financial Risk & Controls

Implements the final four locked diagnostics: RISK-01 through RISK-04.

Principles enforced: Profit Doctor is management decision support, not an audit opinion; anomaly != error/misconduct/fraud/loss; exposure != expected loss; no probability is invented; governance responses are proportionate and management retains the decision to mitigate, monitor or accept.

New evidence structures: control_evidence, control_exception, financial_exposure_evidence and governance_action_candidate.

Dedicated adversarial suite: 7/7 passing, including registry completeness (56 tests), audit-opinion restraint, anomaly/fraud restraint, exposure/expected-loss separation, proportionate governance, unavailable-data refusal and client isolation.

Known debt: legacy full-suite process/resource shutdown behaviour remains. An attempted whole-suite run timed out. Per-file execution confirmed several suites before the session timeout; economic-engine process still exhibited the known unclosed SQLite ResourceWarnings. Do not represent this as a clean whole-suite pass.

# Profit Doctor v2.26 — Evidence-Granularity-Aware Commercial Canonicalisation

## Purpose
Use genuine aggregate SME schedules without pretending they are transaction-level evidence.

## Added methods
- Annual customer summary -> CUS-01 concentration, CUS-02 Contribution 0 profitability, CUS-07 Pareto/distribution as PARTIAL-A.
- Annual supplier summary -> SUP-01 spend intelligence and SUP-03 spend-concentration dependency as PARTIAL-A.
- Work-centre capacity summary -> PEO-04 operational utilisation as PARTIAL-A when hour units are internally plausible.
- Implausible capacity evidence is refused rather than silently repaired.

## Deliberate refusals
Aggregate customer AR does not unlock CUS-06 invoice/payment behaviour. Annual summaries do not unlock retention/growth, item-level PPV, duplicate-payment tests, cost-to-serve, disruption probability, expected loss, or monetised savings.

## Qualification results
Scenario 1: 15/56 diagnostics completed (previously 12), 41 not run; 51 signals; 8 finding versions. Customer summary unlocked CUS-01/02/07. All 6 capacity rows were refused because the source hour units imply >250% utilisation and are internally implausible.

Scenario 2: 18/56 diagnostics completed (previously 12), 38 not run; 79 signals; 20 finding versions. Customer summary unlocked CUS-01/02/07; supplier summary unlocked SUP-01/03; capacity unlocked PEO-04. CUS-06 remains unavailable.

Tests: v2.26 + v2.25/v2.24/v2.23 intake tests 15/15 PASS. Period-basis + economic + management/benefit + adversarial regression 29/29 PASS. ResourceWarning promoted to error. Combined single-process command exceeded the 45-second execution window after 38 tests, so no claim is made that the complete monolithic suite passed in one process.

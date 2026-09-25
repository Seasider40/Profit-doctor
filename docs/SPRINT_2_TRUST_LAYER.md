# Sprint 2 — Trust Layer (v0.3)

Status: first executable Trust Layer complete for the Northstar vertical slice.

Implemented:
- explicit availability across D01–D18 (missing is UNAVAILABLE, never assumed)
- D07 sales transaction quality assessment
- customer/product row and economic mapping coverage
- internal gross-profit arithmetic reconciliation with explicit immaterial rounding tolerance
- financial-integrity state
- test-specific eligibility: FULL / PARTIAL-A / PARTIAL-B / PARTIAL-C / UNAVAILABLE
- economic coverage persisted separately from quality
- limitation text persisted for degraded tests
- seven initial test contracts: REV-01/02/03, GM-01/02, CUS-01/04

Adversarial regression cases prove clean Northstar is reliable/full; 12-month history degrades to PARTIAL-A; material mapping loss degrades customer diagnostics to PARTIAL-B; and a material arithmetic break degrades integrity-dependent tests to PARTIAL-C.

Scope boundary: this is the Trust Layer for the first Revenue / Gross Margin / Customer vertical slice. Domains without source evidence are explicitly UNAVAILABLE rather than fabricated. Domain-specific quality/reconciliation rules are added as their canonical datasets are introduced.

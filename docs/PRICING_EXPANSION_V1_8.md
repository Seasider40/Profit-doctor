# Profit Doctor v1.8 — Pricing Expansion

Implemented the locked Pricing tests PRI-01..PRI-05.

- PRI-01 Realised Price Movement: comparable customer-product realised unit-price movement and mechanical current-volume effect. No causal attribution.
- PRI-02 Price Dispersion: product-level dispersion across customer relationships. Legitimate commercial differences are explicitly possible.
- PRI-03 Discount/Rebate/Commercial Leakage: below-reference transaction signals only when D14 is absent. No unauthorised-discount, entitlement, recovery or opportunity claim.
- PRI-04 Price Increase Effectiveness: with transaction data alone, reports realised increase coverage only. Planned campaign effectiveness requires D14 pricing history/intended increases/commercial terms.
- PRI-05 Pricing Opportunity & Optimisation: synthesises investigation candidates but refuses addressable/expected opportunity until comparability, contract terms, relationship risk, volume response, mechanism and implementation constraints are evidenced.

The transaction reference in PRI-03 is a weighted realised product reference, not a list price or contractual benchmark. It therefore remains a signal, never a recovery entitlement.

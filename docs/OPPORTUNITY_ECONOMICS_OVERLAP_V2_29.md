# v2.29 Opportunity Economics & Overlap Qualification

This release hardens the Profit & Cash Opportunity Register economics. Supported opportunities retain the funnel **Theoretical → Addressable → Expected** and can be related as overlapping, alternative, mutually exclusive, dependent, sequential, synergistic, independent or cash-manifestation economics.

Portfolio reporting is deliberately separated into economic buckets. Recurring profit, one-off profit, one-off cash release, working-capital efficiency, avoided future cost, risk mitigation and capability/decision value are **not summed into a single headline £ number**.

Evidence-backed portfolio envelopes cap a group of opportunities sharing the same underlying recovery pool. This prevents price, mix and customer-margin interventions from each claiming the same economics. Cross-bucket overlap is refused; profit-to-cash links use CASH_MANIFESTATION and remain non-additive.

The existing guards remain: expected <= addressable <= theoretical where a theoretical ceiling exists, and both addressable and expected must remain within the supported recovery envelope. Reconciliation residuals, exposures and capacity observations do not become opportunities merely because they are numerically large.

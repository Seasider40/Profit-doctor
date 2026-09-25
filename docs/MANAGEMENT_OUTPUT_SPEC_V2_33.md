# Profit Doctor v2.33 — Management Output Specification

## Purpose
v2.33 freezes the first product-facing information hierarchy before UI development. The output layer is a projection of evidenced engine objects; it is not a new reasoning or economic layer.

## Owner/FD information hierarchy
1. **Executive Health Check** — concise business context, key evidenced KPIs, diagnostic coverage and control failures. There is deliberately no universal health score.
2. **Management Attention** — 3–7 evidence-clustered priorities with management question, rationale, confidence, next step and limitation.
3. **Profit & Cash Opportunity Register** — purpose, benefit type, availability, economic state, theoretical/addressable/expected amounts only where supported, evidence required and action. Profit and cash are never combined into one headline total.
4. **Performance Diagnostics** — completed, partial and unavailable tests, preserving graceful degradation across the 56-test estate.
5. **Recommended Actions** — action path, evidence required, owner role and state. An action is not proof of causality or benefit.
6. **Data & MI Maturity** — control/reconciliation evidence and diagnostic coverage. Data quality, integrity, coverage, confidence and MI maturity remain separate concepts.
7. **Benefit Progress** — realised, verified and retained benefit only when explicit longitudinal evidence exists. Opportunity values are never presented as realised benefit.
8. **Evidence & Limitations** — drill-down boundary for lineage, reconciliations and guardrails.

## Navigation model for v2.35+
The default owner view should expose the Health Check, 3–7 priorities and opportunity register first. Every priority can drill to diagnostics/evidence/actions. Technical objects (signals, evidence bundles, primitive IDs) remain available behind the drill-down, not on the landing page.

## Product language rules
- No universal score or red/amber/green vanity score.
- No causal language unless causal evidence supports it.
- Reconciliation residuals are control exceptions, not losses or opportunities.
- Exposure is not expected loss.
- Cash release is not profit.
- Capacity released is not a saving without demonstrated economic use.
- Theoretical, addressable, expected, realised, verified and retained are never collapsed into one number.
- FULL/PARTIAL/UNAVAILABLE/N/A remains visible in diagnostic drill-down.

## Stable contract
`profit_doctor.management.output_spec.build_management_output()` produces the first stable product view-model contract. v2.34 should expose this contract through typed API/view models rather than making the UI query engine tables directly.

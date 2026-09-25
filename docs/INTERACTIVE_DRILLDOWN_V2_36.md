# Profit Doctor v2.36 — Interactive Drill-Down

v2.36 adds a stable product drill-down contract between the owner-facing management view and the underlying diagnostic evidence.

## Navigation contract
Management priority → supporting signals → diagnostic/core question → recommended action → opportunity/economic state.

The UI does not query persistence tables. `get_priority_detail()` and `get_diagnostic_detail()` enforce run/client scope and return strict Pydantic models.

## Guardrails
- No arithmetic is performed in the drill-down layer.
- Unquantified opportunities remain unquantified.
- Control residuals remain control exceptions, not assumed losses.
- Cash release and profit remain non-additive.
- Unavailable diagnostics remain visible.
- Core Questions are exposed as the owner-friendly diagnostic explanation.

## Prototype
`prototype/v236/index.html` is the richer interactive Scenario 2 prototype. It provides executive, profit/cash, diagnostics, and controls views plus slide-in priority/diagnostic drill-downs.

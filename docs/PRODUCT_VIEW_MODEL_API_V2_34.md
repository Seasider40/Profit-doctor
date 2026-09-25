# Profit Doctor v2.34 — Product View Model / API Layer

## Purpose
v2.34 creates the typed boundary between the analytical engine and the visual product. The UI must consume `profit_doctor.api.service` rather than querying engine tables directly.

## Contract
`get_product_view()` validates v2.33 Management Output into strict Pydantic models. `get_product_view_json()` returns a JSON-safe payload for a future FastAPI/React surface.

Financial amounts intentionally remain decimal strings at this boundary, avoiding binary floating-point mutation. Unknown fields are rejected. Wrong-client access fails closed through the existing management-output tenant check.

## Product sections
Executive Health Check; Management Attention; Profit & Cash Opportunity Register; Performance Diagnostics; Recommended Actions; Data & MI Maturity; Benefit Progress; Evidence & Limitations.

## Guardrails retained
No universal health score. No profit+cash grand total. No opportunity-to-realised conversion. No hiding unavailable diagnostics. No new reasoning or economics in the API layer.

## v2.35 hand-off
The first visual prototype can now render a `PVM-2.34` JSON payload without knowledge of persistence tables, primitive objects, signals, or diagnostic internals.

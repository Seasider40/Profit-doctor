# Sprint 3 — Primitive Engine

Status: IN PROGRESS

## Governing rule
Calculate an economic fact once, under an explicit definition and method, preserve lineage, and reuse it everywhere. Missing evidence is never converted to zero and a convenient proxy is not silently substituted for a required economic fact.

## First executable slice
A persistent primitive registry, method registry, dependency graph and execution log are now implemented. Transaction primitives reproduce Northstar known answers exactly with Decimal arithmetic. Customer roll-ups reconcile to the total. Level 1 accounting primitives read only explicitly mapped statement lines. DSO is calculated only where revenue and AR are both evidenced. DPO currently refuses execution because an accounting direct-cost primitive is not yet available.

## Gate evidence
26/26 automated tests pass across foundation, Trust Layer and Primitive Engine. New tests cover registry/dependency seeding, Northstar totals, customer reconciliation, accounting P&L/BS primitives, DSO, missing-data semantics, DPO refusal and lineage.

## Next
Add FIN_DIRECT_COST / cost-of-sales mapping and reconciliation, AR/AP ledger balances and ageing primitives, available cash/liquidity, DPO/CCC, richer customer time-series primitives, period comparability and primitive-level trust gating.

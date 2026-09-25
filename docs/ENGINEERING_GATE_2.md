# Engineering Gate 2 — Primitive Engine Review

Status: PASS WITH CONTROLLED SCOPE

The first Primitive Engine slice was reviewed before Sprint 4. The governing boundary remains: primitives are reusable economic facts, not diagnostic conclusions.

## Review conclusions
- Registry/method/dependency separation is retained.
- Financial and commercial revenue remain distinct.
- Stock, flow and rate metadata remain explicit.
- Missing evidence does not become zero.
- DPO refuses revenue as a proxy for direct cost.
- CCC requires all three components: DSO + DIO - DPO.
- Period compatibility is enforced for closing-balance working-capital ratios.
- Operational inventory snapshots are preserved separately from accounting balance-sheet inventory and are used for DIO only when period-compatible.
- Available Cash remains distinct from Available Liquidity.
- Customer primitives remain reusable facts; no finding/opportunity logic has entered the primitive layer.

## Remediation completed during gate
A review identified that DSO/DPO could combine a latest P&L period with a different latest balance-sheet period. This was corrected: these ratios now refuse execution unless the period bases are compatible. An adversarial regression test locks the behaviour.

## Scope still intentionally deferred
Average-balance DSO/DPO/DIO, invoice-weighted collection/payment days, detailed inventory ageing/movement economics, facility headroom/Available Liquidity, multi-currency translation, and broader time-series primitive families remain future methods/primitives. Their absence does not justify proxy calculations.

Decision: the current primitive layer is sufficiently disciplined for the first diagnostic vertical slice, while Sprint 3 can continue expanding in parallel as new diagnostics require shared facts.

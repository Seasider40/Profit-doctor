# Sprint 3 Primitive Engine v0.6

Expanded deterministic primitive layer.

Added FIN_DIRECT_COST from mapped P&L cost-of-sales evidence; DPO now executes only when that evidence exists and still refuses revenue proxies. Added AR/AP ledger outstanding and overdue primitives, AVAILABLE_CASH with explicit bank-first evidence hierarchy, and explicit CCC refusal until inventory/DIO evidence exists.

Design restraint remains mandatory: cash is not liquidity; ledger balances are not silently treated as control-account balances; missing inventory is not estimated.

# Sprint 4 — First Diagnostic Engine

Status: **FIRST VERTICAL SLICE COMPLETE**

Implemented deterministic execution for REV-01, REV-02, REV-03, GM-01, GM-02, CUS-01, CUS-04, WC-01 and WC-02.

## Boundary
The Diagnostic Engine emits **Signals**, not Findings. It may calculate comparisons, bridges and deterministic materiality classifications, but it does not infer causes, create opportunities, or write FD conclusions. Those belong to the Reasoning/Economic layers.

## Northstar
The production engine now earns a first explicit scenario-level result: CUS-01 identifies Alpha as the largest current comparable-period customer, providing deterministic evidence for the S04 concentration/dependency scenario. This does not imply the remaining Northstar scenarios have passed.

## Restraint
WC-01/WC-02 emit no fabricated signals where the required primitives are unavailable. They consume existing valid primitive results only.

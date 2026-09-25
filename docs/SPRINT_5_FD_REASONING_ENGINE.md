# Sprint 5 — FD Reasoning Engine v0.9

Implemented the first controlled reasoning chain:

Signal → Context → Suppression → Persistence → Evidence Bundle → Fact → Interpretation → Finding Candidate → Finding → FD Review Queue.

## Guardrails
- Signals remain immutable evidence even when context suppresses escalation.
- Informational signals do not become findings by default.
- Management context can suppress/qualify interpretation but cannot rewrite deterministic facts.
- First-run comparable movement is EMERGING, not automatically persistent.
- Interpretations explicitly avoid unsupported causality.
- No opportunity value is created in Sprint 5.
- Every material finding enters the FD Review Queue before client presentation.
- AI is not yet required: v0.9 deliberately proves the structured reasoning contract deterministically first.

## Next
Before Sprint 6, deepen relationship clustering, contradictory evidence, longitudinal finding identity/versioning and management-attention budgeting.

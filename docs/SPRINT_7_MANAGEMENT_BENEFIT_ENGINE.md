# Sprint 7 — Management, Action & Benefit Engine

The engine now persists management decisions and actions against supported opportunities, tracks action progress, and records benefit events/legs only after action completion. A completed action is not itself a benefit.

Benefit legs preserve gross benefit, implementation cost, ongoing cost, adverse effect and net benefit separately. Attribution states are explicit: DIRECTLY_ATTRIBUTABLE, STRONGLY_SUPPORTED, PARTIALLY_ATTRIBUTABLE, UNCERTAIN and NOT_ATTRIBUTABLE. Verification and retention are separate lifecycle steps.

Anti-double-counting continues after implementation. CASH_MANIFESTATION prevents the same profit improvement and its later cash conversion being added twice; OVERLAPPING benefit legs can also be explicitly related.

The original opportunity funnel remains immutable evidence. Realised benefit may exceed or fall below expected value, but it does not silently rewrite the expected opportunity.

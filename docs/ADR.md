# Architecture Decision Records

- **ADR-001:** Start as a modular monolith, not microservices.
- **ADR-002:** PostgreSQL is the production database; SQLite is an executable local harness only.
- **ADR-003:** AI is isolated behind a controlled reasoning gateway and never owns deterministic financial calculations.
- **ADR-004:** Raw source evidence is immutable and content-addressed by SHA-256.
- **ADR-005:** Primitive calculations are deterministic, versioned, and reusable.
- **ADR-006:** Canonical primary keys are generated and client-safe; source identifiers are attributes/aliases, not global keys.
- **ADR-007:** Financial arithmetic uses fixed decimal semantics. Binary floating point must not own accounting £ values.
- **ADR-008:** Commercial transaction revenue and accounting revenue are separate primitives and must reconcile rather than be conflated.
- **ADR-009:** Financial ingestion never silently replaces canonical evidence. Restatements create new dataset versions.
- **ADR-010:** A sprint is not complete because the happy path runs; important failure modes require automated tests.

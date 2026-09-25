# v2.9 Economic Backbone Persistence Migration

## Scope
The production persistence strangler now includes PrimitiveResult, Signal, Finding, EconomicStory, EconomicImpact, EconomicExposure, OpportunityCandidate, Opportunity, Decision, Action and BenefitLeg. Existing diagnostic execution remains on the legacy adapter until vertical-by-vertical equivalence is proven.

## Financial invariants
Money is stored as canonical decimal strings during migration. This is intentional: persistence work must not change financial arithmetic or introduce binary floating-point differences. The legacy economic funnel and anti-double-counting rules remain authoritative.

## Tenant boundary
Foreign keys protect object existence. Because a simple FK does not prove that a valid run and valid story belong to the same client, migrated write services additionally validate run/client/story ownership. Cross-client write attempts are refused.

## Migration discipline
Alembic revision 0002 is reversible. SQLite is a deterministic local adapter only. Live PostgreSQL concurrency, isolation and migration testing remains a release gate because this build environment has no PostgreSQL server.

## Validation
The v2.9 persistence tests pass 3/3. A focused high-risk regression comprising v2.8 persistence, v2.9 persistence, Economic Engine, Management/Benefit, Adversarial SME and Risk/Controls passes 43/43. The repository currently contains 148 test definitions. Existing legacy sqlite ResourceWarnings may still occur in old diagnostic paths and are not represented as fixed by this migration.

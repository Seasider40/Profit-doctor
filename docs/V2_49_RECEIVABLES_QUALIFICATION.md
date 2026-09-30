# v2.49: governed receivables qualification

This additive extension starts from `c2b5ebee5a3ed13174e496916de82c9ae8818d8f`
on `main`. It enables one source-specific production-positive contract,
`OVERDUE_RECEIVABLES_1`, without changing diagnostic or Bridge calculations.
It implements no Opportunity, recoverability or v2.50 behaviour.

## Source and measurement ownership

`Snapshot`, `Invoice`, `Terms` and `StatusEvidence` are typed, versioned source
contracts. Original invoice amount is optional and remains unknown when absent.
Outstanding balance is never substituted for it. Each immutable invoice owner
has a Canonical Measurement Context: customer/invoice scope, GBP, outstanding
balance metric, reporting-date STOCK, coverage and retained file/dataset lineage.
CMC remains the context authority; BIQ and the existing Bridge formulas are unchanged.

The generic ingestion boundary accepts a CSV with one `snapshot` column and one
typed Snapshot JSON document. It is a normalized producer contract, not an
arbitrary spreadsheet/CSV inference engine. Existing source-file and dataset
registration retain the evidence. Producers must explicitly supply scope,
coverage, origin and structured authority; the service does not independently
authenticate commercial contracts or source declarations.

The registered `RECEIVABLES_WORKBOOK_1` adapter validates a declared layout for
Customer Terms, AR Detail and Evidence Context alongside the existing accounting
pack. Inventory Detail, Customer Contracts and Payment History are explicitly
registered but unconsumed as positive Impact providers. Unknown sheets,
conflicting claims and mismatched headers fail closed. Existing seven-sheet
packs remain supported with no extension. This layout is reusable but deliberately
strict; other layouts require an explicit producer adapter.

## Qualification policy

Explicit due dates are accepted without original amount or invoice date. Terms
use calendar days after invoice date, within their effective interval. When both
are supplied, the explicit and derived due dates must agree. Due on the reporting
date is within terms. Missing dates are not invented.

Status applies to the entire outstanding invoice balance. Only `NONE_RECORDED`
with a referenced SOURCE_RECORD reviewed at the snapshot date can qualify overdue
cash. Payment plans, disputes and pending credits are excluded. Unknown, stale,
unverified or management-asserted status cannot silently qualify. Exclusion does
not mean the balance is worthless or unrecoverable. Partial-invoice constraints,
alternative term conventions and currencies other than GBP are not implemented.

Within-terms balances are the current contractual position. The positive amount
is the exact sum of overdue balances without evidenced blocking statuses.
Complete coverage requires exact reconciliation to a retained AR control.
Partial evidence is never extrapolated; an evidenced total exceeding its control
is held. All populations, dates and the reconciliation difference remain available
in the retained snapshot. Decimal serialization and arithmetic preserve precision.
Confidence dimensions stay NOT_ASSESSED; cash materiality records the evidenced
amount without a universal score or collection forecast.

## Identity, history and overlap

Source snapshots are replay-safe and require an explicit predecessor for a
revision. Impact qualification retains its own revision, exclusions, source
snapshot, required position and audit. Canonical writes participate in the
caller's transaction. The existing legacy source registry commits ingestion
independently, so a canonical rollback may leave retained source evidence.

EconomicEffect identity is independent of run/story and includes origin, ledger,
date and qualifying invoice identities. A PARENT_CHILD relationship associates
the population with aggregate AR stock. Existing SAME_EFFECT deduplication and
unknown/partial-overlap blockers remain in force. Aggregate Bridge descriptions
are not qualified Impacts and cannot become additive value. No future aggregate
Impact contract or automatic Bridge-to-effect allocation is implied.

The original synthetic positive resolver remains isolated. Blind evidence uses
the production receivables contract with `BLIND_QUALIFICATION` origin; totals
require explicit selection of that origin and cannot mix it with real-source
totals. Source origin is an explicit trusted-producer declaration, not inferred
from company names. This proves a production-like path, not real customer cash.

## Blind evidence

The unchanged workbook checksum is
`eb3a5995a24d4fe06b6c1f27a070438c7e138b92b1da69ec62ef3cd4c0fc982b`.
No private answer key is used and tests derive the expected population from
invoice predicates, not a target amount.

Independent evidence totals: AR GBP 2,050,000; within terms GBP 1,570,000;
overdue GBP 480,000. Overdue exclusions are payment plans GBP 80,000, disputes
GBP 35,000 and pending credits GBP 25,000. The remaining 14 invoices total
GBP 340,000 and qualify as CASH_TRAPPED under this contract. This is explicitly
not an Opportunity, expected recovery or profit loss.

Inventory obsolescence/slow movement/safety stock lack qualified loss/excess
evidence; customer concentration lacks a loss scenario/probability. Revenue and
Contribution 0 changes and residuals remain Bridge evidence, not qualified
Impacts. The GBP 700,000 working-capital movement is not reclassified.

## Persistence and qualification

Forward migration `0012_receivables_snapshot` adds four tables: snapshot,
invoice owner, snapshot audit and scoped Impact-source edge. Historical migrations
are unchanged. `tests/fixtures/v249_schema.sql` preserves the 0011 schema.
Downgrade removes this new canonical population, its CMC and typed qualification
records/audits, while preserving legacy rows and existing foundation history.
It is a destructive rollback of new canonical records, not source-file deletion.

`test_receivables_v249.py` covers provider semantics, adversarial dates/statuses,
coverage, replay/revision, scope, source integrity, precision, caller rollback,
overlap, blind end-to-end qualification and negative populations.
`test_receivables_migrations_v249.py` covers clean creation, frozen-schema
preservation, downgrade/re-upgrade and migration independence from mutable models.
The authoritative estate registers both modules. Existing migration assertions
change only the expected head from 0011 to 0012.

`qualify_receivables_postgresql_v249.py` runs the new checks plus inherited
Impact/Bridge/foundation and unchanged v2.41 gates against the explicitly
authorized disposable branch, fail-fast without retries. It holds the Windows
awake request for the run and reports connection cleanup. Local result files
belong under ignored `.venv`, never in source control.

Local qualification on Windows / Python 3.12.14: 662 discovered and run,
653 PASS, 0 FAIL, 0 ERROR, 9 legitimate live PostgreSQL SKIPs; no warning/resource
policy errors. All 36 new tests passed. The focused compatibility rerun passed
77 checks, followed by two added checks passing. Compilation passed. Initial
development failures identified missing extension propagation into Bridge source
proof and two new migration-test harness issues (integer FK seeding and Windows
URL interpolation); these were corrected without weakening assertions.

The uninterrupted live gate passed on PostgreSQL 18.6: 144 discovered/run,
144 PASS, 0 FAIL, 0 ERROR, 0 SKIP. It covered the new receivables migration/provider
checks plus inherited Impact, Bridge, foundation and unchanged v2.41 checks.
Only the verified non-primary, non-default, unprotected `v2-41-qualification`
branch of project `tiny-meadow-46991842` was used. Final open connections: 0;
checked-out connections: 0; unraisable errors: 0. No retries or implementation
changes were needed during this final run. The Windows awake request was held
throughout and released afterward. Primary/default Neon was untouched.

The final source review found no credentials or unrelated artefacts. Logs and
JSON results remain ignored local files under `.venv`. Trailing whitespace was
removed from the new preserved SQL fixture after both runs; SQL tokens were
verified unchanged and its three migration tests were rerun. Historical
migrations, diagnostics, Signal calculations, original live gate and CI workflow
remain unchanged. Cross-platform CI and bulk-volume performance are not claimed
for this uncommitted extension.

## Changed-file inventory

| File | Purpose |
|---|---|
| `profit_doctor/reasoning/receivables/__init__.py` | New governed provider package |
| `profit_doctor/reasoning/receivables/contracts.py` | Snapshot, invoice, terms, status and population contracts |
| `profit_doctor/reasoning/receivables/service.py` | Source retention, owner validation, history, CMC and audit |
| `profit_doctor/intake/receivables.py` | Declared workbook evidence provider |
| `profit_doctor/intake/declared_accounting.py` | Explicit extension registration and validation |
| `profit_doctor/persistence/receivables_schema.py` | Four new canonical tables |
| `profit_doctor/persistence/__init__.py` | Register additive schema |
| `profit_doctor/reasoning/measurement/contracts.py` | Invoice stock owner vocabulary |
| `profit_doctor/reasoning/measurement/service.py` | Resolve and revalidate registered invoice owners |
| `profit_doctor/reasoning/bridge/engine.py` | Forward registered extensions during unchanged pack proof |
| `profit_doctor/reasoning/impact/contracts.py` | Typed source-specific amount/Impact and origin validation |
| `profit_doctor/reasoning/impact/registry.py` | Governed production receivables contract |
| `profit_doctor/reasoning/impact/receivables.py` | Qualification and aggregate AR overlap relation |
| `profit_doctor/reasoning/impact/service.py` | Scoped provider integration, source FK and origin-safe totals |
| `alembic/versions/0012_receivables_snapshot.py` | Forward schema and scoped downgrade |
| `tests/fixtures/v249_schema.sql` | Preserved 0011 schema |
| `tests/fixtures/impact_v249/Golden_Manufacturing_v2.49_Impact_Blind.xlsx` | Unchanged blind workbook |
| `tests/fixtures/impact_v249/README.md` | Fixture provenance and origin separation |
| `tests/test_receivables_v249.py` | 33 provider/persistence/adversarial/blind tests |
| `tests/test_receivables_migrations_v249.py` | Three migration tests |
| `tests/test_canonical_migrations_v244.py` | Expected head only |
| `tests/test_graph_migrations_v245.py` | Expected head only |
| `tests/test_hypothesis_migrations_v246.py` | Expected head only |
| `tests/test_story_migrations_v247.py` | Expected head only |
| `tests/test_measurement_context_migrations_v248.py` | Expected head only |
| `tests/test_economic_bridge_migrations_v248b.py` | Expected head only |
| `tests/test_economic_impact_migrations_v249.py` | Expected head only |
| `qualification/test_estate_v242.json` | Additive discovery registration |
| `scripts/qualify_receivables_postgresql_v249.py` | Disposable live runner with Windows awake ownership |
| `docs/V2_49_RECEIVABLES_QUALIFICATION.md` | Architecture, qualification, limitations and file inventory |

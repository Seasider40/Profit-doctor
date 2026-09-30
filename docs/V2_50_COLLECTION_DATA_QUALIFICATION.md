# v2.50 collection evidence ingestion and qualification data

## Authority and scope

This remediation adds ingestion, not a new capture method. The approved
`MATCHED_COLLECTION_OUTCOMES_1` engine and `CE-2.50.1` contracts remain unchanged.
The workbook's proposed balance-scaled cohort fractions are retained as source
context and are never executed. No Opportunity/addressability rule is relaxed.
No v2.51 functionality is introduced.

The machine-readable companion is
`qualification/matched_collection_outcomes_1.json`. Structural validation remains
the existing `CollectionEvidence` Pydantic model. Its `model_json_schema()` is
available to source-tool authors; this document does not introduce a second
validator or duplicate calculation engine.

## Registered adapter

`profit_doctor.intake.collection.CollectionWorkbook` is explicitly registered
alongside `ReceivablesWorkbook` in `inspect_pack` / `capture_pack`. Required core
accounting validation and exact sheet-catalogue checks are unchanged. Conflicting
providers, extra sheets/columns, duplicate keys, orphan rows, unknown consumed
vocabulary, mismatched entity/source/context, invalid dates and conflicting
receipts fail closed. There is no company name, invoice ID or target amount in
the production adapter.

Two layouts are supported:

1. `TABLES` (default): Collection Evidence, Collection Authority, Existing
   Recovery, Recovery History, Historical Receipts, Collection Method and
   Recovery Context. Headers are the exact published tuples in `intake/collection.py`,
   on row 4, with data from row 5. Empty initiative/history/receipt extracts are
   allowed but do not establish absence, zero outcomes or completeness.
2. `NORMALIZED`: one `Collection Document` sheet. A4 is `Collection document`;
   A5 is one existing `CE-2.50.1` JSON document. This supports source systems that
   supply explicit per-invoice initiative reviews and complete matched cohorts.
   It uses the same contract validation and frozen Opportunity service as CSV.
   No undeclared positive semantics are inferred from adjacent text.

For an accounting pack, select one collection layout. The exact allowed catalogue
is seven core accounting sheets, six receivables-provider sheets, and the chosen
collection sheet set. Arbitrary extra tabs are still rejected. A source tool can
also continue to submit the existing normalized `collection` CSV transport.

Tabular correspondence retains original evidence IDs, source/version/context,
customer/invoice IDs, facts, dates and promises. Source contacts remain source
records; management delegations remain `MANAGEMENT_ASSERTION`. A promise is not
received cash. Current acknowledged `MATCHING_CLEARED`/`REMITTANCE_IN_PROGRESS`
with valid ordinary authority maps to `ORDINARY_COLLECTION`;
`SERVICE_LIAISON_PENDING` with a current approved commercial mandate maps to
`COMMERCIAL_INTERVENTION`. An explicit internal acceleration hold maps to
`STRATEGIC_CONSTRAINT`. Unknown/expired/unverified authority stays `UNKNOWN`.
These mappings describe the documented collection posture, not recoverability.

Named recovery activity retains its original ID, start date, observation and
owner. Only `IN_PROGRESS` and `CUSTOMER_REMITTANCE_CONFIRMED` map to active
named initiatives in this layout; unknown status labels fail closed.
Missing rows never map to `NO_QUALIFYING_PRIOR_INITIATIVE_EVIDENCED`.
The tabular layout has no complete negative-review field, so it cannot assert
that stronger state. Normalized sources may supply an explicit complete review.

Historical receipt totals are independently reconciled from dated POSTED
receipts, using Decimal arithmetic. Only the exact recognized SUMIFS formula
shape (or matching literal total) is accepted. Historical terms, ageing, dates,
paired arms and paired scope are checked. Other authoritative formulas refuse.
The reporting-date-plus-horizon formula is independently checked too.

The tabular history layout identifies episodes, not the original historical
invoices, and contains no explicit per-current-invoice inception manifest.
Therefore these historical records are retained, not fabricated into
`HistoricalCase.invoice_id` or promoted into `MatchedPair` capture inputs.
They remain available for precise source-data remediation.

Capture retains the entire immutable workbook through the existing source-file
owner, then feeds one normalized CSV into `OpportunityService.ingest_evidence`.
Every mapped evidence reference retains its original locator/record/context and
adds the workbook file ID, SHA-256 and provider identity. The source-version
envelope also contains the root workbook reference, preserving lineage even for
unknown reviews without contacts. Unmapped history, coverage declarations and
method text remain in the retained original source. The canonical evidence
document retains the normal immutable dataset reference and existing replay
checks. No persistence schema, repository writer, transaction ownership or
historical migration is changed by this remediation.

## Exact qualification data

For **each current invoice**, provide the following. A mechanism-wide aggregate
or a customer class cannot substitute for the invoice-level contract.

| Field | Required evidence |
|---|---|
| Source identity | Current canonical `OVERDUE_RECEIVABLES_1` Impact, same client/run/origin; original customer and invoice IDs |
| Current amount | Exact outstanding GBP Decimal from that Impact, never an independently supplied Opportunity valuation |
| Terms and ageing | Governed contractual net days and days overdue at the current snapshot; missing terms refuse capture |
| Current intervention | `ORDINARY_COLLECTION` or `COMMERCIAL_INTERVENTION`, with dated authority; strategic holds remain exclusions |
| Assessment/horizon | Assessment equals source snapshot date; declared integral horizon 1–3660 days |
| Initiative review | Explicit review of the relevant invoice and existing recovery activity, complete and current at assessment date |
| Negative initiative finding | `NO_QUALIFYING_PRIOR_INITIATIVE_EVIDENCED`, complete=true, dated review, no initiative ID/start date |
| Positive prior initiative | `ALREADY_UNDERWAY`, original initiative ID, dated evidence and start before assessment; excluded from new value |
| Cohort denominator | `COMPLETE_INCEPTION_COHORT`, SOURCE_RECORD manifest, explicit comparability basis and eligible pair count exactly equal to all supplied pairs |
| Minimum sample | At least three distinct matched pairs for this current invoice's exact comparable population |
| Historical identities | Stable case IDs AND original invoice IDs for both arms; every customer/invoice key distinct within the cohort and different from the current invoice |
| Exact exposure | Both arms' opening exposures equal the current invoice's outstanding amount exactly; no scaling or monetary tolerance |
| Matching | Both arms same current customer, GBP, contractual terms, ageing band and horizon |
| Historical status | `ORDINARY_UNCONSTRAINED`; no fabricated status or missing status silently filled |
| Baseline arm | `BUSINESS_AS_USUAL`, observed posted cash in the complete historical window |
| Intervention arm | Same intervention class as the current review, observed posted cash in the complete historical window |
| Historical dates | Both arms same start/end; duration exactly horizon; closed before/on assessment; observation evidence dated after/on close and before/on assessment |
| Authority | Matching, cohort manifest and both outcome evidence records are `SOURCE_RECORD` with dated references |
| Receipts | Exact Decimal, nonnegative, no greater than opening exposure; promises never replace receipts |
| Completeness | No selected-success sample, no silent omissions; `cohort_exclusions=[]`; retain the source denominator and inclusion criteria |
| Lineage | Original file/dataset/version, source locators, current invoice, historic invoices/cases, pair mapping and source review references |

Age bands are 1–30, 31–60, 61–90 and over 90 days. Equality is by band, not exact
day. The two historical arms must share a window, but distinct pairs can have
different completed windows if each satisfies the same current horizon and
matching criteria. Three pairs is an eligibility floor, not a statistical claim.

Complete collection coverage means every qualified source invoice has a review.
Partial coverage is allowed, with missing evidence remaining unresolved. Extra
invoice/customer keys outside the qualified Impact are rejected, not silently
filtered. Source-tool authors must retain excluded or broader raw evidence in
the owning source and must not disguise selected outcomes as an inception cohort.

## Capture calculation, without scaling

For each eligible pair, let `d = intervention cash - baseline cash`, using exact
financial arithmetic. Any negative `d` makes the **whole current invoice cohort**
unqualified; it cannot be discarded to improve the answer. No receipt can exceed
its exact exposure.

- Low = minimum of all eligible `d` values.
- High = maximum of all eligible `d` values.
- Central is absent by default (`NOT_ASSESSED`). If explicitly requested as
  `EMPIRICAL_PAIR_MEAN`, it is the unweighted arithmetic mean of every pair's
  difference, only when exactly representable as a terminating Decimal.
- A nonterminating mean remains absent. No midpoint, rounding, confidence
  percentage, pooled receipt fraction or scaling is substituted.
- All-zero differences produce no positive Opportunity.
- Disjoint qualified current-invoice portions contribute their low/high values
  to the assessment. Total central exists only when every contributing portion
  has central. Unresolved or excluded portions are not extrapolated.

The range is an empirical prospective incremental CASH scenario envelope, not
a guaranteed recovery range, probability, causal estimate or confidence interval.
It is not profit, realised benefit, an instruction to pursue a debtor or a
substitute for the source Impact. Impact and Opportunity are not additive.

### Synthetic worked examples (not blind-workbook values)

Assume one £1,200 current invoice and three independently identified historical
pairs, each arm also £1,200, with all other matching/completeness conditions met.

| Pair | Baseline cash | Intervention cash | Difference |
|---|---:|---:|---:|
| 1 | £200 | £450 | £250 |
| 2 | £250 | £600 | £350 |
| 3 | £300 | £700 | £400 |

Low £250; high £400. With `EMPIRICAL_PAIR_MEAN`, central is absent because
£1,000 / 3 is nonterminating. With the same baselines and intervention cash of
£500, £650 and £800, differences are £300, £400 and £500: low £300, high £500,
central £400 when explicitly requested. The default central is still absent.

A historical opening exposure of £600 cannot be doubled to qualify either
example. A fourth outcome where baseline exceeds intervention cannot be omitted;
it blocks that invoice's capture. Missing prior-initiative review blocks
incrementality even when all historical matching is otherwise valid.

## Unchanged blind workbook assessment

Source SHA-256:
`953cfa1a58e6f8d4d8b2cb660f1e50c8c561ded5bd9c4a4b2e2e5e041dd9c49c`.
No source cell was edited. The initial read-only inspection found no answer-key
markers, hidden sheets/rows/columns, defined names, comments or external links.

Registered accounting, receivables and collection ingestion succeeds. The
unchanged source independently produces a £340,000 qualified receivables Impact.
The Opportunity assessment is **UNRESOLVED**, with no Opportunity ID, low, high
or central. Aggregation is EMPTY. This is not a claim of zero recoverable cash.

| Readable collection posture | Amount | Incrementality result |
|---|---:|---|
| Ordinary collection | £185,000 | £35,000 named prior activity; £150,000 incomplete initiative reviews |
| Commercial/service liaison | £70,000 | Incomplete initiative reviews |
| Strategic constraints | £55,000 | Excluded from new capture; not declared unrecoverable |
| Unknown current authority | £30,000 | Unresolved |

The frozen assessment partitions £340,000 into £90,000 excluded and £250,000
unresolved. Its established addressable amount is £0 because no remaining invoice
has the necessary complete negative initiative review. Readable collection
posture must not be misreported as established incremental addressability.
Only AR26-021 has named existing activity, dated before assessment. The other
13 invoice initiative states remain UNKNOWN; none receives a default NONE.

### Current populations and necessary matched data

Each row below needs its own complete matching evidence before any positive
capture can be considered. The table describes existing source facts, not targets
for altering the source or historic receipts.

| Invoice | Customer | GBP exposure | Terms days | Age band | Posture |
|---|---|---:|---:|---|---|
| AR26-021 | CUST-02 | 35,000 | 45 | 1–30 | Ordinary; prior initiative excluded |
| AR26-023 | CUST-06 | 40,000 | 30 | 1–30 | Commercial |
| AR26-024 | CUST-02 | 30,000 | 45 | 1–30 | Commercial |
| AR26-025 | CUST-07 | 25,000 | 45 | 1–30 | Ordinary |
| AR26-026 | CUST-04 | 20,000 | 60 | 1–30 | Ordinary |
| AR26-027 | CUST-08 | 30,000 | 60 | 1–30 | Unknown |
| AR26-030 | CUST-10 | 30,000 | 45 | 31–60 | Strategic constraint |
| AR26-031 | CUST-11 | 25,000 | 60 | 31–60 | Strategic constraint |
| AR26-032 | CUST-02 | 20,000 | 45 | 31–60 | Ordinary |
| AR26-033 | CUST-06 | 20,000 | 30 | 31–60 | Ordinary |
| AR26-035 | CUST-07 | 20,000 | 45 | 61–90 | Ordinary |
| AR26-036 | CUST-02 | 15,000 | 45 | 61–90 | Ordinary |
| AR26-037 | CUST-02 | 25,000 | 45 | over 90 | Ordinary |
| AR26-039 | CUST-10 | 5,000 | 45 | over 90 | Ordinary |

The declared current horizon is 90 days. Existing historical windows are also
90 days; currency and window duration are not the identified failures.

### Why all six historical cohorts fail

There are five pairs in each of OC-1, OC-2, OC-3, SL-1, SL-2 and SL-3:
30 pairs / 60 episodes in total. All opening exposures are £20,000.
All six lack original historical invoice identities, a complete inception
manifest and explicit per-current-invoice cohort membership. Episode IDs do not
prove unique historic invoices. The selected-history declaration cannot be
promoted to complete inception coverage.

Within each OC cohort, customer/terms/age profiles are CUST-02/45/15,
CUST-06/30/30, CUST-07/45/60, CUST-11/60/90 and CUST-10/45/150.
Within each SL cohort they are CUST-02/45/10, CUST-06/30/15,
CUST-07/45/20, CUST-11/60/30 and CUST-10/45/45.

- OC-1, OC-2 and OC-3 each have **zero** fully dimension-matching pairs for
  any current invoice. Non-£20,000 invoices fail exact exposure. Of the four
  £20,000 invoices, AR26-026 has no CUST-04 history; AR26-032 and AR26-033
  have the wrong historical ageing bands for their customers; AR26-035 also
  has the wrong ageing band. Other-customer pairs cannot fill the denominator.
- SL-1, SL-2 and SL-3 likewise each have **zero** fully dimension-matching
  pairs. The two current commercial invoices are £40,000 and £30,000, so all
  pairs fail exact exposure. Ordinary/strategically constrained/unknown
  invoices do not acquire commercial-intervention eligibility from SL history.
- The count of five pairs per cohort is not five eligible pairs for each
  invoice. Combining windows does not fix customer, amount or ageing mismatch.

The qualification script emits a per-invoice, per-cohort machine-readable
failure census to a caller-selected **local report**, including customer,
exposure, terms, ageing, intervention and window failure counts. This is an
eligibility report, not a second capture implementation.

## Dataset remediation required

1. Retain the original workbook unchanged as evidence of the blind attempt.
   Supply a separately versioned qualification dataset or companion source.
2. Provide explicit dated complete initiative reviews for each intended
   positive current invoice. Preserve the named prior activity and strategic
   holds as negative controls. Unknowns should remain unknown unless new actual
   review evidence resolves them.
3. Provide complete source-defined inception cohorts with at least three pairs
   per current invoice's exact customer/exposure/terms/age/intervention/horizon.
   Do not scale existing £20,000 episodes or replace actual values to fit a
   desired result. If no matching evidence exists, retain an unresolved outcome.
4. Supply original historical invoice IDs, case IDs, both arm assignments,
   dated matching reviews, denominators, inclusion basis and lineage. Preserve
   contradictory and zero outcomes. Do not select only successful episodes.
5. Represent the complete evidence using the already supported normalized
   `CE-2.50.1` transport (`collection` CSV or NORMALIZED workbook layout).
   Bind client/run/Impact IDs only after independently ingesting the source
   snapshot. Use Decimal strings. The provider replaces the pending dataset ID
   with the retained source dataset ID.
6. The proposed pooled/scaled method must not be used as acceptance authority.
   Expected blind answers must instead be derived independently from the frozen
   exact-exposure contract, including legitimate unavailable outcomes.

These requirements do not guarantee a positive result. A valid independent test
must be able to demonstrate correct refusal as well as qualified capture.

## Qualification and limitations

The adapter adds no migration or change to production persistence writers. Its
new retention route uses the existing immutable-file/normalized-document owners,
covered by generic SQLite persistence tests and the prior 189-PASS uninterrupted
PostgreSQL gate. No new live PostgreSQL run is claimed for this ingestion-only
remediation. The existing v2.41 gate and v2.42 CI/resource lifecycle are unchanged.

Final qualification:

| Gate | Discovered/run | PASS | FAIL | ERROR | SKIP |
|---|---:|---:|---:|---:|---:|
| Focused adapter, Opportunity, migration and compatibility | 86 | 86 | 0 | 0 | 0 |
| Unchanged blind workbook end-to-end local qualification | 1 | 1 | 0 | 0 | 0 |
| Authoritative full estate | 737 | 728 | 0 | 0 | 9 |

The 86 focused checks comprise 29 adapter, 43 existing Opportunity, three
Opportunity migration and 11 v2.42 compatibility/resource tests. The full estate
completed in 992.594 seconds with strict DeprecationWarning and ResourceWarning
handling and no policy/unraisable errors. The nine live PostgreSQL skips are not
passes. Compile checks and both independently exercised synthetic specification
examples passed. `git diff --check` and checks of the new untracked files passed.

An initial sandbox attempt could not access Windows temporary SQLite files;
the normal-host focused run passed. The first full run was deliberately stopped
when review identified an overly broad active-initiative status mapping in the
new adapter. The adapter now rejects unknown statuses, with an adversarial test.
The final complete full-estate run above covers that correction. No failed
product assertion was retried until green and no existing assertion was weakened.

Files added by this remediation:

| File | Purpose |
|---|---|
| profit_doctor/intake/collection.py | Registered tabular/normalized collection provider |
| tests/test_collection_workbook_v250.py | 29 generic and adversarial adapter/persistence checks |
| scripts/qualify_collection_workbook_v250.py | Isolated local workbook qualification and per-cohort failure census |
| qualification/matched_collection_outcomes_1.json | Machine-readable frozen-contract data/calculation specification |
| docs/V2_50_COLLECTION_DATA_QUALIFICATION.md | Human-readable specification, blind assessment and results |

Existing pending files updated here: `qualification/test_estate_v242.json`
(additive registration only) and `docs/V2_50_OPPORTUNITY_ENGINE.md` (record the
subsequent successful live run and link this remediation). The pre-existing
22-file v2.50 implementation remains pending; the complete intended working tree
now contains 27 modified/new files. Its engine, contracts, service, schema,
migration and original tests remain byte-for-byte unchanged by this remediation.

Local qualification JSON/logs and review utilities remain ignored under `.venv`.
They are not source fixtures. The blind workbook is not copied into the
repository. No commit, push, production data write or Neon change was performed.

**READY FOR DATASET REMEDIATION REVIEW** — not a positive blind Opportunity
qualification or a formal v2.50 release freeze.

# v2.54 — Governed Temporal & Recurrence Evidence

## Status and baseline

Architecturally approved release candidate; cross-platform CI is pending.
This is not yet a frozen release. Baseline:
`8057956ee57fce5add88887aa9ba93781a893f63`, `main` (frozen v2.53).
Final architectural review authorizes commit/push of the qualified change set.

## Approved evidence boundary

This is an additive, opt-in evidence layer. Existing diagnostic, Signal,
Fact/Finding, Graph, Interpretation, Story, Bridge, Impact, Opportunity,
Priority/Decision and attention consumers are unchanged.

Dataset Contract/Comparability remains the authority for the eleven dimensions.
Temporal evidence neither verifies a declaration nor makes row counts/totals
proof of population equivalence. Measurement Context retains ownership of the
measurement period; a broad Signal interval is not a metric reporting period.
Production providers cannot currently verify all temporal prerequisites.
Production results therefore remain `NOT_ASSESSED`, even if caller-supplied
documents claim verification. Positive evaluation is explicitly
`SYNTHETIC_QUALIFICATION` and cannot be persisted by the production service.

## Catalogue and feasibility

| Contract | Qualified synthetic capability | Production boundary |
| --- | --- | --- |
| CONTRIBUTION_0_MARGIN_TRAJECTORY | Complete monthly rate sequence, adjacent movement, trajectory, qualified directionality | Exact GM-01/CONTRIBUTION_MARGIN_CHANGE canonical Facts; metric period/population verification unavailable |
| REVENUE_DESCRIPTIVE_TRAJECTORY | Complete monthly revenue-flow sequence and descriptive trajectory | Exact REV-01/COMPARABLE_REVENUE_CHANGE canonical Facts; comparable metric-level reporting bases unavailable |
| CASH_TRAPPED_RECEIVABLES_LIFECYCLE | Month-end positive presence / explicit absence sequence, lifecycle | Production receivables Impact owner may establish positive presence; no qualified production temporal population/absence provider |

C0 is Contribution 0 margin, never relabelled gross profit. Revenue decrease is
descriptive and does not establish economic worsening. CASH_TRAPPED remains a
cash-stock condition, not profit loss, Opportunity, collection capture or
realised benefit. Its magnitude has no v2.54 directional/tolerance policy.

## Significance audit and tolerance policy

Frozen SIGNIFICANCE-2.44.1 creates a margin-movement Finding at absolute derived
change >= 1 percentage point. Revenue significance uses absolute movement >=
5% of absolute prior revenue, with a nonzero prior comparison. Neither Finding
policy proves monthly population comparability or a temporal trajectory.

The temporal numbers are reused only within separately governed, versioned
synthetic contracts, never by invoking the Finding significance operation:

* C0-ADJACENT-1PP-2.54.1: exact adjacent change in percentage points. Absolute
  change < 1 is within tolerance; equality and greater change are material.
* REVENUE-ADJACENT-5PCT-2.54.1: exact adjacent monetary change against 0.05 times
  the strictly positive prior monthly revenue. Below that threshold is within
  tolerance; equality and above are material. A zero/negative prior base has
  no qualified relative movement.

Revenue retains the monetary delta and monetary threshold; the relative-percent
basis identifies the denominator policy. No rounded percentage is invented.
Decimal arithmetic covers disparate exponents and serializes values losslessly.
There is no generic tolerance, score or confidence uplift.

## Four independent layers

`TemporalInput` retains origin, client, subject, explicit `Window`, observations,
source snapshots, revisions, lineage, Dataset Contracts and Measurement Context
binding identifiers. `TemporalResult` retains every included/excluded reference,
replacement, gap, dimensional comparison, policy version and reason.

1. Sequence: complete qualified requested monthly window, ordered observations.
   One observation may be sequenced with no movement/trend claim.
2. Movement/trajectory: two observations produce adjacent movement only. At least
   three are required for trajectory. Every adjacent movement is checked.
   Both material signs yield MIXED; only positive yields INCREASING; only
   negative yields DECREASING; all within tolerance yields STABLE. Flat
   intervals do not break direction. There is no first/last shortcut,
   majority vote, regression, acceleration or seasonality inference.
3. Lifecycle: presence/absence, independently of magnitude. Two consecutive
   PRESENT observations establish PERSISTENT. PRESENT / ABSENT_VERIFIED /
   PRESENT establishes RECURRENT. A current verified absence after prior
   presence establishes RESOLVED. UNKNOWN/gaps cannot establish recurrence
   or resolution. NEW means first presence in the requested qualified history,
   not never previously present anywhere.
4. Interpretation: only qualified C0 directionality maps increasing/decreasing
   to improving/worsening. Revenue interpretation stays NOT_ASSESSED.

Persistence with decreasing magnitude is explicitly tested. Independent fields
can represent persistent-and-improving under a future separately qualified
magnitude policy, but the current cash lifecycle contract does not manufacture
that interpretation.

## Presence, absence and scope

PRESENT requires a positive qualified CASH_TRAPPED Impact premise. Missing
Impact, NOT_APPLICABLE, zero amount and missing data remain UNKNOWN.
AR-ABSENCE-2.54.1 requires explicit complete-population verification, reconciled
control, complete contractual/status review, no unresolved classifications,
verified condition absence, exact client/scope/as-of/currency/population and
retained evidence ancestry. Only synthetic absence evidence exists in v2.54.
Absence of a record is never proof of condition absence.

Production `TemporalService` resolves sources through the canonical, dataset,
Measurement Context and Impact owning services. Fact IDs must belong to the
exact assessed Finding; CASH_TRAPPED history must contain its assessed Impact.
Foreign-client/run references and changed source digests are rejected. Only
REAL_SOURCE production receivables qualify as production premises; blind or
synthetic sources do not become production claims. A production candidate
without qualified Impact stays UNKNOWN, never ABSENT_VERIFIED.

## Window, cadence and restatements

Window start/end are explicit and identity-bearing. Only full calendar-month
windows are qualified. Quarterly/annual/unknown cadence vocabulary is retained
but unqualified. C0/revenue require full monthly RATE/FLOW periods respectively;
cash requires month-end POINT_IN_TIME STOCK. Unknown/partial metric periods,
missing months and incomparable populations are refused with retained reasons.
Out-of-window observations are retained as exclusions, not silently cherry-picked.

Duplicate periods are not additional time. A source-verified linear same-period
restatement/correction/supersession chain can select its single authoritative
tip, retain earlier snapshots/exclusions, and count one observation. Missing
predecessors, competing tips and incompatible replacements fail closed. All
other comparison dimensions must MATCH; only the proven replacement's revision
relationship can have the frozen comparability LIMITED_MATCH state.
Pure recipe comparisons use a fixed assessment timestamp for deterministic
replay; persisted assessment/audit creation timestamps remain actual timestamps.

## Persistence and migration

Repository Contract serialization, scoped identifiers/FKs, Decimal, ISO timestamp
strings and caller-owned SQLAlchemy sessions are reused. No new framework.

`0016_temporal_evidence` (22 characters, within Alembic VARCHAR(32)) adds:

* canonical_temporal_assessment: immutable indexed document, series/revision
  uniqueness, subject/client FK, run FK, scoped predecessor FK.
* canonical_temporal_audit: immutable assessment/client FK and audit document.

The service appends one assessment/audit transactionally with a nested
savepoint; it neither commits nor owns/disposes the caller session. Exact replay
returns the previous record. Changed evidence requires an explicit predecessor
revision. Historical documents remain readable; current reads revalidate owners
and evidence. Raw database mutation is not offered as an application operation.

Frozen v2.53 fixture is generated from migration 0015, includes all 56 tables
(including alembic_version), 410 columns, 131 FK constraints / 194 FK elements,
28 unique constraints, 15 indexes, and no business rows. The existing generic two-phase
preserved-fixture loader reconstructs PostgreSQL-compatible dependencies.
Upgrade tests seed every legacy application table and verify exact row
preservation. Downgrade intentionally removes v2.54 assessments/audits only;
upgrade restores empty new tables. Historical migrations are untouched.

Existing current-head migration expectations advance to 0016 only. The inherited
v2.43 historical migration assertion remains frozen at 0004; the cumulative
runner continues to isolate it at 0004 and restore current head afterwards.

## Qualification

New focused modules: temporal contracts (34), service (12), migrations (3),
offline cumulative runner (4). Strict DeprecationWarning/ResourceWarning applies.
Final focused qualification: 53 run, 53 passed, zero failures/errors/skips.
The initial new runner-tail assertion was corrected to retain the entire
inherited readiness/v2.41 module tail, including its final static check.

The v2.54 live runner reuses the approved v2.53 safety and checkpoint machinery.
It preserves all 472 inherited checks exactly once, adds 48 temporal checks,
and keeps readiness/v2.41 resource/isolation checks last: 520 total. No retry,
segmentation, credential disclosure or safety bypass. Exact project/branch,
non-primary/non-default READY branch and enabled direct endpoint ownership must
be API-verified before any connection/reset.

Final uninterrupted cumulative live qualification: 520 discovered/run, 520 PASS,
0 FAIL, 0 ERROR, 0 SKIP on PostgreSQL 18.6. The dedicated disposable
v2-41-qualification branch was independently verified as primary=false,
default=false with direct endpoint ownership verified before database access.
Cleanup confirmed 0 open connections, 0 checked-out connections and 0 unraisable
resource errors. Primary/default was untouched. No retry or segmentation was used.

Final authoritative local qualification (Python 3.12.14): 904 discovered/run,
895 PASS, 0 FAIL, 0 ERROR, 9 legitimate live-only SKIP; no policy errors or
unraisable resource errors. Inventory agrees across all 89 test modules.
DeprecationWarning/ResourceWarning are errors under the unchanged full-estate
policy. Source/tests/scripts/migrations compile successfully. The complete run
took 1296.906 seconds. No implementation inputs changed during qualification.
`git diff --check` passes; local qualification logs, reports and hash records
remain ignored under `.venv`, outside the intended change set.

## Explicit non-goals and limitations

No production comparability/absence verification extension, downstream consumer
cutover, Priority reassessment, urgency, controllability, relative-materiality
uplift, recommendation, Action, Benefit Realisation, forecast, acceleration,
seasonality, anomaly detection, causal inference, AI narrative or temporal UI.
No diagnostic 57+, v2.55+ functionality or Golden Manufacturing v2.54 dataset.
Later providers require independent evidence qualification before any positive
production temporal capability is enabled. The governed representation and
immutable history are designed to support that extension without a second
source of authority.

## Architectural acceptance answers

1. Comparable observations can be sequenced without a trend: one observation
   qualifies the sequence only, within its explicit complete window.
2. Two observations can show movement without a multi-period trajectory.
3. A condition can persist with decreasing magnitude. Persistent-and-improving
   is structurally representable, but current cash interpretation is deliberately
   NOT_ASSESSED until a separate magnitude policy is qualified.
4. Explicit verified absence can establish resolution; missing data cannot.
   Positive absence qualification is synthetic-only in this release.
5. Recurrence requires the verified absence gap; repeated uninterrupted presence
   is persistence. UNKNOWN is neither proof of absence nor recurrence.
6. Proven same-period replacements revise one observation, without new time.
7. Revenue DECREASING retains NOT_ASSESSED economic interpretation.
8. Contribution 0 WORSENING requires the exact qualified definition,
   comparability, monthly cadence, tolerance and directional contract.
9. Production remains NOT_ASSESSED when verification is unavailable; synthetic
   positive premises cannot bypass that boundary.
10. Future consumers can use separate sequence/lifecycle/trajectory/interpretation
    fields and immutable lineage/history. Enabling production positives still
    requires separately qualified providers; no downstream integration is claimed.

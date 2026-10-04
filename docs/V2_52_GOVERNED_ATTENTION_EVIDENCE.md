# Profit Doctor v2.52 — Governed Attention Evidence

## Baseline and scope decisions

Frozen v2.51: `304a16cc628a418ce864da706ec15ffaf9ee6849`, branch `main`.
This release is opt-in and does not switch existing runtime/report consumers.
The approved final scope permits evidence-strength qualification and explicit
temporal refusal. Positive production temporal classification is deferred.

## Production capability

`AttentionPriorityService` extends the existing Priority persistence/decision
service. It accepts owning canonical services, never caller-supplied dimension
values, evidence lists or an Interpretation payload. It finds the scoped
`INDEPENDENT_CORROBORATION` Hypothesis and consumes its already-assessed,
immutable Interpretation. It never generates or reassesses hypotheses.

Policy `ATTENTION-EVIDENCE-2.52.1` means:

- STRONG: the existing EVIDENCE_QUALITY independent exact-reproduction contract
  is SUPPORTED after its mandatory disconfirmation checks, without blocking gaps.
- CONFLICTED: qualified counter-evidence or a retained unresolved challenge.
  Both supporting and opposing paths remain in the Interpretation snapshot.
- NOT_ASSESSED: absent, unassessed, stale, shared-only, incomplete or otherwise
  unqualified independent corroboration. This does not label valid facts false.

STRONG is explicitly proposition-scoped corroboration, not a universal assurance
rating. It establishes neither complete population coverage nor accounting
reconciliation, causality, economic-mechanism support or higher confidence.
Shared ancestry never gains weight from the number of downstream objects.
Provenance independence does not exclude undocumented copying.

The provider reuses the owning Hypothesis service's read-only evidence search,
including unlinked same-run Facts, declared counter-evidence, source currentness,
ancestry and alternatives. Changes invalidate current corroboration until an
explicit owning-service reassessment. The provider depends on that internal
search interface; a future change to it requires attention regression review.

Opportunity valuation and eligibility remain owned by OpportunityService. No
Opportunity evidence-strength contract is introduced. An unqualified candidate
is still refused; a qualified range retains its exact Decimal values and horizon.

## Still intentionally unassessed

`TEMPORAL-REFUSAL-2.52.1` always returns NOT_ASSESSED for current production
sources. Its reason identifies missing commercial population coverage,
per-measurement context and revision comparability. Multiple runs, changing
dataset versions, repeated signals, known broad intervals and declining values
do not establish RECURRING, WORSENING, INTERMITTENT, ISOLATED, HISTORICAL_ONLY or
STRUCTURAL. No positive temporal framework claim is made in this release.

Urgency, controllability and relative materiality remain NOT_ASSESSED.
Cash stock and overdue balances do not establish liquidity urgency; capture
horizon is not a consequence deadline. Collection authority/addressability is
not general management control. Monetary amounts are not relative materiality.
Consequently STRONG corroboration can correctly coexist with overall
INSUFFICIENT_EVIDENCE under the unchanged ATTENTION-2.51.1 evaluator.

## Measurement Context decision

The partial REV-01 provider is deferred entirely, as permitted by the final
scope decision. No new context authority, backfill or propagation rule is added.
The existing calculation retains two separate rolling sales windows; combined
Signal dates span both and are not substituted into either measurement slot.
Known context already retained by the Measurement Context authority remains
unchanged; missing Fact-slot dates, coverage and restatement basis remain unknown.
Accounting revenue context is not commercial revenue, margin or customer share.

Inspection found that sales trust completeness concerns populated fields in
supplied rows, and mapping coverage concerns those same rows. These measures do
not establish a stable commercial population across extracts. Dataset versions
identify snapshots but do not establish their economic revision relationship.

## History, persistence and backward compatibility

No schema change or migration is needed. Head remains `0014_priority_decision`.
Existing assessment text-JSON stores a versioned attention envelope alongside
the original source snapshot, including exact Interpretation revision, complete
evidence snapshot, lineage, gaps, checks and limitations. Existing assessment
revision uniqueness, scope FKs, audits and caller-owned transactions are reused.

Historical reads validate the exact persisted Interpretation revision and its
digest/scope/source snapshot. They do not demand that historical evidence remain
current. Current reads re-resolve the provider. Changed evidence requires the
existing explicit predecessor revision and appends history; it never rewrites
an adviser decision. Replay preserves original identity and timestamps.

The sole frozen-service adjustment extracts its existing production dimension
check into an overridable validation method. The default PriorityService keeps
its original refusal rules, including rejecting STRONG provider-derived records.
Consumers must explicitly use AttentionPriorityService to read the new records.
The new service can read old v2.51 history. This opt-in compatibility boundary
must be respected by callers; it is not a silent downstream cutover.

No diagnostic, Signal, Fact, Hypothesis, Graph, Story, Bridge, Impact, Opportunity,
Measurement Context, Priority evaluator, adviser authority or historical migration
is changed. No existing test assertion is modified.

## Deferred source-evidence architecture

Commercial dataset comparability needs a separately designed source contract:
population identity; selection/exclusion basis; coverage state and covered period;
commercial definition/version; exact dataset/file identity; revision relationship
and affected periods; declaration authority/provenance; and resolution of conflicts
between declarations and observed data. None is inferred or implemented here.
This prerequisite affects trends, comparisons, recurrence, improvement/worsening,
benchmarking, longitudinal monitoring and future reporting/investigation.

Positive urgency separately needs a scoped, authoritative, current, dated
consequence with lineage and limitations; liquidity urgency additionally needs
qualified cash-flow/headroom evidence. Controllability needs governed rights,
authority, feasibility and constraints. Relative materiality needs matching
business denominators and a versioned policy. These are deferred streams.

## Qualification and limitations

New tests exercise real owning canonical/Hypothesis/Priority service boundaries
using repository-safe retained-source fixtures. They do not inject a positive
assessment directly into persistence or claim a production customer deployment.
The approved Golden workbook is unchanged: its Impact remains £340,000; absent
qualified collection evidence still prevents an Opportunity/attention bypass.

The live runner preserves the disposable branch/direct-host checks, clean reset,
fail-fast/no-retry execution, Windows awake guard and connection/unraisable counts
of the existing qualification runner. It adds attention tests to the inherited
216-check gate. No primary/default Neon branch may be used.

Focused strict DeprecationWarning/ResourceWarning qualification: **26 discovered/run,
26 PASS, 0 FAIL, 0 ERROR, 0 SKIP**. The authoritative full estate on Windows /
Python 3.12.14: **806 discovered/run, 797 PASS, 0 FAIL, 0 ERROR, 9 SKIP** in
1186.5 seconds. The nine skips are the existing live PostgreSQL checks without
a test URL; they are not passes. No expected failures, unexpected successes or
warning/resource policy errors occurred. Source, tests, scripts and migrations
compile successfully. Alembic remains at `0014_priority_decision`; no migration
was needed because v2.52 stores its versioned evidence snapshot in the existing
immutable Priority assessment record.

The uninterrupted live PostgreSQL qualification passed on PostgreSQL **18.6**
against the independently verified disposable Neon project
`tiny-meadow-46991842`, branch `v2-41-qualification`
(`br-royal-math-za046ex1`). It collected and ran **242 checks: 242 PASS, 0 FAIL,
0 ERROR, 0 SKIP**. The target was verified as READY, with `primary=False` and
`default=False`, and the direct endpoint host was verified to belong to that
project and branch. The primary/default branch was untouched. Final cleanup
reported **0 open connections, 0 checked-out connections and 0 unraisable
resource errors**. The qualification used the established uninterrupted,
fail-fast runner with inherited v2.41 and v2.43–v2.51 checks; no retries or
segments were used. The report and connection credentials remain local and are
not included in this change.

Final `git diff --check`, credential scan and whitespace scan passed. The eight
intended changed files are the opt-in attention package, Priority validation
hook, estate registration, focused tests, live qualification script and this
document. Historical migrations, diagnostics, Facts, frozen reasoning layers,
Priority classification rules and adviser-decision behaviour are unchanged.

No AI, recommendation, report generation, publication, action, benefit tracking,
autonomous advice or later-release functionality is implemented.

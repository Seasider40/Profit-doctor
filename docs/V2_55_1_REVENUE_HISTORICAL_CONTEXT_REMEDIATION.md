# v2.55.1 — Revenue Historical Context Remediation

Baseline: clean `main` / local `origin/main` at
`7d86d4c3ae9d82f3dd1585d239c62bd4e5d54e47`. Frozen qualification was
1,278 local checks (1,269 PASS, nine legitimate live skips), 732 live PASS
and four CI matrix jobs PASS. Those are completed baseline results, not reruns.

## Defect and ownership contract

Realistic finance-pack qualification exposed a legitimate same-period Revenue
restatement failing during historical temporal traversal. The temporal service
deliberately reads retained predecessors and requalifies their source evidence.
However, its context-binding lookup silently called a current-only monthly
owner resolver. That correctly rejected the superseded owner with
`RevisionConflict('Superseded evidence is historical, not current')`.

The defect was inconsistent read intent, not incorrect Revenue, reconciliation,
revision authority, Dataset Contract or temporal arithmetic. No private workbook,
answer key or grading material is imported by this remediation.

## Smallest service correction

Measurement Context `lookup` and `resolve_binding` accept explicit keyword-only
`current`, defaulting to `True`. It propagates through `_owner` to registered
monthly/margin providers. Those provider owner APIs retain current-only defaults.
Historical binding access is limited to these separately owned monthly resources;
it does not turn other legacy/Fact/receivable lookups historical.

Production temporal Revenue and margin traversal passes `current=not historical`
at binding lookup. Its existing historical source requalification remains.
No latest check, predecessor traversal, source verification, digest, scope or
revision guard was removed. Historical access reads the pinned owner/context
without changing its current state or creating a new economic period.

The same concrete context-binding mismatch existed in historical C0 margin
traversal and is corrected through the same explicit contract. No arithmetic,
threshold, cadence, window, gap, minimum observation or lifecycle code changes.

## Broader historical-owner audit

| Path | Outcome |
| --- | --- |
| Monthly Revenue | Historical owner was followed by current-only binding lookup; corrected. |
| Monthly monetary C0 | Provider owner API now supports explicit history; monetary C0 still cannot enter rate temporal policy. |
| C0 component binding | Historical requalification already uses retained component/proof predecessors; no separate correction. |
| C0 margin | Same binding mismatch as Revenue; corrected and regression covered. |
| AR projection / absence | Explicit historical owner semantics already propagated; no Measurement Context traversal. Unchanged. |
| UNKNOWN | Historical receipts remain historical; current refusal revalidation remains current. Unchanged. |
| Production assessment | Historical reads retain snapshots; current replay deliberately traverses valid predecessors through the corrected monthly route. |
| Evidence Readiness | Historical reads retain snapshots; current evidence checks intentionally require current owners. Unchanged. |

## Regression coverage and qualification

Eleven registered synthetic-source regression tests cover current and historical
context resolution, preservation of current-only refusal, six economic periods
with a same-period restatement, authoritative current value and retained original,
multiple revisions, frozen thresholds/directionality, durable assessments,
idempotent replay, retained prior assessments, cross-client refusal, unresolved
revision refusal, arbitrary stale requests and historical C0 margin contexts.
Test values are independent synthetic amounts, not private finance-pack answers.

Local qualification on Windows / Python 3.12.14 completed on 7 October 2026:

- Focused compatibility: all 278 existing tests passed. The initial combined
  run reported 288 PASS / one ERROR in a newly written test expectation; after
  correcting that test against the frozen result/refusal contract, all eleven
  new regressions passed with strict warnings. No production correction was
  required for those test-writing errors.
- Authoritative estate: 1,289 discovered/run, 1,280 PASS, zero FAIL, zero ERROR,
  nine legitimate live-only SKIPs; 105/105 modules match the inventory.
- Strict deprecation/resource warnings passed; no unraisable-resource or other
  policy errors. The full run completed in 1,845.937 seconds.
- Source/tests/scripts/migrations compilation and `git diff --check` passed.

No existing assertions are changed. Local results/logs remain ignored under
`.venv`; they are not intended repository changes.

## Live qualification impact and migrations

The changed lookup path is exercised by the existing production temporal,
assessment, ownership and component suites. Renewed live qualification was required.
The same eleven regressions are added to the cumulative runner before the retained
final v2.41 gate: 732 inherited checks plus eleven = 743 checks. Static discovery
confirmed 743 unique IDs, zero duplicates, all 732 inherited IDs retained and
the final nine-check resource/isolation gate unchanged. Offline runner refusal
tests passed.

The subsequently executed cumulative live qualification was approved on
8 October 2026: 743 collected/run, 743 PASS, zero FAIL, zero ERROR, zero SKIP,
PostgreSQL 18.6. The independently verified disposable `v2-41-qualification`
branch reported primary=false and default=false. Final resource accounting:
zero open connections, zero checked-out connections and no unraisable errors.

No schema change is needed. Migration head remains `0019_production_history`;
all migrations 0001–0019 and preserved fixtures remain unchanged.

## Separate AR oracle finding

The finance-pack AR expectation discrepancy is an oracle defect, not a product
defect. UNKNOWN without a qualified Dataset Contract is refused at admission
with sequence/lifecycle NOT_ASSESSED before lifecycle evaluation. No AR admission,
UNKNOWN, Dataset Contract or lifecycle semantics are changed to match an oracle.

Final commit/push is authorised after staged review. Formal freeze remains
pending all four Full Estate CI matrix jobs passing. No v2.56 work is included.
